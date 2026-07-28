from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import warnings

import pandas as pd

from adapters import arc_agi_2, bullshit_bench, delegate_52, eci, vals_index
from framework.cross_eval import (
    EXCLUDED_SUMMARY_FILES,
    build_cross_eval_summary,
    render_cross_eval_report_markdown,
)
from framework.diffing import build_eval_diff_report, render_artifact_diff_markdown
from framework.loading import load_llm_chess_inputs
from framework.mapping import check_player_resolution, load_mapping_file
from framework.mapping_review import build_mapping_review
from framework.model_identity import build_llm_chess_inventory, inventory_summary
from framework.rendering import render_mapping_review_html
from framework.serialization import json_safe

REPO_ROOT = Path(__file__).resolve().parents[2]
CROSS_REF_ROOT = Path(__file__).resolve().parent
MODEL_IDENTITY_DIR = CROSS_REF_ROOT / "model-identity"
MAPPINGS_DIR = CROSS_REF_ROOT / "mappings"
RESULTS_DIR = CROSS_REF_ROOT / "results"
PUBLISHED_OUTPUT_DIRS = (MODEL_IDENTITY_DIR, RESULTS_DIR)

ADAPTERS = {
    "eci": eci,
    "arc_agi_2": arc_agi_2,
    "bullshit_bench": bullshit_bench,
    "delegate_52": delegate_52,
    "vals_index": vals_index,
}

ALLOW_METADATA_ONLY_HELP = (
    "Let the publish gate accept accepted mapping rows whose llm_chess_player is known to "
    "data/models_metadata.csv but has no row in data/elo_refined.csv. Off by default: absence "
    "from elo_refined.csv is a failure because such a row contributes to no statistic."
)


def _scratch_output_dir(label: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"cross_ref_{label}_"))


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _ensure_publish_allowed(paths: list[Path | None], publish: bool) -> None:
    if publish:
        return
    published_paths = [
        path
        for path in paths
        if path is not None and any(_is_inside(path, root) for root in PUBLISHED_OUTPUT_DIRS)
    ]
    if published_paths:
        formatted_paths = ", ".join(_report_path(path) for path in published_paths)
        raise ValueError(f"checked-in generated artifact outputs require --publish: {formatted_paths}")


def _output_mode(publish: bool) -> str:
    return "publish" if publish else "review"


def _llm_chess_inventory() -> pd.DataFrame:
    return build_llm_chess_inventory(*load_llm_chess_inputs(REPO_ROOT)[:2])


def _player_resolution_by_eval(
    mapping_dir: Path,
    inventory: pd.DataFrame,
    eval_ids: list[str] | None = None,
) -> dict[str, dict[str, list[dict[str, object]]]]:
    resolution = {}
    for eval_id in sorted(eval_ids or ADAPTERS):
        mapping_path = mapping_dir / f"{eval_id}.csv"
        if not mapping_path.exists():
            continue
        resolution[eval_id] = check_player_resolution(load_mapping_file(mapping_path), inventory)
    return resolution


def _resolution_rows(
    resolution: dict[str, dict[str, list[dict[str, object]]]],
    kind: str,
) -> list[dict[str, object]]:
    return [row for entry in resolution.values() for row in entry[kind]]


def _unresolved_player_kinds(allow_metadata_only: bool) -> tuple[str, ...]:
    """Which resolution buckets count as unresolved.

    Absence from data/elo_refined.csv is the failure condition: such a row contributes to no
    statistic, so whether the name is unknown entirely or merely metadata-only does not change
    that. ``allow_metadata_only`` restores the older leniency for the rare case that wants it.
    """
    return ("dangling",) if allow_metadata_only else ("dangling", "metadata_only")


def _unresolved_player_rows(
    resolution: dict[str, dict[str, list[dict[str, object]]]],
    *,
    allow_metadata_only: bool = False,
) -> list[dict[str, object]]:
    return [
        row
        for kind in _unresolved_player_kinds(allow_metadata_only)
        for row in _resolution_rows(resolution, kind)
    ]


def _describe_unresolved_players(rows: list[dict[str, object]]) -> str:
    names = sorted({str(row["llm_chess_player"]) for row in rows})
    return f"{len(rows)} accepted mapping rows ({', '.join(names)})"


def _ensure_player_resolution_publishable(
    resolution: dict[str, dict[str, list[dict[str, object]]]],
    publish: bool,
    *,
    allow_metadata_only: bool = False,
) -> None:
    if not publish:
        return
    unresolved = _unresolved_player_rows(resolution, allow_metadata_only=allow_metadata_only)
    if unresolved:
        raise ValueError(
            f"{_describe_unresolved_players(unresolved)} point at llm_chess_player values with no "
            "row in data/elo_refined.csv and must not be published; repoint the mapping CSVs first"
        )


def _warn_unresolved_players(
    resolution: dict[str, dict[str, list[dict[str, object]]]],
    *,
    allow_metadata_only: bool = False,
) -> None:
    unresolved = _unresolved_player_rows(resolution, allow_metadata_only=allow_metadata_only)
    if unresolved:
        warnings.warn(
            f"{_describe_unresolved_players(unresolved)} point at llm_chess_player values with no "
            "row in data/elo_refined.csv; this state cannot be published",
            stacklevel=2,
        )


def _actual_llm_chess_input_rows() -> dict[str, int]:
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    return {"elo_refined": int(len(elo)), "models_metadata": int(len(metadata))}


# verify's own artifact matches the *_summary.json glob but is not a per-eval summary, so it must
# not be checked as one once it has been published into results/.
NON_EVAL_SUMMARY_FILES = EXCLUDED_SUMMARY_FILES | {"verify_summary.json"}


def _published_summary_paths(results_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in results_dir.glob("*_summary.json")
        if path.is_file() and path.name not in NON_EVAL_SUMMARY_FILES
    )


def _recorded_input_row_checks(results_dir: Path, actual_rows: dict[str, int]) -> list[dict[str, object]]:
    checks = []
    for summary_path in _published_summary_paths(results_dir):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        recorded = summary.get("llm_chess_inputs") if isinstance(summary, dict) else None
        recorded = recorded if isinstance(recorded, dict) else {}
        for input_id, actual in actual_rows.items():
            input_contract = recorded.get(input_id)
            recorded_rows = input_contract.get("rows") if isinstance(input_contract, dict) else None
            checks.append(
                {
                    "eval_id": summary.get("eval_id") if isinstance(summary, dict) else None,
                    "summary_path": _report_path(summary_path),
                    "input_id": input_id,
                    "recorded_rows": recorded_rows,
                    "actual_rows": actual,
                    "matches": recorded_rows == actual,
                }
            )
    return checks


def _ensure_recorded_input_rows_publishable(checks: list[dict[str, object]], publish: bool) -> None:
    if not publish:
        return
    stale = [check for check in checks if not check["matches"]]
    if stale:
        details = ", ".join(
            f"{check['summary_path']}:{check['input_id']} recorded {check['recorded_rows']} vs actual {check['actual_rows']}"
            for check in stale[:6]
        )
        raise ValueError(
            f"{len(stale)} published summaries record llm_chess input row counts that disagree with the "
            f"current authoritative inputs and must not be published: {details}"
        )


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


def refresh_inventory(output_path: Path | None = None, *, publish: bool = False) -> tuple[Path, dict[str, object]]:
    output_path = output_path or (
        MODEL_IDENTITY_DIR / "llm_chess_models.csv"
        if publish
        else _scratch_output_dir("inventory") / "llm_chess_models.csv"
    )
    _ensure_publish_allowed([output_path], publish)
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    _ensure_parent(output_path)
    inventory.to_csv(output_path, index=False)
    return output_path, {
        "inventory_path": _report_path(output_path),
        "inventory_summary": inventory_summary(inventory),
    }


def run_eval(args: argparse.Namespace) -> dict[str, object]:
    adapter = ADAPTERS[args.eval_id]
    publish = bool(getattr(args, "publish", False))
    mistake_stats = getattr(args, "mistake_stats", "excluded")
    if mistake_stats == "clean_only" and publish:
        raise ValueError(
            "mistake_stats=clean_only is a research-only mode and must not be published; "
            "drop --publish and use explicit scratch outputs instead"
        )
    allow_metadata_only = bool(getattr(args, "allow_metadata_only", False))
    mapping_path = args.mapping_path or MAPPINGS_DIR / f"{args.eval_id}.csv"
    inventory = _llm_chess_inventory()
    resolution = {args.eval_id: check_player_resolution(load_mapping_file(mapping_path), inventory)}
    _ensure_player_resolution_publishable(resolution, publish, allow_metadata_only=allow_metadata_only)
    _warn_unresolved_players(resolution, allow_metadata_only=allow_metadata_only)
    scratch_dir = None if publish else _scratch_output_dir(args.eval_id)
    source_path = getattr(args, "source_path", None)
    inventory_output = args.inventory_output or (
        MODEL_IDENTITY_DIR / "llm_chess_models.csv"
        if publish
        else scratch_dir / "llm_chess_models.csv"
    )
    summary_output = args.summary_output or (
        RESULTS_DIR / f"{args.eval_id}_summary.json"
        if publish
        else scratch_dir / f"{args.eval_id}_summary.json"
    )
    html_path = args.html_output or (
        RESULTS_DIR / f"{args.eval_id}.html"
        if publish
        else scratch_dir / f"{args.eval_id}.html"
    )
    normalized_path = args.normalized_output
    coverage_path = args.coverage_output or (
        RESULTS_DIR / f"{args.eval_id}_coverage.csv"
        if publish
        else scratch_dir / f"{args.eval_id}_coverage.csv"
    )
    _ensure_publish_allowed(
        [inventory_output, summary_output, html_path, normalized_path, coverage_path],
        publish,
    )
    inventory_path, inventory_info = refresh_inventory(inventory_output, publish=publish)
    mapping = load_mapping_file(mapping_path)
    verification = _build_verification_record(args, inventory_path, inventory_info, mapping_path)
    summary, normalized_output, coverage_output, html_output = adapter.run_analysis(
        inventory,
        mapping,
        verification=verification,
        source_path=source_path,
        mapping_path=mapping_path,
        mistake_stats=mistake_stats,
    )
    if not verification["known_limitations"] and summary.get("limitations"):
        verification["known_limitations"] = list(summary["limitations"])
    summary["verification"] = verification
    artifact_paths = {
        "summary_json": _report_path(summary_output),
        "html": _report_path(html_path),
        "coverage_csv": _report_path(coverage_path),
    }
    if normalized_path is not None:
        artifact_paths["normalized_csv"] = _report_path(normalized_path)
    summary["verification"]["artifact_paths"] = artifact_paths
    summary = json_safe(summary)
    _write_json(summary_output, summary)
    _ensure_parent(html_path)
    html_path.write_text(html_output, encoding="utf-8")
    if normalized_path is not None:
        _ensure_parent(normalized_path)
        normalized_output.to_csv(normalized_path, index=False)
    _ensure_parent(coverage_path)
    coverage_output.to_csv(coverage_path, index=False)
    payload = {
        "output_mode": _output_mode(publish),
        "summary_output": _report_path(summary_output),
        "html_output": _report_path(html_path),
        "coverage_output": _report_path(coverage_path),
        "inventory_output": _report_path(inventory_path),
        "mapping_path": _report_path(mapping_path),
    }
    if source_path is not None:
        payload["source_path"] = _report_path(source_path)
    if normalized_path is not None:
        payload["normalized_output"] = _report_path(normalized_path)
    return payload


def run_mapping_review(args: argparse.Namespace) -> dict[str, object]:
    publish = bool(getattr(args, "publish", False))
    review_rows, payload = build_mapping_review(
        args.mapping_dir or MAPPINGS_DIR,
        eval_id=args.filter_eval_id,
        player=args.filter_player,
        statuses=args.filter_status,
        provider=args.filter_provider,
    )
    if args.csv_output is None and args.html_output is None:
        output_dir = RESULTS_DIR if publish else _scratch_output_dir("mapping_review")
        csv_path = output_dir / "mapping_review.csv"
        html_path = output_dir / "mapping_review.html"
    elif args.csv_output is None:
        html_path = args.html_output
        csv_path = html_path.with_suffix(".csv")
    elif args.html_output is None:
        csv_path = args.csv_output
        html_path = csv_path.with_suffix(".html")
    else:
        csv_path = args.csv_output
        html_path = args.html_output
    _ensure_publish_allowed([csv_path, html_path], publish)
    _ensure_parent(csv_path)
    review_rows.to_csv(csv_path, index=False)
    _ensure_parent(html_path)
    html_path.write_text(render_mapping_review_html(payload), encoding="utf-8")
    return {
        "output_mode": _output_mode(publish),
        "csv_output": _report_path(csv_path),
        "html_output": _report_path(html_path),
        "filters": payload["filters"],
        "summary": payload["summary"],
        "status_counts": payload["status_counts"],
    }


def run_cross_eval(args: argparse.Namespace) -> dict[str, object]:
    publish = bool(getattr(args, "publish", False))
    results_dir = args.results_dir or RESULTS_DIR
    _ensure_publish_state_clean(
        results_dir,
        MAPPINGS_DIR,
        publish,
        allow_metadata_only=bool(getattr(args, "allow_metadata_only", False)),
    )
    if args.summary_output is None and args.report_output is None:
        output_dir = results_dir if publish else _scratch_output_dir("cross_eval")
        summary_output = output_dir / "cross_ref_summary.json"
        report_output = output_dir / "cross_ref_report.md"
    elif args.summary_output is None:
        report_output = args.report_output
        summary_output = report_output.with_name("cross_ref_summary.json")
    elif args.report_output is None:
        summary_output = args.summary_output
        report_output = summary_output.with_name("cross_ref_report.md")
    else:
        summary_output = args.summary_output
        report_output = args.report_output
    _ensure_publish_allowed([summary_output, report_output], publish)
    summary = build_cross_eval_summary(
        results_dir=results_dir,
        summary_output=summary_output,
        report_output=report_output,
        repo_root=REPO_ROOT,
    )
    _write_json(summary_output, summary)
    _ensure_parent(report_output)
    report_output.write_text(render_cross_eval_report_markdown(summary), encoding="utf-8")
    return {
        "output_mode": _output_mode(publish),
        "summary_output": _report_path(summary_output),
        "report_output": _report_path(report_output),
        "eval_count": summary["eval_count"],
        "eval_ids": [entry["eval_id"] for entry in summary["evals"]],
        "source_summaries": [entry["summary_path"] for entry in summary["generated_from"]["summaries"]],
    }


def run_rerun_diff(args: argparse.Namespace) -> dict[str, object]:
    baseline_results_dir = args.baseline_results_dir or RESULTS_DIR
    baseline_summary_path = baseline_results_dir / f"{args.target}_summary.json"
    if not baseline_summary_path.exists():
        raise ValueError(f"baseline summary_json artifact not found at {baseline_summary_path}")
    baseline_summary = json.loads(baseline_summary_path.read_text(encoding="utf-8"))
    baseline_verification = baseline_summary.get("verification", {}) if isinstance(baseline_summary, dict) else {}
    baseline_mapping = baseline_summary.get("mapping", {}) if isinstance(baseline_summary, dict) else {}
    scratch_dir = args.scratch_dir or Path(tempfile.mkdtemp(prefix=f"cross_ref_{args.target}_"))
    scratch_dir.mkdir(parents=True, exist_ok=True)

    candidate_summary = scratch_dir / f"{args.target}_summary.json"
    candidate_html = scratch_dir / f"{args.target}.html"
    candidate_coverage = scratch_dir / f"{args.target}_coverage.csv"
    candidate_inventory = scratch_dir / f"{args.target}_inventory.csv"

    eval_args = argparse.Namespace(
        command=args.target,
        eval_id=args.target,
        inventory_output=candidate_inventory,
        mapping_path=args.mapping_path,
        source_path=args.source_path,
        summary_output=candidate_summary,
        html_output=candidate_html,
        normalized_output=None,
        coverage_output=candidate_coverage,
        verification_command=[],
        verification_output=None,
        verification_output_file=None,
        test_status=baseline_verification.get("test_status", "not-run"),
        mapping_qa_status=baseline_mapping.get("qa_verdict", "pending"),
        run_qa_status=baseline_verification.get("run_qa_status", "pending"),
        known_limitation=baseline_verification.get("known_limitations"),
    )
    run_eval(eval_args)

    baseline_artifacts = {
        "summary_json": baseline_summary_path,
        "coverage_csv": baseline_results_dir / f"{args.target}_coverage.csv",
    }
    for artifact_id, artifact_path in baseline_artifacts.items():
        if not artifact_path.exists():
            raise ValueError(f"baseline {artifact_id} artifact not found at {artifact_path}")

    candidate_artifacts = {
        "summary_json": candidate_summary,
        "coverage_csv": candidate_coverage,
    }
    diff_payload = build_eval_diff_report(
        args.target,
        baseline_artifacts=baseline_artifacts,
        candidate_artifacts=candidate_artifacts,
    )

    diff_json_output = args.diff_json_output or scratch_dir / f"{args.target}_diff.json"
    diff_md_output = args.diff_md_output or scratch_dir / f"{args.target}_diff.md"
    _write_json(diff_json_output, diff_payload)
    _ensure_parent(diff_md_output)
    diff_md_output.write_text(render_artifact_diff_markdown(diff_payload), encoding="utf-8")
    return {
        "target": args.target,
        "has_diff": diff_payload["has_diff"],
        "scratch_dir": _report_path(scratch_dir),
        "baseline_artifacts": {key: _report_path(path) for key, path in baseline_artifacts.items()},
        "candidate_artifacts": {key: _report_path(path) for key, path in candidate_artifacts.items()},
        "diff_json_output": _report_path(diff_json_output),
        "diff_md_output": _report_path(diff_md_output),
    }


def render_audit_markdown(summary: dict[str, object]) -> str:
    benchmark_ids = ", ".join(summary["benchmarks"]["ids"])
    lines = [
        "# Cross-Ref Audit",
        "",
        f"overall_status: {summary['overall_status']}",
        f"reproducibility_status: {summary['reproducibility_status']}",
        f"coverage_status: {summary['coverage_status']}",
        f"benchmarks: {benchmark_ids}",
        "",
        "trust this:",
    ]
    lines.extend(f"- {item}" for item in summary["trust_boundaries"]["safe_for"])
    lines.append("")
    lines.append("do not trust this:")
    lines.extend(f"- {item}" for item in summary["trust_boundaries"]["not_safe_for"])
    lines.extend(
        [
            "",
            "counts:",
            f"- total benches: {summary['benchmarks']['count']}",
            f"- external evals: {summary['benchmarks']['external_eval_count']}",
            f"- unresolved mapping rows: {summary['mapping_review']['unresolved_row_count']}",
            f"- rerun diffs with changes: {summary['reproducibility']['evals_with_diff_count']}",
            "",
            "per-eval reproducibility:",
            "| eval | rerun_diff | metric_rows | elo_rows | raw_elo_r | prediction_r2 | prediction_n | unresolved_high_impact |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for entry in summary["reproducibility"]["per_eval"]:
        lines.append(
            "| {eval_id} | {status} | {metric_rows} | {elo_rows} | {raw_elo_r} | {prediction_r2} | {prediction_n} | {unresolved_high_impact} |".format(
                eval_id=entry["eval_id"],
                status="clean" if not entry["has_diff"] else "diff",
                metric_rows=entry["metric_rows"],
                elo_rows=entry["elo_rows"],
                raw_elo_r=entry["raw_elo_pearson_r"],
                prediction_r2=entry["prediction_r2"],
                prediction_n=entry["prediction_n"],
                unresolved_high_impact=entry["unresolved_high_impact_count"],
            )
        )
    if summary["review_needed_reasons"]:
        lines.extend(["", "review-needed reasons:"])
        lines.extend(f"- {item}" for item in summary["review_needed_reasons"])
    if summary["failure_reasons"]:
        lines.extend(["", "failure reasons:"])
        lines.extend(f"- {item}" for item in summary["failure_reasons"])
    lines.extend(
        [
            "",
            "published summary sha256:",
        ]
    )
    for entry in summary["published_state"]["source_summaries"]:
        lines.append(f"- {entry['eval_id']}: {entry['summary_sha256']}")
    lines.append("")
    lines.append("This file is generated by `run_cross_ref.py audit`. It is the single trust check, not a hand-written narrative.")
    return "\n".join(lines) + "\n"


def run_audit(args: argparse.Namespace) -> dict[str, object]:
    publish = bool(getattr(args, "publish", False))
    results_dir = args.results_dir or RESULTS_DIR
    mapping_dir = args.mapping_dir or MAPPINGS_DIR
    _ensure_publish_state_clean(
        results_dir,
        mapping_dir,
        publish,
        allow_metadata_only=bool(getattr(args, "allow_metadata_only", False)),
    )
    summary_output = args.summary_output
    report_output = args.report_output
    if summary_output is None and report_output is None:
        output_dir = results_dir if publish else _scratch_output_dir("audit")
        summary_output = output_dir / "audit_summary.json"
        report_output = output_dir / "audit_report.md"
    elif summary_output is None:
        summary_output = report_output.with_name("audit_summary.json")
    elif report_output is None:
        report_output = summary_output.with_name("audit_report.md")
    _ensure_publish_allowed([summary_output, report_output], publish)

    with tempfile.TemporaryDirectory(prefix="cross_ref_audit_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        _, inventory_info = refresh_inventory(tmp_dir / "llm_chess_inventory.csv")
        _, mapping_payload = build_mapping_review(mapping_dir)
        cross_eval_summary = build_cross_eval_summary(
            results_dir=results_dir,
            summary_output=tmp_dir / "cross_ref_summary.json",
            report_output=tmp_dir / "cross_ref_report.md",
            repo_root=REPO_ROOT,
        )
        per_eval = []
        for eval_id in sorted(ADAPTERS):
            rerun_payload = run_rerun_diff(
                argparse.Namespace(
                    command="rerun-diff",
                    target=eval_id,
                    baseline_results_dir=results_dir,
                    scratch_dir=tmp_dir / f"{eval_id}_scratch",
                    # Honour --mapping-dir for the reruns too. Falling back to the global
                    # MAPPINGS_DIR here let the rerun read different mapping bytes than the
                    # baseline, which turns a concurrent mapping edit into a spurious diff.
                    mapping_path=mapping_dir / f"{eval_id}.csv",
                    source_path=None,
                    diff_json_output=tmp_dir / f"{eval_id}_diff.json",
                    diff_md_output=tmp_dir / f"{eval_id}_diff.md",
                )
            )
            eval_summary = next(entry for entry in cross_eval_summary["evals"] if entry["eval_id"] == eval_id)
            per_eval.append(
                {
                    "eval_id": eval_id,
                    "has_diff": bool(rerun_payload["has_diff"]),
                    "metric_rows": eval_summary["coverage"].get("metric_analysis_rows_max_dedupe"),
                    "elo_rows": eval_summary["coverage"].get("elo_analysis_rows_max_dedupe"),
                    "raw_elo_pearson_r": eval_summary["relationships"]["raw_elo"].get("pearson_r"),
                    "prediction_r2": eval_summary["prediction"]["ols"].get("r2"),
                    # The CV row count the r2 above was computed on, not the wider metric sample.
                    "prediction_n": eval_summary["prediction"].get("n"),
                    "unresolved_high_impact_count": eval_summary["mapping"].get("unresolved_high_impact_count"),
                }
            )

    failure_reasons = []
    review_needed_reasons = []
    if cross_eval_summary["eval_count"] != len(ADAPTERS):
        failure_reasons.append(
            f"expected {len(ADAPTERS)} published eval summaries but found {cross_eval_summary['eval_count']}"
        )
    if any(entry["has_diff"] for entry in per_eval):
        failure_reasons.append("one or more published eval artifacts do not reproduce cleanly against current authoritative inputs")

    unresolved_row_count = int(mapping_payload["summary"]["unresolved_row_count"])
    if unresolved_row_count > args.max_unresolved_rows:
        review_needed_reasons.append(
            f"mapping review still has {unresolved_row_count} unresolved rows above the allowed threshold of {args.max_unresolved_rows}"
        )
    if unresolved_row_count > 0:
        review_needed_reasons.append(
            "claims that depend on unresolved mappings being correct still need manual review"
        )

    reproducibility_status = "fail" if failure_reasons else "pass"
    coverage_status = "review-needed" if unresolved_row_count > args.max_unresolved_rows else "pass"
    if failure_reasons:
        overall_status = "fail"
    elif coverage_status != "pass":
        overall_status = "review-needed"
    else:
        overall_status = "pass"

    audit_summary = {
        "artifact_kind": "cross_ref_audit",
        "overall_status": overall_status,
        "reproducibility_status": reproducibility_status,
        "coverage_status": coverage_status,
        "benchmarks": {
            "count": 1 + cross_eval_summary["eval_count"],
            "ids": ["llm_chess", *[entry["eval_id"] for entry in cross_eval_summary["evals"]]],
            "reference_metric": "llm_chess",
            "external_eval_count": cross_eval_summary["eval_count"],
            "external_eval_ids": [entry["eval_id"] for entry in cross_eval_summary["evals"]],
        },
        "published_state": {
            "results_dir": _report_path(results_dir),
            "inventory_summary": inventory_info["inventory_summary"],
            "source_summaries": cross_eval_summary["generated_from"]["summaries"],
        },
        "mapping_review": {
            "row_count": mapping_payload["summary"]["row_count"],
            "eval_count": mapping_payload["summary"]["eval_count"],
            "unique_llm_chess_players": mapping_payload["summary"]["unique_llm_chess_players"],
            "unresolved_row_count": unresolved_row_count,
            "allowed_unresolved_row_count": args.max_unresolved_rows,
            "status_counts": mapping_payload["status_counts"],
        },
        "reproducibility": {
            "cross_eval_generated_from_published_summaries": True,
            "rerun_diff_all_clean": not any(entry["has_diff"] for entry in per_eval),
            "evals_with_diff_count": sum(1 for entry in per_eval if entry["has_diff"]),
            "per_eval": per_eval,
        },
        "analysis_snapshot": {
            "strongest_raw_elo": cross_eval_summary["comparisons"].get("strongest_raw_elo"),
            "best_prediction": cross_eval_summary["comparisons"].get("best_prediction"),
        },
        "trust_boundaries": {
            "safe_for": [
                "Published per-eval summaries reproduce cleanly against the current source snapshots and mapping CSVs." if not failure_reasons else "Published per-eval summaries need investigation before they can be trusted.",
                "The aggregate cross-eval report is regenerated from the published per-eval summaries.",
                "The benchmark set covered by this audit is "
                + ", ".join(["llm_chess", *[entry["eval_id"] for entry in cross_eval_summary["evals"]]])
                + ".",
            ],
            "not_safe_for": [
                "Claims that assume unresolved mapping rows are already resolved.",
                "Whole-surface drift explanation above the per-eval rerun-diff layer.",
            ],
        },
        "review_needed_reasons": review_needed_reasons,
        "failure_reasons": failure_reasons,
    }
    _write_json(summary_output, audit_summary)
    _ensure_parent(report_output)
    report_output.write_text(render_audit_markdown(audit_summary), encoding="utf-8")
    return {
        "output_mode": _output_mode(publish),
        "summary_output": _report_path(summary_output),
        "report_output": _report_path(report_output),
        "overall_status": audit_summary["overall_status"],
        "reproducibility_status": audit_summary["reproducibility_status"],
        "coverage_status": audit_summary["coverage_status"],
        "benchmark_ids": audit_summary["benchmarks"]["ids"],
        "unresolved_row_count": unresolved_row_count,
        "evals_with_diff_count": audit_summary["reproducibility"]["evals_with_diff_count"],
    }


def _ensure_publish_state_clean(
    results_dir: Path,
    mapping_dir: Path,
    publish: bool,
    *,
    allow_metadata_only: bool = False,
) -> None:
    """Refuse to cement a state the verify checks already know is broken."""
    if not publish:
        return
    _ensure_player_resolution_publishable(
        _player_resolution_by_eval(mapping_dir, _llm_chess_inventory()),
        publish,
        allow_metadata_only=allow_metadata_only,
    )
    _ensure_recorded_input_rows_publishable(
        _recorded_input_row_checks(results_dir, _actual_llm_chess_input_rows()), publish
    )


def _summary_player_names(payload: object) -> set[str]:
    names: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "llm_chess_player" and isinstance(value, str) and value.strip():
                names.add(value.strip())
            else:
                names.update(_summary_player_names(value))
    elif isinstance(payload, list):
        for value in payload:
            names.update(_summary_player_names(value))
    return names


def _coverage_player_names(coverage_path: Path) -> set[str]:
    coverage = pd.read_csv(coverage_path)
    if "llm_chess_player" not in coverage.columns:
        return set()
    return {
        str(value).strip()
        for value in coverage["llm_chess_player"].dropna()
        if str(value).strip()
    }


def _html_player_names(html: str, candidates: set[str]) -> set[str]:
    # Rendered reports are free text, so names can only be recognised from a candidate list. The
    # trailing guard stops `gemini-3-pro-preview` matching inside `gemini-3-pro-preview-high`.
    return {
        candidate
        for candidate in candidates
        if re.search(re.escape(candidate) + r"(?![-\w.])", html)
    }


def _artifact_player_agreement_checks(results_dir: Path) -> list[dict[str, object]]:
    checks = []
    for summary_path in _published_summary_paths(results_dir):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(summary, dict) or not summary.get("eval_id"):
            continue
        eval_id = str(summary["eval_id"])
        coverage_path = results_dir / f"{eval_id}_coverage.csv"
        html_path = results_dir / f"{eval_id}.html"
        summary_players = _summary_player_names(summary)
        coverage_players = _coverage_player_names(coverage_path) if coverage_path.exists() else set()
        html_players = (
            _html_player_names(html_path.read_text(encoding="utf-8"), summary_players | coverage_players)
            if html_path.exists()
            else set()
        )
        # The coverage CSV is the row-level ledger of a publish, so every player named by the other
        # artifacts of the same publish has to appear in it.
        summary_missing = sorted(summary_players - coverage_players)
        html_missing = sorted(html_players - coverage_players)
        checks.append(
            {
                "eval_id": eval_id,
                "summary_path": _report_path(summary_path),
                "coverage_path": _report_path(coverage_path) if coverage_path.exists() else None,
                "html_path": _report_path(html_path) if html_path.exists() else None,
                "summary_player_count": len(summary_players),
                "coverage_player_count": len(coverage_players),
                "html_player_count": len(html_players),
                "summary_players_missing_from_coverage": summary_missing,
                "html_players_missing_from_coverage": html_missing,
                "matches": not summary_missing and not html_missing,
            }
        )
    return checks


def _published_summary_sha256_checks(results_dir: Path) -> list[dict[str, object]]:
    cross_eval_path = results_dir / "cross_ref_summary.json"
    if not cross_eval_path.exists():
        return [
            {
                "eval_id": None,
                "summary_path": _report_path(cross_eval_path),
                "recorded_sha256": None,
                "actual_sha256": None,
                "matches": False,
                "note": "aggregate cross_ref_summary.json is missing, so no recorded sha256 exists to check",
            }
        ]
    cross_eval_summary = json.loads(cross_eval_path.read_text(encoding="utf-8"))
    recorded = {
        entry.get("eval_id"): entry.get("summary_sha256")
        for entry in cross_eval_summary.get("generated_from", {}).get("summaries", [])
        if isinstance(entry, dict)
    }
    checks = []
    for summary_path in _published_summary_paths(results_dir):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        eval_id = summary.get("eval_id") if isinstance(summary, dict) else None
        actual_sha256 = hashlib.sha256(summary_path.read_bytes()).hexdigest()
        recorded_sha256 = recorded.get(eval_id)
        checks.append(
            {
                "eval_id": eval_id,
                "summary_path": _report_path(summary_path),
                "recorded_sha256": recorded_sha256,
                "actual_sha256": actual_sha256,
                "matches": recorded_sha256 == actual_sha256,
            }
        )
    return checks


def _check_block(check_id: str, description: str, rows: list[dict[str, object]]) -> dict[str, object]:
    failures = [row for row in rows if not row["matches"]]
    return {
        "check_id": check_id,
        "description": description,
        "passed": not failures,
        "checked_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "rows": rows,
    }


def run_verify(args: argparse.Namespace) -> dict[str, object]:
    publish = bool(getattr(args, "publish", False))
    results_dir = args.results_dir or RESULTS_DIR
    mapping_dir = args.mapping_dir or MAPPINGS_DIR
    allow_metadata_only = bool(getattr(args, "allow_metadata_only", False))

    inventory = _llm_chess_inventory()
    resolution = _player_resolution_by_eval(mapping_dir, inventory)
    actual_rows = _actual_llm_chess_input_rows()
    input_row_checks = _recorded_input_row_checks(results_dir, actual_rows)
    _ensure_player_resolution_publishable(resolution, publish, allow_metadata_only=allow_metadata_only)
    _ensure_recorded_input_rows_publishable(input_row_checks, publish)

    summary_output = args.summary_output or (
        RESULTS_DIR / "verify_summary.json"
        if publish
        else _scratch_output_dir("verify") / "verify_summary.json"
    )
    _ensure_publish_allowed([summary_output], publish)

    dangling = _resolution_rows(resolution, "dangling")
    metadata_only = _resolution_rows(resolution, "metadata_only")
    resolution_rows = [
        {
            "eval_id": eval_id,
            "mapping_file": _report_path(mapping_dir / f"{eval_id}.csv"),
            "dangling_row_count": len(entry["dangling"]),
            "metadata_only_row_count": len(entry["metadata_only"]),
            "dangling": entry["dangling"],
            "metadata_only": entry["metadata_only"],
            "matches": not _unresolved_player_rows(
                {eval_id: entry}, allow_metadata_only=allow_metadata_only
            ),
        }
        for eval_id, entry in resolution.items()
    ]

    checks = [
        _check_block(
            "published_summary_sha256",
            "each results/*_summary.json hashes to the sha256 recorded for it in cross_ref_summary.json",
            _published_summary_sha256_checks(results_dir),
        ),
        _check_block(
            "recorded_llm_chess_input_rows",
            "each published summary's llm_chess_inputs row counts match the current authoritative inputs",
            input_row_checks,
        ),
        _check_block(
            "artifact_player_agreement",
            "llm_chess_player values agree across the summary_json, coverage_csv and html of one publish",
            _artifact_player_agreement_checks(results_dir),
        ),
        _check_block(
            "mapping_player_resolution",
            "every accepted mapping row resolves to a known llm_chess_player"
            if allow_metadata_only
            else "every accepted mapping row resolves to a llm_chess_player with a row in data/elo_refined.csv",
            resolution_rows,
        ),
    ]
    failed_check_ids = [check["check_id"] for check in checks if not check["passed"]]

    verify_summary = {
        "artifact_kind": "cross_ref_verify",
        "overall_status": "fail" if failed_check_ids else "pass",
        "allow_metadata_only": allow_metadata_only,
        "results_dir": _report_path(results_dir),
        "mapping_dir": _report_path(mapping_dir),
        "llm_chess_input_rows": actual_rows,
        "failed_check_ids": failed_check_ids,
        "checks": {check["check_id"]: check for check in checks},
        "metadata_only_players": {
            "row_count": len(metadata_only),
            "player_count": len({str(row["llm_chess_player"]) for row in metadata_only}),
            "players": sorted({str(row["llm_chess_player"]) for row in metadata_only}),
            "note": "known to data/models_metadata.csv but absent from data/elo_refined.csv, so these "
            "rows contribute to no statistic; counted as failures unless --allow-metadata-only is set",
        },
        "dangling_players": {
            "row_count": len(dangling),
            "players": sorted({str(row["llm_chess_player"]) for row in dangling}),
            "note": "absent from both data/elo_refined.csv and data/models_metadata.csv; always a failure",
        },
    }
    _write_json(summary_output, verify_summary)
    return {
        "output_mode": _output_mode(publish),
        "summary_output": _report_path(summary_output),
        "overall_status": verify_summary["overall_status"],
        "failed_check_ids": failed_check_ids,
        "check_status": {check["check_id"]: "pass" if check["passed"] else "fail" for check in checks},
        "failure_counts": {check["check_id"]: check["failure_count"] for check in checks},
        "dangling_player_row_count": len(dangling),
        "metadata_only_player_row_count": len(metadata_only),
        "unresolved_player_row_count": len(
            _unresolved_player_rows(resolution, allow_metadata_only=allow_metadata_only)
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run generalized cross-reference analyses.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Refresh the LLM Chess model inventory.")
    inventory_parser.add_argument("--publish", action="store_true", help="Write the checked-in inventory artifact.")
    inventory_parser.add_argument("--inventory-output", type=Path)

    mapping_review_parser = subparsers.add_parser(
        "mapping-review",
        help="Generate a cross-eval mapping review surface from the run-time mapping CSVs.",
    )
    mapping_review_parser.add_argument("--mapping-dir", type=Path)
    mapping_review_parser.add_argument("--publish", action="store_true", help="Write checked-in mapping review artifacts.")
    mapping_review_parser.add_argument("--eval-id", dest="filter_eval_id")
    mapping_review_parser.add_argument("--player", dest="filter_player")
    mapping_review_parser.add_argument("--status", dest="filter_status", action="append")
    mapping_review_parser.add_argument("--provider", dest="filter_provider")
    mapping_review_parser.add_argument("--csv-output", type=Path)
    mapping_review_parser.add_argument("--html-output", type=Path)

    cross_eval_parser = subparsers.add_parser(
        "cross-eval",
        help="Generate cross-eval summary/report artifacts from published per-eval summaries.",
    )
    cross_eval_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    cross_eval_parser.add_argument("--publish", action="store_true", help="Write checked-in aggregate artifacts.")
    cross_eval_parser.add_argument("--allow-metadata-only", action="store_true", help=ALLOW_METADATA_ONLY_HELP)
    cross_eval_parser.add_argument("--summary-output", type=Path)
    cross_eval_parser.add_argument("--report-output", type=Path)

    audit_parser = subparsers.add_parser(
        "audit",
        help="Run one non-mutating trust audit across llm_chess and every registered external eval.",
    )
    audit_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    audit_parser.add_argument("--mapping-dir", type=Path, default=MAPPINGS_DIR)
    audit_parser.add_argument("--publish", action="store_true", help="Write checked-in audit artifacts.")
    audit_parser.add_argument("--allow-metadata-only", action="store_true", help=ALLOW_METADATA_ONLY_HELP)
    audit_parser.add_argument("--summary-output", type=Path)
    audit_parser.add_argument("--report-output", type=Path)
    audit_parser.add_argument("--max-unresolved-rows", type=int, default=0)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Check the internal consistency the published artifacts already record. Exits non-zero on failure.",
    )
    verify_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    verify_parser.add_argument("--mapping-dir", type=Path, default=MAPPINGS_DIR)
    verify_parser.add_argument("--publish", action="store_true", help="Write the checked-in verify artifact.")
    verify_parser.add_argument("--summary-output", type=Path)
    verify_parser.add_argument(
        "--allow-metadata-only",
        action="store_true",
        help="Relax mapping_player_resolution to accept rows whose llm_chess_player is known to "
        "data/models_metadata.csv but has no row in data/elo_refined.csv. Off by default: absence "
        "from elo_refined.csv is a failure because such a row contributes to no statistic.",
    )

    rerun_diff_parser = subparsers.add_parser(
        "rerun-diff",
        help="Rerun an eval into scratch artifacts and compare the candidate against baseline published outputs.",
    )
    rerun_diff_parser.add_argument("target", choices=sorted(ADAPTERS))
    rerun_diff_parser.add_argument("--baseline-results-dir", type=Path, default=RESULTS_DIR)
    rerun_diff_parser.add_argument("--scratch-dir", type=Path)
    rerun_diff_parser.add_argument("--mapping-path", type=Path)
    rerun_diff_parser.add_argument("--source-path", type=Path)
    rerun_diff_parser.add_argument("--diff-json-output", type=Path)
    rerun_diff_parser.add_argument("--diff-md-output", type=Path)

    for eval_id in ADAPTERS:
        eval_parser = subparsers.add_parser(eval_id, help=f"Run the {eval_id} cross-reference analysis.")
        eval_parser.add_argument("--publish", action="store_true", help="Write checked-in per-eval artifacts.")
        eval_parser.add_argument("--allow-metadata-only", action="store_true", help=ALLOW_METADATA_ONLY_HELP)
        eval_parser.add_argument("--inventory-output", type=Path)
        eval_parser.add_argument("--mapping-path", type=Path)
        eval_parser.add_argument("--source-path", type=Path)
        eval_parser.add_argument(
            "--mistake-stats",
            choices=["excluded", "clean_only"],
            default="excluded",
            help="'clean_only' restricts to models with min_game_date >= the cutoff and re-enables "
            "the repaired wrong-action/wrong-move/mistake metrics (research-only; cannot be published).",
        )
        eval_parser.add_argument("--summary-output", type=Path)
        eval_parser.add_argument("--html-output", type=Path)
        eval_parser.add_argument("--normalized-output", type=Path)
        eval_parser.add_argument("--coverage-output", type=Path)
        eval_parser.add_argument("--verification-command", action="append")
        eval_parser.add_argument("--verification-output", action="append")
        eval_parser.add_argument("--verification-output-file", action="append", type=Path)
        eval_parser.add_argument("--test-status", default="not-run")
        eval_parser.add_argument("--mapping-qa-status", default="reviewed_with_unresolved_debt")
        eval_parser.add_argument("--run-qa-status", default="publish_reproducible")
        eval_parser.add_argument("--known-limitation", action="append")
        eval_parser.set_defaults(eval_id=eval_id)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inventory":
        path, payload = refresh_inventory(args.inventory_output, publish=args.publish)
        print(json.dumps({"output_mode": _output_mode(args.publish), "inventory_path": _report_path(path), **payload}, indent=2))
        return
    if args.command == "mapping-review":
        print(json.dumps(run_mapping_review(args), indent=2))
        return
    if args.command == "cross-eval":
        print(json.dumps(run_cross_eval(args), indent=2))
        return
    if args.command == "audit":
        print(json.dumps(run_audit(args), indent=2))
        return
    if args.command == "verify":
        payload = run_verify(args)
        print(json.dumps(payload, indent=2))
        if payload["overall_status"] != "pass":
            raise SystemExit(1)
        return
    if args.command == "rerun-diff":
        print(json.dumps(run_rerun_diff(args), indent=2))
        return
    print(json.dumps(run_eval(args), indent=2))


if __name__ == "__main__":
    main()