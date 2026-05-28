class RelationCanonicalizer:

    def __init__(self):

        pass

    # =====================================================
    # MAIN
    # =====================================================

    def canonicalize(
        self,
        relation
    ):

        relation = str(
            relation or ""
        ).lower().strip()

        # =================================================
        # ARCHITECT
        # =================================================

        architect_keywords = [

            "architect",
            "kiến trúc sư",
            "kiến trúc sư của",
            "thiết kế",
            "designed by",
            "thiết kế bởi"
        ]

        for keyword in architect_keywords:

            if keyword in relation:
                return "architect"

        # =================================================
        # BUILT BY
        # =================================================

        built_keywords = [

            "xây dựng",
            "built by",
            "constructed by",
            "được xây dựng bởi"
            "xây dựng bởi"
        ]

        for keyword in built_keywords:

            if keyword in relation:
                return "built_by"

        # =================================================
        # LOCATION
        # =================================================

        location_keywords = [

            "located in",
            "located",
            "nằm ở",
            "ở",
            "tại"
        ]

        for keyword in location_keywords:

            if keyword in relation:
                return "located_in"

        # =================================================
        # PART OF
        # =================================================

        part_keywords = [

            "thuộc",
            "part of",
            "là một phần của",
            "là một phần trong"
        ]

        for keyword in part_keywords:

            if keyword in relation:
                return "part_of"

        # =================================================
        # MATERIAL
        # =================================================

        material_keywords = [

            "material",
            "làm bằng"
        ]

        for keyword in material_keywords:

            if keyword in relation:
                return "material_used"

        # =================================================
        # TIME
        # =================================================

        time_keywords = [

            "thời gian",
            "time span",
            "year",
            "date",
            "năm nào",
            "khoảng thời gian",
            "năm bao nhiêu"
        ]

        for keyword in time_keywords:

            if keyword in relation:
                return "time_span"

        # =================================================
        # RELATED
        # =================================================

        return "related_to"