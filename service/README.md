# Truth

Truth is a backend verification engine for misinformation detection. It accepts text or a URL, extracts checkable claims, retrieves live evidence with Tavily, builds an evidence graph, runs specialized reasoning agents, and returns a cited verdict with GraphTrust/CWCP confidence.

This implementation uses **Groq API** for Llama 3.1 8B because it supports low-latency JSON-mode responses.

## Pipeline

1. `app/input_handler.py` cleans raw text or extracts article text from a URL with `trafilatura`.
2. `app/claim_extractor.py` prompts Llama to extract 1-5 factual claims as structured JSON.
3. `app/evidence_retriever.py` queries Tavily using `search_depth="advanced"`, classifies evidence as web/news/academic/trusted/domain-specific, and prioritizes reliable domains.
4. `app/verdict_engine.py` prompts Llama for cited per-claim verdict JSON.
5. `app/graphtrust_scorer.py` computes authority, relevance, agreement, per-node weight, graph score, and confidence.
6. `app/evidence_graph.py` builds dynamic claim/evidence nodes and support/contradiction/neutral edges.
7. `app/relationship_detector.py` adds evidence-to-evidence similarity edges.
8. `app/multi_agent.py` produces specialized agent findings for transparency.
9. `app/neo4j_repository.py` persists every graph to the required Neo4j database.
10. `app/main.py` exposes `POST /verify` and `GET /health`.

## GraphTrust / CWCP Scoring

Each Tavily result is treated as a direct evidence node connected to the claim. The node weight is:

```text
wᵢ = aᵢ × sᵢ × gᵢ
```

- `aᵢ`: authority score from source tier/domain reliability
- `sᵢ`: relevance score from Tavily result score
- `gᵢ`: agreement score from the LLM adjudication confidence when the source is cited as supporting or contradicting

The claim-level graph score is:

```text
R = Σ support(wᵢ) - Σ contradiction(wᵢ / dᵢ)
```

Direct Tavily evidence uses `dᵢ = 1`. Confidence is then:

```text
confidence = 1 / (1 + e^(-kR))
```

The default `k` is `2.5`. The API returns confidence as `0-100`.

Final verdict thresholds:

- `true`: confidence > 70
- `false`: confidence < 30
- `misleading`: otherwise
- `unverifiable`: no cited evidence signal

The article-level `credibility_score` is the average of the graph-scored claim confidences.

This backend computes `gᵢ` from the LLM adjudication confidence for sources cited as supporting or contradicting. The multi-agent layer exposes deterministic specialized findings over that graph; it does not make extra paid LLM calls per agent by default.

## Output Transparency

`POST /verify` returns:

- article-level verdict, confidence, and credibility score
- per-claim verdicts, reasoning, supporting and contradicting source URLs
- per-node scores: `authority`, `relevance`, `agreement`, `weight`, `hop_distance`
- specialized agent findings
- evidence graph snapshots with nodes and edges

## Required Neo4j Persistence

Neo4j is part of the core TruthGraph pipeline. The API health check fails until
Neo4j is configured and reachable:

```text
NEO4J_ENABLED=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

Then run Neo4j yourself or use Docker Compose.

The API also permits the local frontend through `CORS_ORIGINS`. The defaults
cover ports 3000 and 4173 on both `localhost` and `127.0.0.1`.

Persisted nodes keep the compatibility label `EvidenceGraphNode` and also get semantic labels:

- `Claim`
- `SupportingEvidence`
- `ContradictingEvidence`
- `NeutralEvidence`

Persisted relationships use semantic types:

- `SUPPORTS`
- `CONTRADICTS`
- `REFERS_TO`
- `SIMILAR_TO`

Useful Neo4j Browser queries:

```cypher
MATCH (c:Claim)<-[r:SUPPORTS|CONTRADICTS|REFERS_TO]-(e)
RETURN c, r, e
LIMIT 50
```

```cypher
MATCH (a)-[r:SIMILAR_TO]-(b)
RETURN a, r, b
LIMIT 50
```

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add keys to `.env`:

- Tavily: create an API key from [Tavily](https://app.tavily.com/)
- Groq: create an API key from [Groq Console](https://console.groq.com/keys)

## Run

```bash
uvicorn app.main:app --reload
```

Run with Docker:

```bash
docker compose up --build
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Verify text:

```bash
curl -X POST http://127.0.0.1:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"input":"NASA landed Apollo 11 on the Moon in 1969.","type":"text"}'
```

Sample response:

```json
{
  "overall_verdict": "true",
  "overall_confidence": 92,
  "credibility_score": 100,
  "claims": [
    {
      "claim": "NASA landed Apollo 11 on the Moon in 1969.",
      "verdict": "true",
      "confidence": 92,
      "graph_score": 1.2,
      "graph_confidence": 92,
      "reasoning": "NASA and historical records support that Apollo 11 landed on the Moon in July 1969.",
      "supporting_sources": ["https://www.nasa.gov/mission/apollo-11/"],
      "contradicting_sources": [],
      "evidence_nodes": [],
      "agent_findings": []
    }
  ],
  "evidence_graphs": []
}
```

## Test

The test suite uses mocked Tavily, Groq, and URL extraction behavior. It does not make live API calls.

```bash
pytest
```
