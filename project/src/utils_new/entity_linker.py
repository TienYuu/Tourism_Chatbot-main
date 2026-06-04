# utils_new /entity_linker.py

from rapidfuzz import fuzz
from collections import OrderedDict

from utils_new.text_normalizer import normalize_text


class EntityLinker:

    def __init__(self, graph_query, max_cache_size=1000):
        self.graph_query = graph_query
        self.max_cache_size = max_cache_size

        # cache normalized entity names
        self.entity_cache = self._build_entity_cache()
        
        # OPTIMIZATION 6: LRU cache for link results
        # Limited to max_cache_size to avoid unbounded memory growth
        self.lru_link_cache = OrderedDict()  # {query_hash: result}
        
        # OPTIMIZATION 7: Hierarchical entity index by type
        # Structure: {entity_type: [entities_of_type]}
        # Common types: PERSON, PLACE, FAC, EVENT, ARTIFACT, etc.
        self.entity_index_by_type = self._build_hierarchical_index()

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
    
    def _build_hierarchical_index(self):
        """
        🔥 OPTIMIZATION 7: Build hierarchical index by entity type
        Structure: {entity_type: [entities_of_type]}
        Enables faster filtering when question specifies type
        """
        index_by_type = {}
        
        for entity in self.entity_cache:
            labels = entity.get("raw", {}).get("labels", [])
            
            # Default to "OTHER" if no labels
            if not labels:
                labels = ["OTHER"]
            
            # Index entity under each of its types
            for entity_type in labels:
                if entity_type not in index_by_type:
                    index_by_type[entity_type] = []
                index_by_type[entity_type].append(entity)
        
        return index_by_type
    
    def link_entity_by_type(
        self,
        query: str,
        entity_type=None,
        threshold: int = 80
    ):
        """
        Link entity with optional type filtering.
        OPTIMIZATION 7: Uses hierarchical index for faster lookup
        
        If entity_type is specified:
        - Only search within that type (e.g., "PERSON", "PLACE")
        - 5-10x faster than searching all entities
        """
        if entity_type and entity_type in self.entity_index_by_type:
            # Search only within specified type
            candidates = self.entity_index_by_type[entity_type]
        else:
            # Search all entities if no type specified
            candidates = self.entity_cache
        
        normalized_query = normalize_text(query)
        best_score = -1
        best_entity = None
        
        for entity in candidates:
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

    def link_entity(
        self,
        query: str,
        threshold: int = 80
    ):
        """
        Find best matching entity.
        OPTIMIZATION 6: Uses LRU cache for repeated queries
        """
        
        # OPTIMIZATION 6: Check LRU cache first
        cache_key = f"{query}:{threshold}"
        if cache_key in self.lru_link_cache:
            # Move to end (most recently used)
            self.lru_link_cache.move_to_end(cache_key)
            return self.lru_link_cache[cache_key]

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
            result = None
        else:
            result = {
                "score": best_score,
                "entity": best_entity
            }
        
        # OPTIMIZATION 6: Store in LRU cache with size limit
        if len(self.lru_link_cache) >= self.max_cache_size:
            # Remove least recently used (first item)
            self.lru_link_cache.popitem(last=False)
        
        self.lru_link_cache[cache_key] = result
        
        return result

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