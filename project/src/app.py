# app.py

import streamlit as st

from groq_client import GroqClient

from graph.graph_query import GraphQuery
from graph.traversal_engine import TraversalEngine

from dotenv import load_dotenv
import os
load_dotenv()

from reasoning.semantic_parser import SemanticParser
from reasoning.path_ranker import PathRanker
from reasoning.planner import Planner
from reasoning.reasoning_engine import ReasoningEngine

from utils_new.entity_linker import EntityLinker


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Historical KG Reasoning",
    layout="wide"
)

st.title("Historical KG Reasoning System")

# =========================================================
# ENV CONFIG
# =========================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")

NEO4J_USER = os.getenv("NEO4J_USER")

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

# =========================================================
# INIT SYSTEM
# =========================================================

def initialize_system():

    st.write("Init GraphQuery")
    graph_query = GraphQuery(
        uri=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )

    st.write("Init GroqClient")
    groq_client = GroqClient(
        api_key=GROQ_API_KEY
    )

    st.write("Init EntityLinker")
    entity_linker = EntityLinker(
        graph_query
    )

    st.write("Init SemanticParser")
    semantic_parser = SemanticParser(
        groq_client
    )

    st.write("Init PathRanker")
    path_ranker = PathRanker()

    st.write("Init TraversalEngine")
    traversal_engine = TraversalEngine(
        graph_query=graph_query,
        path_ranker=path_ranker
    )

    st.write("Init Planner")
    planner = Planner()

    st.write("Init ReasoningEngine")
    reasoning_engine = ReasoningEngine(
        semantic_parser=semantic_parser,
        entity_linker=entity_linker,
        planner=planner,
        traversal_engine=traversal_engine
    )

    return reasoning_engine


# =========================================================
# INIT BUTTON
# =========================================================

if st.button("Initialize System"):

    try:

        st.session_state.system = (
            initialize_system()
        )

        st.success("System initialized.")

    except Exception as e:

        st.error(str(e))

# =========================================================
# QUESTION INPUT
# =========================================================

question = st.text_input(
    "Ask a historical question:",
    value="Ai là kiến trúc sư của Dinh Độc Lập?"
)

# =========================================================
# RUN REASONING
# =========================================================

if st.button("Run Reasoning"):

    if "system" not in st.session_state:

        st.error(
            "Please initialize system first."
        )

    else:

        with st.spinner("Reasoning..."):

            result = (
                st.session_state.system
                .answer_question(question)
            )

        # =================================================
        # ANSWER
        # =================================================

        st.header("Final Answer")

        st.success(

            result.get(
                "final_answer",
                "No answer found."
            )
        )

        # =================================================
        # REASONING ANSWER
        # =================================================

        if "answer" in result:

            st.header("Reasoning Answer")

            st.json(
                result["answer"]
            )

        elif result.get(
            "reasoning_type"
        ) == "property_retrieval":

            st.header(
                "Property Retrieval"
            )

            st.info(
                "Answer retrieved directly "
                "from entity properties."
            )
        # =================================================
        # ROOT ENTITY
        # =================================================

        st.header("Root Entity")

        st.json(
            result.get(
                "root_entity",
                {}
            )
        )

        # =================================================
        # SEMANTIC PARSE
        # =================================================

        st.header("Semantic Parse")

        st.json(
            result.get(
                "semantic_parse",
                {}
            )
        )

        # =================================================
        # REASONING PLAN
        # =================================================

        st.header("Reasoning Plan")

        st.json(
            result.get(
                "plan",
                {}
            )
        )

        # =================================================
        # REASONING PATHS
        # =================================================

        st.header("Reasoning Paths")

        paths = result.get(
            "reasoning_paths",
            []
        )

        if not paths:

            st.warning("No paths found.")

        else:

            for idx, path in enumerate(paths):

                with st.expander(
                    f"Path {idx+1} | Score: {round(path['score'], 3)}"
                ):

                    st.write("### Nodes")

                    st.write(path["nodes"])

                    st.write("### Edges")

                    for edge in path["edges"]:

                        st.json(edge)

# =========================================================
# SAMPLE QUESTIONS
# =========================================================

st.sidebar.header("Sample Questions")

samples = [

    "Ai là kiến trúc sư của Dinh Độc Lập?",

    "Dinh Độc Lập nằm ở đâu?",

    "Những công trình nào do kiến trúc sư của Dinh Độc Lập thiết kế?",

    "Công trình nào thuộc Quận 1?",

    "Ai xây dựng Dinh Độc Lập?"
]

for s in samples:

    st.sidebar.write(f"- {s}")