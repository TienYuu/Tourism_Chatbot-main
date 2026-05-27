from typing import Any
import pandas as pd


class TripleBuilder:

    def __init__(self) -> None:
        pass

    def build_triples(self, relations: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Xây dựng ma trận bộ ba Triples (Subject, Predicate, Object) từ dữ liệu quan hệ.
        Tối ưu hóa tốc độ bằng Pandas Vectorization và tự động khử trùng lặp.
        """
        if not relations:
            return pd.DataFrame(columns=["subject", "predicate", "object"])

        # Tạo thẳng DataFrame từ danh sách dict gốc (Nhanh và tiết kiệm RAM hơn vòng lặp for)
        df = pd.DataFrame(relations)

        # Đảm bảo các trường dữ liệu bắt buộc phải tồn tại, nếu thiếu tự điền giá trị rỗng/mặc định
        for col in ["source", "relation", "target"]:
            if col not in df.columns:
                df[col] = None

        # Trích xuất và đổi tên các cột theo chuẩn RDF Triple
        triple_df = df[["source", "relation", "target"]].copy()
        triple_df.columns = ["subject", "predicate", "object"]

        # Loại bỏ các dòng bị thiếu thông tin cốt lõi (bắt buộc phải có đầy đủ Subject và Object)
        triple_df = triple_df.dropna(subset=["subject", "object"])

        # Khử trùng lặp các bộ ba giống hệt nhau
        initial_count = len(triple_df)
        triple_df = triple_df.drop_duplicates()
        
        # Điền giá trị mặc định cho predicate nếu bị trống
        triple_df["predicate"] = triple_df["predicate"].fillna("related_to")

        return triple_df