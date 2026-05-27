import json
import re
from pathlib import Path
from collections import defaultdict
import traceback
import sys
from rapidfuzz import fuzz
from tqdm import tqdm

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

NODE_PATH = BASE_DIR / "data" / "processed" / "stage2_nodes.json"
REL_PATH = BASE_DIR / "data" / "processed" / "stage2_relations.json"
CHUNK_PATH = BASE_DIR / "data" / "processed" / "text_chunks.json"

OUTPUT_NODE_PATH = BASE_DIR / "data" / "refined" / "refined_nodes.json"
OUTPUT_REL_PATH = BASE_DIR / "data" / "refined" / "refined_relations.json"
OUTPUT_ALIAS_PATH = BASE_DIR / "data" / "refined" / "canonical_entity_map.json"
OUTPUT_PROVENANCE_PATH = BASE_DIR / "data" / "refined" / "provenance_links.json"

# ============================================================
# HELPERS
# ============================================================
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_text(text):

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(r"\s+", " ", text)

    return text.strip()

# ============================================================
# OPTIMIZED ENTITY ALIGNER & LINKER
# ============================================================
class EntityAligner:
    def __init__(self, threshold=90):
        self.threshold = threshold

    def is_same_entity(self, node_a, node_b):
        # Ưu tiên type CIDOC
        if node_a.get("type") != node_b.get("type"):
            return False

        # Tránh merge PERSON với PLACE do NER lỗi
        if node_a.get("ner_type") != node_b.get("ner_type"):
            return False
        
        label_a = normalize_text(node_a.get("label", ""))
        label_b = normalize_text(node_b.get("label", ""))
        
        # Nếu nhãn giống hệt nhau sau khi normalize -> Khỏi cần tính toán fuzzy
        if label_a == label_b:
            return True
            
        score = fuzz.token_sort_ratio(label_a, label_b)
        return score >= self.threshold


class CrossSourceLinker:
    def __init__(self, threshold=92):
        self.threshold = threshold

    def build_links(self, nodes):
        """
        Tối ưu hóa tìm liên kết chéo bằng cơ chế K-d Blocking (Nhóm theo chữ cái đầu).
        Giảm độ phức tạp từ O(N^2) xuống xấp xỉ O(N).
        """
        links = []
        # Gom cụm các node có cùng ký tự đầu tiên của nhãn để tránh so sánh mù quáng
        buckets = defaultdict(list)
        for node in nodes:
            lbl = normalize_text(node.get("label", ""))
            if lbl:
                buckets[lbl[0]].append(node)

        for first_char, bucket_nodes in buckets.items():
            n = len(bucket_nodes)
            if n < 2:
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    node_a = bucket_nodes[i]
                    node_b = bucket_nodes[j]
                    
                    if node_a["id"] == node_b["id"]:
                        continue

                    score = fuzz.ratio(normalize_text(node_a["label"]), normalize_text(node_b["label"]))
                    if score >= self.threshold:
                        links.append({
                            "source": node_a["id"],
                            "target": node_b["id"],
                            "relation": "related_to",
                            "confidence": round(float(score), 2)
                        })
        return links

# ============================================================
# OPTIMIZED PROVENANCE BUILDER
# ============================================================
class ProvenanceBuilder:
    def build_provenance(self, nodes, chunks):
        """
        Xây dựng nguồn gốc thực thể dựa trên Regex biên từ (Word Boundary) để tránh lỗi trùng từ con.
        Tối ưu tốc độ bằng cách lập chỉ mục đảo trước (Inverted Index Mapping).
        """
        provenance_links = []
        
        # Tiền xử lý normalize toàn bộ văn bản của chunks để tăng tốc độ so khớp
        processed_chunks = []
        for chunk in chunks:
            processed_chunks.append({
                "id": chunk.get("chunk_id"),
                "src": chunk.get("source", "wikipedia"),
                "norm_text": normalize_text(chunk.get("text", ""))
            })

        for node in tqdm(nodes, desc="Building Provenance"):
            label = normalize_text(node.get("label", ""))
            if not label or len(label) < 2: # Bỏ qua các nhãn quá ngắn gây nhiễu
                continue
                
            # Sử dụng regex an toàn bảo vệ biên từ để tránh tình trạng "An" nằm trong "Thanh"
            # Thích ứng mượt mà cho tiếng Việt
            pattern = re.compile(
                r'(?<!\w)'
                + re.escape(label)
                + r'(?!\w)',
                flags=re.IGNORECASE
            )

            for p_chunk in processed_chunks:
                if pattern.search(p_chunk["norm_text"]):
                    provenance_links.append({
                        "entity_id": node["id"],
                        "chunk_id": p_chunk["id"],
                        "source": p_chunk["src"]
                    })
        return provenance_links

# ============================================================
# TEMPORAL NORMALIZER
# ============================================================
class TemporalNormalizer:

    def normalize(self, node):

        results = []

        # =========================
        # inception year
        # =========================

        inception = node.get("inception")

        if inception:

            try:

                year = str(inception)[1:5]

                results.append({
                    "id": f"YEAR_{year}",
                    "label": year,
                    "type": "E52_Time_Span"
                })

            except:
                pass

        return results

# ============================================================
# GRAPH REFINER
# ============================================================
class GraphRefiner:
    def __init__(self):
        self.aligner = EntityAligner()
        self.temporal = TemporalNormalizer()
        self.linker = CrossSourceLinker()
        self.alias_map = {}

    def deduplicate_nodes(self, nodes):

        canonical_nodes = []

        used = set()

        buckets = defaultdict(list)

        for idx, node in enumerate(nodes):

            lbl = normalize_text(node.get("label", ""))

            first_char = lbl[0] if lbl else ""

            buckets[first_char].append((idx, node))

        for _, bucket_items in buckets.items():

            for i in range(len(bucket_items)):

                orig_idx_i, current = bucket_items[i]

                if orig_idx_i in used:
                    continue

                canonical = dict(current)

                aliases = canonical.get("aliases", [])

                for j in range(i + 1, len(bucket_items)):

                    orig_idx_j, candidate = bucket_items[j]

                    if orig_idx_j in used:
                        continue

                    if self.aligner.is_same_entity(
                        canonical,
                        candidate
                    ):

                        aliases.append(
                            candidate.get("label", "")
                        )

                        self.alias_map[
                            candidate["id"]
                        ] = canonical["id"]

                        # =========================
                        # GPS inheritance
                        # =========================

                        if (
                            canonical.get("latitude") is None
                            and candidate.get("latitude") is not None
                        ):
                            canonical["latitude"] = candidate["latitude"]

                        if (
                            canonical.get("longitude") is None
                            and candidate.get("longitude") is not None
                        ):
                            canonical["longitude"] = candidate["longitude"]

                        # =========================
                        # Inception inheritance
                        # =========================

                        if (
                            not canonical.get("inception")
                            and candidate.get("inception")
                        ):
                            canonical["inception"] = candidate["inception"]

                        # =========================
                        # Address inheritance
                        # =========================

                        if (
                            not canonical.get("address")
                            and candidate.get("address")
                        ):
                            canonical["address"] = candidate["address"]

                        # =========================
                        # wd_properties merge
                        # =========================

                        if "wd_properties" in candidate:

                            if "wd_properties" not in canonical:
                                canonical["wd_properties"] = {}

                            for prop_k, prop_v in candidate[
                                "wd_properties"
                            ].items():

                                if prop_k not in canonical["wd_properties"]:
                                    canonical["wd_properties"][prop_k] = []

                                existing = canonical["wd_properties"][prop_k]

                                existing_ids = {
                                    x["id"]
                                    for x in existing
                                    if isinstance(x, dict)
                                    and "id" in x
                                }

                                for item in prop_v:

                                    if (
                                        isinstance(item, dict)
                                        and item.get("id")
                                        not in existing_ids
                                    ):
                                        existing.append(item)

                        used.add(orig_idx_j)

                canonical["aliases"] = sorted(
                    list(set(aliases))
                )

                canonical_nodes.append(canonical)

                used.add(orig_idx_i)

        return canonical_nodes

    def remap_relations(self, relations):
        refined = []
        unique_rel = set()

        for rel in relations:
            src = rel["source"]
            tgt = rel["target"]

            # Ánh xạ ID từ alias về ID chuẩn (Canonical ID)
            src = self.alias_map.get(src, src)
            tgt = self.alias_map.get(tgt, tgt)

            if src == tgt: # Loại bỏ vòng lặp vô hạn vào chính nó
                continue
            if not src or not tgt:
                continue
            
            key = (
                src,
                rel.get("relation", "related_to"),
                tgt
            )
            
            if key in unique_rel:
                continue

            unique_rel.add(key)
            refined.append({
                "source": src,
                "target": tgt,
                "relation": rel.get("relation", "related_to")
            })

        return refined

    def enrich_temporal(self, nodes, relations):

        temporal_nodes = []

        temporal_rel = []

        existing_ids = {
            n["id"]
            for n in nodes
        }

        for node in nodes:

            temporal_matches = self.temporal.normalize(node)

            for t in temporal_matches:

                if t["id"] not in existing_ids:

                    temporal_nodes.append(t)

                    existing_ids.add(t["id"])

                temporal_rel.append({
                    "source": node["id"],
                    "target": t["id"],
                    "relation": "P4_has_time_span"
                })

        nodes.extend(temporal_nodes)

        relations.extend(temporal_rel)

        return nodes, relations

# ============================================================
# MAIN ORCHESTRATOR
# ============================================================
def main():
    print("\n==================================================")
    print("🚀 KHỞI ĐỘNG CHẠY TIẾN TRÌNH STAGE 3 — GRAPH REFINEMENT")
    print("==================================================")

    try:
        print("[1/5] Đang đọc file dữ liệu từ Stage 2...")
        nodes = load_json(NODE_PATH)
        relations = load_json(REL_PATH)
        chunks = load_json(CHUNK_PATH)
        print(f" -> Dữ liệu đầu vào: {len(nodes)} nodes, {len(relations)} relations, {len(chunks)} text chunks.")

        refiner = GraphRefiner()

        print("\n[2/5] Đang tiến hành khử trùng lập và gộp Node (Deduplication)...")
        refined_nodes = refiner.deduplicate_nodes(nodes)
        print(f" -> Số lượng Node sau tinh lọc sạch: {len(refined_nodes)}")

        print("\n[3/5] Đang dọn dẹp và chuẩn hóa liên kết quan hệ (Relations)...")
        refined_relations = refiner.remap_relations(relations)
        print(f" -> Số lượng quan hệ sau dọn dẹp: {len(refined_relations)}")

        print("\n[4/5] Đang thực hiện làm giàu dòng thời gian (Temporal Enrichment)...")
        refined_nodes, refined_relations = refiner.enrich_temporal(refined_nodes, refined_relations)

        print("\n[5/5] Đang tính toán liên kết chéo (Cross-source linkage)...")
        linkage_rel = refiner.linker.build_links(refined_nodes)
        refined_relations.extend(linkage_rel)
        print(f" -> Đã tạo thêm {len(linkage_rel)} liên kết tương đồng.")

        print("\n[💥] Đang chạy thiết lập nguồn gốc xuất xứ trích dẫn (Provenance Builder)...")
        provenance_builder = ProvenanceBuilder()
        provenance_links = provenance_builder.build_provenance(refined_nodes, chunks)
        print(f" -> Tạo thành công {len(provenance_links)} liên kết kiểm chứng nguồn.")

        print("\n[💾] Đang xuất dữ liệu đồ thị tri thức sạch tinh khiết...")
        save_json(OUTPUT_NODE_PATH, refined_nodes)
        save_json(OUTPUT_REL_PATH, refined_relations)
        save_json(OUTPUT_ALIAS_PATH, refiner.alias_map)
        save_json(OUTPUT_PROVENANCE_PATH, provenance_links)

        print("\n==================================================")
        print("🎉 STAGE 3 HOÀN THÀNH AN TOÀN & TỐI ƯU!")
        print("==================================================")

    except Exception as e:
        print("\n❌❌❌ HỆ THỐNG STAGE 3 GẶP LỖI SẬP NGUỒN ❌❌❌")
        print("-" * 60)
        traceback.print_exc(file=sys.stdout)
        print("-" * 60)

if __name__ == "__main__":
    main()