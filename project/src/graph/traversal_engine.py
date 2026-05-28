from collections import deque
import heapq


class TraversalEngine:

    def __init__(
        self,
        graph_query,
        path_ranker
    ):

        self.graph_query = graph_query
        self.path_ranker = path_ranker

    # =====================================================
    # SEMANTIC BEAM SEARCH
    # =====================================================

    def beam_search(
        self,
        start_entity_id,
        semantic_parse,
        beam_width=5,
        max_depth=3,
        min_score_threshold=0.25
    ):

        initial_path = {
            "nodes": [start_entity_id],
            "edges": [],
            "score": 0.0
        }

        beams = [initial_path]

        completed_paths = []

        global_visited = set()

        for depth in range(max_depth):

            candidate_paths = []

            for path in beams:

                current_node = path["nodes"][-1]

                # =====================================
                # NODE CACHE
                # =====================================

                cache_key = (
                    current_node,
                    depth
                )

                if cache_key in global_visited:
                    continue

                global_visited.add(cache_key)

                neighbors = (
                    self.graph_query
                    .expand_bidirectional(
                        current_node
                    )
                )

                # =====================================
                # SEMANTIC FILTERING
                # =====================================

                neighbors = self.filter_neighbors(
                    neighbors,
                    semantic_parse
                )

                for edge in neighbors:

                    next_node = edge["target_id"]

                    # =================================
                    # CYCLE DETECTION
                    # =================================

                    if next_node in path["nodes"]:
                        continue

                    new_path = {

                        "nodes":
                            path["nodes"] + [next_node],

                        "edges":
                            path["edges"] + [edge],

                        "score": 0.0
                    }

                    # =================================
                    # INCREMENTAL SCORING
                    # =================================

                    score = self.path_ranker.score_path(
                        new_path,
                        semantic_parse
                    )

                    new_path["score"] = score

                    # =================================
                    # SCORE FILTER
                    # =================================

                    if score < min_score_threshold:
                        continue

                    candidate_paths.append(
                        new_path
                    )

            # =========================================
            # DIVERSITY-AWARE RANKING
            # =========================================

            candidate_paths = (
                self.diversity_rerank(
                    candidate_paths
                )
            )

            # =========================================
            # KEEP BEST
            # =========================================

            beams = sorted(
                candidate_paths,
                key=lambda x: x["score"],
                reverse=True
            )[:beam_width]

            completed_paths.extend(beams)

            # =========================================
            # EARLY STOPPING
            # =========================================

            if self.should_stop(
                beams,
                semantic_parse
            ):
                break

        completed_paths = sorted(
            completed_paths,
            key=lambda x: x["score"],
            reverse=True
        )

        return completed_paths

    # =====================================================
    # SEMANTIC NEIGHBOR FILTER
    # =====================================================

    def filter_neighbors(
        self,
        neighbors,
        semantic_parse
    ):

        requested_relations = semantic_parse.get(
            "relations",
            []
        )

        if not requested_relations:
            return neighbors

        filtered = []

        for edge in neighbors:

            relation = edge["relation"]

            score = (
                self.path_ranker
                .semantic_relation_similarity(
                    relation,
                    requested_relations
                )
            )

            edge["relation_score"] = score

            if score > 0.35:
                filtered.append(edge)

        # fallback
        if not filtered:
            return neighbors[:10]

        filtered.sort(
            key=lambda x: x["relation_score"],
            reverse=True
        )

        return filtered[:15]

    # =====================================================
    # DIVERSITY RERANK
    # =====================================================

    def diversity_rerank(
        self,
        candidate_paths
    ):

        selected = []

        used_relations = set()

        sorted_paths = sorted(
            candidate_paths,
            key=lambda x: x["score"],
            reverse=True
        )

        for path in sorted_paths:

            relations = tuple([
                e["relation"]
                for e in path["edges"]
            ])

            if relations in used_relations:
                continue

            used_relations.add(relations)

            selected.append(path)

        return selected

    # =====================================================
    # EARLY STOPPING
    # =====================================================

    def should_stop(
        self,
        beams,
        semantic_parse
    ):

        if not beams:
            return True

        best_score = beams[0]["score"]

        # strong semantic confidence
        if best_score > 0.92:
            return True

        return False