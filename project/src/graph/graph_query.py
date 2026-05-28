# graph/graph_query.py

from neo4j import GraphDatabase
import os


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")

NEO4J_USER = os.getenv("NEO4J_USER")

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

class GraphQuery:

    def __init__(
        self,
        uri,
        username,
        password,
        database="ditichtest"
    ):

        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password)
        )
        self.database = database

    def close(self):
        self.driver.close()

    # =========================================================
    # ENTITY LOADING
    # =========================================================

    def get_all_entities(self):

        query = """
        MATCH (n)
        RETURN
            n.id AS id,
            n.label AS label,
            labels(n) AS labels
        """

        with self.driver.session(
    database=self.database
) as session:

            result = session.run(query)

            entities = []

            for record in result:

                entities.append({
                    "id": record["id"],
                    "label": record["label"],
                    "labels": record["labels"]
                })

            return entities

    # =========================================================
    # ENTITY FETCH
    # =========================================================

    def get_entity_by_id(
        self,
        entity_id
    ):

        query = """
        MATCH (n {id: $entity_id})
        RETURN n
        LIMIT 1
        """

        with self.driver.session(
    database=self.database
) as session:

            result = session.run(
                query,
                entity_id=entity_id
            )

            record = result.single()

            if not record:
                return None

            return dict(record["n"])

    # =========================================================
    # GENERIC NEIGHBOR EXPANSION
    # =========================================================

    def expand_neighbors(
        self,
        entity_id,
        limit=50
    ):

        query = """
        MATCH (a {id: $entity_id})-[r]->(b)

        RETURN
            a.id AS source_id,
            a.label AS source_label,

            type(r) AS relation,

            b.id AS target_id,
            b.label AS target_label,
            labels(b) AS target_labels

        LIMIT $limit
        """

        with self.driver.session(
    database=self.database
) as session:

            result = session.run(
                query,
                entity_id=entity_id,
                limit=limit
            )

            neighbors = []

            for record in result:

                neighbors.append({

                    "source_id":
                        record["source_id"],

                    "source_label":
                        record["source_label"],

                    "relation":
                        record["relation"],

                    "target_id":
                        record["target_id"],

                    "target_label":
                        record["target_label"],

                    "target_labels":
                        record["target_labels"]
                })

            return neighbors

    # =========================================================
    # BIDIRECTIONAL EXPANSION
    # =========================================================

    def expand_bidirectional(
        self,
        entity_id,
        limit=100
    ):

        query = """
        MATCH (a {id: $entity_id})-[r]-(b)

        RETURN
            a.id AS source_id,
            a.label AS source_label,

            type(r) AS relation,

            b.id AS target_id,
            b.label AS target_label,
            labels(b) AS target_labels

        LIMIT $limit
        """

        with self.driver.session(
    database=self.database
) as session:

            result = session.run(
                query,
                entity_id=entity_id,
                limit=limit
            )

            edges = []

            for record in result:

                edges.append({

                    "source_id":
                        record["source_id"],

                    "source_label":
                        record["source_label"],

                    "relation":
                        record["relation"],

                    "target_id":
                        record["target_id"],

                    "target_label":
                        record["target_label"],

                    "target_labels":
                        record["target_labels"]
                })

            return edges

    # =========================================================
    # MULTI HOP CYPHER
    # =========================================================

    def multi_hop_paths(
        self,
        start_entity_id,
        max_depth=3,
        limit=100
    ):

        query = f"""
        MATCH path = (a {{id: $start_entity_id}})
            -[*1..{max_depth}]-
            (b)

        RETURN path
        LIMIT $limit
        """

        with self.driver.session(
    database=self.database
) as session:

            result = session.run(
                query,
                start_entity_id=start_entity_id,
                limit=limit
            )

            paths = []

            for record in result:

                path = record["path"]

                nodes = []
                relationships = []

                for node in path.nodes:

                    nodes.append({
                        "id": node.get("id"),
                        "label": node.get("label")
                    })

                for rel in path.relationships:

                    relationships.append(rel.type)

                paths.append({
                    "nodes": nodes,
                    "relationships": relationships
                })

            return paths
    
    # =====================================================
# GET ENTITY BY ID
# =====================================================
    
    # =====================================================
# GENERIC CYPHER QUERY
# =====================================================

    def run_query(
        self,
        query,
        parameters=None
    ):

        if parameters is None:
            parameters = {}

        with self.driver.session(
            database=self.database
        ) as session:

            result = session.run(
                query,
                parameters
            )

            return list(result)
    
    def get_entity_by_id(
        self,
        entity_id
    ):

        query = """

        MATCH (n)

        WHERE n.id = $entity_id

        RETURN n

        LIMIT 1

        """

        result = self.run_query(
            query,
            {
                "entity_id": entity_id
            }
        )

        if not result:
            return None

        return dict(
            result[0]["n"]
        )