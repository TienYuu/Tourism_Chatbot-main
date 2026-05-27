import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm

# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

driver = GraphDatabase.driver(
    URI,
    auth=(USER, PASSWORD)
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

NODE_PATH = (
    BASE_DIR
    / "data"
    / "refined"
    / "refined_nodes.json"
)

REL_PATH = (
    BASE_DIR
    / "data"
    / "refined"
    / "refined_relations.json"
)

# ============================================================
# LOAD JSON
# ============================================================

with open(NODE_PATH, "r", encoding="utf-8") as f:
    nodes = json.load(f)

with open(REL_PATH, "r", encoding="utf-8") as f:
    relations = json.load(f)

# ============================================================
# HELPERS
# ============================================================

def clean_properties(data: dict) -> dict:
    """
    Loại bỏ:
    - None
    - ""
    - []
    - {}
    """
    cleaned = {}

    for k, v in data.items():

        if v is None:
            continue

        if v == "":
            continue

        if isinstance(v, (list, dict)) and len(v) == 0:
            continue

        cleaned[k] = v

    return cleaned


def safe_relation_type(rel_type: str) -> str:
    """
    Neo4j relation type không cho phép ký tự lạ.
    """
    if not rel_type:
        return "RELATED_TO"

    return (
        rel_type
        .replace("-", "_")
        .replace(" ", "_")
        .replace(".", "_")
    )

# ============================================================
# CREATE CONSTRAINT
# ============================================================

def create_constraints(tx):

    tx.run("""
    CREATE CONSTRAINT entity_id_unique
    IF NOT EXISTS
    FOR (n:Entity)
    REQUIRE n.id IS UNIQUE
    """)

# ============================================================
# INSERT NODE
# ============================================================

def insert_node(tx, node):

    node_id = node.get("id")

    if not node_id:
        return

    wd_props = node.get("wd_properties", {})

    instance_of = [
        x.get("label")
        for x in wd_props.get("instance_of", [])
        if isinstance(x, dict)
    ]

    instance_of_ids = [
        x.get("id")
        for x in wd_props.get("instance_of", [])
        if isinstance(x, dict)
    ]

    heritage_designation = [
        x.get("label")
        for x in wd_props.get("heritage_designation", [])
        if isinstance(x, dict)
    ]

    country = [
        x.get("label")
        for x in wd_props.get("country", [])
        if isinstance(x, dict)
    ]

    country_ids = [
        x.get("id")
        for x in wd_props.get("country", [])
        if isinstance(x, dict)
    ]

    # Nhập các thuộc tính ban đầu + bổ sung inception và address
    props = clean_properties({
        "id": node.get("id"),
        "label": node.get("label"),
        "type": node.get("type"),
        "ner_type": node.get("ner_type"),
        "description": node.get("description"),

        "latitude": node.get("latitude"),
        "longitude": node.get("longitude"),

        # BỔ SUNG 2 TRƯỜNG MỚI Ở ĐÂY
        "inception": node.get("inception"),
        "address": node.get("address"),

        "aliases": node.get("aliases"),

        # FLATTENED WIKIDATA PROPERTIES
        "instance_of": instance_of,
        "instance_of_ids": instance_of_ids,

        "heritage_designation": heritage_designation,

        "country": country,
        "country_ids": country_ids,

        "source": node.get("source"),
        "download_date": node.get("download_date")
    })

    query = """
    MERGE (n:Entity {id: $id})
    SET n += $props
    """

    tx.run(
        query,
        id=node_id,
        props=props
    )

# ============================================================
# INSERT RELATION
# ============================================================

def insert_relation(tx, rel):

    source = rel.get("source")
    target = rel.get("target")

    if not source or not target:
        return

    relation_type = safe_relation_type(
        rel.get("relation", "RELATED_TO")
    )

    relation_props = clean_properties({
        "confidence": rel.get("confidence")
    })

    query = f"""
    MATCH (a:Entity {{id: $source}})
    MATCH (b:Entity {{id: $target}})

    MERGE (a)-[r:{relation_type}]->(b)

    SET r += $props
    """

    tx.run(
        query,
        source=source,
        target=target,
        props=relation_props
    )

# ============================================================
# MAIN
# ============================================================

def main():

    print("\n==================================================")
    print("🚀 START IMPORT TO NEO4J")
    print("==================================================")

    with driver.session(database=DATABASE) as session:

        # ------------------------------------------------
        # CREATE CONSTRAINTS
        # ------------------------------------------------

        print("\n[1/3] Creating constraints...")

        session.execute_write(
            create_constraints
        )

        # ------------------------------------------------
        # INSERT NODES
        # ------------------------------------------------

        print("\n[2/3] Loading nodes...")

        success_nodes = 0

        for node in tqdm(nodes, desc="Import Nodes"):

            try:

                session.execute_write(
                    insert_node,
                    node
                )

                success_nodes += 1

            except Exception as e:

                print("\n[NODE ERROR]")
                print(node.get("id"))
                print(e)

        # ------------------------------------------------
        # INSERT RELATIONS
        # ------------------------------------------------

        print("\n[3/3] Loading relations...")

        success_relations = 0

        for rel in tqdm(relations, desc="Import Relations"):

            try:

                session.execute_write(
                    insert_relation,
                    rel
                )

                success_relations += 1

            except Exception as e:

                print("\n[RELATION ERROR]")
                print(rel)
                print(e)

    driver.close()

    print("\n==================================================")
    print("🎉 IMPORT COMPLETED")
    print("==================================================")

    print(f"Nodes imported: {success_nodes}")
    print(f"Relations imported: {success_relations}")

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()