class PropertyReasoner:

    def __init__(
        self,
        graph_query
    ):

        self.graph_query = graph_query

    # =====================================================
    # PROPERTY QUESTION ANSWERING
    # =====================================================

    def answer_property_question(
        self,
        entity_id,
        semantic_parse
    ):

        relations = semantic_parse.get(
            "relations",
            []
        )

        if not relations:
            return None

        relation = str(
            relations[0]
        ).lower()

        node = (
            self.graph_query
            .get_entity_by_id(
                entity_id
            )
        )

        if not node:
            return None

        # =================================================
        # COORDINATES
        # =================================================

        coordinate_keywords = [

            "kinh độ",
            "vĩ độ",
            "tọa độ",
            "coordinates",
            "latitude",
            "longitude"
        ]

        if any(
            keyword in relation
            for keyword in coordinate_keywords
        ):

            latitude = node.get(
                "latitude"
            )

            longitude = node.get(
                "longitude"
            )

            if (
                latitude is not None
                and longitude is not None
            ):

                return {

                    "answer":
                        (
                            f"Vĩ độ: {latitude}, "
                            f"Kinh độ: {longitude}"
                        ),

                    "latitude":
                        latitude,

                    "longitude":
                        longitude
                }

        return None