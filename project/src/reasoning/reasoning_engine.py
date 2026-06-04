# reasoning/reasoning_engine.py
from reasoning.property_reasoner import PropertyReasoner

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
        
        self.property_reasoner = PropertyReasoner(
            traversal_engine.graph_query
        )

    def extract_answer(
        self,
        reasoning_paths,
        semantic_parse=None
    ):
        if not reasoning_paths:
            return "Không tìm thấy câu trả lời."

        # Multi-hop architect query: prefer longer path to the actual work
        if semantic_parse and semantic_parse.get("question_type") == "architect_works":
            for path in reasoning_paths:
                if len(path.get("edges", [])) > 1:
                    last_edge = path["edges"][-1]
                    return last_edge.get("target_label", "Không rõ")
            return "Không tìm thấy câu trả lời."

        best_path = reasoning_paths[0]

        if not best_path["edges"]:
            return "Không tìm thấy câu trả lời."

        last_edge = best_path["edges"][-1]
        answer = last_edge.get("target_label", "Không rõ")
        return answer

    # =====================================================
    # MAIN QA PIPELINE
    # =====================================================
    
    def answer_question(self, question):
        # ==========================================
        # STEP 1: SEMANTIC PARSE
        # ==========================================
        semantic_parse = self.semantic_parser.parse(question)

        # ==========================================
        # STEP 2: ENTITY EXTRACTION
        # ==========================================
        entities = self.entity_linker.extract_entities_from_question(question)

        if not entities:
            return {
                "error": "No entity found.",
                "semantic_parse": semantic_parse
            }

        root_entity = entities[0]

        # ==========================================
        # STEP 3: BUILD PLAN
        # ==========================================
        plan = self.planner.build_plan(semantic_parse)

        # ==========================================
        # STEP 4: TRAVERSAL & PROPERTY REASONING
        # ==========================================
        property_answer = self.property_reasoner.answer_property_question(
            root_entity["id"],
            semantic_parse
        )

        if property_answer:
            return {
                "final_answer": self.format_property_answer(
                    root_entity,
                    semantic_parse,
                    property_answer
                ),
                "reasoning_type": "property_retrieval",
                "reasoning_paths": [],
                "root_entity": root_entity,
                "semantic_parse": semantic_parse,
                "plan": {"strategy": "property_retrieval"}
            }

        reasoning_paths = self.traversal_engine.beam_search(
            start_entity_id=root_entity["id"],
            semantic_parse=semantic_parse,
            beam_width=plan["beam_width"],
            max_depth=plan["max_depth"]
        )

        # ==========================================
        # STEP 5: SELECT BEST PATH
        # ==========================================
        best_paths = reasoning_paths[:5]

        # ==========================================
        # STEP 6: BUILD RESPONSE
        # ==========================================
        best_answer = self.extract_answer(reasoning_paths, semantic_parse)
        answer = self.build_answer(
            question,
            semantic_parse,
            reasoning_paths,
            root_entity
        )
        final_answer = self.format_final_answer(
            root_entity,
            semantic_parse,
            answer,
            best_answer
        )

        return {
            "question": question,
            "semantic_parse": semantic_parse,
            "root_entity": root_entity,
            "plan": plan,
            "reasoning_paths": best_paths,
            "final_answer": final_answer,
            "answer": answer
        }

    def format_property_answer(
        self,
        root_entity,
        semantic_parse,
        property_answer
    ):
        root_label = root_entity.get("label", "mục tiêu")
        answer_text = property_answer.get("answer", "Không tìm thấy câu trả lời.")
        relation = None

        if semantic_parse:
            relations = semantic_parse.get("relations", [])
            relation = relations[0] if relations else semantic_parse.get("question_type")

        relation = str(relation or "").lower()

        if "coordinates" in relation or "tọa độ" in relation:
            return f"Theo KG, tọa độ của {root_label} là {answer_text}."

        if "address" in relation or "địa chỉ" in relation:
            return f"Theo KG, {root_label} có địa chỉ: {answer_text}."

        if "description" in relation or "mô tả" in relation or "thông tin" in relation:
            return f"Theo KG, thông tin về {root_label}: {answer_text}."

        if "country" in relation or "nước" in relation or "quốc gia" in relation:
            return f"Theo KG, {root_label} thuộc {answer_text}."

        return answer_text
        
    # =====================================================
    # ANSWER BUILDER
    # =====================================================

    def build_answer(
        self,
        question,
        semantic_parse,
        paths,
        root_entity=None
    ):
        if not paths:
            return "Không tìm thấy thông tin."

        if semantic_parse.get("question_type") == "architect_works":
            root_label = root_entity.get("label") if root_entity else None
            filtered_paths = []
            for p in paths:
                edges = p.get("edges", [])
                if len(edges) <= 1:
                    continue
                last_edge = edges[-1]
                if root_label and last_edge.get("target_label") == root_label:
                    continue
                filtered_paths.append(p)
            paths = filtered_paths

        answers = []

        for path in paths:
            edges = path["edges"]
            if not edges:
                continue

            if semantic_parse.get("question_type") == "architect_works" and len(edges) > 1:
                first_edge = edges[0]
                final_edge = edges[-1]

                answers.append({
                    "answer": first_edge["target_label"],
                    "relation": first_edge["relation"],
                    "score": path["score"]
                })
                answers.append({
                    "answer": final_edge["target_label"],
                    "relation": final_edge["relation"],
                    "score": path["score"]
                })
            else:
                final_edge = edges[-1]
                answers.append({
                    "answer": final_edge["target_label"],
                    "relation": final_edge["relation"],
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

    def format_final_answer(
        self,
        root_entity,
        semantic_parse,
        answers,
        fallback_answer
    ):
        question_type = semantic_parse.get("question_type", "")
        root_label = root_entity.get("label", "mục tiêu")

        def unique_answer_texts(answer_list):
            texts = [a["answer"] for a in answer_list]
            unique_texts = []
            seen = set()
            for text in texts:
                if text not in seen:
                    seen.add(text)
                    unique_texts.append(text)
            return unique_texts

        if question_type == "architect_works":
            if isinstance(answers, list) and answers:
                architect_answers = [
                    a for a in answers
                    if a["relation"] in ("P14_carried_out_by", "architect")
                ]
                work_answers = [
                    a for a in answers
                    if a["relation"] not in ("P14_carried_out_by", "architect")
                ]

                works = unique_answer_texts(work_answers)

                if architect_answers and works:
                    architect_name = architect_answers[0]["answer"]
                    works_text = ", ".join(works)
                    return (
                        f"Theo KG, kiến trúc sư của {root_label} là {architect_name}; "
                        f"các công trình do kiến trúc sư này thiết kế gồm: {works_text}."
                    )

                if works:
                    works_text = ", ".join(works)
                    return f"Theo KG, các công trình do kiến trúc sư của {root_label} thiết kế gồm: {works_text}."

                if architect_answers:
                    architect_name = architect_answers[0]["answer"]
                    return f"Theo KG, kiến trúc sư của {root_label} là {architect_name}."

            if fallback_answer and fallback_answer != "Không tìm thấy câu trả lời.":
                return f"Theo KG, kiến trúc sư của {root_label} là {fallback_answer}."

            return f"Theo KG, không tìm thấy công trình thiết kế bởi kiến trúc sư của {root_label}."

        if isinstance(answers, list) and answers:
            relation_names = [
                a["relation"].lower() for a in answers if a.get("relation")
            ]
            texts = unique_answer_texts(answers)

            if question_type in ("architect", "architect_works"):
                if len(texts) == 1:
                    return f"Theo KG, kiến trúc sư của {root_label} là {texts[0]}."
                return f"Theo KG, các kiến trúc sư của {root_label} gồm: {', '.join(texts)}."

            if question_type in ("built_by", "founded_by"):
                if len(texts) == 1:
                    return f"Theo KG, {root_label} được xây dựng bởi {texts[0]}."
                return f"Theo KG, {root_label} được xây dựng bởi: {', '.join(texts)}."

            if question_type == "located_in" or any(
                rel in ("located_in", "location") for rel in relation_names
            ):
                if len(texts) == 1:
                    return f"Theo KG, {root_label} nằm ở {texts[0]}."
                return f"Theo KG, {root_label} nằm ở: {', '.join(texts)}."

            if question_type == "material_used" or any(
                rel in ("material_used", "P45_consists_of") for rel in relation_names
            ):
                if len(texts) == 1:
                    return f"Theo KG, {root_label} được làm bằng {texts[0]}."
                return f"Theo KG, {root_label} được làm bằng: {', '.join(texts)}."

            if len(texts) == 1:
                return f"Theo KG, câu trả lời là {texts[0]}."
            return f"Theo KG, các câu trả lời gồm: {', '.join(texts)}."

        if isinstance(answers, str) and answers:
            if answers != "Không tìm thấy thông tin.":
                return f"Theo KG, câu trả lời là {answers}."
            return "Theo KG, không tìm thấy câu trả lời phù hợp."

        return fallback_answer