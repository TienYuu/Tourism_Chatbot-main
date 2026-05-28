from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from ontology.relation_canonicalizer import (
    RelationCanonicalizer
)

class PathRanker:

    def __init__(self):

        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.canonicalizer = (
            RelationCanonicalizer()
        )
        # ==========================================
        # RELATION ALIASES
        # ==========================================

        self.relation_aliases = {

            "architect": [
                "architect",
                "designed by",
                "kiến trúc sư",
                "thiết kế",
                "kiến trúc sư của"
            ],

            "built_by": [
                "built by",
                "constructed by",
                "xây dựng",
                "do ai xây dựng",
                "được xây dựng bởi"
            ],

            "located_in": [
                "located in",
                "nằm ở",
                "ở",
                "ở đâu",
            ],

            "part_of": [
                "part of",
                "thuộc",
                "thuộc về",
                "là một phần của"
            ],

            "consists_of": [
                "consists of",
                "làm bằng",
                "được làm bằng",
                "chất liệu",
                "material used"
            ],

        }

        # ==========================================
        # EMBEDDING CACHE
        # ==========================================

        self.embedding_cache = {}

        # ==========================================
        # PRECOMPUTE ALIAS EMBEDDINGS
        # ==========================================

        self.alias_embeddings = {}

        for relation, aliases in self.relation_aliases.items():

            self.alias_embeddings[relation] = (
                self.embedding_model.encode(
                    aliases,
                    convert_to_numpy=True
                )
            )

    # =====================================================
    # MAIN SCORING
    # =====================================================

    def score_path(
        self,
        path,
        semantic_parse
    ):

        relation_score = self.score_relations(
            path,
            semantic_parse
        )

        structure_score = self.structure_score(
            path
        )

        target_score = self.target_score(
            path,
            semantic_parse
        )

        final_score = (
            relation_score * 0.55
            + structure_score * 0.25
            + target_score * 0.20
        )

        return round(float(final_score), 4)

    # =====================================================
    # RELATION SCORE
    # =====================================================

    def score_relations(
        self,
        path,
        semantic_parse
    ):

        edges = path.get("edges", [])

        if not edges:
            return 0.0

        requested_relations = semantic_parse.get(
            "relations",
            []
        )

        if not requested_relations:
            return 0.0

        edge_scores = []

        for idx, edge in enumerate(edges):

            relation = edge["relation"]

            score = self.semantic_relation_similarity(
                relation,
                requested_relations
            )

            # ======================================
            # POSITION WEIGHT
            # Earlier edges slightly more important
            # ======================================

            weight = 1 / (idx + 1)

            edge_scores.append(
                score * weight
            )

        return np.mean(edge_scores)

    
    def semantic_relation_similarity(
        self,
        graph_relation,
        requested_relations
    ):

        # =====================================================
        # GRAPH RELATION
        # =====================================================

        normalized_relation = (
            self.normalize_relation_name(
                graph_relation
            )
        )

        canonical_graph_relation = (
            self.canonicalizer
            .canonicalize(
                normalized_relation
            )
        )

        # =====================================================
        # REQUESTED RELATIONS
        # =====================================================

        canonical_requested = [

            self.canonicalizer
            .canonicalize(r)

            for r in requested_relations
        ]

        # =====================================================
        # EXACT MATCH BOOST
        # =====================================================

        if canonical_graph_relation in canonical_requested:

            return 1.0

        # =====================================================
        # EMBEDDING SIMILARITY
        # =====================================================

        graph_emb = self.get_embedding(
            canonical_graph_relation
        )

        best_score = 0.0

        for requested in canonical_requested:

            req_emb = self.get_embedding(
                requested
            )

            similarity = cosine_similarity(
                [graph_emb],
                [req_emb]
            )[0][0]

            if similarity > best_score:
                best_score = similarity
            print("=" * 50)
            print("GRAPH RELATION:", graph_relation)
            print("NORMALIZED:", normalized_relation)
            print("REQUESTED:", requested_relations)
            print("CANONICAL:", canonical_requested)
        return float(best_score)
    

    # =====================================================
    # STRUCTURE SCORE
    # =====================================================

    def structure_score(
        self,
        path
    ):

        edges = path.get("edges", [])

        if not edges:
            return 0.0

        length = len(edges)

        # ==========================================
        # Prefer shorter reasoning chains
        # ==========================================

        return max(
            0.0,
            1.0 - (length - 1) * 0.15
        )

    # =====================================================
    # TARGET TYPE SCORE
    # =====================================================

    def target_score(
        self,
        path,
        semantic_parse
    ):

        target = str(

            semantic_parse.get(
                "target"
            )

            or

            semantic_parse.get(
                "target_type"
            )

            or

            ""

        ).lower()

        if not target:
            return 0.0

        edges = path.get("edges", [])

        if not edges:
            return 0.0

        last_edge = edges[-1]

        labels = last_edge.get(
            "target_labels",
            []
        )

        if not labels:
            return 0.0

        label_scores = []

        target_emb = self.get_embedding(
            target
        )

        for label in labels:

            label_emb = self.get_embedding(
                label.lower()
            )

            sim = cosine_similarity(
                [target_emb],
                [label_emb]
            )[0][0]

            label_scores.append(sim)

        return float(np.max(label_scores))

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def normalize_relation_name(
        self,
        relation
    ):

        relation = relation.lower()

        ontology_map = {

            "p14_carried_out_by":
                "architect",

            "p108_was_produced_by":
                "built_by",

            "p53_has_former_or_current_location":
                "located_in",

            "p46_is_composed_of":
                "part_of",

            "p45_consists_of":
                "material_used",

            "p4_has_time_span":
                "time_span",

            "p130_shows_features_of":
                "related_to"
        }

        return ontology_map.get(
            relation,
            relation
        )

    # =====================================================
    # EMBEDDING CACHE
    # =====================================================

    def get_embedding(
        self,
        text
    ):

        text = text.lower()

        if text not in self.embedding_cache:

            self.embedding_cache[text] = (
                self.embedding_model.encode(
                    text,
                    convert_to_numpy=True
                )
            )

        return self.embedding_cache[text]