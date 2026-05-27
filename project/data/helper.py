import pandas as pd
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

try:
    from src.config import USER_AGENT, DEFAULT_SLEEP
except ImportError:
    USER_AGENT = "MyWikiProject/1.0"
    DEFAULT_SLEEP = 1.0

# Số luồng song song & kích thước batch cho wbgetentities
MAX_WORKERS = 5
BATCH_SIZE = 50


class WikidataHelper:
    def __init__(self):
        self.url = "https://www.wikidata.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        # Retry tự động: 3 lần, chờ lũy tiến 0.5s → 1s → 2s
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        )
        self.session.mount("https://", adapter)
        self._search_cache: dict[str, str | None] = {}  # query → QID

    # ------------------------------------------------------------------
    # Bước 1: Tìm QID (có cache, chạy song song bên ngoài)
    # ------------------------------------------------------------------
    def _search_qid(self, query: str) -> str | None:
        """Trả về QID đầu tiên khớp với query, hoặc None."""
        if query in self._search_cache:
            return self._search_cache[query]

        try:
            res = self.session.get(
                self.url,
                params={
                    "action": "wbsearchentities",
                    "search": query,
                    "language": "vi",
                    "format": "json",
                    "limit": 1,
                },
                timeout=10,
            ).json()
            qid = (res.get("search") or [{}])[0].get("id")
        except Exception as e:
            print(f"  ⚠️  search lỗi '{query}': {e}")
            qid = None

        self._search_cache[query] = qid
        return qid

    # ------------------------------------------------------------------
    # Bước 2: Lấy chi tiết nhiều QID cùng lúc (batch)
    # ------------------------------------------------------------------
    def _fetch_details_batch(self, qids: list[str]) -> dict:
        """
        Gọi wbgetentities một lần cho tối đa BATCH_SIZE QID.
        Trả về dict {qid: entity_data}.
        """
        results = {}
        for i in range(0, len(qids), BATCH_SIZE):
            chunk = qids[i : i + BATCH_SIZE]
            try:
                data = self.session.get(
                    self.url,
                    params={
                        "action": "wbgetentities",
                        "ids": "|".join(chunk),
                        "props": "labels|aliases",
                        "languages": "vi|en",
                        "format": "json",
                    },
                    timeout=15,
                ).json()
                results.update(data.get("entities", {}))
                # Lịch sự với API giữa các batch (nếu có nhiều hơn 1 batch)
                if i + BATCH_SIZE < len(qids):
                    time.sleep(DEFAULT_SLEEP)
            except Exception as e:
                print(f"  ⚠️  batch detail lỗi (chunk {i}): {e}")
        return results

    # ------------------------------------------------------------------
    # API công khai
    # ------------------------------------------------------------------
    def process_list(self, names: list[str]) -> list[dict]:
        """
        Xử lý toàn bộ danh sách:
        1. Tìm QID song song (ThreadPoolExecutor)
        2. Lấy chi tiết theo batch (1–2 request thay vì N request)
        """
        print(f"🔍 Tìm kiếm {len(names)} mục song song (workers={MAX_WORKERS})…")

        # --- Bước 1: tìm QID song song ---
        qid_map: dict[str, str] = {}  # name → QID
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._search_qid, name): name for name in names}
            for fut in as_completed(futures):
                name = futures[fut]
                qid = fut.result()
                if qid:
                    qid_map[name] = qid
                    print(f"  ✅ {name} → {qid}")
                else:
                    print(f"  ⚠️  Không tìm thấy: {name}")
        # Chờ một chút trước khi batch detail (tránh burst)
        time.sleep(DEFAULT_SLEEP)

        # --- Bước 2: lấy chi tiết theo batch ---
        if not qid_map:
            return []

        unique_qids = list(set(qid_map.values()))
        print(f"\n📦 Lấy chi tiết {len(unique_qids)} thực thể (batch size={BATCH_SIZE})…")
        entities = self._fetch_details_batch(unique_qids)

        # --- Bước 3: tổng hợp kết quả ---
        records = []
        for name, qid in qid_map.items():
            entity = entities.get(qid, {})
            canonical = (
                entity.get("labels", {}).get("vi", {}).get("value")
                or entity.get("labels", {}).get("en", {}).get("value")
                or name
            )
            aliases = {
                a["value"]
                for lang in ("vi", "en")
                for a in entity.get("aliases", {}).get(lang, [])
            }
            records.append(
                {
                    "input_name": name,
                    "wikidata_id": qid,
                    "canonical_name": canonical,
                    "aliases": "|".join(sorted(aliases)),
                }
            )
        return records


def main():
    raw_monuments = [
        "Phố cổ Hội An",
        "Cố đô Huế",
        "Hoàng thành Thăng Long",
        "Thánh địa Mỹ Sơn",
        "Dinh Độc Lập",
        "Vịnh Hạ Long",
        "Vườn Quốc gia Phong Nha - Kẻ Bàng",
        "Đền Hùng",
        "Thành nhà Hồ",
        "Hang Pác Bó",
        "Đền Cửa Ông",
    ]

    helper = WikidataHelper()
    t0 = time.time()
    final_data = helper.process_list(raw_monuments)
    elapsed = time.time() - t0

    os.makedirs("data/raw", exist_ok=True)
    output_path = "data/raw/input_generated.csv"
    df = pd.DataFrame(final_data)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n✨ Xong! {len(final_data)} mục → {output_path}  (⏱ {elapsed:.1f}s)")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()