from neo4j import GraphDatabase
from dotenv import load_dotenv
import re
from rapidfuzz import fuzz
import re
import unicodedata

import os
import logging

# ============================================================
# ENV
# ============================================================

load_dotenv(override=True)

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

# ============================================================
# LOGGER
# ============================================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# ============================================================
# NEO4J DRIVER
# ============================================================

driver = GraphDatabase.driver(
    URI,
    auth=(USER, PASSWORD)
)

# ============================================================
# GRAPH QUERY ENGINE
# ============================================================

def normalize_text(text: str) -> str:

        if not text:
            return ""

        text = text.lower()

        # bỏ dấu tiếng Việt
        text = unicodedata.normalize("NFD", text)

        text = "".join(
            c for c in text
            if unicodedata.category(c) != "Mn"
        )

        # thay ký tự đặc biệt thành space
        text = re.sub(r"[-_/]", " ", text)

        # bỏ ký tự lạ
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        # collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

class HeritageGraphQuery:
   
    def __init__(self):

        self.driver = driver

    # ========================================================
    # LOW LEVEL QUERY
    # ========================================================
    
    def get_subgraph_context(self, entity_name, hops=2):
        # CHỈ tìm theo 'label' vì DB của bạn không có 'name'
        query = """
        MATCH (n) 
        WHERE n.label =~ $regex
        MATCH path = (n)-[r*1..%d]-(m)
        RETURN path LIMIT 30
        """ % hops
        
        # Sử dụng Regex không phân biệt hoa thường để tìm "Huế" trong "Cố đô Huế"
        regex = f"(?i).*{entity_name}.*"
        
        with self.driver.session(database=DATABASE) as session:
            result = session.run(query, regex=regex)
            return [record["path"] for record in result]
    
    def multi_hop_location_reasoning(
        self,
        entity_label: str,
        target_location: str | None = None,
        max_hops: int = 3
    ):
        """
        Multi-hop reasoning:
        Eiffel Tower -> District 7 -> Paris
        """

        query = f"""
        MATCH path =
        (start:Entity)
        -[:P53_has_former_or_current_location*1..{max_hops}]->
        (loc:Entity)

        WHERE
            toLower(start.label)
            CONTAINS toLower($entity_label)

        RETURN
            [n IN nodes(path) |
                {{
                    id: n.id,
                    label: n.label,
                    type: n.type
                }}
            ] AS path_nodes
        """

        results = self.run_query(
            query,
            {
                "entity_label": entity_label
            }
        )

        # ----------------------------------------------------
        # FILTER TARGET LOCATION
        # ----------------------------------------------------

        if target_location:

            filtered = []

            for r in results:

                labels = [
                    n["label"].lower()
                    for n in r["path_nodes"]
                ]

                if any(
                    target_location.lower() in lbl
                    for lbl in labels
                ):
                    filtered.append(r)

            return filtered

        return results

    def run_query(
        self,
        cypher: str,
        params: dict | None = None
    ) -> list[dict]:

        if params is None:
            params = {}

        try:

            with self.driver.session(
                database=DATABASE
            ) as session:

                result = session.run(
                    cypher,
                    **params
                )

                return [
                    r.data()
                    for r in result
                ]

        except Exception as e:

            logger.error(
                "Cypher query failed: %s",
                e
            )

            return []

    # ========================================================
    # SEARCH ENTITY
    # ========================================================

    def search_entity(
        self,
        keyword: str,
        limit: int = 10
    ) -> list[dict]:

        keyword_norm = normalize_text(keyword)

        query = """
        MATCH (n:Entity)

        WITH n,
            toLower(
                replace(
                    replace(
                        replace(n.label, '-', ' '),
                        '_',
                        ' '
                    ),
                    '/',
                    ' '
                )
            ) AS norm_label

        WHERE norm_label CONTAINS $keyword

        RETURN
            n.id               AS id,
            n.label            AS label,
            n.type             AS type,
            n.ner_type         AS ner_type,
            n.description      AS description,
            n.latitude         AS latitude,
            n.longitude        AS longitude,
            n.instance_of      AS instance_of,
            n.country          AS country

        ORDER BY size(n.label)

        LIMIT $limit
        """

        return self.run_query(
            query,
            {
                "keyword": keyword_norm,
                "limit": limit
            }
        )

    # ========================================================
    # ASK NATURAL QUESTION
    # ========================================================

    def ask(
        self,
        question: str
    ) -> list[dict]:

        q = question.lower()

        # ----------------------------------------------------
        # MATERIAL
        # ----------------------------------------------------

        if "vật liệu" in q:

            entities = self.search_entity(question)

            if not entities:
                return []

            entity_id = entities[0]["id"]

            return self.get_materials_of_site(
                entity_id
            )

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        if "ở đâu" in q or "thuộc" in q:

            entities = self.search_entity(question)

            if not entities:
                return []

            entity_id = entities[0]["id"]

            return self.get_location_hierarchy(
                entity_id
            )

        # ----------------------------------------------------
        # DEFAULT
        # ----------------------------------------------------

        return self.search_entity(question)

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.driver.close()

# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    graph = HeritageGraphQuery()

    print("\n===== SEARCH =====")

    result = graph.search_entity(
        "Tháp Eiffel"
    )

    print(result)

    print("\n===== RELATIONS =====")

    if result:

        entity_id = result[0]["id"]

        rels = graph.get_relations_of_entity(
            entity_id
        )

        print(rels)

    graph.close()