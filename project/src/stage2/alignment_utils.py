from rapidfuzz import fuzz


class EntityAligner:

    def __init__(
        self,
        threshold=90
    ):

        self.threshold = threshold

    def is_same_entity(
        self,
        a: str,
        b: str
    ):

        score = fuzz.token_sort_ratio(
            a.lower(),
            b.lower()
        )

        return score >= self.threshold