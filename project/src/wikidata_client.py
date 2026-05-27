import time
import logging
from typing import Optional, Any

import requests

from config import WIKIDATA_API, HEADERS, MAX_HOPS

logger = logging.getLogger(__name__)

# ============================================================
# RELATION ONTOLOGY
# ============================================================

PROPERTY_TO_RELATION: dict[str, str] = {
    "P84":   "architect",
    "P131":  "located_in",
    "P276":  "located_in",
    "P186":  "material_used",
    "P176":  "built_by",
    "P361":  "part_of",
    "P130":  "related_to",
}

# ============================================================
# METADATA PROPERTIES
# ============================================================

METADATA_PROPERTIES: frozenset[str] = frozenset({
    "P17",     # country
    "P31",     # instance of
    "P1435",   # heritage designation
    "P571",    # inception
    "P6375",   # address
    "P625",    # coordinates
})

ALLOWED_PROPERTIES: frozenset[str] = (
    frozenset(PROPERTY_TO_RELATION)
    | METADATA_PROPERTIES
)

_BATCH_SIZE = 50
_DEFAULT_MAX_NODES = 200


# ============================================================
# CLIENT
# ============================================================

class WikidataClient:

    def __init__(
        self,
        max_nodes: int = _DEFAULT_MAX_NODES,
        max_hops: int = MAX_HOPS,
        batch_size: int = _BATCH_SIZE,
    ) -> None:

        self.max_nodes = max_nodes
        self.max_hops = max_hops
        self.batch_size = min(batch_size, _BATCH_SIZE)

        self._cache: dict[str, dict[str, Any]] = {}

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ========================================================
    # CONTEXT
    # ========================================================

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.session.close()

    # ========================================================
    # REQUEST
    # ========================================================

    def _safe_request(
        self,
        params: dict[str, Any],
        retries: int = 3,
        backoff: float = 1.0,
    ) -> Optional[dict[str, Any]]:

        attempt = 0

        while attempt < retries:

            try:
                resp = self.session.get(
                    WIKIDATA_API,
                    params=params,
                    timeout=15,
                )

                if resp.status_code == 429:

                    wait = float(
                        resp.headers.get(
                            "Retry-After",
                            5
                        )
                    )

                    logger.warning(
                        "Rate limited. Waiting %.1f sec",
                        wait
                    )

                    time.sleep(wait)

                    attempt += 1
                    continue

                resp.raise_for_status()

                body = resp.text.strip()

                if not body:
                    raise ValueError("Empty response body")

                return resp.json()

            except Exception as exc:

                logger.warning(
                    "Request failed (%d/%d): %s",
                    attempt + 1,
                    retries,
                    exc
                )

                time.sleep(
                    backoff * (2 ** attempt)
                )

                attempt += 1

        return None

    # ========================================================
    # SEARCH ENTITY
    # ========================================================

    def search_entity(
        self,
        query: str
    ) -> Optional[str]:

        data = self._safe_request({
            "action": "wbsearchentities",
            "format": "json",
            "language": "vi",
            "search": query,
        })

        results = (
            data or {}
        ).get("search", [])

        return (
            results[0]["id"]
            if results else None
        )

    # ========================================================
    # FETCH BATCH
    # ========================================================

    def _fetch_batch(
        self,
        ids: list[str]
    ) -> dict[str, dict[str, Any]]:

        result = {}

        uncached = [
            eid
            for eid in ids
            if eid not in self._cache
        ]

        for i in range(
            0,
            len(uncached),
            self.batch_size
        ):

            chunk = uncached[
                i : i + self.batch_size
            ]

            data = self._safe_request({
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "format": "json",
                "languages": "vi|en",
                "props": (
                    "labels|"
                    "descriptions|"
                    "aliases|"
                    "claims"
                ),
            })

            if data and "entities" in data:

                for eid, entity in data[
                    "entities"
                ].items():

                    if "missing" not in entity:
                        self._cache[eid] = entity

            if i + self.batch_size < len(uncached):
                time.sleep(0.5)

        for eid in ids:

            if eid in self._cache:
                result[eid] = self._cache[eid]

        return result

    # ========================================================
    # ENTITY INFO
    # ========================================================

    @staticmethod
    def _parse_info(
        entity: dict[str, Any]
    ) -> dict[str, Any]:

        def first(
            d: dict[str, Any]
        ) -> str:

            return (
                d.get("vi", {})
                .get("value")
                or
                d.get("en", {})
                .get("value", "")
            )

        return {
            "id": entity["id"],
            "label": first(
                entity.get("labels", {})
            ),
            "description": first(
                entity.get("descriptions", {})
            ),
            "aliases": [
                a["value"]
                for a in entity
                .get("aliases", {})
                .get("vi", [])
            ]
        }

    # ========================================================
    # HELPER
    # ========================================================

    def _resolve_entity_label(
        self,
        entity_id: str
    ) -> Optional[str]:

        if entity_id not in self._cache:
            return None

        entity = self._cache[entity_id]

        labels = entity.get(
            "labels",
            {}
        )

        return (
            labels.get("vi", {})
            .get("value")
            or
            labels.get("en", {})
            .get("value")
        )

    # ========================================================
    # CLAIM EXTRACTION
    # ========================================================

    def _extract_claims(
        self,
        entity: dict[str, Any]
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]]
    ]:

        relations = []
        metadata = []

        entity_id = entity["id"]

        claims = entity.get(
            "claims",
            {}
        )

        for prop, values in claims.items():

            if prop not in ALLOWED_PROPERTIES:
                continue

            for val in values:

                try:
                    mainsnak = val["mainsnak"]

                    datatype = mainsnak.get(
                        "datatype"
                    )

                    datavalue = mainsnak.get(
                        "datavalue",
                        {}
                    )

                    raw_value = datavalue.get(
                        "value"
                    )

                    if raw_value is None:
                        continue

                    # ====================================
                    # METADATA
                    # ====================================

                    if prop in METADATA_PROPERTIES:

                        target_value = None

                        # ------------------------
                        # COORDINATES
                        # ------------------------

                        if (
                            datatype == "globe-coordinate"
                            and isinstance(raw_value, dict)
                        ):

                            lat = raw_value.get(
                                "latitude"
                            )

                            lon = raw_value.get(
                                "longitude"
                            )

                            target_value = {
                                "latitude": lat,
                                "longitude": lon,
                            }

                        # ------------------------
                        # TIME
                        # ------------------------

                        elif (
                            datatype == "time"
                            and isinstance(raw_value, dict)
                        ):

                            target_value = raw_value.get(
                                "time"
                            )

                        # ------------------------
                        # ENTITY LINK
                        # ------------------------

                        elif (
                            datatype == "wikibase-item"
                            and isinstance(raw_value, dict)
                        ):

                            target_id = raw_value.get(
                                "id"
                            )

                            target_label = (
                                self._resolve_entity_label(
                                    target_id
                                )
                            )

                            target_value = {
                                "id": target_id,
                                "label": target_label,
                            }

                        # ------------------------
                        # TEXT
                        # ------------------------

                        elif datatype in (
                            "string",
                            "monolingualtext"
                        ):

                            if isinstance(raw_value, dict):

                                target_value = raw_value.get(
                                    "text"
                                )

                            else:
                                target_value = raw_value

                        if target_value is not None:

                            metadata.append({
                                "entity_id": entity_id,
                                "property": prop,
                                "target": target_value,
                            })

                    # ====================================
                    # RELATIONS
                    # ====================================

                    else:

                        if (
                            datatype == "wikibase-item"
                            and isinstance(raw_value, dict)
                        ):

                            relations.append({
                                "source": entity_id,
                                "property": prop,
                                "target": raw_value.get("id"),
                                "relation": PROPERTY_TO_RELATION[prop]
                            })

                except Exception:
                    continue

        return relations, metadata

    # ========================================================
    # BFS TRAVERSAL
    # ========================================================

    def multi_hop_traversal(
        self,
        seed_name: str,
        seed_id: Optional[str] = None,
    ):

        if seed_id is None:
            seed_id = self.search_entity(seed_name)

        if not seed_id:

            logger.warning(
                "Entity not found: %s",
                seed_name
            )

            return [], [], []

        visited = set()

        entities = {}

        all_relations = []
        all_metadata = []

        frontier = [seed_id]

        for hop in range(
            self.max_hops + 1
        ):

            if not frontier:
                break

            if len(entities) >= self.max_nodes:
                break

            budget = (
                self.max_nodes
                - len(entities)
            )

            to_visit = list(dict.fromkeys([
                eid
                for eid in frontier
                if eid not in visited
            ]))[:budget]

            if not to_visit:
                break

            visited.update(to_visit)

            raw = self._fetch_batch(
                to_visit
            )

            next_frontier = []

            # ====================================
            # PRELOAD NEIGHBOR LABELS
            # ====================================

            neighbor_ids = []

            for entity in raw.values():

                claims = entity.get(
                    "claims",
                    {}
                )

                for prop, values in claims.items():

                    if prop not in ALLOWED_PROPERTIES:
                        continue

                    for val in values:

                        try:
                            mainsnak = val["mainsnak"]

                            datavalue = mainsnak.get(
                                "datavalue",
                                {}
                            )

                            raw_value = datavalue.get(
                                "value"
                            )

                            if (
                                isinstance(raw_value, dict)
                                and "id" in raw_value
                            ):
                                neighbor_ids.append(
                                    raw_value["id"]
                                )

                        except Exception:
                            continue

            self._fetch_batch(
                list(set(neighbor_ids))
            )

            # ====================================
            # PROCESS
            # ====================================

            for eid, entity in raw.items():

                entities[eid] = self._parse_info(
                    entity
                )

                rels, meta = self._extract_claims(
                    entity
                )

                all_relations.extend(rels)
                all_metadata.extend(meta)

                if hop < self.max_hops:

                    next_frontier.extend([
                        r["target"]
                        for r in rels
                        if r["target"] not in visited
                    ])

            frontier = next_frontier

        logger.info(
            "Traversal done: %d entities, %d relations, %d metadata",
            len(entities),
            len(all_relations),
            len(all_metadata),
        )

        return (
            list(entities.values()),
            all_relations,
            all_metadata
        )