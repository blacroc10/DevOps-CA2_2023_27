import math

from app.config import Settings, get_settings
from app.models import ClaimEvidence, ClaimVerdict, EvidenceNodeScore, VerdictLabel


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def authority_score(reliability: int, has_domain: bool = True) -> float:
    if reliability >= 5:
        return 1.0
    if reliability == 4:
        return 0.8
    if reliability > 0:
        return 0.5
    return 0.5 if has_domain else 0.2


def relevance_score(score: float | None) -> float:
    return _clamp(score if score is not None else 0.5)


def sigmoid_confidence(raw_score: float, k: float) -> int:
    confidence = 1 / (1 + math.exp(-k * raw_score))
    return round(confidence * 100)


def verdict_from_confidence(confidence: int, has_evidence_signal: bool) -> VerdictLabel:
    if not has_evidence_signal:
        return "unverifiable"
    if confidence > 70:
        return "true"
    if confidence < 30:
        return "false"
    return "misleading"


class GraphTrustScorer:
    """CWCP-inspired graph scoring over direct Tavily evidence nodes."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def score_claim(self, claim_evidence: ClaimEvidence, verdict: ClaimVerdict) -> tuple[ClaimVerdict, list[EvidenceNodeScore]]:
        nodes = self._node_scores(claim_evidence, verdict)
        support_total = sum(node.weight for node in nodes if node.stance == "support")
        contradiction_total = sum(node.weight / node.hop_distance for node in nodes if node.stance == "contradiction")
        raw_score = support_total - contradiction_total
        graph_confidence = sigmoid_confidence(raw_score, self.settings.graph_confidence_k)
        has_signal = any(node.stance != "neutral" and node.agreement > 0 for node in nodes)
        graph_verdict = verdict_from_confidence(graph_confidence, has_signal)
        reasoning_suffix = (
            f" GraphTrust CWCP score R={raw_score:.3f}; confidence={graph_confidence}/100 "
            "using authority x relevance x agreement over cited evidence nodes."
        )

        return (
            verdict.model_copy(
                update={
                    "verdict": graph_verdict,
                    "confidence": graph_confidence,
                    "graph_score": round(raw_score, 4),
                    "graph_confidence": graph_confidence,
                    "reasoning": f"{verdict.reasoning}{reasoning_suffix}",
                }
            ),
            nodes,
        )

    def _node_scores(self, claim_evidence: ClaimEvidence, verdict: ClaimVerdict) -> list[EvidenceNodeScore]:
        supporting = set(verdict.supporting_sources)
        contradicting = set(verdict.contradicting_sources)
        agreement = verdict.confidence / 100
        nodes: list[EvidenceNodeScore] = []

        for source in claim_evidence.evidence:
            url = str(source.url)
            stance = self._stance(url, supporting, contradicting)
            node_agreement = agreement if stance != "neutral" else 0.0
            authority = authority_score(source.reliability, has_domain=bool(source.url.host))
            relevance = relevance_score(source.score)
            weight = authority * relevance * node_agreement
            nodes.append(
                EvidenceNodeScore(
                    url=url,
                    stance=stance,
                    authority=round(authority, 4),
                    relevance=round(relevance, 4),
                    agreement=round(node_agreement, 4),
                    hop_distance=self.settings.direct_evidence_hop_distance,
                    weight=round(weight, 4),
                )
            )
        return nodes

    @staticmethod
    def _stance(url: str, supporting: set[str], contradicting: set[str]) -> str:
        if url in supporting:
            return "support"
        if url in contradicting:
            return "contradiction"
        return "neutral"
