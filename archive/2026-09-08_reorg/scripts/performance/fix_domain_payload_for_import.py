import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a Jaspersoft Domain Designer payload for faster/stable import "
            "(expanded=false, remove temp schema metadata, keep expression logic intact)."
        )
    )
    parser.add_argument("--in", dest="in_file", required=True, help="Input payload JSON path")
    parser.add_argument("--out", dest="out_file", required=True, help="Output payload JSON path")
    parser.add_argument(
        "--schema-label",
        dest="schema_label",
        default=None,
        help="Optional schema label override",
    )
    parser.add_argument(
        "--domain-label",
        dest="domain_label",
        default=None,
        help="Optional domain label override",
    )
    args = parser.parse_args()

    in_path = Path(args.in_file)
    out_path = Path(args.out_file)

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    payload["expanded"] = False

    expr_container = payload.get("expression")
    if not isinstance(expr_container, dict) or "expression" not in expr_container:
        raise ValueError("Payload missing expression.expression")

    expr_raw = expr_container["expression"]
    if isinstance(expr_raw, str):
        expr_json = json.loads(expr_raw)
    elif isinstance(expr_raw, dict):
        expr_json = expr_raw
    else:
        raise ValueError("expression.expression must be string JSON or object")

    schema = expr_json.get("schema", {})
    if isinstance(schema, dict):
        for key in ("creationDate", "uri", "permissionMask"):
            schema.pop(key, None)
        # Keep semantic designer schema version positive for import stability.
        schema["version"] = 1
        if args.schema_label:
            schema["label"] = args.schema_label
        expr_json["schema"] = schema

    if args.domain_label:
        expr_json["label"] = args.domain_label

    # Keep compatibility with APIs that expect expression.expression as string JSON.
    payload["expression"]["expression"] = json.dumps(expr_json, separators=(",", ":"))

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

