import re

from app.config import Settings, get_settings
from app.models import EvidenceGraphEdge, EvidenceSource


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if len(token) > 2}


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


class RelationshipDetector:
    """Detects lightweight evidence-to-evidence relationships for the graph."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def similar_evidence_edges(self, evidence: list[EvidenceSource], node_ids: list[str]) -> list[EvidenceGraphEdge]:
        edges: list[EvidenceGraphEdge] = []
        for left_index, left in enumerate(evidence):
            for right_index in range(left_index + 1, len(evidence)):
                right = evidence[right_index]
                similarity = jaccard_similarity(left.content, right.content)
                if similarity >= self.settings.relationship_similarity_threshold:
                    edges.append(
                        EvidenceGraphEdge(
                            source=node_ids[left_index],
                            target=node_ids[right_index],
                            type="similar_to",
                            weight=round(similarity, 4),
                        )
                    )
        return edges
