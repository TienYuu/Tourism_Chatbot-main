import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from wikidata_client import WikidataClient
from wikipedia_crawler import WikipediaCrawler
from chunking import SectionAwareChunker

from config import (
    OUTPUT_RAW_ENTITY,
    OUTPUT_RAW_RELATION,
    OUTPUT_CHUNKS,
    OUTPUT_RAW_METADATA,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent.parent
)

SEED_PATH = (
    BASE_DIR
    / "data"
    / "heritage_seed_entities.csv"
)

seed_df = pd.read_csv(SEED_PATH)

MONUMENTS = seed_df.to_dict("records")

# ============================================================
# JSON HELPERS
# ============================================================

def load_existing_data(
    path: Path
):

    if not path.exists():
        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:
        return []

# ============================================================
# SAVE + MERGE
# ============================================================

def merge_and_save(
    path: Path,
    new_data: list,
    identity_key,
):

    existing_data = load_existing_data(
        path
    )

    merged_dict = {}

    # ========================================
    # OLD DATA
    # ========================================

    for item in existing_data:

        try:

            key = (
                identity_key(item)
                if callable(identity_key)
                else item.get(identity_key)
            )

            if key:
                merged_dict[key] = item

        except Exception:
            continue

    # ========================================
    # NEW DATA
    # ========================================

    for item in new_data:

        try:

            key = (
                identity_key(item)
                if callable(identity_key)
                else item.get(identity_key)
            )

            if key:
                merged_dict[key] = item

        except Exception:
            continue

    # ========================================
    # SAVE
    # ========================================

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            list(merged_dict.values()),
            f,
            ensure_ascii=False,
            indent=2
        )

    return len(merged_dict)

# ============================================================
# METADATA CHECKER
# ============================================================

def check_coordinates_in_metadata(
    metadata_path: Path
):

    try:

        with open(
            metadata_path,
            "r",
            encoding="utf-8"
        ) as f:

            metadata = json.load(f)

        coord_records = [

            item

            for item in metadata

            if item.get("property") == "P625"
        ]

        entities_with_coord = set()

        for item in coord_records:

            entity_id = item.get(
                "entity_id"
            )

            if entity_id:
                entities_with_coord.add(
                    entity_id
                )

        print("\n" + "=" * 60)

        print("[KIỂM TRA METADATA TỌA ĐỘ]")

        print(
            f"Tổng metadata: {len(metadata)}"
        )

        print(
            f"Số bản ghi P625: {len(coord_records)}"
        )

        print(
            "Số entity có tọa độ:",
            len(entities_with_coord)
        )

        # ====================================
        # SAMPLE
        # ====================================

        if coord_records:

            print("\n[MẪU TỌA ĐỘ]")

            for item in coord_records[:5]:

                entity_id = item.get(
                    "entity_id"
                )

                coord = item.get(
                    "target",
                    {}
                )

                lat = coord.get(
                    "latitude"
                )

                lon = coord.get(
                    "longitude"
                )

                print(
                    f"- {entity_id}"
                    f" -> lat={lat}, lon={lon}"
                )

        else:

            print(
                "\n[CẢNH BÁO]"
                " Không tìm thấy P625"
            )

        print("=" * 60)

    except Exception as e:

        print(
            f"[METADATA CHECK ERROR] {e}"
        )

# ============================================================
# MAIN
# ============================================================

def main():

    wikidata_client = WikidataClient()

    crawler = WikipediaCrawler()

    chunker = SectionAwareChunker()

    all_entities = []

    all_relations = []

    all_metadata = []

    all_chunks = []

    # ========================================================
    # LOOP SEEDS
    # ========================================================

    for monument in tqdm(
        MONUMENTS,
        desc="Processing Heritage Seeds"
    ):

        canonical_name = monument[
            "canonical_name"
        ]

        wikidata_id = monument[
            "wikidata_id"
        ]

        print(
            "\n"
            + "=" * 60
        )

        print(
            f"[PROCESSING] {canonical_name}"
        )

        # ====================================================
        # WIKIDATA TRAVERSAL
        # ====================================================

        try:

            entities, relations, metadata = (
                wikidata_client.multi_hop_traversal(
                    canonical_name,
                    seed_id=wikidata_id
                )
            )

            if entities:

                all_entities.extend(
                    entities
                )

                all_relations.extend(
                    relations
                )

                all_metadata.extend(
                    metadata
                )

            print(
                f"[WIKIDATA]"
                f" entities={len(entities)}"
                f" relations={len(relations)}"
                f" metadata={len(metadata)}"
            )

        except Exception as e:

            print(
                f"[WIKIDATA ERROR]"
                f" {canonical_name}: {e}"
            )

        # ====================================================
        # WIKIPEDIA TEXT
        # ====================================================

        try:

            sections = crawler.crawl_page(
                canonical_name
            )

            if sections:

                chunks = chunker.create_chunks(
                    canonical_name,
                    sections
                )

                all_chunks.extend(
                    chunks
                )

                print(
                    f"[WIKIPEDIA]"
                    f" sections={len(sections)}"
                    f" chunks={len(chunks)}"
                )

        except Exception as e:

            print(
                f"[CRAWLER ERROR]"
                f" {canonical_name}: {e}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 60)

    print(
        f"ENTITY COUNT: {len(all_entities)}"
    )

    print(
        f"RELATION COUNT: {len(all_relations)}"
    )

    print(
        f"METADATA COUNT: {len(all_metadata)}"
    )

    print(
        f"CHUNK COUNT: {len(all_chunks)}"
    )

    print("=" * 60)

    # ========================================================
    # SAVE ENTITIES
    # ========================================================

    merge_and_save(
        OUTPUT_RAW_ENTITY,
        all_entities,
        "id"
    )

    # ========================================================
    # SAVE RELATIONS
    # ========================================================

    merge_and_save(
        OUTPUT_RAW_RELATION,
        all_relations,
        lambda x: (
            x["source"],
            x["property"],
            x["target"]
        )
    )

    # ========================================================
    # SAVE METADATA
    # ========================================================

    def metadata_identity(item):

        entity_id = item.get(
            "entity_id"
        )

        prop = item.get(
            "property"
        )

        target = item.get(
            "target"
        )

        return (
            entity_id,
            prop,
            json.dumps(
                target,
                sort_keys=True,
                ensure_ascii=False
            )
        )

    merge_and_save(
        OUTPUT_RAW_METADATA,
        all_metadata,
        metadata_identity
    )

    # ========================================================
    # SAVE CHUNKS
    # ========================================================

    merge_and_save(
        OUTPUT_CHUNKS,
        all_chunks,
        "chunk_id"
    )

    # ========================================================
    # CHECK COORDINATES
    # ========================================================

    check_coordinates_in_metadata(
        OUTPUT_RAW_METADATA
    )

    print("\n✅ Stage 1 hoàn tất")

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()