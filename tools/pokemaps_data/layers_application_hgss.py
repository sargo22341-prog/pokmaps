"""Vue supérieure unique HGSS : les coupes techniques ne sont pas des étages du guide."""


def actor_layer(record: dict, ceiling: int) -> str:
    if ceiling not in {layer["ceiling_fx32"] for layer in record["layers"]}:
        raise ValueError(f"HGSS : coupe inconnue pour {record['const']} : {ceiling}")
    return record["const"]


def surface_map(record: dict, height: int) -> str:
    return record["const"]
