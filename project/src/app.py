import json
import streamlit as st

from graph_query import HeritageGraphQuery

from groq_client import (
    ask_groq,
    extract_question_entities
)

from evidence_builder import (
    EvidenceBuilder
)

# ============================================================
# INIT
# ============================================================

st.set_page_config(
    page_title="Vietnam Heritage KG Chatbot",
    layout="wide"
)

graph = HeritageGraphQuery()

builder = EvidenceBuilder()

st.title("Vietnam Heritage Knowledge Graph Chatbot")

st.markdown("""
Hệ thống hỏi đáp sử dụng:
- Neo4j Knowledge Graph
- Multi-hop Graph Reasoning
- Wikidata + Wikipedia
- Groq LLM
""")

# ============================================================
# HELPERS
# ============================================================

def safe_json_load(raw_text):

    try:

        return json.loads(raw_text)

    except Exception:

        # fallback nếu LLM trả markdown
        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")

        return json.loads(raw_text)

def is_location_reasoning(reasoning_type):

    reasoning_type = (
        reasoning_type or ""
    ).lower()

    LOCATION_TYPES = [
        "location",
        "location-based",
        "geographical",
        "geography",
        "place",
        "spatial",
        "geo",
        "multi_hop"
    ]

    return any(
        rt in reasoning_type
        for rt in LOCATION_TYPES
    )

def detect_reasoning_type(parsed):

    reasoning = parsed.get(
        "reasoning",
        ""
    ).lower()

    return reasoning


# ============================================================
# USER INPUT
# ============================================================

question = st.text_input(
    "Nhập câu hỏi"
)

# ============================================================
# MAIN QA PIPELINE
# ============================================================

if question:

    st.divider()

    # ========================================================
    # STEP 1 — QUESTION ANALYSIS
    # ========================================================

    st.subheader("1. Question Analysis")

    try:

        analysis_raw = extract_question_entities(
            question
        )

        parsed = safe_json_load(
            analysis_raw
        )

    except Exception as e:

        st.error(
            f"Không thể parse question analysis: {e}"
        )

        st.stop()

    st.json(parsed)

    # ========================================================
# NORMALIZE PARSED OUTPUT
# ========================================================

    entity_label = (
        parsed.get("entity")
        or parsed.get("main_entity")
        or ""
    )

    target_location = (
        parsed.get("target_location")
        or parsed.get("location")
    )

    reasoning_type = (
        parsed.get("reasoning_type")
        or parsed.get("reasoning")
        or ""
    ).lower()

    # ========================================================
    # STEP 2 — GRAPH RETRIEVAL
    # ========================================================

    st.subheader("2. Graph Retrieval")

    evidence = None
    raw_results = None

    try:

        # ----------------------------------------------------
        # MULTI HOP LOCATION
        # ----------------------------------------------------

        if is_location_reasoning(reasoning_type):

            raw_results = graph.multi_hop_location_reasoning(
                entity_label=entity_label,
                target_location=target_location
            )

            evidence = builder.build_multi_hop_context(
                raw_results
            )

        # ----------------------------------------------------
        # MATERIAL QUERY
        # ----------------------------------------------------

        elif reasoning_type == "material":

            entities = graph.search_entity(
                entity_label
            )

            if entities:

                entity_id = entities[0]["id"]

                raw_results = graph.get_materials_of_site(
                    entity_id
                )

                evidence = builder.build_context(
                    raw_results
                )

        # ----------------------------------------------------
        # LOCATION QUERY
        # ----------------------------------------------------

        elif reasoning_type == "location":

            entities = graph.search_entity(
                entity_label
            )

            if entities:

                entity_id = entities[0]["id"]

                raw_results = graph.get_location_hierarchy(
                    entity_id
                )

                evidence = builder.build_multi_hop_context(
                    raw_results
                )

        # ----------------------------------------------------
        # DEFAULT SEARCH
        # ----------------------------------------------------

        else:

            raw_results = graph.search_entity(
                entity_label or question
            )

            evidence = builder.build_context(
                raw_results
            )

    except Exception as e:

        st.error(
            f"Lỗi Graph Retrieval: {e}"
        )

        st.stop()

    # ========================================================
    # SHOW RAW KG RESULTS
    # ========================================================

    with st.expander(
        "Raw KG Results",
        expanded=False
    ):

        st.json(raw_results)

    # ========================================================
    # STEP 3 — BUILD CONTEXT
    # ========================================================

    st.subheader("3. Evidence Context")

    context = evidence.get(
        "context",
        ""
    )

    provenance = evidence.get(
        "provenance",
        []
    )

    st.text_area(
        "Context",
        context,
        height=250
    )

    # ========================================================
    # STEP 4 — LLM REASONING
    # ========================================================

    st.subheader("4. LLM Reasoning")

    prompt = f"""

Bạn là hệ thống QA cho Heritage Knowledge Graph.

NHIỆM VỤ:

1. Chỉ sử dụng thông tin trong KNOWLEDGE GRAPH FACTS
làm factual evidence.

2. Nếu cần suy luận:
phải ghi rõ [LLM-INFERENCE]

3. Không được bịa fact.

4. Nếu KG không đủ dữ liệu:
nói rõ:
"Không tìm thấy trực tiếp trong KG"

5. Nếu tồn tại reasoning chain:
hãy phân tích chain từng bước.

==================================================

QUESTION:

{question}

==================================================

KNOWLEDGE GRAPH FACTS:

{context}

==================================================

FORMAT OUTPUT:

[KG-FACTS]
...

[REASONING]
...

[LLM-INFERENCE]
...

[FINAL ANSWER]
...

[PROVENANCE]
...

"""

    try:

        answer = ask_groq(
            question=question,
            evidence=evidence
        )

    except Exception as e:

        st.error(
            f"Lỗi gọi Groq: {e}"
        )

        st.stop()

    # ========================================================
    # FINAL ANSWER
    # ========================================================

    st.subheader("5. Final Answer")

    st.write(answer)

    # ========================================================
    # PROVENANCE
    # ========================================================

    with st.expander(
        "Provenance",
        expanded=False
    ):

        st.json(provenance)

    # ========================================================
    # DEBUG PANEL
    # ========================================================

    with st.expander(
        "Debug Info",
        expanded=False
    ):

        st.write("Reasoning Type:")
        st.code(reasoning_type)

        st.write("Entity:")
        st.code(entity_label)

        st.write("Target Location:")
        st.code(target_location)