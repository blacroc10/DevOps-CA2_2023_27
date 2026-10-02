from app.models import EvidenceGraphEdge, EvidenceGraphNode
from app.neo4j_repository import semantic_node_label, semantic_relationship_type


def test_semantic_node_label_maps_graph_node_types():
    assert semantic_node_label(EvidenceGraphNode(id="c1", type="claim", label="Claim")) == "Claim"
    assert semantic_node_label(EvidenceGraphNode(id="e1", type="supporting_evidence", label="Evidence")) == "SupportingEvidence"
    assert semantic_node_label(EvidenceGraphNode(id="e2", type="contradicting_evidence", label="Evidence")) == "ContradictingEvidence"
    assert semantic_node_label(EvidenceGraphNode(id="e3", type="neutral_evidence", label="Evidence")) == "NeutralEvidence"


def test_semantic_relationship_type_maps_edge_types():
    assert semantic_relationship_type(EvidenceGraphEdge(source="e1", target="c1", type="supports")) == "SUPPORTS"
    assert semantic_relationship_type(EvidenceGraphEdge(source="e1", target="c1", type="contradicts")) == "CONTRADICTS"
    assert semantic_relationship_type(EvidenceGraphEdge(source="e1", target="c1", type="refers_to")) == "REFERS_TO"
    assert semantic_relationship_type(EvidenceGraphEdge(source="e1", target="e2", type="similar_to")) == "SIMILAR_TO"
