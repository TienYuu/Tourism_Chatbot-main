import json
import sys
import traceback

from pathlib import Path

from tqdm import tqdm

from stage2.entity_extractor import (
    HeritageEntityExtractor
)

from stage2.node_builder import (
    NodeBuilder
)

from stage2.relation_mapper import (
    RelationMapper
)

from stage2.triple_builder import (
    TripleBuilder
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = (
    Path(__file__).resolve()
    .parent.parent
)

RAW_ENTITY_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "raw_entities.json"
)

RAW_RELATION_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "raw_relations.json"
)

RAW_METADATA_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "metadata.json"
)

RAW_CHUNK_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "text_chunks.json"
)

OUTPUT_NODE_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "stage2_nodes.json"
)

OUTPUT_REL_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "stage2_relations.json"
)

OUTPUT_TRIPLE_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "triples.csv"
)


# =========================================================
# HELPERS
# =========================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(path, data):

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
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# METADATA LOOKUP
# =========================================================

def build_metadata_lookup(raw_metadata):

    metadata_lookup = {}

    skipped = 0

    for item in raw_metadata:

        # FIX:
        # stage1 now uses entity_id instead of source
        entity_id = item.get("entity_id")

        prop = item.get("property")

        target = item.get("target")

        if (
            not entity_id
            or not prop
            or target is None
        ):
            skipped += 1
            continue

        if entity_id not in metadata_lookup:
            metadata_lookup[entity_id] = {}

        if prop not in metadata_lookup[entity_id]:
            metadata_lookup[entity_id][prop] = []

        metadata_lookup[entity_id][prop].append(
            target
        )

    print(
        f" -> Metadata lookup built: "
        f"{len(metadata_lookup)} entities"
    )

    if skipped > 0:
        print(
            f" -> Skipped invalid metadata rows: {skipped}"
        )

    return metadata_lookup


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n" + "=" * 60)
    print("🚀 STAGE 2 PROCESSING")
    print("=" * 60)

    try:

        # =================================================
        # LOAD RAW DATA
        # =================================================

        print("\n[1/6] Loading raw data...")

        raw_entities = load_json(
            RAW_ENTITY_PATH
        )

        raw_relations = load_json(
            RAW_RELATION_PATH
        )

        raw_metadata = load_json(
            RAW_METADATA_PATH
        )

        # Optional chunks
        raw_chunks = []

        if RAW_CHUNK_PATH.exists():

            raw_chunks = load_json(
                RAW_CHUNK_PATH
            )

        print(
            f" -> Loaded:\n"
            f"    Entities : {len(raw_entities)}\n"
            f"    Relations: {len(raw_relations)}\n"
            f"    Metadata : {len(raw_metadata)}\n"
            f"    Chunks   : {len(raw_chunks)}"
        )

        # =================================================
        # METADATA LOOKUP
        # =================================================

        print("\n[2/6] Building metadata lookup...")

        metadata_lookup = build_metadata_lookup(
            raw_metadata
        )

        # =================================================
        # INIT MODULES
        # =================================================

        print("\n[3/6] Initializing models...")

        extractor = HeritageEntityExtractor()

        node_builder = NodeBuilder()

        relation_mapper = RelationMapper()

        triple_builder = TripleBuilder()

        print(" -> Modules initialized")

        # =================================================
        # DEDUP ENTITIES
        # =================================================

        print("\n[4/6] Processing nodes...")

        unique_entities = {
            e["id"]: e
            for e in raw_entities
            if e.get("id")
        }

        print(
            f" -> Unique entities: "
            f"{len(unique_entities)}"
        )

        final_nodes = []

        failed_nodes = 0

        for entity in tqdm(
            unique_entities.values(),
            desc="Building Nodes",
            unit="node"
        ):

            try:

                entity_id = entity.get("id")

                label = (
                    entity.get("label", "")
                    or entity.get("title", "")
                )

                description = (
                    entity.get("description", "")
                )

                text_for_ner = (
                    f"{label} {description}"
                    .strip()
                )

                entity_metadata = metadata_lookup.get(
                    entity_id,
                    {}
                )

                # NER
                extracted = extractor.extract_entities(
                    text_for_ner
                )

                ner_type = (
                    extracted[0]["label"]
                    if extracted
                    else "UNKNOWN"
                )

                # Build node
                node = node_builder.build_knowledge_node(
                    entity,
                    ner_type,
                    metadata=entity_metadata
                )

                final_nodes.append(node)

            except Exception as exc:

                failed_nodes += 1

                print(
                    f"\n[NODE ERROR] "
                    f"{entity.get('id')} -> {exc}"
                )

        print(
            f"\n -> Final nodes: {len(final_nodes)}"
        )

        if failed_nodes > 0:

            print(
                f" -> Failed nodes: {failed_nodes}"
            )

        # =================================================
        # RELATIONS
        # =================================================

        print("\n[5/6] Mapping relations...")

        final_relations = []

        relation_seen = set()

        failed_relations = 0

        for relation in tqdm(
            raw_relations,
            desc="Mapping Relations",
            unit="rel"
        ):

            try:

                source = relation.get("source")

                target = relation.get("target")

                prop = relation.get("property")

                if not source or not target:

                    failed_relations += 1
                    continue

                key = (
                    source,
                    prop,
                    target
                )

                if key in relation_seen:
                    continue

                relation_seen.add(key)

                mapped = relation_mapper.map_relation(
                    relation
                )

                if mapped:
                    final_relations.append(mapped)

            except Exception as exc:

                failed_relations += 1

                print(
                    f"\n[REL ERROR] "
                    f"{relation} -> {exc}"
                )

        print(
            f"\n -> Final relations: "
            f"{len(final_relations)}"
        )

        if failed_relations > 0:

            print(
                f" -> Failed relations: "
                f"{failed_relations}"
            )

        # =================================================
        # BUILD TRIPLES
        # =================================================

        print("\n[6/6] Building triples...")

        triple_df = triple_builder.build_triples(
            final_relations
        )

        # =================================================
        # SAVE
        # =================================================

        save_json(
            OUTPUT_NODE_PATH,
            final_nodes
        )

        save_json(
            OUTPUT_REL_PATH,
            final_relations
        )

        triple_df.to_csv(
            OUTPUT_TRIPLE_PATH,
            index=False,
            encoding="utf-8"
        )

        print("\n" + "=" * 60)
        print("🎉 STAGE 2 COMPLETED")
        print("=" * 60)

        print(
            f"Nodes     : {len(final_nodes)}\n"
            f"Relations : {len(final_relations)}\n"
            f"Triples   : {len(triple_df)}"
        )

    except Exception:

        print(
            "\n❌ STAGE 2 CRASHED"
        )

        print("-" * 60)

        traceback.print_exc(
            file=sys.stdout
        )

        print("-" * 60)


if __name__ == "__main__":
    main()