from app.config import Settings, get_settings
from app.models import ClaimEvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


NODE_LABELS = {
    "claim": "Claim",
    "supporting_evidence": "SupportingEvidence",
    "contradicting_evidence": "ContradictingEvidence",
    "neutral_evidence": "NeutralEvidence",
}

RELATIONSHIP_TYPES = {
    "supports": "SUPPORTS",
    "contradicts": "CONTRADICTS",
    "refers_to": "REFERS_TO",
    "similar_to": "SIMILAR_TO",
}


def semantic_node_label(node: EvidenceGraphNode) -> str:
    return NODE_LABELS[node.type]


def semantic_relationship_type(edge: EvidenceGraphEdge) -> str:
    return RELATIONSHIP_TYPES[edge.type]


class Neo4jGraphRepository:
    """Neo4j persistence and readiness checks for evidence graphs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def enabled(self) -> bool:
        return bool(
            self.settings.neo4j_enabled
            and self.settings.neo4j_uri
            and self.settings.neo4j_user
            and self.settings.neo4j_password
        )

    def verify_connection(self) -> None:
        if not self.enabled():
            raise RuntimeError(
                "Neo4j is required. Set NEO4J_ENABLED=true and provide "
                "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
            )
        from neo4j import GraphDatabase

        with GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        ) as driver:
            driver.verify_connectivity()

    def save_graph(self, graph: ClaimEvidenceGraph) -> None:
        if not self.enabled():
            raise RuntimeError(
                "Neo4j is required but is not configured. Evidence graph persistence was not performed."
            )
        from neo4j import GraphDatabase

        with GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        ) as driver:
            with driver.session() as session:
                session.execute_write(self._merge_graph, graph)

    @staticmethod
    def _merge_graph(tx, graph: ClaimEvidenceGraph) -> None:
        for node in graph.nodes:
            semantic_label = semantic_node_label(node)
            tx.run(
                f"""
                MERGE (n:EvidenceGraphNode:{semantic_label} {{id: $id}})
                SET n.type = $type,
                    n.label = $label,
                    n.url = $url,
                    n.authority = $authority,
                    n.relevance = $relevance,
                    n.agreement = $agreement,
                    n.weight = $weight
                """,
                node.model_dump(),
            )
        for edge in graph.edges:
            relationship_type = semantic_relationship_type(edge)
            tx.run(
                f"""
                MATCH (source:EvidenceGraphNode {{id: $source}})
                MATCH (target:EvidenceGraphNode {{id: $target}})
                MERGE (source)-[r:{relationship_type}]->(target)
                SET r.type = $type,
                    r.weight = $weight
                """,
                edge.model_dump(),
            )
