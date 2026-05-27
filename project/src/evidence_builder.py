class EvidenceBuilder:

    # ========================================================
    # DEFAULT ENTITY CONTEXT
    # ========================================================

    def build_context(
        self,
        kg_results
    ):

        context = []

        provenance = []

        for item in kg_results:

            fact = f"""
Entity:
{item.get('label', '')}

Description:
{item.get('description', '')}

Type:
{item.get('type', '')}
"""

            # ----------------------------------------------
            # OPTIONAL FIELDS
            # ----------------------------------------------

            if item.get("country"):

                fact += f"""
Country:
{item.get('country')}
"""

            if item.get("instance_of"):

                fact += f"""
Instance Of:
{item.get('instance_of')}
"""

            if (
                item.get("latitude") is not None
                and item.get("longitude") is not None
            ):

                fact += f"""
Coordinates:
({item.get('latitude')}, {item.get('longitude')})
"""

            context.append(fact)

            provenance.append({

                "label":
                item.get("label"),

                "source":
                item.get(
                    "source",
                    "neo4j"
                ),

                "evidence_type":
                "KG_ENTITY"
            })

        return {

            "context":
            "\n".join(context),

            "provenance":
            provenance
        }

    # ========================================================
    # MULTI HOP REASONING
    # ========================================================

    def build_multi_hop_context(
        self,
        paths
    ):

        context = []

        provenance = []

        for p in paths:

            nodes = p.get(
                "path_nodes",
                []
            )

            if not nodes:
                continue

            chain = []

            for n in nodes:

                chain.append(
                    f"{n.get('label')} ({n.get('type')})"
                )

            chain_text = " -> ".join(chain)

            context.append(
                f"""
Location reasoning chain:
{chain_text}
"""
            )

            provenance.append({

                "reasoning_type":
                "multi_hop_graph_traversal",

                "path":
                chain
            })

        return {

            "context":
            "\n".join(context),

            "provenance":
            provenance
        }

    # ========================================================
    # RELATION CONTEXT
    # ========================================================

    def build_relation_context(
        self,
        relations
    ):

        context = []

        provenance = []

        for rel in relations:

            fact = f"""
{rel.get('source')}
-[{rel.get('relation')}]->
{rel.get('target')}
"""

            context.append(fact)

            provenance.append({

                "source":
                rel.get("source"),

                "target":
                rel.get("target"),

                "relation":
                rel.get("relation"),

                "evidence_type":
                "KG_RELATION"
            })

        return {

            "context":
            "\n".join(context),

            "provenance":
            provenance
        }