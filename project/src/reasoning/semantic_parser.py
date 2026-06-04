# reasoning/semantic_parser.py
import json

# ============================================================
# SYSTEM PROMPT (HƯỚNG DẪN CHO LLM NHẬN DIỆN THUỘC TÍNH VÀ QUAN HỆ)
# ============================================================
SYSTEM_PROMPT = """
You are a semantic parser for a historical knowledge graph QA system aligned with CIDOC-CRM.

Your task:
Convert user question into a structured reasoning intent.

Return JSON only.

Output format:
{
    "target": "...",
    "question_type": "...",
    "constraints": [],
    "relations": [],
    "reasoning_depth": 1
}

Rules for 'relations' and 'question_type':
- Use property/attribute names if asking for specific entity details:
  * "coordinates" (for tọa độ, kinh độ, vĩ độ)
  * "address" (for địa chỉ, ở đường nào, số mấy)
  * "description" (for mô tả, giới thiệu, là gì, thông tin)
  * "country" (for quốc gia, nước nào, thuộc nước)
- Use concept-related keywords if asking for graph paths:
  * "material_used" (for vật liệu, chất liệu, làm bằng gì)
  * "architect" (for kiến trúc sư, thiết kế)
  * "built_by" (for xây dựng, tạo nên)
  * "located_in" (for vị trí, nằm ở đâu)

Rules for 'reasoning_depth':
- 1 = direct property lookup or single relation (e.g., coordinates, address, description, material_used)
- 2 = multi-hop reasoning path
- 3 = complex multi-hop constraints
"""

class SemanticParser:

    def __init__(self, groq_client):
        self.groq_client = groq_client

    # =====================================================
    # RULE-BASED RELATION & PROPERTY DETECTION (FALLBACK)
    # =====================================================
    def rule_based_relation_detection(self, question):
        q = str(question or "").lower().strip()

        # 1. Tọa độ (Coordinates)
        coordinate_keywords = ["kinh độ", "vĩ độ", "tọa độ", "coordinates", "latitude", "longitude"]
        if any(k in q for k in coordinate_keywords):
            return "coordinates"

        # 2. Địa chỉ (Address)
        address_keywords = ["địa chỉ", "address", "ở số mấy", "đường nào", "vị trí cụ thể"]
        if any(k in q for k in address_keywords):
            return "address"

        # 3. Mô tả (Description)
        description_keywords = ["mô tả", "description", "giới thiệu", "là gì", "thông tin về", "tóm tắt"]
        if any(k in q for k in description_keywords):
            return "description"

        # 4. Quốc gia (Country)
        country_keywords = ["quốc gia", "nước nào", "thuộc nước", "quốc tịch", "country"]
        if any(k in q for k in country_keywords):
            return "country"

        # 5. Vị trí / nằm ở đâu (Located In)
        location_keywords = ["ở đâu", "nằm ở đâu", "vị trí", "địa điểm", "thuộc", "nằm ở"]
        if any(k in q for k in location_keywords):
            return "located_in"

        # 6. Vật liệu (Material - Phục vụ PathRanker)
        material_keywords = ["vật liệu", "chất liệu", "làm bằng", "được làm bằng", "thành phần"]
        if any(k in q for k in material_keywords):
            return "material_used"

        # 7. Kiến trúc sư (Architect)
        architect_keywords = ["kiến trúc sư", "architect", "thiết kế"]
        if any(k in q for k in architect_keywords):
            return "architect"

        return None

    def rule_based_multi_hop_detection(self, question):
        q = str(question or "").lower()

        # Detect requests like: "Những công trình nào do kiến trúc sư của Tháp Eiffel thiết kế?"
        if ("công trình" in q or "công trình nào" in q or "những công trình" in q) and (
            "kiến trúc sư của" in q or ("kiến trúc sư" in q and "thiết kế" in q)
        ):
            return {
                "relations": ["architect", "built_by"],
                "question_type": "architect_works",
                "reasoning_depth": 2
            }

        return None

    # =====================================================
    # MAIN PARSE METHOD
    # =====================================================
    def parse(self, question: str):
        user_prompt = f"Question:\n{question}\n\nReturn JSON only."

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
                "reasoning_depth": 1
            }

        # =====================================================
        # RULE-BASED MULTI-HOP DETECTION
        # =====================================================
        multi_hop = self.rule_based_multi_hop_detection(question)

        if multi_hop:
            parsed["relations"] = multi_hop["relations"]
            parsed["question_type"] = multi_hop["question_type"]
            parsed["reasoning_depth"] = multi_hop["reasoning_depth"]
            return parsed

        # =====================================================
        # RULE-BASED FALLBACK (BỌC LÓT KHI LLM SAI HOẶC RA SỔ LẠC)
        # =====================================================
        fallback_relation = self.rule_based_relation_detection(question)

        if fallback_relation:
            # Nếu LLM không bóc tách được quan hệ nào, nạp giá trị từ bộ lọc cứng
            if not parsed.get("relations"):
                parsed["relations"] = [fallback_relation]

            # Nếu question_type bị trống hoặc không rõ ràng, đồng bộ hóa nó theo thuộc tính phát hiện được
            if not parsed.get("question_type") or parsed.get("question_type") == "unknown":
                parsed["question_type"] = fallback_relation

            # Tự động hạ reasoning_depth xuống 1 cho các thuộc tính tĩnh trực tiếp
            if fallback_relation in ["coordinates", "address", "description", "country"]:
                parsed["reasoning_depth"] = 1

        return parsed