from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from adapters import arc_agi_2, bullshit_bench, delegate_52, eci
from framework.cross_eval import build_cross_eval_summary, render_cross_eval_report_markdown
from framework.diffing import build_eval_diff_report, render_artifact_diff_markdown
from framework.loading import load_llm_chess_inputs
from framework.mapping import load_mapping_file
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
}


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
    inventory = build_llm_chess_inventory(*load_llm_chess_inputs(REPO_ROOT)[:2])
    mapping_path = args.mapping_path or MAPPINGS_DIR / f"{args.eval_id}.csv"
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
            "| eval | rerun_diff | metric_rows | elo_rows | raw_elo_r | prediction_r2 | unresolved_high_impact |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for entry in summary["reproducibility"]["per_eval"]:
        lines.append(
            "| {eval_id} | {status} | {metric_rows} | {elo_rows} | {raw_elo_r} | {prediction_r2} | {unresolved_high_impact} |".format(
                eval_id=entry["eval_id"],
                status="clean" if not entry["has_diff"] else "diff",
                metric_rows=entry["metric_rows"],
                elo_rows=entry["elo_rows"],
                raw_elo_r=entry["raw_elo_pearson_r"],
                prediction_r2=entry["prediction_r2"],
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
                    mapping_path=None,
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
    cross_eval_parser.add_argument("--summary-output", type=Path)
    cross_eval_parser.add_argument("--report-output", type=Path)

    audit_parser = subparsers.add_parser(
        "audit",
        help="Run one non-mutating trust audit across llm_chess and every registered external eval.",
    )
    audit_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    audit_parser.add_argument("--mapping-dir", type=Path, default=MAPPINGS_DIR)
    audit_parser.add_argument("--publish", action="store_true", help="Write checked-in audit artifacts.")
    audit_parser.add_argument("--summary-output", type=Path)
    audit_parser.add_argument("--report-output", type=Path)
    audit_parser.add_argument("--max-unresolved-rows", type=int, default=0)

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
    if args.command == "rerun-diff":
        print(json.dumps(run_rerun_diff(args), indent=2))
        return
    print(json.dumps(run_eval(args), indent=2))


if __name__ == "__main__":
    main()