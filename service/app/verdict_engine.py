from app.config import Settings, get_settings
from app.evidence_graph import EvidenceGraphBuilder
from app.exceptions import InvalidModelOutputError
from app.graphtrust_scorer import GraphTrustScorer
from app.llm_client import LlamaClient
from app.multi_agent import MultiAgentReasoner
from app.neo4j_repository import Neo4jGraphRepository
from app.models import ClaimEvidence, ClaimVerdict, VerificationResponse, VerdictLabel


SYSTEM_PROMPT = """You are a careful fact-checking analyst.
Use only the supplied evidence. Return strict JSON only.
If evidence is insufficient, use verdict "unverifiable".
Do not cite a source unless its URL appears in the evidence list.
For true, false, or misleading verdicts, reasoning must reference cited evidence.
The JSON shape must be:
{
  "claim": "string",
  "verdict": "true" | "false" | "misleading" | "unverifiable",
  "confidence": 0,
  "reasoning": "string",
  "supporting_sources": ["https://..."],
  "contradicting_sources": ["https://..."]
}"""

class VerdictEngine:
    def __init__(
        self,
        llm_client: LlamaClient | None = None,
        settings: Settings | None = None,
        graph_scorer: GraphTrustScorer | None = None,
        graph_builder: EvidenceGraphBuilder | None = None,
        multi_agent_reasoner: MultiAgentReasoner | None = None,
        graph_repository: Neo4jGraphRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LlamaClient(self.settings)
        self.graph_scorer = graph_scorer or GraphTrustScorer(self.settings)
        self.graph_builder = graph_builder or EvidenceGraphBuilder()
        self.multi_agent_reasoner = multi_agent_reasoner or MultiAgentReasoner()
        self.graph_repository = graph_repository or Neo4jGraphRepository(self.settings)

    async def verify_claims(self, claim_evidence: list[ClaimEvidence]) -> VerificationResponse:
        verdicts = []
        evidence_graphs = []
        for item in claim_evidence:
            llm_verdict = await self.verify_claim(item)
            graph_verdict, node_scores = self.graph_scorer.score_claim(item, llm_verdict)
            evidence_graph = self.graph_builder.build(item, graph_verdict, node_scores)
            agent_findings = self.multi_agent_reasoner.analyze(item, graph_verdict, evidence_graph, node_scores)
            graph_verdict = graph_verdict.model_copy(
                update={
                    "evidence_nodes": node_scores,
                    "agent_findings": agent_findings,
                }
            )
            self.graph_repository.save_graph(evidence_graph)
            verdicts.append(graph_verdict)
            evidence_graphs.append(evidence_graph)
        credibility_score = self._credibility_score(verdicts)
        return VerificationResponse(
            overall_verdict=self._overall_verdict(credibility_score, verdicts),
            overall_confidence=self._overall_confidence(verdicts),
            credibility_score=credibility_score,
            claims=verdicts,
            evidence_graphs=evidence_graphs,
        )

    async def verify_claim(self, claim_evidence: ClaimEvidence) -> ClaimVerdict:
        evidence_lines = "\n".join(
            f"- URL: {source.url}\n  Title: {source.title or 'Untitled'}\n  Evidence: {source.content}"
            for source in claim_evidence.evidence
        )
        prompt = f"""Claim:
{claim_evidence.claim}

Evidence:
{evidence_lines or "No evidence found."}

Return only valid JSON with keys: claim, verdict, confidence, reasoning, supporting_sources, contradicting_sources.
Use integer confidence from 0 to 100. Source lists must contain URL strings only."""
        try:
            verdict = await self.llm_client.complete_json(SYSTEM_PROMPT, prompt, ClaimVerdict)
        except InvalidModelOutputError:
            retry_prompt = f"{prompt}\n\nYour prior answer was malformed. Return only valid JSON matching the requested keys."
            verdict = await self.llm_client.complete_json(SYSTEM_PROMPT, retry_prompt, ClaimVerdict)
        return self._enforce_source_rule(verdict)

    @staticmethod
    def _enforce_source_rule(verdict: ClaimVerdict) -> ClaimVerdict:
        if verdict.verdict != "unverifiable" and not (verdict.supporting_sources or verdict.contradicting_sources):
            return verdict.model_copy(
                update={
                    "verdict": "unverifiable",
                    "confidence": min(verdict.confidence, 50),
                    "reasoning": "The model did not cite evidence, so this claim is treated as unverifiable.",
                }
            )
        return verdict

    @staticmethod
    def _credibility_score(verdicts: list[ClaimVerdict]) -> int:
        if not verdicts:
            return 50
        return round(sum(item.confidence for item in verdicts) / len(verdicts))

    @staticmethod
    def _overall_confidence(verdicts: list[ClaimVerdict]) -> int:
        if not verdicts:
            return 0
        return round(sum(item.confidence for item in verdicts) / len(verdicts))

    @staticmethod
    def _overall_verdict(score: int, verdicts: list[ClaimVerdict]) -> VerdictLabel:
        if verdicts and all(item.verdict == "unverifiable" for item in verdicts):
            return "unverifiable"
        if score > 70:
            return "true"
        if score < 30:
            return "false"
        return "misleading"
