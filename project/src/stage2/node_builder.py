from datetime import datetime
from typing import Any
from stage2.ontology_mapper import CIDOC_CLASS_MAPPING
from stage2.ontology_mapper import (
    get_cidoc_class,
    resolve_semantic_type,
)


class NodeBuilder:

    def __init__(self) -> None:
        pass

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _extract_coordinates(
        metadata: dict
    ) -> tuple[float | None, float | None]:

        p625_values = metadata.get(
            "P625",
            []
        )

        if not p625_values:
            return None, None

        first_coord = p625_values[0]

        if not isinstance(first_coord, dict):
            return None, None

        lat = first_coord.get("latitude")
        lon = first_coord.get("longitude")

        return lat, lon

    @staticmethod
    def _extract_inception(
        metadata: dict
    ) -> str | None:

        values = metadata.get(
            "P571",
            []
        )

        if not values:
            return None

        return values[0]

    @staticmethod
    def _extract_address(
        metadata: dict
    ) -> str | None:

        values = metadata.get(
            "P6375",
            []
        )

        if not values:
            return None

        return values[0]

    # ========================================================
    # MAIN NODE BUILDER
    # ========================================================

    def build_knowledge_node(
        self,
        entity: dict,
        ner_type: str,
        metadata: dict = None
    ) -> dict:

        if metadata is None:
            metadata = {}

        # =====================================================
        # EXTRACT METADATA
        # =====================================================

        p31_targets = metadata.get("P31", [])

        p1435_targets = metadata.get("P1435", [])
        inception = metadata.get("P571", [None])[0]
        address = metadata.get("P6375", [None])[0]

        # =====================================================
        # EXTRACT COORDINATES FROM P625
        # =====================================================

        latitude = None

        longitude = None

        coord_list = metadata.get("P625", [])

        if coord_list:

            first_coord = coord_list[0]

            if isinstance(first_coord, dict):

                latitude = first_coord.get(
                    "latitude"
                )

                longitude = first_coord.get(
                    "longitude"
                )

        has_coordinates = (
            latitude is not None
            and longitude is not None
        )

        # =====================================================
        # DEFAULT
        # =====================================================

        final_ner_type = ner_type

        # =====================================================
        # PRIORITY 1:
        # HERITAGE / SITE DETECTION
        # =====================================================

        if p1435_targets or has_coordinates:

            final_ner_type = "FAC"

        # =====================================================
# PRIORITY 2:
# P31 SEMANTIC MAPPING
# =====================================================

        else:

            p31_labels = []

            for item in p31_targets:

                if isinstance(item, dict):

                    label = (
                        item.get("label", "")
                        .lower()
                        .strip()
                    )

                    p31_labels.append(label)

            joined = " ".join(p31_labels)

            # =================================================
            # MATERIAL
            # =================================================

            MATERIAL_KEYWORDS = {

                "material",
                "alloy",
                "metal",
                "steel",
                "iron",
                "wood",
                "stone",
                "ceramic",

                "vật liệu",
                "hợp kim",
                "kim loại",
                "thép",
                "sắt",
                "gỗ",
                "đá",
                "gốm",
                "đất nung",
                "sứ",
                "gạch",
                "bê tông",
            }

            # =================================================
            # PERSON
            # =================================================

            PERSON_KEYWORDS = {

                "human",
                "person",
                "people",
                "nhân vật",
                "con người",
                "người",
                "nhân vật lịch sử",
                "vua",
                "nữ hoàng",
                "hoàng đế",
                "hoàng hậu",
                "kiến trúc sư",
                "nghệ sĩ",
                "họa sĩ",
                "nhà điêu khắc",
                "lãnh đạo",
                "chính khách",
                "chủ tịch",
                "thủ tướng",
            }

            # =================================================
            # ORGANIZATION
            # =================================================

            ORG_KEYWORDS = {

                "organization",
                "company",
                "institution",
                "agency",
                "government agency",
                "public institution",
                "intermunicipal",

                "tổ chức",
                "công ty",
                "cơ quan",
                "viện",
            }

            # =================================================
            # PLACE
            # =================================================

            PLACE_KEYWORDS = {

                "country",
                "city",
                "district",
                "province",
                "state",
                "kingdom",
                "department",
                "arrondissement",
                "administrative",
                "administrative unit",
                "geographical object",
                "territorial entity",

                "quốc gia",
                "thành phố",
                "quận",
                "huyện",
                "tỉnh",
                "vương quốc",
                "đơn vị hành chính",
                "địa danh",
            }

            # =================================================
            # HERITAGE / SITE
            # =================================================

            SITE_KEYWORDS = {

                "tower",
                "temple",
                "pagoda",
                "citadel",
                "monument",
                "heritage",

                "tháp",
                "chùa",
                "đền",
                "thành",
                "di tích",
                "miếu",
                "đình",
            }

            # =================================================
            # MATCHING
            # =================================================

            if any(
                kw in joined
                for kw in SITE_KEYWORDS
            ):

                final_ner_type = "FAC"

            elif any(
                kw in joined
                for kw in MATERIAL_KEYWORDS
            ):

                final_ner_type = "MATERIAL"

            elif any(
                kw in joined
                for kw in ORG_KEYWORDS
            ):

                final_ner_type = "ORG"

            elif any(
                kw in joined
                for kw in PLACE_KEYWORDS
            ):

                final_ner_type = "GPE"

            elif any(
                kw in joined
                for kw in PERSON_KEYWORDS
            ):

                final_ner_type = "PER"

        # =====================================================
        # CIDOC CLASS
        # =====================================================

        crm_class = CIDOC_CLASS_MAPPING.get(
            final_ner_type,
            "E1_CRM_Entity"
        )

        # =====================================================
        # BUILD NODE
        # =====================================================

        return {

            "id": entity.get("id"),

            "label": (
                entity.get("label")
                or entity.get("title", "")
            ),

            "type": crm_class,

            "ner_type": final_ner_type,

            "description": entity.get(
                "description",
                ""
            ),

            "latitude": latitude,

            "longitude": longitude,

            "inception": inception,
            "address": address,

            "wd_properties": {

                "instance_of": p31_targets,

                "heritage_designation": p1435_targets,

                "country": metadata.get(
                    "P17",
                    []
                ),
            },

            "source": "wikidata",

            "download_date": (
                entity.get("download_date")
                or datetime.now().isoformat()
            ),
        }

        return node