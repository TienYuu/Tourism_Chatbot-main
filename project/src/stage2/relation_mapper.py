from typing import Any
from stage2.ontology_mapper import RELATION_MAPPING


class RelationMapper:

    def __init__(self) -> None:
        pass

    def map_relation(self, relation: dict[str, Any]) -> dict[str, Any]:
        """
        Ánh xạ quan hệ thô từ Wikidata sang quan hệ chuẩn của Ontology.
        Hỗ trợ cả định dạng cũ (property_label) và định dạng tối ưu mới (relation/property).
        """
        # Xác định thuộc tính gốc làm chìa khóa tra cứu (Key)
        # Ưu tiên chuỗi relation logic ("located_in") -> mã P-code ("P131") -> nhãn cũ nếu có
        raw_property = (
            relation.get("relation") or 
            relation.get("property") or 
            relation.get("property_label", "related_to")
        )

        # Ánh xạ sang ontology đích dựa trên RELATION_MAPPING
        mapped_relation = RELATION_MAPPING.get(raw_property, "related_to")

        return {
            "source": relation.get("source"),
            "target": relation.get("target"),
            "relation": mapped_relation,
            "original_relation": raw_property
        }