# reasoning/traversal_engine.py
from collections import deque
import heapq
import numpy as np

class TraversalEngine:

    def __init__(self, graph_query, path_ranker):
        self.graph_query = graph_query
        self.path_ranker = path_ranker
        self.relation_type_cache = {}
        
        # OPTIMIZATION 5: Relation-specific cache
        # Cache structure: {(entity_id, relation_type): neighbors_list}
        self.relation_specific_cache = {}

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
        
        # OPTIMIZATION 2: Dynamic beam width tracking
        depth_quality_scores = {}

        for depth in range(max_depth):
            candidate_paths = []

            for path in beams:
                current_node = path["nodes"][-1]

                # =====================================
                # NODE CACHE
                # =====================================
                cache_key = (current_node, depth)
                if cache_key in global_visited:
                    continue

                global_visited.add(cache_key)
                
                # OPTIMIZATION 1: Try semantic filter first at Cypher level
                relation_types = self._extract_relation_types(semantic_parse)
                
                # OPTIMIZATION 5: Check relation-specific cache first
                cache_key_rel = (current_node, tuple(relation_types) if relation_types else None)
                if cache_key_rel in self.relation_specific_cache:
                    neighbors = self.relation_specific_cache[cache_key_rel]
                elif relation_types:
                    neighbors = self.graph_query.expand_with_semantic_filter(
                        current_node,
                        relation_types
                    )
                    # Store in relation-specific cache
                    self.relation_specific_cache[cache_key_rel] = neighbors
                else:
                    neighbors = self.graph_query.expand_bidirectional(current_node)

                # =====================================
                # SEMANTIC FILTERING (Python-level)
                # =====================================
                neighbors = self.filter_neighbors(neighbors, semantic_parse)

                for edge in neighbors:
                    next_node = edge["target_id"]

                    # =================================
                    # CYCLE DETECTION
                    # =================================
                    if next_node in path["nodes"]:
                        continue

                    new_path = {
                        "nodes": path["nodes"] + [next_node],
                        "edges": path["edges"] + [edge],
                        "score": 0.0
                    }

                    # =================================
                    # INCREMENTAL SCORING
                    # =================================
                    score = self.path_ranker.score_path(new_path, semantic_parse)
                    new_path["score"] = score

                    # =================================
                    # SCORE FILTER
                    # =================================
                    if score < min_score_threshold:
                        continue

                    candidate_paths.append(new_path)

            # =========================================
            # OPTIMIZATION 2: DYNAMIC BEAM WIDTH
            # =========================================
            if candidate_paths:
                scores = [p["score"] for p in candidate_paths]
                avg_quality = np.mean(scores) if scores else 0.0
                max_quality = max(scores) if scores else 0.0
                
                depth_quality_scores[depth] = {
                    "avg": avg_quality,
                    "max": max_quality
                }
                
                quality_ratio = avg_quality / max(max_quality, 0.1)
                adaptive_beam = max(3, int(beam_width * quality_ratio))
            else:
                adaptive_beam = beam_width
            
            # =========================================
            # KEEP BEST (with adaptive width)
            # =========================================
            beams = sorted(
                candidate_paths,
                key=lambda x: x["score"],
                reverse=True
            )[:adaptive_beam]

            completed_paths.extend(beams)

            # =========================================
            # EARLY STOPPING (enhanced)
            # =========================================
            if self.should_stop(beams, semantic_parse, depth_quality_scores):
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

    def filter_neighbors(self, neighbors, semantic_parse):
        requested_relations = semantic_parse.get("relations", [])

        if not requested_relations:
            return neighbors

        filtered = []

        for edge in neighbors:
            relation = edge["relation"]
            score = self.path_ranker.semantic_relation_similarity(
                relation,
                requested_relations
            )

            edge["relation_score"] = score

            if score > 0.35:
                filtered.append(edge)

        # fallback
        if not filtered:
            return neighbors[:10]

        filtered.sort(key=lambda x: x["relation_score"], reverse=True)
        return filtered[:15]

    # =====================================================
    # DIVERSITY RERANK
    # =====================================================

    def diversity_rerank(self, candidate_paths):
        selected = []
        used_relations = set()

        sorted_paths = sorted(
            candidate_paths,
            key=lambda x: x["score"],
            reverse=True
        )

        for path in sorted_paths:
            relations = tuple([e["relation"] for e in path["edges"]])

            if relations in used_relations:
                continue

            used_relations.add(relations)
            selected.append(path)

        return selected

    # =====================================================
    # OPTIMIZATION 3: EARLY STOPPING (Enhanced)
    # =====================================================

    def should_stop(self, beams, semantic_parse, depth_quality_scores=None):
        """Enhanced early stopping with quality checking"""
        if not beams:
            return True

        best_score = beams[0]["score"]

        # Strategy 1: Strong semantic confidence
        if best_score > 0.92:
            return True
        
        # Strategy 2: Diminishing quality
        if depth_quality_scores and len(depth_quality_scores) >= 2:
            last_depth = max(depth_quality_scores.keys())
            prev_depth = last_depth - 1
            
            if prev_depth in depth_quality_scores:
                last_quality = depth_quality_scores[last_depth]["avg"]
                prev_quality = depth_quality_scores[prev_depth]["avg"]
                
                if last_quality < prev_quality * 0.85:
                    return True

        return False
    
    # =====================================================
    # HELPER: Convert relation names to CIDOC-CRM types
    # =====================================================
    
    def _extract_relation_types(self, semantic_parse):
        """Convert relation names to CIDOC-CRM types"""
        relations = semantic_parse.get("relations", [])
        if not relations:
            return None
        
        mapping = {
            "architect": "P14_carried_out_by",
            "built_by": "P108_was_produced_by",
            "founded_by": "P11_had_participant",
            "located_in": "P53_has_former_or_current_location",
            "part_of": "P46_is_composed_of",
            "material_used": "P45_consists_of",
            "time_span": "P4_has_time_span",
            "related_to": "P130_shows_features_of"
        }
        
        cidoc_types = []
        for rel in relations:
            rel_lower = str(rel).lower().strip()
            if rel_lower in mapping:
                cidoc_types.append(mapping[rel_lower])
            else:
                for key, cidoc_type in mapping.items():
                    if key in rel_lower:
                        cidoc_types.append(cidoc_type)
                        break
        
        return cidoc_types if cidoc_types else None