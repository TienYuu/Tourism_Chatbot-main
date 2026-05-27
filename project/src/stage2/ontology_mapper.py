"""
ONTOLOGY MAPPER
Semantic ontology layer for Heritage Knowledge Graph
CIDOC-CRM aligned
"""

# ============================================================
# CIDOC CLASS MAPPING
# ============================================================

CIDOC_CLASS_MAPPING = {

    # ========================================
    # PERSON
    # ========================================

    "PER": "E21_Person",

    # ========================================
    # PLACES
    # ========================================

    "GPE": "E53_Place",
    "LOC": "E53_Place",

    # ========================================
    # HERITAGE / SITE / BUILDING
    # ========================================

    "FAC": "E27_Site",
    "HISTORICAL_RELICT": "E27_Site",

    # ========================================
    # EVENTS
    # ========================================

    "EVENT": "E5_Event",
    "DYNASTY": "E4_Period",
    "TIME": "E52_Time_Span",

    # ========================================
    # ORGANIZATION
    # ========================================

    "ORG": "E74_Group",

    # ========================================
    # ARTIFACT
    # ========================================

    "ARTIFACT": "E22_Human-Made_Object",

    # ========================================
    # MATERIAL
    # ========================================

    "MATERIAL": "E57_Material",

    # ========================================
    # FALLBACK
    # ========================================

    "UNKNOWN": "E1_CRM_Entity"
}

# ============================================================
# RELATION MAPPING
# ============================================================

RELATION_MAPPING = {

    # ========================================
    # CREATION
    # ========================================

    "architect": "P14_carried_out_by",

    "built_by": "P108_was_produced_by",

    "founded_by": "P11_had_participant",

    # ========================================
    # LOCATION
    # ========================================

    "located_in": (
        "P53_has_former_or_current_location"
    ),

    "part_of": "P46_is_composed_of",

    # ========================================
    # MATERIAL
    # ========================================

    "material_used": "P45_consists_of",

    # ========================================
    # TIME
    # ========================================

    "time_span": "P4_has_time_span",

    # ========================================
    # RELATED
    # ========================================

    "related_to": "P130_shows_features_of",
}

# ============================================================
# SEMANTIC KEYWORDS
# ============================================================

SEMANTIC_KEYWORDS = {

    # ========================================
    # MATERIALS
    # ========================================

    "material": "MATERIAL",
    "metal": "MATERIAL",
    "alloy": "MATERIAL",
    "steel": "MATERIAL",
    "wood": "MATERIAL",
    "stone": "MATERIAL",
    "brick": "MATERIAL",
    "ceramic": "MATERIAL",
    "bronze": "MATERIAL",

    # ========================================
    # BUILDINGS / FACILITIES
    # ========================================

    "tower": "FAC",
    "temple": "FAC",
    "pagoda": "FAC",
    "museum": "FAC",
    "monument": "FAC",
    "castle": "FAC",
    "fortress": "FAC",
    "citadel": "FAC",
    "bridge": "FAC",
    "church": "FAC",
    "cathedral": "FAC",
    "mosque": "FAC",
    "shrine": "FAC",
    "building": "FAC",
    "architecture": "FAC",

    # ========================================
    # HERITAGE
    # ========================================

    "heritage": "HISTORICAL_RELICT",
    "historical site": "HISTORICAL_RELICT",
    "archaeological site": "HISTORICAL_RELICT",

    # ========================================
    # GEO POLITICAL
    # ========================================

    "district": "GPE",
    "city": "GPE",
    "province": "GPE",
    "country": "GPE",
    "village": "GPE",
    "commune": "GPE",
    "ward": "GPE",

    # ========================================
    # NATURAL LOCATION
    # ========================================

    "mountain": "LOC",
    "river": "LOC",
    "lake": "LOC",
    "forest": "LOC",
    "island": "LOC",
    "beach": "LOC",
    "cave": "LOC",

    # ========================================
    # PERSON
    # ========================================

    "human": "PER",
    "person": "PER",
    "architect": "PER",
    "artist": "PER",
    "king": "PER",
    "emperor": "PER",

    # ========================================
    # ORGANIZATION
    # ========================================

    "organization": "ORG",
    "company": "ORG",
    "agency": "ORG",
    "committee": "ORG",
    "association": "ORG",
    "university": "ORG",

    # ========================================
    # EVENTS
    # ========================================

    "festival": "EVENT",
    "battle": "EVENT",
    "war": "EVENT",
    "ceremony": "EVENT",

    # ========================================
    # TIME PERIOD
    # ========================================

    "dynasty": "DYNASTY",
    "historical period": "DYNASTY",
}

# ============================================================
# SAFE CLASS LOOKUP
# ============================================================

def get_cidoc_class(
    ner_label: str
) -> str:

    if not ner_label:
        return CIDOC_CLASS_MAPPING["UNKNOWN"]

    clean_label = (
        str(ner_label)
        .strip()
        .upper()
    )

    return CIDOC_CLASS_MAPPING.get(
        clean_label,
        CIDOC_CLASS_MAPPING["UNKNOWN"]
    )

# ============================================================
# SAFE RELATION LOOKUP
# ============================================================

def get_cidoc_relation(
    raw_relation: str
) -> str:

    if not raw_relation:
        return RELATION_MAPPING["related_to"]

    clean_rel = (
        str(raw_relation)
        .strip()
        .lower()
    )

    return RELATION_MAPPING.get(
        clean_rel,
        RELATION_MAPPING["related_to"]
    )

# ============================================================
# TEXT KEYWORD MATCH
# ============================================================

def infer_semantic_type_from_text(
    text: str
) -> str | None:

    if not text:
        return None

    clean_text = text.lower().strip()

    for keyword, semantic_type in (
        SEMANTIC_KEYWORDS.items()
    ):

        if keyword in clean_text:
            return semantic_type

    return None

# ============================================================
# METADATA INFERENCE
# ============================================================

def infer_ner_from_metadata(
    metadata: dict
) -> str | None:

    if not metadata:
        return None

    # ========================================
    # PRIORITY 1:
    # HERITAGE DESIGNATION
    # ========================================

    if metadata.get("P1435"):
        return "HISTORICAL_RELICT"

    # ========================================
    # PRIORITY 2:
    # INSTANCE OF (P31)
    # ========================================

    p31_values = metadata.get(
        "P31",
        []
    )

    for item in p31_values:

        if not isinstance(item, dict):
            continue

        label = item.get(
            "label",
            ""
        )

        inferred = (
            infer_semantic_type_from_text(
                label
            )
        )

        if inferred:
            return inferred

    # ========================================
    # PRIORITY 3:
    # COORDINATES
    # ========================================

    if metadata.get("P625"):
        return "LOC"

    return None

# ============================================================
# FINAL SEMANTIC RESOLUTION
# ============================================================

def resolve_semantic_type(
    metadata: dict,
    ner_type: str | None = None,
) -> str:

    # ========================================
    # METADATA FIRST
    # ========================================

    metadata_type = (
        infer_ner_from_metadata(
            metadata
        )
    )

    if metadata_type:
        return metadata_type

    # ========================================
    # NER FALLBACK
    # ========================================

    if ner_type:

        ner_type = (
            str(ner_type)
            .strip()
            .upper()
        )

        if ner_type in CIDOC_CLASS_MAPPING:
            return ner_type

    # ========================================
    # UNKNOWN
    # ========================================

    return "UNKNOWN"