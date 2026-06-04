from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

SUMMARY_IGNORED_PATHS = [
    "$.verification",
    "$.inputs.source.file",
    "$.inputs.source_file_paths",
    "$.mapping_source_of_truth.mapping_file",
    "$.mapping.mapping_file_path",
]
MAX_JSON_CHANGES = 200
MAX_CSV_ROWS = 100


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_path(path: str, key: str) -> str:
    return f"{path}.{key}" if key.isidentifier() else f'{path}["{key}"]'


def _normalize_summary_for_diff(summary: dict[str, object]) -> dict[str, object]:
    normalized = deepcopy(summary)
    normalized.pop("verification", None)

    inputs = normalized.get("inputs")
    if isinstance(inputs, dict):
        source = inputs.get("source")
        if isinstance(source, dict) and "file" in source:
            source["file"] = "__SOURCE_FILE__"
        if isinstance(inputs.get("source_file_paths"), list):
            inputs["source_file_paths"] = ["__SOURCE_FILE__" for _ in inputs["source_file_paths"]]

    mapping_source = normalized.get("mapping_source_of_truth")
    if isinstance(mapping_source, dict) and "mapping_file" in mapping_source:
        mapping_source["mapping_file"] = "__MAPPING_FILE__"

    mapping = normalized.get("mapping")
    if isinstance(mapping, dict) and "mapping_file_path" in mapping:
        mapping["mapping_file_path"] = "__MAPPING_FILE__"

    return normalized


def _diff_json_values(
    baseline: object,
    candidate: object,
    *,
    path: str,
    changes: list[dict[str, object]],
) -> None:
    if baseline == candidate:
        return

    if isinstance(baseline, dict) and isinstance(candidate, dict):
        for key in sorted(set(baseline) | set(candidate)):
            child_path = _json_path(path, key)
            if key not in baseline:
                changes.append(
                    {
                        "path": child_path,
                        "change": "added",
                        "baseline": None,
                        "candidate": candidate[key],
                    }
                )
                continue
            if key not in candidate:
                changes.append(
                    {
                        "path": child_path,
                        "change": "removed",
                        "baseline": baseline[key],
                        "candidate": None,
                    }
                )
                continue
            _diff_json_values(baseline[key], candidate[key], path=child_path, changes=changes)
        return

    if isinstance(baseline, list) and isinstance(candidate, list):
        max_len = max(len(baseline), len(candidate))
        for index in range(max_len):
            child_path = f"{path}[{index}]"
            if index >= len(baseline):
                changes.append(
                    {
                        "path": child_path,
                        "change": "added",
                        "baseline": None,
                        "candidate": candidate[index],
                    }
                )
                continue
            if index >= len(candidate):
                changes.append(
                    {
                        "path": child_path,
                        "change": "removed",
                        "baseline": baseline[index],
                        "candidate": None,
                    }
                )
                continue
            _diff_json_values(baseline[index], candidate[index], path=child_path, changes=changes)
        return

    changes.append(
        {
            "path": path,
            "change": "changed",
            "baseline": baseline,
            "candidate": candidate,
        }
    )


def compare_summary_json_files(baseline_path: Path, candidate_path: Path) -> dict[str, object]:
    baseline_raw = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_raw = json.loads(candidate_path.read_text(encoding="utf-8"))
    baseline = _normalize_summary_for_diff(baseline_raw)
    candidate = _normalize_summary_for_diff(candidate_raw)

    all_changes: list[dict[str, object]] = []
    _diff_json_values(baseline, candidate, path="$", changes=all_changes)
    changes = all_changes[:MAX_JSON_CHANGES]

    return {
        "artifact_id": "summary_json",
        "artifact_type": "json",
        "compare_mode": "normalized_summary_json",
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "changed": bool(all_changes),
        "change_count": len(all_changes),
        "changes": changes,
        "truncated": len(all_changes) > len(changes),
        "ignored_paths": SUMMARY_IGNORED_PATHS,
    }


def _normalize_cell(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _row_to_dict(row: pd.Series) -> dict[str, object]:
    return {column: _normalize_cell(value) for column, value in row.items()}


def _duplicate_key_counts(df: pd.DataFrame, key_column: str) -> list[dict[str, object]]:
    duplicate_counts = (
        df.loc[df[key_column].duplicated(keep=False), key_column]
        .value_counts(dropna=False)
        .sort_index()
    )
    duplicates: list[dict[str, object]] = []
    for key, count in duplicate_counts.items():
        duplicates.append({"key": _normalize_cell(key), "count": int(count)})
    return duplicates


def compare_csv_files(
    baseline_path: Path,
    candidate_path: Path,
    *,
    artifact_id: str,
    key_column: str | None,
) -> dict[str, object]:
    baseline_df = pd.read_csv(baseline_path)
    candidate_df = pd.read_csv(candidate_path)
    columns_changed = list(baseline_df.columns) != list(candidate_df.columns)
    usable_key = key_column if key_column and key_column in baseline_df.columns and key_column in candidate_df.columns else None

    if usable_key is None:
        changed = columns_changed or not baseline_df.equals(candidate_df)
        return {
            "artifact_id": artifact_id,
            "artifact_type": "csv",
            "compare_mode": "raw_csv",
            "baseline_path": str(baseline_path),
            "candidate_path": str(candidate_path),
            "changed": changed,
            "row_count": {"baseline": int(len(baseline_df)), "candidate": int(len(candidate_df))},
            "columns": {"baseline": list(baseline_df.columns), "candidate": list(candidate_df.columns)},
            "key_column": None,
            "added_row_count": 0,
            "removed_row_count": 0,
            "changed_row_count": int(changed),
            "added_rows": [],
            "removed_rows": [],
            "changed_rows": [],
            "truncated": False,
        }

    baseline_duplicates = _duplicate_key_counts(baseline_df, usable_key)
    candidate_duplicates = _duplicate_key_counts(candidate_df, usable_key)
    if baseline_duplicates or candidate_duplicates:
        return {
            "artifact_id": artifact_id,
            "artifact_type": "csv",
            "compare_mode": "keyed_csv",
            "baseline_path": str(baseline_path),
            "candidate_path": str(candidate_path),
            "changed": True,
            "row_count": {"baseline": int(len(baseline_df)), "candidate": int(len(candidate_df))},
            "columns": {"baseline": list(baseline_df.columns), "candidate": list(candidate_df.columns)},
            "key_column": usable_key,
            "added_row_count": 0,
            "removed_row_count": 0,
            "changed_row_count": 0,
            "added_rows": [],
            "removed_rows": [],
            "changed_rows": [],
            "truncated": False,
            "validation_error": {
                "code": "duplicate_key",
                "message": "Duplicate key values prevent a keyed CSV diff for this artifact.",
                "key_column": usable_key,
                "baseline_duplicates": baseline_duplicates,
                "candidate_duplicates": candidate_duplicates,
            },
        }

    baseline_keyed = baseline_df.sort_values(usable_key).set_index(usable_key, drop=False)
    candidate_keyed = candidate_df.sort_values(usable_key).set_index(usable_key, drop=False)
    baseline_keys = set(baseline_keyed.index)
    candidate_keys = set(candidate_keyed.index)
    added_rows = sorted(candidate_keys - baseline_keys)
    removed_rows = sorted(baseline_keys - candidate_keys)

    all_changed_rows: list[dict[str, object]] = []
    for row_key in sorted(baseline_keys & candidate_keys):
        baseline_row = _row_to_dict(baseline_keyed.loc[row_key])
        candidate_row = _row_to_dict(candidate_keyed.loc[row_key])
        changed_columns = [
            column
            for column in sorted(set(baseline_row) | set(candidate_row))
            if baseline_row.get(column) != candidate_row.get(column)
        ]
        if changed_columns:
            all_changed_rows.append({"key": row_key, "changed_columns": changed_columns})

    changed = columns_changed or bool(added_rows or removed_rows or all_changed_rows)
    changed_rows = all_changed_rows[:MAX_CSV_ROWS]
    return {
        "artifact_id": artifact_id,
        "artifact_type": "csv",
        "compare_mode": "keyed_csv",
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "changed": changed,
        "row_count": {"baseline": int(len(baseline_df)), "candidate": int(len(candidate_df))},
        "columns": {"baseline": list(baseline_df.columns), "candidate": list(candidate_df.columns)},
        "key_column": usable_key,
        "added_row_count": len(added_rows),
        "removed_row_count": len(removed_rows),
        "changed_row_count": len(all_changed_rows),
        "added_rows": added_rows[:MAX_CSV_ROWS],
        "removed_rows": removed_rows[:MAX_CSV_ROWS],
        "changed_rows": changed_rows,
        "truncated": len(added_rows) > len(added_rows[:MAX_CSV_ROWS])
        or len(removed_rows) > len(removed_rows[:MAX_CSV_ROWS])
        or len(all_changed_rows) > len(changed_rows),
    }


def build_eval_diff_report(
    target: str,
    *,
    baseline_artifacts: dict[str, Path],
    candidate_artifacts: dict[str, Path],
) -> dict[str, object]:
    artifact_diffs = [
        compare_summary_json_files(
            baseline_artifacts["summary_json"],
            candidate_artifacts["summary_json"],
        ),
        compare_csv_files(
            baseline_artifacts["coverage_csv"],
            candidate_artifacts["coverage_csv"],
            artifact_id="coverage_csv",
            key_column="eval_row_id",
        ),
    ]
    has_diff = any(bool(entry["changed"]) for entry in artifact_diffs)
    has_validation_error = any("validation_error" in entry for entry in artifact_diffs)
    return {
        "artifact_kind": "cross_ref_rerun_diff",
        "target": target,
        "generated_at_utc": _timestamp_utc(),
        "baseline_artifacts": {key: str(path) for key, path in baseline_artifacts.items()},
        "candidate_artifacts": {key: str(path) for key, path in candidate_artifacts.items()},
        "summary_json_compare_ignored_paths": SUMMARY_IGNORED_PATHS,
        "has_diff": has_diff,
        "has_validation_error": has_validation_error,
        "artifact_diffs": artifact_diffs,
        "message": (
            "Diff validation errors detected while comparing baseline and rerun candidate artifacts."
            if has_validation_error
            else (
                "Differences detected between baseline and rerun candidate artifacts."
                if has_diff
                else "No differences detected between baseline and rerun candidate artifacts."
            )
        ),
    }


def _stringify(value: object, limit: int = 120) -> str:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True) if isinstance(value, (dict, list)) else repr(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def render_artifact_diff_markdown(diff_report: dict[str, object]) -> str:
    artifact_diffs = diff_report.get("artifact_diffs", [])
    lines = [
        f"# Rerun Diff: {diff_report.get('target', 'unknown')}",
        "",
        diff_report.get("message", ""),
        "",
        "Summary JSON comparison ignores runtime-only path and verification metadata:",
    ]
    for ignored_path in diff_report.get("summary_json_compare_ignored_paths", []):
        lines.append(f"- `{ignored_path}`")

    for artifact in artifact_diffs:
        lines.extend(
            [
                "",
                f"## {artifact['artifact_id']}",
                "",
                f"Baseline: `{artifact['baseline_path']}`",
                f"Candidate: `{artifact['candidate_path']}`",
                "",
            ]
        )
        if not artifact.get("changed"):
            lines.append("No differences detected.")
            continue

        validation_error = artifact.get("validation_error")
        if isinstance(validation_error, dict):
            lines.append(validation_error.get("message", "Validation error."))
            lines.append("")
            lines.append(f"Key column: `{validation_error.get('key_column')}`")
            baseline_duplicates = validation_error.get("baseline_duplicates", [])
            candidate_duplicates = validation_error.get("candidate_duplicates", [])
            if baseline_duplicates:
                lines.append("")
                lines.append("Baseline duplicate keys:")
                for row in baseline_duplicates:
                    lines.append(f"- `{row.get('key')}` x {row.get('count')}")
            if candidate_duplicates:
                lines.append("")
                lines.append("Candidate duplicate keys:")
                for row in candidate_duplicates:
                    lines.append(f"- `{row.get('key')}` x {row.get('count')}")
            continue

        if artifact.get("artifact_type") == "json":
            lines.append(f"Changed paths: {artifact['change_count']}")
            lines.append("")
            lines.append("| Path | Baseline | Candidate |")
            lines.append("| --- | --- | --- |")
            for change in artifact.get("changes", []):
                lines.append(
                    f"| `{change['path']}` | `{_stringify(change.get('baseline'))}` | `{_stringify(change.get('candidate'))}` |"
                )
            if artifact.get("truncated"):
                lines.append("")
                lines.append("Additional JSON changes omitted from this markdown view.")
            continue

        lines.append(f"Changed rows: {artifact['changed_row_count']}")
        lines.append(f"Added rows: {artifact['added_row_count']}")
        lines.append(f"Removed rows: {artifact['removed_row_count']}")
        lines.append("")
        if artifact.get("changed_rows"):
            lines.append("| Row key | Changed columns |")
            lines.append("| --- | --- |")
            for row in artifact["changed_rows"]:
                lines.append(f"| `{row['key']}` | `{', '.join(row['changed_columns'])}` |")
        if artifact.get("added_rows"):
            lines.append("")
            lines.append(f"Added row keys: `{', '.join(str(row) for row in artifact['added_rows'])}`")
        if artifact.get("removed_rows"):
            lines.append("")
            lines.append(f"Removed row keys: `{', '.join(str(row) for row in artifact['removed_rows'])}`")
        if artifact.get("truncated"):
            lines.append("")
            lines.append("Additional CSV row changes omitted from this markdown view.")

    lines.append("")
    return "\n".join(lines)