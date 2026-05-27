WIKIDATA_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "VietnamHeritageKG/1.0 (daotiendung16702@gmail.com) Python-requests"
}

MAX_HOPS = 3


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_RAW_ENTITY = (
    BASE_DIR / "data" / "raw" / "raw_entities.json"
)

OUTPUT_RAW_RELATION = (
    BASE_DIR / "data" / "raw" / "raw_relations.json"
)

OUTPUT_CHUNKS = (
    BASE_DIR / "data" / "processed" / "text_chunks.json"
)

OUTPUT_RAW_METADATA = (
    BASE_DIR / "data" / "raw" / "metadata.json"
)