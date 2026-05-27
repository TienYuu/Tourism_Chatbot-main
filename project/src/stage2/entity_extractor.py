import re
from underthesea import ner
from typing import List

class HeritageEntityExtractor:
    def __init__(self):
        # Khởi tạo một số luật Regex bổ sung cho đặc thù Di sản Việt Nam (Heritage Heuristics)
        # Vì underthesea đôi khi bỏ sót các danh hiệu di sản đặc thù
        self.heritage_keywords = re.compile(
            r"\b(chùa|đền|lăng|thành cổ|cố đô|vịnh|hang|động|tháp|vườn quốc gia|phố cổ)\b", 
            re.IGNORECASE
        )

    def extract_entities(self, text: str) -> List[dict]:
        if not text or not text.strip():
            return []

        try:
            # ner(text) trả về danh sách các tuple: (token, pos, chunk, ner_label)
            # Ví dụ: [('Hội An', 'Np', 'B-NP', 'B-LOC'), ...]
            raw_results = ner(text)
        except Exception:
            # Đảm bảo hệ thống không sập nếu dòng văn bản bị lỗi encoding lạ
            return []
        
        entities = []
        
        # -----------------------------------------------------------------
        # THUẬT TOÁN ĐỘNG: GÌM VỊ TRÍ CHÍNH XÁC KHÔNG BỊ TRÙNG TỪ ĐƠN
        # -----------------------------------------------------------------
        # Thay vì dùng text.find mù quáng, ta theo dõi index thực tế chạy dọc văn bản
        current_char_idx = 0
        tokens_with_positions = []
        
        for item in raw_results:
            token = item[0]
            ner_tag = item[3]
            
            # Tìm vị trí xuất hiện tiếp theo của token bắt đầu từ vị trí hiện tại
            start_idx = text.find(token, current_char_idx)
            if start_idx == -1:
                # Fallback nếu chuỗi có khoảng trắng đặc biệt
                start_idx = current_char_idx
                
            end_idx = start_idx + len(token)
            current_char_idx = end_idx # Khóa vị trí lại, không quay đầu tìm kiếm ngược
            
            tokens_with_positions.append({
                "token": token,
                "tag": ner_tag,
                "start": start_idx,
                "end": end_idx
            })

        # -----------------------------------------------------------------
        # STATE MACHINE: GỘP TOKENS (B- và I-) THÀNH THỰC THỂ TRỌN VẸN
        # -----------------------------------------------------------------
        current_entity = None
        
        for p in tokens_with_positions:
            tag = p["tag"]
            
            if tag == 'O':
                # Nếu gặp nhãn 'O' (không phải thực thể), đóng thực thể cũ nếu đang mở
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
                continue
                
            # Tách tiền tố (B, I) và loại thực thể (LOC, PER, ORG)
            parts = tag.split('-')
            prefix = parts[0]
            ent_type = parts[1] if len(parts) > 1 else "MISC"
            
            if prefix == 'B':
                # Nếu đang có một thực thể mở từ trước, đóng nó lại trước khi mở thực thể mới
                if current_entity:
                    entities.append(current_entity)
                    
                current_entity = {
                    "text": p["token"],
                    "label": ent_type,
                    "start": p["start"],
                    "end": p["end"]
                }
                
            elif prefix == 'I':
                # Nếu là nhãn I-, nối dài vào thực thể B- trước đó nếu cùng loại nhãn
                if current_entity and current_entity["label"] == ent_type:
                    # Tạo khoảng cách trắng giữa các token nếu văn bản gốc có khoảng trắng
                    gap = text[current_entity["end"]:p["start"]]
                    current_entity["text"] += gap + p["token"]
                    current_entity["end"] = p["end"]
                else:
                    # Nếu tự dưng xuất hiện I- mà không có B-, coi như nó tự khởi tạo
                    if current_entity:
                        entities.append(current_entity)
                    current_entity = {
                        "text": p["token"],
                        "label": ent_type,
                        "start": p["start"],
                        "end": p["end"]
                    }

        # Đóng thực thể cuối cùng nếu vòng lặp kết thúc
        if current_entity:
            entities.append(current_entity)

        # -----------------------------------------------------------------
        # HERITAGE RE-LABELING: LÀM GIÀU DỮ LIỆU DI SẢN (HỌC THUẬT DU LỊCH)
        # -----------------------------------------------------------------
        # Thay đổi nhãn LOC thông thường thành HISTORICAL_RELICT nếu chứa từ khóa di sản
        for ent in entities:
            if ent["label"] == "LOC" and self.heritage_keywords.search(ent["text"]):
                ent["label"] = "HISTORICAL_RELICT"

        return entities