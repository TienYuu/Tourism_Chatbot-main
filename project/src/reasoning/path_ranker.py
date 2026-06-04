# path_reranker.py

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ontology.relation_canonicalizer import RelationCanonicalizer


class PathRanker:

    def __init__(self):
        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.canonicalizer = RelationCanonicalizer()

        # ==========================================
        # RELATION ALIASES
        # Đồng bộ chính xác theo các key của RELATION_MAPPING
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
            "founded_by": [
                "founded by",
                "sáng lập",
                "người sáng lập",
                "thành lập bởi",
                "được sáng lập bởi"
            ],
            "located_in": [
                "located in",
                "nằm ở",
                "ở",
                "ở đâu",
                "vị trí tại"
            ],
            "part_of": [
                "part of",
                "thuộc",
                "thuộc về",
                "là một phần của",
                "nằm trong"
            ],
            "material_used": [
                "consists of",
                "làm bằng",
                "được làm bằng",
                "chất liệu",
                "chất liệu gì",
                "vật liệu",
                "vật liệu gì",
                "tạo bởi vật liệu gì",
                "được tạo bởi vật liệu gì",
                "thành phần",
                "material used"
            ],
            "time_span": [
                "time span",
                "thời gian",
                "vào năm nào",
                "khi nào",
                "niên đại",
                "thời kỳ"
            ],
            "related_to": [
                "related to",
                "liên quan đến",
                "đặc điểm của",
                "thể hiện"
            ]
        }

        # ==========================================
        # EMBEDDING CACHE & PRECOMPUTATION
        # ==========================================
        self.embedding_cache = {}
        self.alias_embeddings = {}

        for relation, aliases in self.relation_aliases.items():
            self.alias_embeddings[relation] = self.embedding_model.encode(
                aliases,
                convert_to_numpy=True
            )

    # =====================================================
    # MAIN SCORING
    # =====================================================
    def score_path(self, path, semantic_parse):
        relation_score = self.score_relations(path, semantic_parse)
        structure_score = self.structure_score(path)
        target_score = self.target_score(path, semantic_parse)

        final_score = (
            relation_score * 0.55
            + structure_score * 0.25
            + target_score * 0.20
        )
        return round(float(final_score), 4)

    # =====================================================
    # RELATION SCORE
    # =====================================================
    def score_relations(self, path, semantic_parse):
        edges = path.get("edges", [])
        if not edges:
            return 0.0

        requested_relations = semantic_parse.get("relations", [])
        if not requested_relations:
            return 0.0

        edge_scores = []
        for idx, edge in enumerate(edges):
            relation = edge["relation"]
            score = self.semantic_relation_similarity(relation, requested_relations)

            # Vị trí cạnh càng gần gốc (đầu chuỗi) thì trọng số càng cao
            weight = 1 / (idx + 1)
            edge_scores.append(score * weight)

        return np.mean(edge_scores)

    def semantic_relation_similarity(self, graph_relation, requested_relations):
        # 1. Chuẩn hóa Graph Relation về mã nội bộ (ví dụ: p45_consists_of -> material_used)
        normalized_relation = self.normalize_relation_name(graph_relation)

        # 2. Tạo một bộ lọc cứng (Hard Mapping) từ Câu hỏi -> Key hệ thống để chặn lỗi embedding trùng lặp
        detected_requested_keys = set()
        for req in requested_relations:
            req_lower = req.lower().strip()
            
            # Quét qua bảng aliases để tìm group thực sự mà người dùng muốn hỏi
            for rel_key, aliases in self.relation_aliases.items():
                if any(alias in req_lower for alias in aliases) or req_lower == rel_key:
                    detected_requested_keys.add(rel_key)

        # 🎯 CHIẾN LƯỢC 1: NẾU KHỚP MÃ CỨNG (EXACT GROUP MATCH) -> ƯU TIÊN TUYỆT ĐỐI
        if normalized_relation in detected_requested_keys:
            return 1.0
            
        # 🎯 CHIẾN LƯỢC 2: PHẠT NẶNG (PENALTY) NẾU SAI LỆCH KHÁI NIỆM LỚN
        if "material_used" in detected_requested_keys and normalized_relation != "material_used":
            return 0.1  # Phạt nặng để triệt tiêu các quan hệ gây nhiễu như P46 hay P53

        # 3. CƠ CHẾ DỰ PHÒNG: DÙNG CANONICALIZER & EMBEDDING SIMILARITY
        canonical_graph_relation = self.canonicalizer.canonicalize(normalized_relation)
        canonical_requested = [
            self.canonicalizer.canonicalize(r) for r in requested_relations
        ]

        if canonical_graph_relation in canonical_requested:
            return 1.0

        graph_emb = self.get_embedding(canonical_graph_relation)
        best_score = 0.0

        for requested in canonical_requested:
            req_emb = self.get_embedding(requested)
            similarity = cosine_similarity([graph_emb], [req_emb])[0][0]

            if similarity > best_score:
                best_score = similarity

        return float(best_score)

    # =====================================================
    # STRUCTURE SCORE
    # =====================================================
    def structure_score(self, path):
        edges = path.get("edges", [])
        if not edges:
            return 0.0
        length = len(edges)
        # Ưu tiên các chuỗi thực thể ngắn gọn hơn
        return max(0.0, 1.0 - (length - 1) * 0.15)

    # =====================================================
    # TARGET TYPE SCORE
    # =====================================================
    def target_score(self, path, semantic_parse):
        target = str(
            semantic_parse.get("target") or 
            semantic_parse.get("target_type") or ""
        ).lower()

        if not target:
            return 0.0

        edges = path.get("edges", [])
        if not edges:
            return 0.0

        last_edge = edges[-1]
        labels = last_edge.get("target_labels", [])
        if not labels:
            return 0.0

        label_scores = []
        target_emb = self.get_embedding(target)

        for label in labels:
            label_emb = self.get_embedding(label.lower())
            sim = cosine_similarity([target_emb], [label_emb])[0][0]
            label_scores.append(sim)

        return float(np.max(label_scores))

    # =====================================================
    # NORMALIZATION (ĐỒNG BỘ HOÀN TOÀN THEO DATABASE ONTOLOGY)
    # =====================================================
    def normalize_relation_name(self, relation):
        """
        Chuyển đổi các mã CIDOC-CRM thu được từ DB 
        về dạng alias key tương ứng phục vụ matching ngữ nghĩa.
        """
        relation = str(relation).strip().lower()

        # Ánh xạ đảo ngược (Inverted Mapping) từ RELATION_MAPPING của DB
        ontology_map = {
            "p14_carried_out_by": "architect",
            "p108_was_produced_by": "built_by",
            "p11_had_participant": "founded_by",
            "p53_has_former_or_current_location": "located_in",
            "p46_is_composed_of": "part_of",
            "p45_consists_of": "material_used",
            "p4_has_time_span": "time_span",
            "p130_shows_features_of": "related_to"
        }

        return ontology_map.get(relation, relation)

    # =====================================================
    # EMBEDDING CACHE
    # =====================================================
    def get_embedding(self, text):
        text = text.lower()
        if text not in self.embedding_cache:
            self.embedding_cache[text] = self.embedding_model.encode(
                text, 
                convert_to_numpy=True
            )
        return self.embedding_cache[text]
    
    def get_embeddings_batch(self, texts):
        """
        🔥 OPTIMIZATION 8: Batch compute embeddings
        Encode multiple texts in one forward pass
        
        Impact: 3-5x faster than computing individually
        """
        if not texts:
            return {}
        
        texts_lower = [str(t).lower() for t in texts]
        texts_to_encode = []
        text_mapping = {}
        
        for i, text in enumerate(texts_lower):
            if text not in self.embedding_cache:
                texts_to_encode.append(text)
                text_mapping[len(texts_to_encode) - 1] = text
        
        if texts_to_encode:
            batch_embeddings = self.embedding_model.encode(
                texts_to_encode,
                convert_to_numpy=True,
                batch_size=len(texts_to_encode)
            )
            
            for idx, text in text_mapping.items():
                self.embedding_cache[text] = batch_embeddings[idx]
        
        result = {}
        for text in texts_lower:
            result[text] = self.embedding_cache[text]
        
        return result