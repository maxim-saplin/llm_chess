import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CROSS_REF_ROOT = REPO_ROOT / "data/cross-ref"
if str(CROSS_REF_ROOT) not in sys.path:
    sys.path.insert(0, str(CROSS_REF_ROOT))

from adapters import arc_agi_2, eci  # noqa: E402
from framework.loading import load_llm_chess_inputs  # noqa: E402
from framework.mapping import apply_mapping, load_mapping_file  # noqa: E402
from framework.model_identity import build_llm_chess_inventory, inventory_summary  # noqa: E402
from framework.normalization import parse_currency, parse_day_month_year, parse_percent  # noqa: E402
import run_cross_ref  # noqa: E402


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


def test_seed_eci_mapping_preserves_source_bridge():
    elo, metadata, _ = load_llm_chess_inputs(REPO_ROOT)
    inventory = build_llm_chess_inventory(elo, metadata)
    normalized, _ = eci.normalize_source()
    seed_mapping = eci.build_seed_mapping(inventory)

    assert len(seed_mapping) == len(normalized)
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
    assert summary["analysis_surfaces"]["metric_analysis"]["count"] == 54
    assert summary["analysis_surfaces"]["elo_analysis"]["count"] == 51
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