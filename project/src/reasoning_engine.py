import re

from graph_query import HeritageGraphQuery


class HeritageReasoner:

    def __init__(self):

        self.graph = HeritageGraphQuery()

    # ========================================================
    # MAIN QA
    # ========================================================

    def answer(
        self,
        question: str
    ):

        q = question.lower()

        # ----------------------------------------------------
        # DISTRICT OF CITY
        # ----------------------------------------------------

        if "quận nào" in q:

            return self._reason_district(
                question
            )

        # ----------------------------------------------------
        # DEFAULT
        # ----------------------------------------------------

        return {
            "answer": "Chưa hỗ trợ dạng suy luận này.",
            "evidence": []
        }

    # ========================================================
    # REASON: DISTRICT
    # ========================================================

    def _reason_district(
        self,
        question: str
    ):

        # ----------------------------------------------------
        # EXTRACT ENTITY
        # ----------------------------------------------------

        entities = self.graph.search_entity(
            question
        )

        if not entities:

            return {
                "answer": "Không tìm thấy thực thể.",
                "evidence": []
            }

        source = entities[0]

        source_id = source["id"]

        # ----------------------------------------------------
        # MULTI HOP QUERY
        # ----------------------------------------------------

        cypher = """
        MATCH path =
        (a:Entity {id: $source_id})
        -[:P53_has_former_or_current_location*1..3]->
        (b:Entity)

        RETURN path
        """

        results = self.graph.run_query(
            cypher,
            {
                "source_id": source_id
            }
        )

        # ----------------------------------------------------
        # REASONING
        # ----------------------------------------------------

        for row in results:

            path = row["path"]

            nodes = path.nodes

            labels = [
                n.get("label")
                for n in nodes
            ]

            # Example:
            # ["Tháp Eiffel", "Quận 7", "Paris"]

            if "Paris" in labels:

                if len(labels) >= 2:

                    district = labels[-2]

                    return {
                        "answer": district,
                        "evidence": labels
                    }

        return {
            "answer": "Không suy luận được.",
            "evidence": []
        }