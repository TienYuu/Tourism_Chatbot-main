# utils_new /entity_linker.py

from rapidfuzz import fuzz

from utils_new.text_normalizer import normalize_text


class EntityLinker:

    def __init__(self, graph_query):
        self.graph_query = graph_query

        # cache normalized entity names
        self.entity_cache = self._build_entity_cache()

    def _build_entity_cache(self):
        """
        Load all entities from graph.
        """

        entities = self.graph_query.get_all_entities()

        cache = []

        for entity in entities:

            label = entity.get("label", "")
            entity_id = entity.get("id")

            normalized = normalize_text(label)

            cache.append({
                "id": entity_id,
                "label": label,
                "normalized": normalized,
                "raw": entity
            })

        return cache

    def link_entity(
        self,
        query: str,
        threshold: int = 80
    ):
        """
        Find best matching entity.
        """

        normalized_query = normalize_text(query)

        best_score = -1
        best_entity = None

        for entity in self.entity_cache:

            score = fuzz.token_set_ratio(
                normalized_query,
                entity["normalized"]
            )

            if score > best_score:
                best_score = score
                best_entity = entity

        if best_score < threshold:
            return None

        return {
            "score": best_score,
            "entity": best_entity
        }

    def extract_entities_from_question(
        self,
        question: str
    ):
        """
        Naive entity extraction by scanning entities.
        Can later replace with LLM NER.
        """

        normalized_question = normalize_text(question)

        found_entities = []

        for entity in self.entity_cache:

            if entity["normalized"] in normalized_question:

                found_entities.append(entity)

        return found_entities