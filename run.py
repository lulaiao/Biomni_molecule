#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import sys
from pathlib import Path

CURRENT_SCRIPT = Path(__file__).resolve()
BASE_DIR = CURRENT_SCRIPT.parent
LIBINVENT_DIR = BASE_DIR / "Lib-INVENT"

if not LIBINVENT_DIR.exists():
    raise FileNotFoundError(f"Lib-INVENT directory not found: {LIBINVENT_DIR}")

if str(LIBINVENT_DIR) not in sys.path:
    sys.path.insert(0, str(LIBINVENT_DIR))

from running_modes.manager import Manager


def normalize_config(params: dict) -> dict:
    """
    Support either:
    1. flat tool-style params
    2. original Lib-INVENT config format with top-level 'parameters'
    """
    if "parameters" in params and "run_type" in params:
        return params

    run_type = params.get("run_type", "scaffold_decorating")

    return {
        "run_type": run_type,
        "parameters": {
            "model_path": params.get(
                "model_path",
                str(LIBINVENT_DIR / "trained_models" / "reaction_based.model")
            ),
            "input_scaffold_path": params.get(
                "input_scaffold_path",
                str(LIBINVENT_DIR / "examples" / "scaffolds.smi")
            ),
            "output_path": params.get(
                "output_path",
                str(LIBINVENT_DIR / "examples" / "decorate_output.csv")
            ),
            "logging_path": params.get(
                "logging_path",
                str(LIBINVENT_DIR / "examples" / "decorate_log")
            ),
            "batch_size": params.get("batch_size", 1),
            "number_of_decorations_per_scaffold": params.get(
                "number_of_decorations_per_scaffold", 32
            ),
            "randomize": params.get("randomize", True),
        },
    }


def resolve_params_file() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return (BASE_DIR / "params.json").resolve()


def validate_paths(config: dict):
    params = config["parameters"]

    model_path = Path(params["model_path"])
    input_scaffold_path = Path(params["input_scaffold_path"])
    output_path = Path(params["output_path"])
    logging_path = Path(params["logging_path"])

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    if not input_scaffold_path.exists():
        raise FileNotFoundError(f"Input scaffold file not found: {input_scaffold_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logging_path.parent.mkdir(parents=True, exist_ok=True)


def summarize_csv(output_path: Path, preview_rows: int = 5) -> dict:
    """
    Summarize Lib-INVENT output CSV.
    """
    if not output_path.exists():
        return {
            "output_exists": False,
            "row_count": 0,
            "columns": [],
            "preview": [],
        }

    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)

    preview = rows[:preview_rows]

    return {
        "output_exists": True,
        "row_count": len(rows),
        "columns": columns,
        "preview": preview,
    }


def main():
    result = {}

    try:
        params_file = resolve_params_file()
        if not params_file.exists():
            raise FileNotFoundError(f"params file not found: {params_file}")

        with open(params_file, "r", encoding="utf-8") as f:
            params = json.load(f)

        config = normalize_config(params)
        validate_paths(config)

        manager = Manager(config)
        manager.run()

        output_path = Path(config["parameters"]["output_path"])
        logging_path = Path(config["parameters"]["logging_path"])

        summary = summarize_csv(output_path, preview_rows=5)

        if not summary["output_exists"]:
            raise FileNotFoundError(f"Expected output file was not created: {output_path}")

        result = {
            "success": True,
            "message": "Lib-INVENT run completed successfully.",
            "params_file": str(params_file),
            "run_type": config["run_type"],
            "parameters": config["parameters"],
            "outputs": {
                "output_path": str(output_path),
                "logging_path": str(logging_path),
            },
            "summary": summary,
        }

    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
        }

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if result.get("success"):
        print("Task completed. Output saved to result.json.")
    else:
        print("Task failed. See result.json for details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()