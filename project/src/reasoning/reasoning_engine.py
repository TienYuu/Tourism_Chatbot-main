# reasoning/reasoning_engine.py
from reasoning.property_reasoner import (
    PropertyReasoner
)

class ReasoningEngine:

    def __init__(
        self,
        semantic_parser,
        entity_linker,
        planner,
        traversal_engine
    ):

        self.semantic_parser = semantic_parser

        self.entity_linker = entity_linker

        self.planner = planner

        self.traversal_engine = traversal_engine
        
        self.property_reasoner = (
            PropertyReasoner(
                traversal_engine.graph_query
            )
)
    def extract_answer(
        self,
        reasoning_paths
    ):

        if not reasoning_paths:
            return "Không tìm thấy câu trả lời."

        best_path = reasoning_paths[0]

        if not best_path["edges"]:
            return "Không tìm thấy câu trả lời."

        last_edge = best_path["edges"][-1]

        answer = last_edge.get(
            "target_label",
            "Không rõ"
        )

        return answer

    # =====================================================
    # MAIN QA PIPELINE
    # =====================================================
    
    def answer_question(
        self,
        question
    ):

        # ==========================================
        # STEP 1: SEMANTIC PARSE
        # ==========================================

        semantic_parse = (
            self.semantic_parser.parse(question)
        )

        # ==========================================
        # STEP 2: ENTITY EXTRACTION
        # ==========================================

        entities = (
            self.entity_linker
            .extract_entities_from_question(
                question
            )
        )

        if not entities:

            return {
                "error":
                    "No entity found.",
                "semantic_parse":
                    semantic_parse
            }

        root_entity = entities[0]

        # ==========================================
        # STEP 3: BUILD PLAN
        # ==========================================

        plan = self.planner.build_plan(
            semantic_parse
        )

        # ==========================================
        # STEP 4: TRAVERSAL
        # ==========================================
        # =====================================================
# PROPERTY REASONING
# =====================================================

        property_answer = (

            self.property_reasoner
            .answer_property_question(

                root_entity["id"],
                semantic_parse
            )
        )

        if property_answer:

            return {

                "final_answer":
                    property_answer["answer"],

                "reasoning_type":
                    "property_retrieval",

                "reasoning_paths": [],

                "root_entity":
                    root_entity,

                "semantic_parse":
                    semantic_parse,

                "plan":
                    {
                        "strategy":
                            "property_retrieval"
                    }
            }

        reasoning_paths = (
            self.traversal_engine
            .beam_search(
                start_entity_id=root_entity["id"],
                semantic_parse=semantic_parse,
                beam_width=plan["beam_width"],
                max_depth=plan["max_depth"]
            )
        )

        # ==========================================
        # STEP 5: SELECT BEST PATH
        # ==========================================

        best_paths = reasoning_paths[:5]

        # ==========================================
        # STEP 6: BUILD RESPONSE
        # ==========================================
        best_answer = self.extract_answer(
              reasoning_paths
        )
        answer = self.build_answer(
            question,
            semantic_parse,
            best_paths
        )

        return {

            "question": question,

            "semantic_parse":
                semantic_parse,

            "root_entity":
                root_entity,

            "plan":
                plan,

            "reasoning_paths":
                best_paths,
            
            "final_answer": best_answer,

            "answer":
                answer
        }
        
    # =====================================================
    # ANSWER BUILDER
    # =====================================================

    def build_answer(
        self,
        question,
        semantic_parse,
        paths
    ):

        if not paths:
            return "Không tìm thấy thông tin."

        answers = []

        for path in paths:

            edges = path["edges"]

            if not edges:
                continue

            final_edge = edges[-1]

            target_label = (
                final_edge["target_label"]
            )

            relation = (
                final_edge["relation"]
            )

            answers.append({
                "answer": target_label,
                "relation": relation,
                "score": path["score"]
            })

        # deduplicate
        unique_answers = []

        seen = set()

        for ans in answers:

            key = ans["answer"]

            if key in seen:
                continue

            seen.add(key)

            unique_answers.append(ans)

        return unique_answers