import uuid
from typing import List

class SectionAwareChunker:
    def __init__(self, chunk_size: int = 800, overlap: int = 100):
        """
        Bộ cắt văn bản thông minh bảo vệ toàn vẹn từ ghép tiếng Việt và ranh giới câu.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        chunks = []
        text_len = len(text)
        start = 0

        while start < text_len:
            # Nếu đoạn văn bản còn lại ngắn hơn chunk_size, lấy nốt phần còn lại
            if start + self.chunk_size >= text_len:
                chunks.append(text[start:])
                break

            end = start + self.chunk_size

            # 💥 THUẬT TOÁN LOOK-BACK: Quét ngược tìm điểm ngắt từ/ngắt câu an toàn
            # Tránh việc chẻ đôi một từ ghép tiếng Việt ngay ranh giới cắt
            safe_end = end
            while safe_end > start and text[safe_end - 1] not in [' ', '\n', '.', ',', '!', '?']:
                safe_end -= 1
            
            # Nếu quét ngược quá sâu (gặp từ quá dài hoặc không tìm thấy khoảng trắng), 
            # bắt buộc phải quay lại ranh giới end ban đầu
            if safe_end == start:
                safe_end = end

            chunk = text[start:safe_end]
            chunks.append(chunk)

            # Tính toán điểm start tiếp theo dựa trên độ dịch chuyển thực tế của safe_end và overlap
            actual_chunk_len = safe_end - start
            start += max(1, actual_chunk_len - self.overlap)

        return chunks

    def create_chunks(self, monument_name: str, sections: List[dict], default_source: str = "wikipedia") -> List[dict]:
        """
        Tạo danh sách các chunk văn bản có định danh UUID và bổ sung trường source 
        đáp ứng hoàn hảo đầu vào cho Stage 2 và Stage 3.
        """
        final_chunks = []

        for sec in sections:
            sec_text = sec.get("text", "")
            if not sec_text or not sec_text.strip():
                continue

            text_chunks = self.split_text(sec_text)

            for idx, chunk in enumerate(text_chunks):
                # Thu thập thông tin source có sẵn từ section, nếu không có sẽ dùng default_source
                source_info = sec.get("source", default_source)

                final_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "monument": monument_name,
                    "section": sec.get("section", "Tổng quan"),
                    "text": chunk.strip(),
                    "source": source_info # Khóa trường dữ liệu cốt lõi phục vụ Provenance Stage 3
                })

        return final_chunks