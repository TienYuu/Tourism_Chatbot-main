# reasoning/semantic_parser.py

import json


SYSTEM_PROMPT = """
You are a semantic parser for a historical knowledge graph QA system.

Your task:

Convert user question into structured reasoning intent.

Return JSON only.

Output format:

{
    "target": "...",
    "question_type": "...",
    "constraints": [],
    "relations": [],
    "reasoning_depth": 2
}

Rules:

- Do NOT generate Cypher.
- Do NOT answer the question.
- Only extract semantic meaning.
- reasoning_depth:
    1 = direct relation
    2 = multi-hop
    3 = complex reasoning
"""


class SemanticParser:

    def __init__(self, groq_client):
        self.groq_client = groq_client
    
    # =====================================================
# RULE-BASED RELATION DETECTION
# =====================================================

    # =====================================================
# RULE-BASED RELATION DETECTION
# =====================================================

    def rule_based_relation_detection(
        self,
        question
    ):

        q = str(
            question or ""
        ).lower()

        coordinate_keywords = [

            "kinh độ",
            "vĩ độ",
            "tọa độ",
            "coordinates",
            "latitude",
            "longitude"
        ]

        if any(
            k in q
            for k in coordinate_keywords
        ):

            return "coordinates"

        architect_keywords = [

            "kiến trúc sư",
            "architect",
            "thiết kế"
        ]

        if any(
            k in q
            for k in architect_keywords
        ):

            return "architect"

        return None

    def parse(self, question: str):

        user_prompt = f"""
Question:
{question}

Return JSON only.
"""

        response = self.groq_client.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

        try:

            parsed = json.loads(response)

        except Exception:

            parsed = {

                "target": None,

                "question_type": "unknown",

                "constraints": [],

                "relations": [],

                "reasoning_depth": 2
            }

        # =====================================================
        # RULE-BASED FALLBACK
        # =====================================================

        fallback_relation = (

            self.rule_based_relation_detection(
                question
            )
        )

        if fallback_relation:

            if not parsed.get("relations"):

                parsed["relations"] = [
                    fallback_relation
                ]

            if (
                not parsed.get(
                    "question_type"
                )
                or parsed.get(
                    "question_type"
                ) == "unknown"
            ):

                parsed["question_type"] = (
                    fallback_relation
                )

        return parsed
        
    
    