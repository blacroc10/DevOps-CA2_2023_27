from app.models import EvidenceSource
from app.relationship_detector import RelationshipDetector, jaccard_similarity


def test_jaccard_similarity_detects_overlap():
    similarity = jaccard_similarity("Apollo landed on the Moon in 1969", "The Moon landing happened in 1969")

    assert similarity > 0


def test_similar_evidence_edges(test_settings):
    detector = RelationshipDetector(test_settings)
    evidence = [
        EvidenceSource(url="https://example.com/a", content="Apollo landed on the Moon in 1969."),
        EvidenceSource(url="https://example.com/b", content="The Apollo Moon landing happened in 1969."),
    ]

    edges = detector.similar_evidence_edges(evidence, ["e1", "e2"])

    assert edges
    assert edges[0].type == "similar_to"

