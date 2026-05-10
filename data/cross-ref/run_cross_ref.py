from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters import arc_agi_2, eci
from framework.loading import load_llm_chess_inputs
from framework.mapping import load_mapping_file
from framework.model_identity import build_llm_chess_inventory, inventory_summary
from framework.serialization import json_safe

REPO_ROOT = Path(__file__).resolve().parents[2]
CROSS_REF_ROOT = Path(__file__).resolve().parent
MODEL_IDENTITY_DIR = CROSS_REF_ROOT / "model-identity"
MAPPINGS_DIR = CROSS_REF_ROOT / "mappings"
RESULTS_DIR = CROSS_REF_ROOT / "results"

ADAPTERS = {
    "eci": eci,
    "arc_agi_2": arc_agi_2,
}


def _load_verification_outputs(
    inline_outputs: list[str] | None,
    output_files: list[Path] | None,
) -> list[str]:
    outputs = list(inline_outputs or [])
    for output_file in output_files or []:
        outputs.append(output_file.read_text(encoding="utf-8").rstrip())
    return outputs


def _build_verification_record(
    args: argparse.Namespace,
    inventory_path: Path,
    inventory_info: dict[str, object],
    mapping_path: Path,
) -> dict[str, object]:
    verification_commands = args.verification_command or []
    verification_outputs = _load_verification_outputs(
        args.verification_output,
        args.verification_output_file,
    )
    if verification_outputs and len(verification_outputs) != len(verification_commands):
        raise ValueError(
            "verification outputs must be supplied 1:1 with verification commands"
        )
    verification_checks = []
    for index, command in enumerate(verification_commands):
        check = {"command": command}
        if verification_outputs:
            check["output"] = verification_outputs[index]
        verification_checks.append(check)
    return {
        "runner_command": " ".join([".venv/bin/python", str(Path(__file__).relative_to(REPO_ROOT)), args.eval_id]),
        "inventory_path": inventory_info["inventory_path"],
        "mapping_file": _report_path(mapping_path),
        "verification_commands": verification_commands,
        "verification_checks": verification_checks,
        "test_status": args.test_status,
        "mapping_qa_status": args.mapping_qa_status,
        "run_qa_status": args.run_qa_status,
        "known_limitations": args.known_limitation or [],
    }


def _report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _ensure_parent(path)
    path.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def refresh_inventory(output_path: Path | None = None) -> tuple[Path, dict[str, object]]:
    output_path = output_path or MODEL_IDENTITY_DIR / "llm_chess_models.csv"
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    _ensure_parent(output_path)
    inventory.to_csv(output_path, index=False)
    return output_path, {
        "inventory_path": _report_path(output_path),
        "inventory_summary": inventory_summary(inventory),
    }


def run_eval(args: argparse.Namespace) -> None:
    adapter = ADAPTERS[args.eval_id]
    inventory_path, inventory_info = refresh_inventory(args.inventory_output)
    inventory = build_llm_chess_inventory(*load_llm_chess_inputs(REPO_ROOT)[:2])
    mapping_path = args.mapping_path or MAPPINGS_DIR / f"{args.eval_id}.csv"
    mapping = load_mapping_file(mapping_path)
    verification = _build_verification_record(args, inventory_path, inventory_info, mapping_path)
    summary, normalized_output, coverage_output, html_output = adapter.run_analysis(
        inventory,
        mapping,
        verification=verification,
    )
    if not verification["known_limitations"] and summary.get("limitations"):
        verification["known_limitations"] = list(summary["limitations"])
    summary["verification"] = verification
    summary_output = args.summary_output or RESULTS_DIR / f"{args.eval_id}_summary.json"
    html_path = args.html_output or RESULTS_DIR / f"{args.eval_id}.html"
    normalized_path = args.normalized_output or RESULTS_DIR / f"{args.eval_id}_normalized.csv"
    coverage_path = args.coverage_output or RESULTS_DIR / f"{args.eval_id}_coverage.csv"
    summary["verification"]["artifact_paths"] = {
        "summary_json": _report_path(summary_output),
        "html": _report_path(html_path),
        "normalized_csv": _report_path(normalized_path),
        "coverage_csv": _report_path(coverage_path),
    }
    summary = json_safe(summary)
    _write_json(summary_output, summary)
    _ensure_parent(html_path)
    html_path.write_text(html_output, encoding="utf-8")
    _ensure_parent(normalized_path)
    normalized_output.to_csv(normalized_path, index=False)
    _ensure_parent(coverage_path)
    coverage_output.to_csv(coverage_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run generalized cross-reference analyses.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Refresh the LLM Chess model inventory.")
    inventory_parser.add_argument("--inventory-output", type=Path)

    for eval_id in ADAPTERS:
        eval_parser = subparsers.add_parser(eval_id, help=f"Run the {eval_id} cross-reference analysis.")
        eval_parser.add_argument("--inventory-output", type=Path)
        eval_parser.add_argument("--mapping-path", type=Path)
        eval_parser.add_argument("--summary-output", type=Path)
        eval_parser.add_argument("--html-output", type=Path)
        eval_parser.add_argument("--normalized-output", type=Path)
        eval_parser.add_argument("--coverage-output", type=Path)
        eval_parser.add_argument("--verification-command", action="append")
        eval_parser.add_argument("--verification-output", action="append")
        eval_parser.add_argument("--verification-output-file", action="append", type=Path)
        eval_parser.add_argument("--test-status", default="not-run")
        eval_parser.add_argument("--mapping-qa-status", default="pending")
        eval_parser.add_argument("--run-qa-status", default="pending")
        eval_parser.add_argument("--known-limitation", action="append")
        eval_parser.set_defaults(eval_id=eval_id)

    args = parser.parse_args()
    if args.command == "inventory":
        path, payload = refresh_inventory(args.inventory_output)
        print(json.dumps({"inventory_path": _report_path(path), **payload}, indent=2))
        return
    run_eval(args)


if __name__ == "__main__":
    main()