# reasoning/planner.py


class Planner:

    def build_plan(
        self,
        semantic_parse
    ):

        reasoning_depth = (
            semantic_parse.get(
                "reasoning_depth",
                1
            )
        )

        question_type = (
            semantic_parse.get(
                "question_type",
                "factoid"
            )
        )

        # ==========================================
        # PLAN DEFAULTS
        # ==========================================

        plan = {

            "strategy": "beam_search",

            "beam_width": 5,

            "max_depth": 2,

            "expand_limit": 50
        }

        # ==========================================
        # MULTI HOP
        # ==========================================

        if reasoning_depth >= 2:

            plan["max_depth"] = 3
            plan["beam_width"] = 8

        # ==========================================
        # COMPLEX REASONING
        # ==========================================

        if reasoning_depth >= 3:

            plan["max_depth"] = 4
            plan["beam_width"] = 10

        # ==========================================
        # LIST QUESTIONS
        # ==========================================

        if question_type == "list":

            plan["beam_width"] += 5

        return plan