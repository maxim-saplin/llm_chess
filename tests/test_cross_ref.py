import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CROSS_REF_ROOT = REPO_ROOT / "data/cross-ref"
if str(CROSS_REF_ROOT) not in sys.path:
    sys.path.insert(0, str(CROSS_REF_ROOT))

from adapters import arc_agi_2, eci  # noqa: E402
from framework.data_quality import filter_multifactor_candidate_metrics  # noqa: E402
from framework.diffing import compare_csv_files  # noqa: E402
from framework.loading import load_llm_chess_inputs  # noqa: E402
from framework.mapping import apply_mapping, load_mapping_file  # noqa: E402
from framework.mapping_review import build_mapping_review  # noqa: E402
from framework.model_identity import build_llm_chess_inventory, inventory_summary  # noqa: E402
from framework.normalization import parse_currency, parse_day_month_year, parse_percent  # noqa: E402
import framework.statistics as statistics  # noqa: E402
from framework.statistics import build_metric_relationships, build_prediction_summary  # noqa: E402
import run_cross_ref  # noqa: E402


def _artifact_diffs_by_id(diff_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {entry["artifact_id"]: entry for entry in diff_payload["artifact_diffs"]}


def _write_current_eval_baseline(results_dir: Path, *eval_ids: str) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    parser = run_cross_ref.build_parser()
    for eval_id in eval_ids:
        args = parser.parse_args(
            [
                eval_id,
                "--inventory-output",
                str(results_dir / f"{eval_id}_inventory.csv"),
                "--summary-output",
                str(results_dir / f"{eval_id}_summary.json"),
                "--html-output",
                str(results_dir / f"{eval_id}.html"),
                "--coverage-output",
                str(results_dir / f"{eval_id}_coverage.csv"),
            ]
        )
        run_cross_ref.run_eval(args)
    return results_dir


def _run_rerun_diff(
    tmp_path: Path,
    target: str,
    *extra_args: str,
    baseline_results_dir: Path | None = None,
) -> tuple[dict[str, object], dict[str, object], str]:
    baseline_results_dir = baseline_results_dir or _write_current_eval_baseline(tmp_path / "baseline_results", target)
    scratch_dir = tmp_path / f"{target}_scratch"
    diff_json_output = tmp_path / f"{target}_diff.json"
    diff_md_output = tmp_path / f"{target}_diff.md"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "rerun-diff",
            target,
            "--baseline-results-dir",
            str(baseline_results_dir),
            "--scratch-dir",
            str(scratch_dir),
            "--diff-json-output",
            str(diff_json_output),
            "--diff-md-output",
            str(diff_md_output),
            *extra_args,
        ]
    )

    payload = run_cross_ref.run_rerun_diff(args)
    diff_payload = json.loads(diff_json_output.read_text(encoding="utf-8"))
    diff_markdown = diff_md_output.read_text(encoding="utf-8")
    return payload, diff_payload, diff_markdown


def _snapshot_files(paths: list[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def _assert_snapshot_unchanged(snapshot: dict[Path, bytes | None]) -> None:
    for path, expected in snapshot.items():
        if expected is None:
            assert not path.exists()
        else:
            assert path.read_bytes() == expected


def _assert_outside_cross_ref(path_value: str) -> None:
    path = Path(path_value).resolve()
    try:
        path.relative_to(CROSS_REF_ROOT.resolve())
    except ValueError:
        return
    raise AssertionError(f"review output unexpectedly landed under data/cross-ref: {path}")


def test_normalization_helpers_parse_arc_formats():
    assert parse_percent("84.6%") == 84.6
    assert parse_percent("N/A") is None
    assert parse_currency("$10.51") == 10.51
    assert parse_currency("—") is None
    assert parse_day_month_year("23.04.2026") == "2026-04-23"


def test_runner_allows_external_inventory_output_path(tmp_path):
    inventory_path = tmp_path / "llm_chess_models.csv"

    path, payload = run_cross_ref.refresh_inventory(inventory_path)

    assert path == inventory_path
    assert payload["inventory_path"] == str(inventory_path)
    assert inventory_path.exists()


def test_runner_embeds_verification_output_and_known_limitations(tmp_path):
    summary_output = tmp_path / "arc_summary.json"
    html_output = tmp_path / "arc.html"
    normalized_output = tmp_path / "arc_normalized.csv"
    coverage_output = tmp_path / "arc_coverage.csv"
    inventory_output = tmp_path / "llm_chess_models.csv"
    verification_output_file = tmp_path / "pytest_output.txt"
    verification_output_file.write_text("bringing up nodes...\n...... [100%]\n6 passed in 16.23s\n")

    args = run_cross_ref.argparse.Namespace(
        command="arc_agi_2",
        eval_id="arc_agi_2",
        inventory_output=inventory_output,
        mapping_path=None,
        summary_output=summary_output,
        html_output=html_output,
        normalized_output=normalized_output,
        coverage_output=coverage_output,
        verification_command=[".venv/bin/python -m pytest tests/test_cross_ref.py"],
        verification_output=None,
        verification_output_file=[verification_output_file],
        test_status="passed",
        mapping_qa_status="qa-resubmitted",
        run_qa_status="qa-resubmitted",
        known_limitation=None,
    )

    run_cross_ref.run_eval(args)

    summary = json.loads(summary_output.read_text())
    assert summary["verification"]["verification_checks"] == [
        {
            "command": ".venv/bin/python -m pytest tests/test_cross_ref.py",
            "output": "bringing up nodes...\n...... [100%]\n6 passed in 16.23s",
        }
    ]
    assert summary["verification"]["known_limitations"] == summary["limitations"]
    assert summary["verification"]["artifact_paths"]["summary_json"] == str(summary_output)
    assert summary["verification"]["artifact_paths"]["normalized_csv"] == str(normalized_output)


def test_runner_skips_published_normalized_csv_without_explicit_output_path(tmp_path):
    summary_output = tmp_path / "eci_summary.json"
    html_output = tmp_path / "eci.html"
    coverage_output = tmp_path / "eci_coverage.csv"
    inventory_output = tmp_path / "llm_chess_models.csv"
    verification_output_file = tmp_path / "pytest_output.txt"
    verification_output_file.write_text("bringing up nodes...\n...... [100%]\n6 passed in 16.23s\n")

    args = run_cross_ref.argparse.Namespace(
        command="eci",
        eval_id="eci",
        inventory_output=inventory_output,
        mapping_path=None,
        summary_output=summary_output,
        html_output=html_output,
        normalized_output=None,
        coverage_output=coverage_output,
        verification_command=[".venv/bin/python -m pytest tests/test_cross_ref.py"],
        verification_output=None,
        verification_output_file=[verification_output_file],
        test_status="passed",
        mapping_qa_status="qa-resubmitted",
        run_qa_status="qa-resubmitted",
        known_limitation=None,
    )

    run_cross_ref.run_eval(args)

    summary = json.loads(summary_output.read_text())
    assert "normalized_csv" not in summary["verification"]["artifact_paths"]
    assert not (tmp_path / "eci_normalized.csv").exists()


def test_mapping_csv_headers_keep_source_and_destination_columns_front_loaded():
    expected_prefix = [
        "eval_id",
        "eval_row_id",
        "eval_model_label",
        "llm_chess_player",
        "eval_variant_label",
        "mapping_status",
        "review_status",
    ]

    for mapping_path in [
        CROSS_REF_ROOT / "mappings" / "eci.csv",
        CROSS_REF_ROOT / "mappings" / "arc_agi_2.csv",
    ]:
        header = mapping_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert header[: len(expected_prefix)] == expected_prefix


def test_mapping_review_builds_cross_eval_rows_and_supports_filters():
    review_rows, payload = build_mapping_review(CROSS_REF_ROOT / "mappings")

    assert set(review_rows["eval_id"].unique()) == {"eci", "arc_agi_2"}
    assert payload["summary"]["eval_count"] == 2
    assert payload["summary"]["row_count"] == len(review_rows)
    assert payload["summary"]["unresolved_row_count"] > 0
    assert {"provider_group_source", "provider_group_confidence"} <= set(review_rows.columns)

    gemini_rows, gemini_payload = build_mapping_review(
        CROSS_REF_ROOT / "mappings",
        player="gemini-3.1-pro-preview",
    )

    assert set(gemini_rows["eval_id"].unique()) == {"eci", "arc_agi_2"}
    assert gemini_payload["summary"]["unique_llm_chess_players"] == 1
    assert gemini_payload["player_matrix_rows"][0]["llm_chess_player"] == "gemini-3.1-pro-preview"

    unmatched_rows, unmatched_payload = build_mapping_review(
        CROSS_REF_ROOT / "mappings",
        statuses=["unmatched"],
    )

    assert not unmatched_rows.empty
    assert set(unmatched_rows["mapping_status"].unique()) == {"unmatched"}
    assert unmatched_payload["summary"]["unresolved_row_count"] == len(unmatched_rows)

    anthropic_rows, anthropic_payload = build_mapping_review(
        CROSS_REF_ROOT / "mappings",
        provider="Anthropic",
    )

    assert not anthropic_rows.empty
    assert set(anthropic_rows["eval_id"].unique()) == {"eci", "arc_agi_2"}
    assert set(anthropic_rows["provider_group"].unique()) == {"Anthropic"}
    assert set(anthropic_payload["provider_counts"].keys()) == {"Anthropic"}


def test_mapping_review_uses_canonical_provider_contract_for_bad_cases():
    review_rows, _ = build_mapping_review(CROSS_REF_ROOT / "mappings")

    magistral_rows = review_rows.loc[review_rows["llm_chess_player"] == "magistral-small"]
    assert not magistral_rows.empty
    assert set(magistral_rows["provider_group"].unique()) == {"Mistral"}
    assert set(magistral_rows["provider_group_source"].unique()) == {"llm_chess_inventory"}
    assert set(magistral_rows["provider_group_confidence"].unique()) == {"high"}

    cerebras_rows = review_rows.loc[review_rows["eval_model_label"] == "Cerebras-GPT-13B"]
    assert not cerebras_rows.empty
    assert set(cerebras_rows["provider_group"].unique()) == {"Cerebras"}
    assert set(cerebras_rows["provider_group_source"].unique()) == {"mapping_provider_or_family"}
    assert set(cerebras_rows["provider_group_confidence"].unique()) == {"medium"}

    openai_rows, _ = build_mapping_review(CROSS_REF_ROOT / "mappings", provider="OpenAI")
    assert "Cerebras-GPT-13B" not in set(openai_rows["eval_model_label"])

    weak_evidence_rows = review_rows.loc[review_rows["eval_model_label"] == "Baichuan1-7B"]
    assert not weak_evidence_rows.empty
    assert set(weak_evidence_rows["provider_group"].unique()) == {"Baichuan1"}
    assert set(weak_evidence_rows["provider_group_source"].unique()) == {"mapping_provider_or_family"}
    assert set(weak_evidence_rows["provider_group_confidence"].unique()) == {"low"}


def test_mapping_review_writes_csv_and_html(tmp_path):
    csv_output = tmp_path / "mapping_review.csv"
    html_output = tmp_path / "mapping_review.html"
    args = run_cross_ref.argparse.Namespace(
        command="mapping-review",
        mapping_dir=CROSS_REF_ROOT / "mappings",
        filter_eval_id=None,
        filter_player="gemini-3.1-pro-preview",
        filter_status=None,
        filter_provider=None,
        csv_output=csv_output,
        html_output=html_output,
    )

    payload = run_cross_ref.run_mapping_review(args)

    csv_rows = pd.read_csv(csv_output)
    html = html_output.read_text(encoding="utf-8")

    assert payload["summary"]["row_count"] == len(csv_rows)
    assert list(csv_rows.columns[:5]) == [
        "eval_id",
        "mapping_file",
        "eval_row_id",
        "eval_model_label",
        "llm_chess_player",
    ]
    assert {"provider_group", "provider_group_source", "provider_group_confidence"} <= set(csv_rows.columns)
    assert set(csv_rows["eval_id"].unique()) == {"eci", "arc_agi_2"}
    assert "gemini-3.1-pro-preview" in set(csv_rows["llm_chess_player"])
    assert "Mapping Review" in html
    assert "gemini-3.1-pro-preview" in html


def test_mapping_review_defaults_to_scratch_outputs_without_mutating_published_review():
    published_paths = [
        CROSS_REF_ROOT / "results" / "mapping_review.csv",
        CROSS_REF_ROOT / "results" / "mapping_review.html",
    ]
    before = _snapshot_files(published_paths)
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["mapping-review"])

    payload = run_cross_ref.run_mapping_review(args)

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["csv_output"])
    _assert_outside_cross_ref(payload["html_output"])
    _assert_snapshot_unchanged(before)


def test_checked_in_generated_outputs_require_publish_flag():
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "mapping-review",
            "--csv-output",
            str(CROSS_REF_ROOT / "results" / "mapping_review.csv"),
            "--html-output",
            str(CROSS_REF_ROOT / "results" / "mapping_review.html"),
        ]
    )

    with pytest.raises(ValueError, match="require --publish"):
        run_cross_ref.run_mapping_review(args)


def test_cross_eval_command_generates_summary_and_report_from_published_summaries(tmp_path):
    results_dir = tmp_path / "results"
    _write_current_eval_baseline(results_dir, "eci", "arc_agi_2")

    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "cross-eval",
            "--results-dir",
            str(results_dir),
            "--publish",
        ]
    )

    payload = run_cross_ref.run_cross_eval(args)

    summary_output = results_dir / "cross_ref_summary.json"
    report_output = results_dir / "cross_ref_report.md"
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    report = report_output.read_text(encoding="utf-8")

    assert payload["output_mode"] == "publish"
    assert payload["summary_output"] == str(summary_output)
    assert payload["report_output"] == str(report_output)
    assert summary["generated_from"]["mode"] == "published_per_eval_summaries"
    assert summary["generated_from"]["reran_evals"] is False
    assert summary["generated_from"]["summary_count"] == 2
    assert summary["report_contract"]["primary_human_report"] == "data/cross-ref/CONSOLIDATED_REPORT.md"
    assert summary["report_contract"]["generated_support_report"] == str(report_output)
    assert summary["report_contract"]["consolidated_report_role"] == "durable_human_report"
    assert summary["report_contract"]["generated_report_role"] == "runner_owned_supporting_artifact"
    assert set(payload["eval_ids"]) == {"eci", "arc_agi_2"}
    assert {entry["eval_id"] for entry in summary["generated_from"]["summaries"]} == {"eci", "arc_agi_2"}
    arc_eval = next(entry for entry in summary["evals"] if entry["eval_id"] == "arc_agi_2")
    assert arc_eval["coverage"]["rows_joined_to_llm_chess_elo"] == 55
    assert arc_eval["prediction"]["feature_selection"]["method"] == "within_cv_training_folds"
    assert summary["comparisons"]["strongest_raw_elo"]["eval_id"] == "eci"
    assert summary["comparisons"]["best_prediction"]["eval_id"] == "eci"
    assert "## Method" in report
    assert "## Signal" in report
    assert "Primary human report: `data/cross-ref/CONSOLIDATED_REPORT.md`" in report
    assert "Features are selected inside each training fold" in report
    assert "eci_summary.json" in report
    assert "arc_agi_2_summary.json" in report
    assert "run_cross_ref.py cross-eval --publish" in report


def test_cross_eval_defaults_to_scratch_outputs_without_mutating_published_aggregate():
    published_paths = [
        CROSS_REF_ROOT / "results" / "cross_ref_summary.json",
        CROSS_REF_ROOT / "results" / "cross_ref_report.md",
    ]
    before = _snapshot_files(published_paths)
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["cross-eval"])

    payload = run_cross_ref.run_cross_eval(args)

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["summary_output"])
    _assert_outside_cross_ref(payload["report_output"])
    _assert_snapshot_unchanged(before)


def test_audit_command_generates_single_status_surface(tmp_path):
    results_dir = _write_current_eval_baseline(tmp_path / "results", "eci", "arc_agi_2")
    summary_output = tmp_path / "audit_summary.json"
    report_output = tmp_path / "audit_report.md"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "audit",
            "--results-dir",
            str(results_dir),
            "--summary-output",
            str(summary_output),
            "--report-output",
            str(report_output),
        ]
    )

    payload = run_cross_ref.run_audit(args)
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    report = report_output.read_text(encoding="utf-8")

    assert payload["summary_output"] == str(summary_output)
    assert payload["report_output"] == str(report_output)
    assert summary["artifact_kind"] == "cross_ref_audit"
    assert summary["benchmarks"]["count"] == 3
    assert summary["benchmarks"]["ids"] == ["llm_chess", "arc_agi_2", "eci"]
    assert summary["reproducibility_status"] == "pass"
    assert summary["reproducibility"]["rerun_diff_all_clean"] is True
    assert all(entry["has_diff"] is False for entry in summary["reproducibility"]["per_eval"])
    assert summary["coverage_status"] == "review-needed"
    assert summary["mapping_review"]["unresolved_row_count"] > 0
    assert "overall_status: review-needed" in report
    assert "benchmarks: llm_chess, arc_agi_2, eci" in report
    assert "This file is generated by `run_cross_ref.py audit`." in report


def test_audit_defaults_to_scratch_outputs_without_mutating_published_audit():
    published_paths = [
        CROSS_REF_ROOT / "results" / "audit_summary.json",
        CROSS_REF_ROOT / "results" / "audit_report.md",
    ]
    before = _snapshot_files(published_paths)
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["audit"])

    payload = run_cross_ref.run_audit(args)

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["summary_output"])
    _assert_outside_cross_ref(payload["report_output"])
    _assert_snapshot_unchanged(before)


def test_audit_threshold_can_promote_clean_reproducible_state(tmp_path):
    results_dir = _write_current_eval_baseline(tmp_path / "results", "eci", "arc_agi_2")
    summary_output = tmp_path / "audit_summary.json"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "audit",
            "--results-dir",
            str(results_dir),
            "--summary-output",
            str(summary_output),
            "--max-unresolved-rows",
            "500",
        ]
    )

    payload = run_cross_ref.run_audit(args)
    summary = json.loads(summary_output.read_text(encoding="utf-8"))

    assert payload["summary_output"] == str(summary_output)
    assert payload["report_output"] == str(tmp_path / "audit_report.md")
    assert (tmp_path / "audit_report.md").exists()
    assert summary["overall_status"] == "pass"
    assert summary["coverage_status"] == "pass"
    assert summary["reproducibility_status"] == "pass"


def test_rerun_diff_reports_no_diff_for_published_eci_artifacts(tmp_path):
    payload, diff_payload, diff_markdown = _run_rerun_diff(tmp_path, "eci")
    artifact_diffs = _artifact_diffs_by_id(diff_payload)

    assert payload["has_diff"] is False
    assert diff_payload["has_diff"] is False
    assert payload["candidate_artifacts"]["summary_json"].startswith(str(tmp_path / "eci_scratch"))
    assert artifact_diffs["summary_json"]["changed"] is False
    assert artifact_diffs["coverage_csv"]["changed"] is False
    assert "No differences detected between baseline and rerun candidate artifacts." in diff_markdown


def test_eval_defaults_to_scratch_outputs_without_mutating_published_artifacts():
    published_paths = [
        CROSS_REF_ROOT / "model-identity" / "llm_chess_models.csv",
        CROSS_REF_ROOT / "results" / "eci_summary.json",
        CROSS_REF_ROOT / "results" / "eci.html",
        CROSS_REF_ROOT / "results" / "eci_coverage.csv",
    ]
    before = _snapshot_files(published_paths)
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["eci"])

    payload = run_cross_ref.run_eval(args)

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["inventory_output"])
    _assert_outside_cross_ref(payload["summary_output"])
    _assert_outside_cross_ref(payload["html_output"])
    _assert_outside_cross_ref(payload["coverage_output"])
    _assert_snapshot_unchanged(before)


def test_rerun_diff_defaults_diff_outputs_to_scratch_space(tmp_path):
    baseline_results_dir = _write_current_eval_baseline(tmp_path / "baseline_results", "eci")
    scratch_dir = tmp_path / "eci_scratch"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "rerun-diff",
            "eci",
            "--baseline-results-dir",
            str(baseline_results_dir),
            "--scratch-dir",
            str(scratch_dir),
        ]
    )

    payload = run_cross_ref.run_rerun_diff(args)

    assert payload["has_diff"] is False
    assert payload["diff_json_output"] == str(scratch_dir / "eci_diff.json")
    assert payload["diff_md_output"] == str(scratch_dir / "eci_diff.md")
    assert (scratch_dir / "eci_diff.json").exists()
    assert (scratch_dir / "eci_diff.md").exists()


def test_rerun_diff_detects_changed_source_override(tmp_path):
    source_path = tmp_path / "epoch_eci_changed.csv"
    source_df = pd.read_csv(CROSS_REF_ROOT / "evals" / "eci" / "epoch_eci_apr_2026.csv")
    changed_index = int(source_df[source_df["llm_chess_model"].notna()].index[0])
    source_df.loc[changed_index, "Score"] = float(source_df.loc[changed_index, "Score"]) + 1.0
    source_df.to_csv(source_path, index=False)

    _, diff_payload, diff_markdown = _run_rerun_diff(
        tmp_path,
        "eci",
        "--source-path",
        str(source_path),
    )
    artifact_diffs = _artifact_diffs_by_id(diff_payload)

    assert diff_payload["has_diff"] is True
    assert artifact_diffs["summary_json"]["changed"] is True
    assert artifact_diffs["coverage_csv"]["changed"] is True
    assert artifact_diffs["coverage_csv"]["changed_row_count"] >= 1
    assert any(row["key"] == f"eci:{changed_index:04d}" for row in artifact_diffs["coverage_csv"]["changed_rows"])
    assert "Changed paths:" in diff_markdown


def test_rerun_diff_detects_changed_mapping_override(tmp_path):
    mapping_path = tmp_path / "eci_mapping_changed.csv"
    mapping_df = pd.read_csv(CROSS_REF_ROOT / "mappings" / "eci.csv")
    changed_index = int(mapping_df[mapping_df["mapping_status"] == "accepted"].index[0])
    changed_row_id = str(mapping_df.loc[changed_index, "eval_row_id"])
    mapping_df.loc[changed_index, "mapping_status"] = "unmatched"
    mapping_df.loc[changed_index, "llm_chess_player"] = pd.NA
    mapping_df.to_csv(mapping_path, index=False)

    _, diff_payload, _ = _run_rerun_diff(
        tmp_path,
        "eci",
        "--mapping-path",
        str(mapping_path),
    )
    artifact_diffs = _artifact_diffs_by_id(diff_payload)
    summary_changes = artifact_diffs["summary_json"]["changes"]

    assert diff_payload["has_diff"] is True
    assert artifact_diffs["summary_json"]["changed"] is True
    assert artifact_diffs["coverage_csv"]["changed"] is True
    assert any(change["path"] == "$.coverage.accepted_mapping_rows" for change in summary_changes)
    assert any(row["key"] == changed_row_id for row in artifact_diffs["coverage_csv"]["changed_rows"])


def test_compare_csv_files_reports_duplicate_key_validation_error(tmp_path):
    baseline_path = tmp_path / "baseline.csv"
    candidate_path = tmp_path / "candidate.csv"
    baseline_df = pd.DataFrame(
        [
            {"eval_row_id": "eci:0001", "score_numeric": 157.0},
            {"eval_row_id": "eci:0001", "score_numeric": 158.0},
        ]
    )
    candidate_df = pd.DataFrame(
        [
            {"eval_row_id": "eci:0001", "score_numeric": 157.0},
            {"eval_row_id": "eci:0002", "score_numeric": 156.0},
        ]
    )
    baseline_df.to_csv(baseline_path, index=False)
    candidate_df.to_csv(candidate_path, index=False)

    diff = compare_csv_files(
        baseline_path,
        candidate_path,
        artifact_id="coverage_csv",
        key_column="eval_row_id",
    )

    assert diff["changed"] is True
    assert diff["changed_row_count"] == 0
    assert diff["validation_error"]["code"] == "duplicate_key"
    assert diff["validation_error"]["key_column"] == "eval_row_id"
    assert diff["validation_error"]["baseline_duplicates"] == [{"key": "eci:0001", "count": 2}]
    assert diff["validation_error"]["candidate_duplicates"] == []


def test_consolidated_report_contains_cross_eval_findings():
    consolidated_report = (CROSS_REF_ROOT / "CONSOLIDATED_REPORT.md").read_text(encoding="utf-8")

    assert "## Bottom Line" in consolidated_report
    assert "## Signal Table" in consolidated_report
    assert "## Method In One Screen" in consolidated_report
    assert "## Coverage Debt" in consolidated_report
    assert "## What Raises Signal" in consolidated_report
    assert "results/cross_ref_report.md" in consolidated_report
    assert "results/cross_ref_summary.json" in consolidated_report
    assert "ECI: usable relationship" in consolidated_report
    assert "ARC-AGI-2: weak relationship" in consolidated_report
    assert "Feature selection happens inside each training fold" in consolidated_report
    assert "pointer_only" not in consolidated_report


def test_inventory_reconciles_current_repo_inputs():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    summary = inventory_summary(inventory)

    elo_players = set(elo["Player"].dropna())
    metadata_models = set(metadata["model"].dropna())

    assert list(inventory.columns) == [
        "llm_chess_player",
        "review_status",
        "provider_or_family",
        "date_released",
        "reasoning_status",
        "reasoning_kind_inferred",
        "reasoning_effort_inferred",
    ]
    assert len(inventory) == len(elo_players | metadata_models)
    assert summary["exact_match"] == len(elo_players & metadata_models)
    assert summary["elo_only"] == len(elo_players - metadata_models)
    assert summary["metadata_only"] == len(metadata_models - elo_players)


def test_llm_chess_inputs_mask_grok_token_and_cost_metrics_for_analysis():
    elo, _, contract = load_llm_chess_inputs(REPO_ROOT)

    grok_rows = elo.loc[elo["Player"].fillna("").str.startswith("grok-")]

    assert not grok_rows.empty
    assert grok_rows["completion_tokens_black_per_move"].isna().all()
    assert grok_rows["average_game_cost"].isna().all()

    data_quality = contract["data_quality"]
    row_mask = data_quality["row_level_masks"][0]
    assert row_mask["rule_id"] == "grok_token_and_cost_metrics_masked"
    assert row_mask["affected_row_count"] == len(grok_rows)
    assert "completion_tokens_black_per_move" in row_mask["masked_columns"]

    global_exclusion = data_quality["global_multifactor_metric_exclusions"][0]
    assert "wrong_moves_per_1000moves" in global_exclusion["metric_columns"]
    assert "mistakes_per_1000moves" in global_exclusion["metric_columns"]


def test_filter_multifactor_candidate_metrics_excludes_historically_tainted_metrics():
    filtered, excluded = filter_multifactor_candidate_metrics(
        [
            "wrong_moves_per_1000moves",
            "player_wins_percent",
            "mistakes_per_1000moves",
            "average_time_per_game_seconds",
        ]
    )

    assert filtered == ["player_wins_percent", "average_time_per_game_seconds"]
    assert excluded == ["wrong_moves_per_1000moves", "mistakes_per_1000moves"]


def test_multifactor_analysis_excludes_historically_tainted_metrics():
    df = pd.DataFrame(
        {
            "target": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "wrong_moves_per_1000moves": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "player_wins_percent": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0],
            "average_time_per_game_seconds": [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
        }
    )

    relationships = build_metric_relationships(
        df,
        target_column="target",
        candidate_metrics=["wrong_moves_per_1000moves", "player_wins_percent"],
    )
    prediction = build_prediction_summary(
        df,
        target_column="target",
        candidate_metrics=["wrong_moves_per_1000moves", "player_wins_percent"],
    )

    assert [row["name"] for row in relationships] == ["player_wins_percent"]
    assert prediction["excluded_candidate_metrics"] == ["wrong_moves_per_1000moves"]
    assert prediction["features"] == ["player_wins_percent"]


def test_prediction_feature_selection_happens_inside_cv_training_folds(monkeypatch):
    df = pd.DataFrame(
        {
            "target": [1.0, 2.0, 1.5, 2.5, 8.0, 9.0, 8.5, 9.5, 12.0, 13.0],
            "metric_a": [1.0, 2.1, 1.4, 2.2, 7.8, 9.1, 8.3, 9.6, 11.8, 13.1],
            "metric_b": [13.0, 11.0, 10.0, 9.0, 7.0, 6.5, 5.0, 4.0, 2.0, 1.0],
        }
    )
    observed_lengths = []
    original_choose_features = statistics.choose_features

    def spy_choose_features(*args, **kwargs):
        observed_lengths.append(len(args[0]))
        return original_choose_features(*args, **kwargs)

    monkeypatch.setattr(statistics, "choose_features", spy_choose_features)

    prediction = statistics.build_prediction_summary(
        df,
        target_column="target",
        candidate_metrics=["metric_a", "metric_b"],
    )

    assert prediction["status"] == "ok"
    assert len(df) not in observed_lengths
    assert prediction["ols"]["feature_selection"]["method"] == "within_cv_training_folds"
    assert prediction["ols"]["feature_selection"]["fold_count"] == 15


def test_seed_eci_mapping_preserves_source_bridge():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = eci.normalize_source()
    seed_mapping = eci.build_seed_mapping(inventory)

    assert len(seed_mapping) == len(normalized)
    assert list(seed_mapping.columns[:7]) == [
        "eval_id",
        "eval_row_id",
        "eval_model_label",
        "llm_chess_player",
        "eval_variant_label",
        "mapping_status",
        "review_status",
    ]
    assert "source_llm_chess_model" in seed_mapping.columns
    assert set(seed_mapping["mapping_status"].unique()) <= {"accepted", "unmatched"}
    assert set(seed_mapping["review_status"].unique()) == {"qa_passed"}


def test_eval_source_tree_contains_only_source_artifacts():
    evals_root = CROSS_REF_ROOT / "evals"

    assert not (CROSS_REF_ROOT / "eci").exists()
    assert not (CROSS_REF_ROOT / "arc-agi-2").exists()
    assert list(evals_root.rglob("*.py")) == []
    assert {path.name for path in (evals_root / "eci").iterdir()} == {"SOURCE.md", "epoch_eci_apr_2026.csv"}
    assert {path.name for path in (evals_root / "arc-agi-2").iterdir()} == {"SOURCE.md", "arc-agi-2-apr-2026.csv"}


def test_arc_mapping_covers_all_rows_and_summary_is_strict_json():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = arc_agi_2.normalize_source()
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/arc_agi_2.csv")
    merged = apply_mapping(normalized, mapping)

    assert len(merged) == len(normalized)
    assert merged["mapping_status"].notna().all()

    summary, _, _, _ = arc_agi_2.run_analysis(
        inventory,
        mapping,
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/arc_agi_2.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )
    json.dumps(summary, allow_nan=False)
    assert summary["inputs"]["source"]["numeric_parse_rates"]["score_arc_agi_2"] > 0
    assert summary["inputs"]["source"]["numeric_parse_rates"]["cost_v3"] == 0.0
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/arc_agi_2.csv"
    assert summary["analysis_surfaces"]["metric_analysis"]["count"] == 55
    assert summary["analysis_surfaces"]["elo_analysis"]["count"] == 52
    assert summary["relationships"]["raw_elo"]["sample_stage_id"] == "elo_analysis_rows_max_dedupe"
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    assert summary["prediction"]["sample_stage_id"] == "metric_analysis_rows_max_dedupe"
    assert summary["prediction"]["sample_n"] == summary["analysis_surfaces"]["metric_analysis"]["count"]
    assert "elo" not in summary["prediction"]["features"]
    assert summary["coverage"]["matched_llm_chess_rows"] == summary["relationships"]["raw_elo"]["n"]
    assert summary["coverage"]["external_rows_without_llm_chess_match"] == (
        summary["coverage"]["numeric_score_rows"] - summary["coverage"]["rows_joined_to_llm_chess_metric_rows"]
    )
    assert [stage["stage_id"] for stage in summary["funnel"]["stages"]] == [
        "numeric_external_eval_rows",
        "accepted_mapping_rows",
        "rows_joined_to_llm_chess_metric_rows",
        "metric_analysis_rows_max_dedupe",
        "rows_joined_to_llm_chess_rows_with_non_null_elo",
        "elo_analysis_rows_max_dedupe",
    ]


def test_eci_summary_preserves_legacy_parity_slice():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/eci.csv")

    summary, _, _, _ = eci.run_analysis(
        inventory,
        mapping,
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/eci.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )

    assert summary["inputs"]["source"]["columns"] == ["Model", "Score", "90% CI", "llm_chess_model"]
    assert summary["inputs"]["source"]["numeric_parse_rates"]["score_numeric"] == 1.0
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/eci.csv"
    assert summary["mapping_source_of_truth"]["source_seed_column"] == "llm_chess_model"
    assert summary["coverage"]["accepted_mapping_rows"] == 89
    assert summary["coverage"]["rows_joined_to_llm_chess_metric_rows"] == 89
    assert summary["coverage"]["metric_analysis_rows_max_dedupe"] == 81
    assert summary["coverage"]["rows_joined_to_llm_chess_elo"] == 74
    assert summary["coverage"]["unique_llm_chess_players_joined_to_elo"] == 66
    assert summary["coverage"]["elo_analysis_rows_max_dedupe"] == 66
    assert summary["coverage"]["regression_rows_max_dedupe"] == 66
    assert summary["analysis_surfaces"]["metric_analysis"]["count"] == 81
    assert summary["analysis_surfaces"]["elo_analysis"]["count"] == 66
    assert summary["relationships"]["raw_elo"]["sample_stage_id"] == "elo_analysis_rows_max_dedupe"
    assert summary["relationships"]["raw_elo"]["n"] == 66
    assert summary["prediction"]["sample_stage_id"] == "metric_analysis_rows_max_dedupe"
    assert summary["prediction"]["sample_n"] == 81
    assert "elo" not in summary["prediction"]["features"]
    assert summary["coverage"]["duplicate_joined_player_rows"] == 8
    assert summary["coverage"]["external_rows_without_llm_chess_elo_join"] == (
        summary["coverage"]["numeric_score_rows"] - summary["coverage"]["rows_joined_to_llm_chess_elo"]
    )
    assert summary["sensitivity"]["legacy_parity"]["matched_sample_max_dedupe"] == 66
    assert round(summary["sensitivity"]["legacy_parity"]["pearson_r"], 12) == round(0.6967985896751968, 12)


def test_coverage_outputs_reconcile_with_funnel_and_explain_missing_elo_and_dedupe():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)

    eci_summary, _, eci_coverage, _ = eci.run_analysis(
        inventory,
        load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/eci.csv"),
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/eci.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )

    assert int(eci_coverage["survived_metric_dedupe"].sum()) == eci_summary["analysis_surfaces"]["metric_analysis"]["count"]
    assert int(eci_coverage["joined_llm_chess_row_with_non_null_elo"].sum()) == eci_summary["coverage"]["rows_joined_to_llm_chess_rows_with_non_null_elo"]
    assert int(eci_coverage["survived_elo_dedupe"].sum()) == eci_summary["analysis_surfaces"]["elo_analysis"]["count"]

    minimax_row = eci_coverage.loc[eci_coverage["llm_chess_player"] == "minimax.minimax-m2.5"].iloc[0]
    assert minimax_row["joined_llm_chess_metric_row"]
    assert minimax_row["survived_metric_dedupe"]
    assert not minimax_row["joined_llm_chess_row_with_non_null_elo"]
    assert minimax_row["elo_drop_side"] == "chess"
    assert "Elo is missing" in minimax_row["elo_drop_reason"]

    arc_summary, _, arc_coverage, _ = arc_agi_2.run_analysis(
        inventory,
        load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/arc_agi_2.csv"),
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/arc_agi_2.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )

    assert int(arc_coverage["survived_metric_dedupe"].sum()) == arc_summary["analysis_surfaces"]["metric_analysis"]["count"]
    assert int(arc_coverage["survived_elo_dedupe"].sum()) == arc_summary["analysis_surfaces"]["elo_analysis"]["count"]

    dedupe_loser = arc_coverage.loc[
        arc_coverage["eval_row_id"] == "arc_agi_2:0041:gemini_3_flash_preview_low"
    ].iloc[0]
    assert not dedupe_loser["survived_metric_dedupe"]
    assert dedupe_loser["metric_drop_side"] == "dedupe"
    assert dedupe_loser["metric_dedupe_kept_eval_row_id"] == "arc_agi_2:0043:gemini_3_flash_preview_high"
    assert dedupe_loser["first_failed_stage"] == "metric_analysis_rows_max_dedupe"