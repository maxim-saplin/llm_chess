import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CROSS_REF_ROOT = REPO_ROOT / "data/cross-ref"
RESULTS_DIR = CROSS_REF_ROOT / "results"
MAPPINGS_DIR = CROSS_REF_ROOT / "mappings"
if str(CROSS_REF_ROOT) not in sys.path:
    sys.path.insert(0, str(CROSS_REF_ROOT))

from adapters import arc_agi_2, bullshit_bench, delegate_52, eci, vals_index  # noqa: E402
from framework.data_quality import (  # noqa: E402
    MISTAKE_STATS_TRUSTED_AFTER,
    REPAIRABLE_MISTAKE_METRICS,
    clean_mistake_stats_mask,
    filter_multifactor_candidate_metrics,
)
from framework.diffing import compare_csv_files  # noqa: E402
from framework.loading import load_llm_chess_inputs  # noqa: E402
from framework.mapping import (  # noqa: E402
    ACCEPTED_MAPPING_STATUSES,
    apply_mapping,
    load_mapping_file,
)
from framework.mapping_review import build_mapping_review  # noqa: E402
from framework.model_identity import build_llm_chess_inventory, inventory_summary  # noqa: E402
from framework.normalization import parse_currency, parse_day_month_year, parse_percent  # noqa: E402
import framework.statistics as statistics  # noqa: E402
from framework.statistics import build_metric_relationships, build_prediction_summary  # noqa: E402
import run_cross_ref  # noqa: E402


def _artifact_diffs_by_id(diff_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {entry["artifact_id"]: entry for entry in diff_payload["artifact_diffs"]}


def _snapshot_mappings(tmp_path: Path) -> Path:
    """Freeze the mapping CSVs for the duration of a test.

    The checked-in mappings are shared mutable input. A test that regenerates a baseline and then
    reruns against it spans minutes, and any write landing in that window shows up as a spurious
    artifact diff, so tests that assert reproducibility must read one pinned copy throughout.
    """
    mapping_dir = tmp_path / "pinned_mappings"
    mapping_dir.mkdir(parents=True, exist_ok=True)
    for mapping_path in MAPPINGS_DIR.glob("*.csv"):
        shutil.copy2(mapping_path, mapping_dir / mapping_path.name)
    return mapping_dir


def _write_current_eval_baseline(results_dir: Path, *eval_ids: str, mapping_dir: Path | None = None) -> Path:
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
                *(["--mapping-path", str(mapping_dir / f"{eval_id}.csv")] if mapping_dir else []),
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
    # COST (V3) uses a thousands shorthand that the ARC-AGI-1/2 cost column never does.
    assert parse_currency("$15.2K") == 15200.0
    assert parse_currency("$10.0k") == 10000.0
    assert parse_currency("K") is None
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
        CROSS_REF_ROOT / "mappings" / "bullshit_bench.csv",
        CROSS_REF_ROOT / "mappings" / "delegate_52.csv",
        CROSS_REF_ROOT / "mappings" / "vals_index.csv",
    ]:
        header = mapping_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert header[: len(expected_prefix)] == expected_prefix


def test_mapping_review_builds_cross_eval_rows_and_supports_filters():
    review_rows, payload = build_mapping_review(CROSS_REF_ROOT / "mappings")

    assert set(review_rows["eval_id"].unique()) == {"eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index"}
    assert payload["summary"]["eval_count"] == 5
    assert payload["summary"]["row_count"] == len(review_rows)
    assert payload["summary"]["unresolved_row_count"] > 0
    assert {"provider_group_source", "provider_group_confidence"} <= set(review_rows.columns)

    gemini_rows, gemini_payload = build_mapping_review(
        CROSS_REF_ROOT / "mappings",
        player="gemini-3.1-pro-preview-high",
    )

    assert set(gemini_rows["eval_id"].unique()) == {"eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index"}
    assert gemini_payload["summary"]["unique_llm_chess_players"] == 1
    assert gemini_payload["player_matrix_rows"][0]["llm_chess_player"] == "gemini-3.1-pro-preview-high"

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
    assert set(anthropic_rows["eval_id"].unique()) == {"eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index"}
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
        filter_player="gemini-3.1-pro-preview-high",
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
    assert set(csv_rows["eval_id"].unique()) == {"eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index"}
    assert "gemini-3.1-pro-preview-high" in set(csv_rows["llm_chess_player"])
    assert "Mapping Review" in html
    assert "gemini-3.1-pro-preview-high" in html


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
            # This test is about aggregate generation, so it opts out of the publish gate's mapping
            # check rather than tracking whatever mapping debt the repo happens to carry.
            "--allow-metadata-only",
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
    mapping_dir = _snapshot_mappings(tmp_path)
    results_dir = _write_current_eval_baseline(
        tmp_path / "results", "eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index", mapping_dir=mapping_dir
    )
    summary_output = tmp_path / "audit_summary.json"
    report_output = tmp_path / "audit_report.md"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "audit",
            "--results-dir",
            str(results_dir),
            "--mapping-dir",
            str(mapping_dir),
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
    assert summary["benchmarks"]["count"] == 6
    assert summary["benchmarks"]["ids"] == [
        "llm_chess",
        "arc_agi_2",
        "bullshit_bench",
        "delegate_52",
        "eci",
        "vals_index",
    ]
    assert summary["benchmarks"]["external_eval_count"] == 5
    assert summary["reproducibility_status"] == "pass"
    assert summary["reproducibility"]["rerun_diff_all_clean"] is True
    assert all(entry["has_diff"] is False for entry in summary["reproducibility"]["per_eval"])
    assert summary["coverage_status"] == "review-needed"
    assert summary["mapping_review"]["unresolved_row_count"] > 0
    assert "overall_status: review-needed" in report
    assert "benchmarks: llm_chess, arc_agi_2, bullshit_bench, delegate_52, eci, vals_index" in report
    assert "This file is generated by `run_cross_ref.py audit`." in report


def test_audit_defaults_to_scratch_outputs_without_mutating_published_audit(tmp_path):
    published_paths = [
        CROSS_REF_ROOT / "results" / "audit_summary.json",
        CROSS_REF_ROOT / "results" / "audit_report.md",
    ]
    before = _snapshot_files(published_paths)
    # audit rerun-diffs every registered adapter, so it needs a baseline covering all of them. Read
    # one from a fixture rather than from results/: a newly registered eval has no published summary
    # until someone runs --publish, and this test is about where a default run *writes*, not about
    # whether results/ is currently complete. No output flags are passed, so the scratch-default
    # routing under assertion is still exactly what runs.
    mapping_dir = _snapshot_mappings(tmp_path)
    results_dir = _write_current_eval_baseline(
        tmp_path / "results", *sorted(run_cross_ref.ADAPTERS), mapping_dir=mapping_dir
    )
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["audit", "--results-dir", str(results_dir), "--mapping-dir", str(mapping_dir)])

    payload = run_cross_ref.run_audit(args)

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["summary_output"])
    _assert_outside_cross_ref(payload["report_output"])
    _assert_snapshot_unchanged(before)


def test_audit_threshold_can_promote_clean_reproducible_state(tmp_path):
    mapping_dir = _snapshot_mappings(tmp_path)
    results_dir = _write_current_eval_baseline(
        tmp_path / "results", "eci", "arc_agi_2", "bullshit_bench", "delegate_52", "vals_index", mapping_dir=mapping_dir
    )
    summary_output = tmp_path / "audit_summary.json"
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "audit",
            "--results-dir",
            str(results_dir),
            "--mapping-dir",
            str(mapping_dir),
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


def _metadata_only_player() -> str:
    """A model known to models_metadata.csv but with no row in elo_refined.csv."""
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    candidates = sorted(set(metadata["model"].dropna()) - set(elo["Player"].dropna()))
    assert candidates, "expected at least one metadata-only model to build the fixture from"
    return candidates[0]


def _mappings_with_metadata_only_row(tmp_path: Path, eval_id: str = "eci") -> tuple[Path, str]:
    """Pin the mappings, then repoint one accepted row at a model that has no chess games.

    The fixture is built rather than borrowed from the checked-in mappings on purpose: whether the
    repo currently carries this kind of debt changes as mappings are repointed, and the semantics
    under test must not depend on that.
    """
    mapping_dir = _snapshot_mappings(tmp_path)
    player = _metadata_only_player()
    mapping_path = mapping_dir / f"{eval_id}.csv"
    mapping = pd.read_csv(mapping_path)
    accepted = mapping[mapping["mapping_status"].isin(sorted(ACCEPTED_MAPPING_STATUSES))]
    assert not accepted.empty, f"{mapping_path} has no accepted rows to repoint"
    mapping.loc[int(accepted.index[0]), "llm_chess_player"] = player
    mapping.to_csv(mapping_path, index=False)
    return mapping_dir, player


def _write_self_consistent_publish(tmp_path: Path, *eval_ids: str, mapping_dir: Path | None = None) -> Path:
    """Build a results dir whose per-eval artifacts and aggregate summary all agree with each other."""
    results_dir = _write_current_eval_baseline(
        tmp_path / "results", *eval_ids, mapping_dir=mapping_dir or _snapshot_mappings(tmp_path)
    )
    parser = run_cross_ref.build_parser()
    run_cross_ref.run_cross_eval(
        parser.parse_args(
            [
                "cross-eval",
                "--results-dir",
                str(results_dir),
                "--summary-output",
                str(results_dir / "cross_ref_summary.json"),
                "--report-output",
                str(results_dir / "cross_ref_report.md"),
            ]
        )
    )
    return results_dir


def _run_verify(results_dir: Path, summary_output: Path, *extra_args: str) -> dict[str, object]:
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(
        [
            "verify",
            "--results-dir",
            str(results_dir),
            "--summary-output",
            str(summary_output),
            *extra_args,
        ]
    )
    return run_cross_ref.run_verify(args)


def test_verify_passes_on_self_consistent_publish_when_metadata_only_is_allowed(tmp_path):
    mapping_dir, player = _mappings_with_metadata_only_row(tmp_path)
    results_dir = _write_self_consistent_publish(tmp_path, "eci", "arc_agi_2", mapping_dir=mapping_dir)
    summary_output = tmp_path / "verify_summary.json"

    # --allow-metadata-only isolates artifact consistency from mapping debt, so this asserts the
    # artifact checks are satisfiable rather than always-red.
    payload = _run_verify(
        results_dir, summary_output, "--mapping-dir", str(mapping_dir), "--allow-metadata-only"
    )
    summary = json.loads(summary_output.read_text(encoding="utf-8"))

    assert payload["overall_status"] == "pass"
    assert payload["failed_check_ids"] == []
    assert set(payload["check_status"]) == {
        "published_summary_sha256",
        "recorded_llm_chess_input_rows",
        "artifact_player_agreement",
        "mapping_player_resolution",
    }
    assert all(status == "pass" for status in payload["check_status"].values())
    assert summary["artifact_kind"] == "cross_ref_verify"
    assert summary["allow_metadata_only"] is True
    assert payload["dangling_player_row_count"] == 0
    assert payload["unresolved_player_row_count"] == 0
    # The metadata-only subset stays visible even when it is not counted as a failure.
    assert payload["metadata_only_player_row_count"] >= 1
    assert player in summary["metadata_only_players"]["players"]


def test_verify_detects_stale_summary_hash_recorded_rows_and_player_disagreement(tmp_path):
    results_dir = _write_self_consistent_publish(tmp_path, "eci")
    summary_path = results_dir / "eci_summary.json"
    published_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    # Simulate the drift the published artifacts carry: a summary regenerated against inputs that
    # the sibling coverage CSV and the aggregate sha256 record never saw.
    published_summary["llm_chess_inputs"]["elo_refined"]["rows"] = 1
    summary_path.write_text(json.dumps(published_summary, indent=2) + "\n", encoding="utf-8")
    coverage_path = results_dir / "eci_coverage.csv"
    coverage = pd.read_csv(coverage_path)
    dropped_player = str(
        coverage.loc[coverage["survived_elo_dedupe"] == True, "llm_chess_player"].dropna().iloc[0]
    )
    coverage.loc[coverage["llm_chess_player"] == dropped_player, "llm_chess_player"] = pd.NA
    coverage.to_csv(coverage_path, index=False)

    # --allow-metadata-only holds the mapping debt constant so the failing set is exactly the three
    # artifact checks this test tampered with.
    payload = _run_verify(results_dir, tmp_path / "verify_summary.json", "--allow-metadata-only")
    summary = json.loads((tmp_path / "verify_summary.json").read_text(encoding="utf-8"))

    assert payload["overall_status"] == "fail"
    assert set(payload["failed_check_ids"]) == {
        "published_summary_sha256",
        "recorded_llm_chess_input_rows",
        "artifact_player_agreement",
    }
    row_failure = summary["checks"]["recorded_llm_chess_input_rows"]["failures"][0]
    assert row_failure["recorded_rows"] == 1
    assert row_failure["actual_rows"] == summary["llm_chess_input_rows"]["elo_refined"]
    player_failure = summary["checks"]["artifact_player_agreement"]["failures"][0]
    assert dropped_player in player_failure["summary_players_missing_from_coverage"]


def test_verify_reports_clean_mapping_player_resolution_for_checked_in_mappings(tmp_path):
    # The complement of the two fixture-driven failure tests: no accepted row in the checked-in
    # mappings may point at a player without a row in data/elo_refined.csv. Only this check is
    # asserted, because the published artifacts in results/ carry their own separate drift.
    payload = _run_verify(RESULTS_DIR, tmp_path / "verify_summary.json")
    summary = json.loads((tmp_path / "verify_summary.json").read_text(encoding="utf-8"))

    assert payload["check_status"]["mapping_player_resolution"] == "pass"
    assert payload["dangling_player_row_count"] == 0
    assert payload["metadata_only_player_row_count"] == 0
    assert payload["unresolved_player_row_count"] == 0
    resolution = summary["checks"]["mapping_player_resolution"]
    assert resolution["checked_count"] == len(run_cross_ref.ADAPTERS)
    assert resolution["failure_count"] == 0
    assert all(entry["matches"] for entry in resolution["rows"])


def test_verify_reports_dangling_mapping_targets_and_refuses_to_publish_them(tmp_path):
    results_dir = _write_self_consistent_publish(tmp_path, "eci")
    mapping_dir = tmp_path / "mappings"
    mapping_dir.mkdir()
    for mapping_path in MAPPINGS_DIR.glob("*.csv"):
        mapping = pd.read_csv(mapping_path)
        if mapping_path.stem == "eci":
            accepted_index = int(mapping[mapping["mapping_status"] == "accepted"].index[0])
            mapping.loc[accepted_index, "llm_chess_player"] = "model-the-repo-never-heard-of"
        mapping.to_csv(mapping_dir / mapping_path.name, index=False)

    payload = _run_verify(
        results_dir, tmp_path / "verify_summary.json", "--mapping-dir", str(mapping_dir)
    )
    summary = json.loads((tmp_path / "verify_summary.json").read_text(encoding="utf-8"))

    assert payload["overall_status"] == "fail"
    assert "mapping_player_resolution" in payload["failed_check_ids"]
    # A name in neither elo_refined.csv nor models_metadata.csv is dangling, not metadata-only, so
    # --allow-metadata-only cannot excuse it.
    assert payload["dangling_player_row_count"] == 1
    assert payload["metadata_only_player_row_count"] == 0
    assert summary["dangling_players"]["players"] == ["model-the-repo-never-heard-of"]
    eci_row = next(row for row in summary["checks"]["mapping_player_resolution"]["rows"] if row["eval_id"] == "eci")
    assert eci_row["dangling_row_count"] == 1
    assert eci_row["metadata_only_row_count"] == 0

    lenient_payload = _run_verify(
        results_dir,
        tmp_path / "lenient_verify.json",
        "--mapping-dir",
        str(mapping_dir),
        "--allow-metadata-only",
    )
    assert lenient_payload["check_status"]["mapping_player_resolution"] == "fail"
    assert lenient_payload["unresolved_player_row_count"] == 1

    parser = run_cross_ref.build_parser()
    publish_args = parser.parse_args(
        [
            "verify",
            "--results-dir",
            str(results_dir),
            "--mapping-dir",
            str(mapping_dir),
            "--summary-output",
            str(tmp_path / "published_verify_summary.json"),
            "--publish",
        ]
    )

    with pytest.raises(ValueError, match="must not be published"):
        run_cross_ref.run_verify(publish_args)
    assert not (tmp_path / "published_verify_summary.json").exists()


def test_verify_fails_by_default_on_accepted_rows_without_elo_coverage(tmp_path):
    mapping_dir, player = _mappings_with_metadata_only_row(tmp_path)
    results_dir = _write_self_consistent_publish(tmp_path, "eci", mapping_dir=mapping_dir)
    summary_output = tmp_path / "default_verify.json"

    default_payload = _run_verify(results_dir, summary_output, "--mapping-dir", str(mapping_dir))
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    lenient_payload = _run_verify(
        results_dir,
        tmp_path / "lenient_verify.json",
        "--mapping-dir",
        str(mapping_dir),
        "--allow-metadata-only",
    )

    # Absence from data/elo_refined.csv is the failure condition, whether or not the name survives
    # in data/models_metadata.csv. Only that check fails here, so the artifact checks stay honest.
    assert default_payload["overall_status"] == "fail"
    assert default_payload["failed_check_ids"] == ["mapping_player_resolution"]
    assert summary["allow_metadata_only"] is False
    assert default_payload["dangling_player_row_count"] == 0
    assert default_payload["metadata_only_player_row_count"] >= 1
    assert default_payload["unresolved_player_row_count"] == default_payload["metadata_only_player_row_count"]
    # The failing mapping file is reported with its own row counts, and the metadata-only subset is
    # still broken out separately rather than collapsed into an opaque failure.
    failures = {entry["eval_id"]: entry for entry in summary["checks"]["mapping_player_resolution"]["failures"]}
    assert "eci" in failures
    assert failures["eci"]["metadata_only_row_count"] >= 1
    assert failures["eci"]["dangling_row_count"] == 0
    assert player in {row["llm_chess_player"] for row in failures["eci"]["metadata_only"]}
    assert player in summary["metadata_only_players"]["players"]

    assert lenient_payload["check_status"]["mapping_player_resolution"] == "pass"
    assert lenient_payload["metadata_only_player_row_count"] == default_payload["metadata_only_player_row_count"]
    assert lenient_payload["unresolved_player_row_count"] == 0


def test_publish_gate_refuses_accepted_rows_without_elo_coverage(tmp_path):
    mapping_dir, _ = _mappings_with_metadata_only_row(tmp_path)
    parser = run_cross_ref.build_parser()
    refused_output = tmp_path / "refused_summary.json"
    publish_args = parser.parse_args(
        [
            "eci",
            "--publish",
            "--mapping-path",
            str(mapping_dir / "eci.csv"),
            "--summary-output",
            str(refused_output),
            "--html-output",
            str(tmp_path / "refused.html"),
            "--coverage-output",
            str(tmp_path / "refused_coverage.csv"),
            "--inventory-output",
            str(tmp_path / "refused_inventory.csv"),
        ]
    )

    with pytest.raises(ValueError, match="no row in data/elo_refined.csv"):
        run_cross_ref.run_eval(publish_args)
    # The refusal happens before any output path is resolved, so nothing is written.
    assert not refused_output.exists()
    assert not (tmp_path / "refused_inventory.csv").exists()


def test_verify_defaults_to_scratch_outputs_and_requires_publish_for_results_dir():
    published_path = RESULTS_DIR / "verify_summary.json"
    before = _snapshot_files([published_path])
    parser = run_cross_ref.build_parser()

    payload = run_cross_ref.run_verify(parser.parse_args(["verify"]))

    assert payload["output_mode"] == "review"
    _assert_outside_cross_ref(payload["summary_output"])
    _assert_snapshot_unchanged(before)

    publish_args = parser.parse_args(["verify", "--summary-output", str(published_path)])
    with pytest.raises(ValueError, match="require --publish"):
        run_cross_ref.run_verify(publish_args)
    _assert_snapshot_unchanged(before)


def test_named_corr_and_bootstrap_corr_guard_zero_variance_inputs():
    constant = pd.Series([1.0, 1.0, 1.0, 1.0])
    varying = pd.Series([1.0, 2.0, 3.0, 4.0])

    # The guard is load-bearing: scipy raises rather than returning nan on constant x.
    with pytest.raises(ValueError, match="all x values are identical"):
        statistics.stats.linregress(constant, varying)

    assert statistics.named_corr("constant_x", constant, varying) == {"name": "constant_x", "n": 4}
    assert statistics.named_corr("constant_y", varying, constant) == {"name": "constant_y", "n": 4}
    assert statistics.bootstrap_corr(constant, varying) is None
    assert statistics.bootstrap_corr(varying, constant) is None
    # A non-degenerate sample still produces intervals.
    assert statistics.named_corr("ok", varying, varying)["pearson_r"] == pytest.approx(1.0)
    assert statistics.bootstrap_corr(varying, varying) is not None


def test_partial_corr_release_month_spends_a_degree_of_freedom_on_the_covariate():
    # Residualizing on release month estimates an intercept and a slope per variable, so the
    # reference distribution loses a degree of freedom relative to a plain correlation. scipy's
    # pearsonr/spearmanr on the residual vectors would test against df = n - 2 and report a p
    # that is too small; the correct df is n - 3.
    rng = np.random.default_rng(7)
    n = 40
    month = pd.Series(np.arange(n, dtype=float))
    score = pd.Series(month * 0.5 + rng.normal(size=n))
    metric = pd.Series(month * 0.3 + rng.normal(size=n))

    result = statistics.partial_corr_release_month(score, metric, month)

    assert result["n"] == n
    assert result["controlled_variables"] == 1
    assert result["df"] == n - 3
    for stat_key, p_key in (("pearson_r", "pearson_p"), ("spearman_r", "spearman_p")):
        r = result[stat_key]
        expected = statistics._partial_corr_p_value(r, n, 1)
        uncorrected = statistics._partial_corr_p_value(r, n, 0)
        assert result[p_key] == pytest.approx(expected)
        # The correction is conservative and non-trivial: it always raises the p.
        assert result[p_key] > uncorrected

    # And the helper reduces to scipy exactly when nothing is controlled, so df is the only change.
    plain = statistics.stats.pearsonr(score, metric)
    assert statistics._partial_corr_p_value(plain.statistic, n, 0) == pytest.approx(plain.pvalue)


def test_rerun_diff_reports_no_diff_when_baseline_regenerated_from_current_inputs(tmp_path):
    # The baseline here is regenerated from current code and inputs, so this only proves the
    # rerun-diff machinery is deterministic. Input drift is covered by the RESULTS_DIR test below.
    payload, diff_payload, diff_markdown = _run_rerun_diff(tmp_path, "eci")
    artifact_diffs = _artifact_diffs_by_id(diff_payload)

    assert payload["has_diff"] is False
    assert diff_payload["has_diff"] is False
    assert payload["candidate_artifacts"]["summary_json"].startswith(str(tmp_path / "eci_scratch"))
    assert artifact_diffs["summary_json"]["changed"] is False
    assert artifact_diffs["coverage_csv"]["changed"] is False
    assert "No differences detected between baseline and rerun candidate artifacts." in diff_markdown


def test_rerun_diff_against_published_results_dir_detects_recorded_input_drift(tmp_path):
    published_summary_path = RESULTS_DIR / "eci_summary.json"
    recorded_elo_rows = json.loads(published_summary_path.read_text(encoding="utf-8"))[
        "llm_chess_inputs"
    ]["elo_refined"]["rows"]
    elo, _, _ = load_llm_chess_inputs(REPO_ROOT)

    payload, diff_payload, _ = _run_rerun_diff(tmp_path, "eci", baseline_results_dir=RESULTS_DIR)
    artifact_diffs = _artifact_diffs_by_id(diff_payload)

    # The baseline must be the checked-in publish itself, not one regenerated from current inputs,
    # otherwise the diff can never report drift.
    assert payload["baseline_artifacts"]["summary_json"] == "data/cross-ref/results/eci_summary.json"
    # A publish that recorded a different elo_refined row count than the current authoritative input
    # cannot reproduce, because that row count is part of the summary being compared.
    if recorded_elo_rows == len(elo):
        assert diff_payload["has_diff"] is False
        assert artifact_diffs["summary_json"]["changed"] is False
    else:
        assert diff_payload["has_diff"] is True
        assert artifact_diffs["summary_json"]["changed"] is True


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
    source_df = pd.read_csv(CROSS_REF_ROOT / "evals" / "eci" / "epoch_eci_jul_2026.csv")
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
    # Prose assertions below match against a whitespace-collapsed copy: the claim has to be present,
    # but where a markdown reflow happens to wrap the line is not a property worth failing on.
    report_prose = " ".join(consolidated_report.split())

    assert "## Bottom Line" in consolidated_report
    assert "## Signal Table" in consolidated_report
    assert "## Method In One Screen" in consolidated_report
    assert "## Coverage Debt" in consolidated_report
    assert "## What Raises Signal" in consolidated_report
    assert "**ECI**: usable relationship" in report_prose
    # Every registered eval must carry a named interpretation, not just a table row. Pinning a
    # verdict phrase per eval is deliberately avoided here: ARC's used to read "weak relationship"
    # and stopped being true when its CV R2 flipped sign, which is a data move, not a report bug.
    for eval_label in ("ECI", "ARC-AGI-2", "Vals Index", "DELEGATE-52", "BullshitBench"):
        assert f"- **{eval_label}**:" in report_prose
    assert "Feature selection happens inside each training fold" in report_prose
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
    assert {path.name for path in (evals_root / "eci").iterdir()} == {"SOURCE.md", "epoch_eci_jul_2026.csv"}
    assert {path.name for path in (evals_root / "arc-agi-2").iterdir()} == {"SOURCE.md", "arc-agi-2-jul-2026.csv"}
    assert {path.name for path in (evals_root / "bullshit-bench").iterdir()} == {"SOURCE.md", "bullshit_bench_v2_may_2026.csv"}
    assert {path.name for path in (evals_root / "delegate-52").iterdir()} == {"SOURCE.md", "delegate-52-may-2026.csv"}
    assert {path.name for path in (evals_root / "vals-index").iterdir()} == {"SOURCE.md", "vals_index_v1_2_july_2026.csv"}


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
    # The 2026-07 refresh rebuilt the snapshot from arcprize.org's JSON and taught parse_currency the
    # leaderboard's "$15.2K" shorthand, so COST (V3) now parses fully instead of at 0.0.
    assert summary["inputs"]["source"]["numeric_parse_rates"]["cost_v3"] == 1.0
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/arc_agi_2.csv"
    assert summary["relationships"]["raw_elo"]["sample_stage_id"] == "elo_analysis_rows_max_dedupe"
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    assert summary["prediction"]["sample_stage_id"] == "metric_analysis_rows_max_dedupe"
    # Two distinct counts. "sample_n" is the metric-analysis sample handed to the prediction block;
    # "n" is what survived dropna and was actually cross-validated. The CV scores belong to "n".
    assert summary["prediction"]["sample_n"] == summary["analysis_surfaces"]["metric_analysis"]["count"]
    assert summary["prediction"]["n"] <= summary["prediction"]["sample_n"]
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


def test_bullshit_bench_mapping_covers_all_rows_and_summary_is_strict_json():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = bullshit_bench.normalize_source()
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/bullshit_bench.csv")
    merged = apply_mapping(normalized, mapping)

    assert len(normalized) == 162
    assert len(merged) == len(normalized)
    assert merged["mapping_status"].notna().all()

    summary, _, coverage, _ = bullshit_bench.run_analysis(
        inventory,
        mapping,
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/bullshit_bench.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )
    json.dumps(summary, allow_nan=False)

    assert summary["target_score_column"] == "score_numeric"
    assert summary["inputs"]["source"]["numeric_parse_rates"]["score_numeric"] == 1.0
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/bullshit_bench.csv"
    assert summary["mapping_source_of_truth"]["source_seed_column"] is None
    # The reviewed mapping resolves a known set of model identities. The repointed mapping moved 5
    # rows from unmatched to variant-compatible, keeping the 162-row total.
    status_counts = summary["mapping"]["mapping_file_status_counts"]
    assert status_counts["accepted"] == 6
    assert status_counts["alias"] == 21
    assert status_counts["variant-compatible"] == 44
    assert status_counts["ambiguous"] == 6
    assert status_counts["unmatched"] == 85
    assert sum(status_counts.values()) == len(normalized)
    # Analysis surfaces reconcile with the relationship samples.
    assert summary["relationships"]["raw_elo"]["sample_stage_id"] == "elo_analysis_rows_max_dedupe"
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    # Both samples gained a net 6 players from the repointing: 7 newly resolved to an elo-backed
    # player and gpt-5.4-medium was repointed to gpt-5.4-high.
    assert summary["coverage"]["elo_analysis_rows_max_dedupe"] == 59
    assert summary["coverage"]["metric_analysis_rows_max_dedupe"] == 62
    assert "elo" not in summary["prediction"]["features"]
    # Key finding: nonsense detection is only weakly tied to chess Elo and well below ECI/ARC.
    assert 0.20 < summary["relationships"]["raw_elo"]["pearson_r"] < 0.40
    assert int(coverage["survived_elo_dedupe"].sum()) == summary["analysis_surfaces"]["elo_analysis"]["count"]


def test_delegate_52_mapping_covers_all_rows_and_reports_depth_profile():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = delegate_52.normalize_source()
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/delegate_52.csv")
    merged = apply_mapping(normalized, mapping)

    assert len(normalized) == 19
    assert len(merged) == len(normalized)
    assert merged["mapping_status"].notna().all()
    # The full RS curve is preserved, anchored on the long-horizon endpoint.
    assert normalized["rs_at_20"].max() == 80.9
    assert normalized["rs_at_20"].min() == 10.0

    summary, _, coverage, _ = delegate_52.run_analysis(
        inventory,
        mapping,
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/delegate_52.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )
    json.dumps(summary, allow_nan=False)

    assert summary["target_score_column"] == "rs_at_20"
    assert summary["inputs"]["source"]["numeric_parse_rates"]["rs_at_20"] == 1.0
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/delegate_52.csv"
    # Conservative reviewed mapping: 13 variant-compatible + 2 alias matched, 2 unmatched, 2 ambiguous.
    status_counts = summary["mapping"]["mapping_file_status_counts"]
    assert status_counts["variant-compatible"] == 13
    assert status_counts["alias"] == 2
    assert status_counts["unmatched"] == 2
    assert status_counts["ambiguous"] == 2
    # claude-opus-4-6 has no Elo, so 15 metric rows but 14 in the Elo sample.
    assert summary["coverage"]["metric_analysis_rows_max_dedupe"] == 15
    assert summary["coverage"]["elo_analysis_rows_max_dedupe"] == 14
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    # Multi-factor headline: Elo correlation reported at every interaction depth plus derived measures.
    depth = summary["relationships"]["raw_elo"]["rs_depth_vs_elo"]
    factors = {entry["factor"] for entry in depth}
    assert {f"rs_at_{k}" for k in range(2, 21, 2)} <= factors
    assert {"rs_mean", "rs_degradation"} <= factors
    # Higher-Elo models degrade less over long horizons (slope correlates negatively with Elo).
    degradation = next(entry for entry in depth if entry["factor"] == "rs_degradation")
    assert degradation["pearson_r"] < 0
    # Per-depth release-controlled correlations are emitted in the sensitivity block.
    assert len(summary["sensitivity"]["rs_depth_release_controlled"]) == len(depth)


def test_vals_index_snapshot_matches_published_composite_formula():
    """The v1.2 index is a published weighted composite of the five component columns.

    Recomputing it from those columns is the one check on this snapshot that does not go through the
    anchor column itself, so it catches a mis-decoded Astro props blob (see evals/vals-index/SOURCE.md)
    rather than merely restating it.
    """
    normalized, contract = vals_index.normalize_source()

    assert len(normalized) == 40
    coding = (
        0.25 * normalized["swebench"] + 0.25 * normalized["terminal_bench_2_1"] + 0.5 * normalized["vibe_code_bench"]
    )
    finance = normalized[["corp_fin_v2", "finance_agent"]].mean(axis=1)
    recomputed = (2.0 * finance + 1.4 * coding) / 3.4
    # Published anchors are rounded to three decimals, so agreement is exact to within that rounding.
    assert (recomputed - normalized["vals_index"]).abs().max() < 0.001

    # Scores arrive already on a 0-100 scale; nothing rescales them.
    assert normalized["vals_index"].max() == pytest.approx(75.145)
    assert normalized["vals_index"].min() == pytest.approx(30.041)
    assert contract["numeric_parse_rates"]["vals_index"] == 1.0

    # Identity is the upstream provider/slug model_key; the payload publishes no display name.
    assert normalized["eval_model_label"].iloc[0] == "anthropic/claude-fable-5"
    assert normalized["eval_model_label"].is_unique
    # Effort is stated in reasoning_effort for most vendors and compute_effort for Anthropic.
    assert normalized["stated_effort"].notna().sum() == 24
    anthropic_opus_4_8 = normalized.loc[normalized["eval_model_label"] == "anthropic/claude-opus-4-8"].iloc[0]
    assert pd.isna(anthropic_opus_4_8["reasoning_effort"])
    assert anthropic_opus_4_8["stated_effort"] == "max"


def test_vals_index_mapping_covers_all_rows_and_reports_task_profile():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = vals_index.normalize_source()
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/vals_index.csv")
    merged = apply_mapping(normalized, mapping)

    assert len(merged) == len(normalized) == 40
    assert merged["mapping_status"].notna().all()

    summary, _, coverage, _ = vals_index.run_analysis(
        inventory,
        mapping,
        verification={
            "runner_command": "pytest",
            "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
            "mapping_file": "data/cross-ref/mappings/vals_index.csv",
            "verification_commands": ["pytest tests/test_cross_ref.py"],
            "test_status": "running-under-pytest",
            "mapping_qa_status": "pending",
            "run_qa_status": "pending",
            "known_limitations": [],
        },
    )
    json.dumps(summary, allow_nan=False)

    assert summary["target_score_column"] == "vals_index"
    assert summary["mapping_source_of_truth"]["mapping_file"] == "data/cross-ref/mappings/vals_index.csv"
    # Reviewed mapping: 4 accepted + 1 alias + 12 variant-compatible matched, 23 with no counterpart.
    status_counts = summary["mapping"]["mapping_file_status_counts"]
    assert status_counts["accepted"] == 4
    assert status_counts["alias"] == 1
    assert status_counts["variant-compatible"] == 12
    assert status_counts["unmatched"] == 23
    # Every matched row resolves to an Elo-backed player, so the funnel is lossless after mapping.
    assert summary["coverage"]["accepted_mapping_rows"] == 17
    assert summary["coverage"]["metric_analysis_rows_max_dedupe"] == 17
    assert summary["coverage"]["elo_analysis_rows_max_dedupe"] == 17
    assert summary["coverage"]["duplicate_mapping_keys"] == 0
    assert summary["coverage"]["external_rows_without_llm_chess_match"] == 23
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    # Stated-effort coverage is surfaced because the mapping's clause choice depends on it.
    assert summary["coverage"]["stated_effort_counts"]["unstated"] == 16

    # Multi-factor headline: the composite is reported alongside each component task and both buckets,
    # so no single sub-benchmark silently drives the conclusion.
    tasks = summary["relationships"]["raw_elo"]["vals_task_vs_elo"]
    factors = {entry["factor"] for entry in tasks}
    assert {"corp_fin_v2", "finance_agent", "swebench", "terminal_bench_2_1", "vibe_code_bench"} <= factors
    assert {"finance_bucket", "coding_bucket"} <= factors
    assert len(summary["sensitivity"]["vals_task_release_controlled"]) == len(tasks)

    # Every row the mapping leaves unmatched stays visible in coverage rather than being dropped.
    assert len(coverage) == 40
    assert int(coverage["joined_llm_chess_metric_row"].sum()) == 17


def test_vals_index_mapping_records_the_reasoning_clause_on_every_resolved_row():
    """Vals states an effort tier more often than the other evals, but above LLM Chess's ceiling.

    Its tier vocabulary includes max and xhigh, which LLM Chess has for no model, so better evidence
    routes rows into clause 3 rather than clause 2. Each resolved row must name the clause it used.
    """
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/vals_index.csv")
    matched = mapping[mapping["mapping_status"].isin(sorted(ACCEPTED_MAPPING_STATUSES))]

    assert len(matched) == 17
    assert matched["reasoning_rule_applied"].notna().all()
    assert matched["reasoning_rule_applied"].value_counts().to_dict() == {
        "nearest-tier": 10,
        "effort_to_effort": 5,
        "assume-highest": 2,
    }
    # No matched row may point at a max/xhigh chess tier, because none exists.
    assert not matched["llm_chess_player"].str.contains("xhigh|-max", regex=True).any()

    by_label = matched.set_index("eval_model_label")
    # Clause 3 substitutes upward when the stated tier is above everything LLM Chess offers.
    sol = by_label.loc["openai/gpt-5.6-sol"]
    assert sol["eval_reasoning_effort"] == "max"
    assert sol["llm_chess_player"] == "gpt-5.6-sol-2026-07-09-high"
    assert sol["reasoning_rule_applied"] == "nearest-tier"
    # Forced substitution against the stated direction must record the conflict, not imply agreement.
    flash = by_label.loc["google/gemini-3.5-flash"]
    assert flash["eval_reasoning_effort"] == "high"
    assert flash["llm_chess_player"] == "gemini-3.5-flash-medium"
    assert "Forced substitution" in flash["open_questions"]
    # reasoning=True picks the thinking run over the non-thinking sibling.
    sonnet = by_label.loc["anthropic/claude-sonnet-4-6"]
    assert sonnet["llm_chess_player"] == "claude-sonnet-4-6_thinking-high"

    # Same-family-different-version rows stay unmatched with a reason, and never borrow a sibling.
    unmatched = mapping[mapping["mapping_status"] == "unmatched"].set_index("eval_model_label")
    for label in ["kimi/kimi-k3", "zai/glm-5.2", "alibaba/qwen3.7-max", "minimax/MiniMax-M3"]:
        assert label in unmatched.index
        assert pd.isna(unmatched.loc[label, "llm_chess_player"])
        assert unmatched.loc[label, "rationale"].strip()
    assert "claude-fable-5" in " ".join(unmatched.index)


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
    assert summary["analysis_surfaces"]["metric_analysis"]["count"] == summary["coverage"]["metric_analysis_rows_max_dedupe"]
    assert summary["analysis_surfaces"]["elo_analysis"]["count"] == summary["coverage"]["elo_analysis_rows_max_dedupe"]
    assert summary["relationships"]["raw_elo"]["sample_stage_id"] == "elo_analysis_rows_max_dedupe"
    assert summary["relationships"]["raw_elo"]["n"] == summary["analysis_surfaces"]["elo_analysis"]["count"]
    assert summary["prediction"]["sample_stage_id"] == "metric_analysis_rows_max_dedupe"
    # Two distinct counts; see the arc_agi_2 test above. The CV scores belong to "n", not "sample_n".
    assert summary["prediction"]["sample_n"] == summary["analysis_surfaces"]["metric_analysis"]["count"]
    assert summary["prediction"]["n"] <= summary["prediction"]["sample_n"]
    assert "elo" not in summary["prediction"]["features"]
    assert summary["coverage"]["external_rows_without_llm_chess_elo_join"] == (
        summary["coverage"]["numeric_score_rows"] - summary["coverage"]["rows_joined_to_llm_chess_elo"]
    )


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
        arc_coverage["eval_row_id"] == "arc_agi_2:0071:gemini_3_flash_preview_low"
    ].iloc[0]
    assert not dedupe_loser["survived_metric_dedupe"]
    assert dedupe_loser["metric_drop_side"] == "dedupe"
    assert dedupe_loser["metric_dedupe_kept_eval_row_id"] == "arc_agi_2:0073:gemini_3_flash_preview_high"
    assert dedupe_loser["first_failed_stage"] == "metric_analysis_rows_max_dedupe"


# --------------------------------------------------------------------------------------------------
# min_game_date stamp + mistake-stats clean_only mode
# --------------------------------------------------------------------------------------------------

_PYTEST_VERIFICATION = {
    "runner_command": "pytest",
    "inventory_path": "data/cross-ref/model-identity/llm_chess_models.csv",
    "mapping_file": "data/cross-ref/mappings/bullshit_bench.csv",
    "verification_commands": ["pytest tests/test_cross_ref.py"],
    "test_status": "running-under-pytest",
    "mapping_qa_status": "pending",
    "run_qa_status": "pending",
    "known_limitations": [],
}


def test_earliest_log_date_helper_parses_and_handles_empty():
    import sys as _sys

    if str(REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(REPO_ROOT))
    from data.get_refined_csv import _earliest_log_date

    class _Log:
        def __init__(self, ts):
            self.time_started = ts

    logs = [_Log("2025.11.27_12:31"), _Log("2025.03.15_23:59"), _Log("2026.01.02_00:00")]
    assert _earliest_log_date(logs) == "2025-03-15"
    assert _earliest_log_date([_Log(""), _Log(None), _Log("garbage")]) == ""
    assert _earliest_log_date([]) == ""


def test_elo_refined_carries_min_game_date_stamp():
    elo, _, _ = load_llm_chess_inputs(REPO_ROOT)

    assert "min_game_date" in elo.columns
    stamped = elo["min_game_date"].astype(str).str.strip()
    populated = stamped[(stamped != "") & (stamped != "nan")]
    # Every Player should be stamped, and dates use ISO YYYY-MM-DD.
    assert len(populated) == len(elo)
    assert populated.str.match(r"^\d{4}-\d{2}-\d{2}$").all()

    mask = clean_mistake_stats_mask(elo)
    # The split is real in both directions on the current data.
    assert mask.sum() > 0
    assert (~mask).sum() > 0
    # A known historical model predates the cutoff and must be flagged not-clean.
    old = elo.loc[elo["Player"] == "claude-3-5-sonnet"]
    assert not old.empty
    assert old["min_game_date"].iloc[0] < MISTAKE_STATS_TRUSTED_AFTER
    assert not bool(mask.loc[old.index[0]])


def test_clean_mistake_stats_mask_uses_single_cutoff_constant():
    assert MISTAKE_STATS_TRUSTED_AFTER == "2025-03-16"
    df = pd.DataFrame(
        {
            "Player": ["a", "b", "c", "d"],
            "min_game_date": ["2025-03-16", "2025-03-15", "2026-01-01", ""],
        }
    )
    mask = clean_mistake_stats_mask(df)
    assert list(mask) == [True, False, True, False]  # on/after cutoff kept; before/blank dropped


def test_filter_multifactor_allows_repaired_metrics_only_when_requested():
    candidates = ["player_wins_percent", "wrong_moves_per_1000moves", "mistakes_per_1000moves"]

    filtered_default, excluded_default = filter_multifactor_candidate_metrics(candidates)
    assert "wrong_moves_per_1000moves" not in filtered_default
    assert "mistakes_per_1000moves" in excluded_default

    filtered_clean, excluded_clean = filter_multifactor_candidate_metrics(
        candidates, allowed_repaired=set(REPAIRABLE_MISTAKE_METRICS)
    )
    assert "wrong_moves_per_1000moves" in filtered_clean
    assert "mistakes_per_1000moves" in filtered_clean
    assert excluded_clean == []


def _run_bullshit(mistake_stats):
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    mapping = load_mapping_file(REPO_ROOT / "data/cross-ref/mappings/bullshit_bench.csv")
    summary, _, coverage, _ = bullshit_bench.run_analysis(
        inventory, mapping, verification=dict(_PYTEST_VERIFICATION), mistake_stats=mistake_stats
    )
    return summary, coverage, elo


def test_default_mode_excludes_mistake_metrics_and_keeps_full_sample():
    summary, _, _ = _run_bullshit("excluded")

    assert summary["mistake_stats"]["mode"] == "excluded"
    assert summary["mistake_stats"]["repaired_metrics_enabled"] == []
    assert summary["mistake_stats"]["pre_cutoff_players_dropped"] == []
    metric_names = {m["name"] for m in summary["relationships"]["selected_metrics"]}
    assert not (metric_names & set(REPAIRABLE_MISTAKE_METRICS))


def test_clean_only_mode_drops_pre_cutoff_models_and_enables_mistake_metrics():
    excluded_summary, _, _ = _run_bullshit("excluded")
    summary, coverage, elo = _run_bullshit("clean_only")

    ms = summary["mistake_stats"]
    assert ms["mode"] == "clean_only"
    assert set(ms["repaired_metrics_enabled"]) == set(REPAIRABLE_MISTAKE_METRICS)
    assert ms["pre_cutoff_player_count"] > 0
    assert ms["pre_cutoff_players_dropped"]  # non-empty list of dropped models

    # The repaired metrics now appear in the relationship surface.
    metric_names = {m["name"] for m in summary["relationships"]["selected_metrics"]}
    assert set(REPAIRABLE_MISTAKE_METRICS) <= metric_names
    assert summary["prediction"]["excluded_candidate_metrics"] == []

    # Clean mode never grows the sample, and every analyzed player is stamped clean.
    clean_n = summary["coverage"]["elo_analysis_rows_max_dedupe"]
    assert clean_n <= excluded_summary["coverage"]["elo_analysis_rows_max_dedupe"]
    date_by_player = dict(zip(elo["Player"], elo["min_game_date"].astype(str)))
    analyzed = coverage.loc[coverage["survived_elo_dedupe"] == True, "llm_chess_player"]
    assert not analyzed.empty
    for player in analyzed:
        assert date_by_player.get(player, "") >= MISTAKE_STATS_TRUSTED_AFTER


def test_clean_only_mode_cannot_be_published():
    parser = run_cross_ref.build_parser()
    args = parser.parse_args(["bullshit_bench", "--mistake-stats", "clean_only", "--publish"])
    with pytest.raises(ValueError, match="research-only"):
        run_cross_ref.run_eval(args)