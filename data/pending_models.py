"""Print a table of models found in game logs but not yet published to elo_refined.csv.

Run from the repo root:

    uv run python data/pending_models.py

Columns (headers wrap across two lines):

    model | vs rand | vs dragon | wins vs rand | wins vs dragon |
          vs random errors | vs dragon errors | last game date | has error | has metadata

- ``wins vs rand`` / ``wins vs dragon``: absolute count of games where
  ``winner in ("Player_Black", "NoN_Synthesizer")`` in the respective log tree.
- ``last game date``: ``YYYY.MM.DD`` prefix of the latest ``time_started`` across both
  trees (``-`` when the model has no games).
- ``has error``: ``yes`` iff ``vs_random_errors + vs_dragon_errors > 0``.

Side effect: for every run folder belonging to a *pending* model that contains at least
one game whose JSON has ``"reason": "ERROR OCCURED"``, writes one ``_errors.md`` in that
folder listing those games with ~20 lines of context pulled from the sibling
``output.txt``. Stale ``_errors.md`` files (including those for no-longer-pending
models) are deleted at the start of every run so the tree only ever shows reports for
the current pending set.

Performance: each log root is walked exactly once and every game JSON is parsed once.
The resulting dict is reused for both the table aggregation and the error reports,
eliminating the triple walk the earlier implementation paid for.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.get_refined_csv import (  # noqa: E402
    ALIASES,
    FILTER_OUT_MODELS,
    FILTER_OUT_PATH_KEYWORDS,
    MODEL_OVERRIDES,
    _model_label_from_run_json,
    _white_opponent_from_run_dir,
)
from llm_chess import TerminationReason  # noqa: E402

RAND_DIR = ROOT / "_logs" / "rand_vs_llm"
ENGINE_DIR = ROOT / "_logs" / "engine_vs_llm"
ELO_REFINED_CSV = ROOT / "data" / "elo_refined.csv"
MODELS_METADATA_CSV = ROOT / "data" / "models_metadata.csv"

ERROR_REASON = "ERROR OCCURED"
CONTEXT_LINES = 20
REPORT_FILENAME = "_errors.md"
WINS_REGEX = re.compile(r"^.+ wins due to .+\.$")

# Same set load_game_logs treats as "interrupted" via GameLog.is_interrupted.
INTERRUPTED_REASONS = {
    TerminationReason.ERROR.value,
    TerminationReason.UNKNOWN_ISSUE.value,
    TerminationReason.MAX_TURNS.value,
    TerminationReason.TOO_MANY_WRONG_ACTIONS.value,
}

# Games only count as "errors" when the interrupt left no declared winner. Runs that
# still produced a winner (e.g. MAX_TURNS with an already-decisive position) are
# considered resolved and excluded from both the error counters and `_errors.md`.
UNRESOLVED_WINNER = "NONE"

LLM_WIN_WINNERS = ("Player_Black", "NoN_Synthesizer")


def _is_unresolved_error(data: dict) -> bool:
    return data.get("reason") in INTERRUPTED_REASONS and data.get("winner") == UNRESOLVED_WINNER


@dataclass
class ModelStats:
    games_rand: int = 0
    games_dragon: int = 0
    errors_rand: int = 0
    errors_dragon: int = 0
    wins_rand: int = 0
    wins_dragon: int = 0
    last_time: str = ""  # raw "YYYY.MM.DD_HH:MM" from time_started


def _read_column(path: Path, column: str) -> set[str]:
    with path.open("r", encoding="utf-8") as f:
        return {row[column].strip() for row in csv.DictReader(f) if row.get(column, "").strip()}


def _find_wins_lines(output_txt: Path) -> list[int]:
    lines: list[int] = []
    with output_txt.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            if WINS_REGEX.match(line.rstrip("\n")):
                lines.append(lineno)
    return lines


def _read_window(output_txt: Path, end_line: int, context: int) -> tuple[int, list[str]]:
    start = max(1, end_line - context)
    out: list[str] = []
    with output_txt.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            if lineno < start:
                continue
            if lineno > end_line:
                break
            out.append(line.rstrip("\n"))
    return start, out


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _walk_game_jsons(root: Path):
    """Yield (folder, filename, parsed_json) for every per-game JSON under root."""
    for dirpath, _, filenames in os.walk(root):
        folder = Path(dirpath)
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            if fn == "_run.json" or fn.endswith("_aggregate_results.json"):
                continue
            p = folder / fn
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            yield folder, fn, data


def _folder_canonical_model(folder: Path, sample_data: dict) -> str | None:
    """Resolve a folder's canonical model label using the same rules as `load_game_logs`.

    Priority: _run.json -> sample game JSON -> None. MODEL_OVERRIDES (matched by folder
    path suffix) and ALIASES are applied last.
    """
    label = _model_label_from_run_json(str(folder))
    if not label:
        label = (sample_data.get("player_black") or {}).get("model")
    if not label:
        return None

    if MODEL_OVERRIDES:
        folder_str = str(folder)
        key = next((k for k in MODEL_OVERRIDES if folder_str.endswith(k)), None)
        if key:
            label = MODEL_OVERRIDES[key]

    return ALIASES.get(label, label)


def _scan_tree(root: Path, label: str) -> tuple[dict[Path, list[tuple[str, dict]]], int]:
    """Walk ``root`` once, parsing each game JSON exactly once.

    Returns ``(folder_logs, files_seen)`` with progress updates on stderr every 100
    files and a final summary line.
    """
    folder_logs: dict[Path, list[tuple[str, dict]]] = defaultdict(list)
    seen = 0
    if not root.exists():
        print(f"scanned  {label}: root {root} missing", file=sys.stderr)
        return folder_logs, 0

    for folder, fn, data in _walk_game_jsons(root):
        seen += 1
        folder_logs[folder].append((fn, data))
        if seen % 100 == 0:
            print(
                f"\rscanning {label}: {seen} files, {len(folder_logs)} folders...",
                end="",
                file=sys.stderr,
                flush=True,
            )
    print(
        f"\rscanned  {label}: {seen} files, {len(folder_logs)} folders   ",
        file=sys.stderr,
    )
    return folder_logs, seen


def _folder_path_filtered(folder: Path) -> bool:
    folder_lower = str(folder).lower()
    return any(kw.lower() in folder_lower for kw in FILTER_OUT_PATH_KEYWORDS)


def _aggregate_stats(
    folder_logs_rand: dict[Path, list[tuple[str, dict]]],
    folder_logs_dragon: dict[Path, list[tuple[str, dict]]],
) -> tuple[
    dict[str, ModelStats],
    dict[Path, list[tuple[str, dict]]],
    dict[Path, list[tuple[str, dict]]],
]:
    """Apply the same per-folder filters as ``load_game_logs`` and tally model stats.

    Returns ``(stats, kept_rand, kept_dragon)``. Kept dicts preserve the original
    ``(filename, json)`` tuples so callers can feed them straight to
    ``_write_folder_error_report`` without re-parsing anything. ``_folder_canonical_model``
    is invoked once per folder.
    """
    stats: dict[str, ModelStats] = defaultdict(ModelStats)
    kept_rand: dict[Path, list[tuple[str, dict]]] = {}
    kept_dragon: dict[Path, list[tuple[str, dict]]] = {}

    for folder, logs in folder_logs_rand.items():
        if _folder_path_filtered(folder):
            continue
        model = _folder_canonical_model(folder, logs[0][1])
        if model is None or model in FILTER_OUT_MODELS:
            continue

        games = errors = wins = 0
        last_time = ""
        for _fn, data in logs:
            pw = (data.get("player_white") or {}).get("name")
            pb = (data.get("player_black") or {}).get("name")
            if pw != "Random_Player" or pb != "Player_Black":
                continue
            games += 1
            if _is_unresolved_error(data):
                errors += 1
            if data.get("winner") in LLM_WIN_WINNERS:
                wins += 1
            t = data.get("time_started", "") or ""
            if t > last_time:
                last_time = t

        if games == 0:
            continue

        s = stats[model]
        s.games_rand += games
        s.errors_rand += errors
        s.wins_rand += wins
        if last_time > s.last_time:
            s.last_time = last_time
        kept_rand[folder] = logs

    for folder, logs in folder_logs_dragon.items():
        if _folder_path_filtered(folder):
            continue
        # Mirrors load_game_logs' "skip conservatively" behaviour for dragon runs.
        if _white_opponent_from_run_dir(str(folder)) is None:
            continue
        model = _folder_canonical_model(folder, logs[0][1])
        if model is None or model in FILTER_OUT_MODELS:
            continue

        games = errors = wins = 0
        last_time = ""
        for _fn, data in logs:
            pb = (data.get("player_black") or {}).get("name")
            if pb != "Player_Black":
                continue
            games += 1
            if _is_unresolved_error(data):
                errors += 1
            if data.get("winner") in LLM_WIN_WINNERS:
                wins += 1
            t = data.get("time_started", "") or ""
            if t > last_time:
                last_time = t

        if games == 0:
            continue

        s = stats[model]
        s.games_dragon += games
        s.errors_dragon += errors
        s.wins_dragon += wins
        if last_time > s.last_time:
            s.last_time = last_time
        kept_dragon[folder] = logs

    return stats, kept_rand, kept_dragon


def _delete_stale_reports() -> int:
    """Remove every existing `_errors.md` under the log roots so each run starts clean."""
    removed = 0
    for root in (RAND_DIR, ENGINE_DIR):
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            if REPORT_FILENAME in filenames:
                try:
                    (Path(dirpath) / REPORT_FILENAME).unlink()
                    removed += 1
                except OSError:
                    pass
    return removed


def _write_folder_error_report(
    folder: Path,
    all_logs: list[tuple[str, dict]],
    error_logs: list[tuple[str, dict]],
) -> bool:
    """Write `_errors.md` for a single folder. Returns True if anchor count matched."""
    ordered = sorted(all_logs, key=lambda pair: (pair[1].get("time_started", ""), pair[0]))
    index_of = {id(pair[1]): idx for idx, pair in enumerate(ordered)}

    output_txt = folder / "output.txt"
    anchors: list[int] | None
    mismatch = False
    if output_txt.exists():
        found = _find_wins_lines(output_txt)
        if len(found) == len(ordered):
            anchors = found
        else:
            print(
                f"WARNING: anchor count mismatch in {output_txt} "
                f"({len(found)} markers vs {len(ordered)} JSONs); snippets omitted"
            )
            anchors = None
            mismatch = True
    else:
        print(f"WARNING: missing {output_txt}; snippets omitted")
        anchors = None

    error_logs = sorted(error_logs, key=lambda pair: (pair[1].get("time_started", ""), pair[0]))

    parts: list[str] = [
        f"# Errors in `{_rel(folder)}`",
        "",
        f"{len(error_logs)} game(s) with `reason: {ERROR_REASON}`.",
        "",
    ]
    for fn, data in error_logs:
        parts.append(f"## {fn}")
        parts.append("")
        parts.append(f"- time_started: {data.get('time_started', '')}")
        parts.append(f"- moves: {data.get('number_of_moves', '')}")
        parts.append(f"- winner: {data.get('winner', '')}")
        parts.append(f"- model: {(data.get('player_black') or {}).get('model', '')}")
        parts.append("")

        if anchors is None:
            parts.append("_No usable `output.txt` — snippet omitted._")
            parts.append("")
            continue

        idx = index_of.get(id(data))
        if idx is None or idx >= len(anchors):
            parts.append("_Could not map this log to an anchor in `output.txt`._")
            parts.append("")
            continue

        anchor = anchors[idx]
        start, snippet = _read_window(output_txt, anchor, CONTEXT_LINES)
        parts.append(f"Context (`output.txt` lines {start}-{anchor}):")
        parts.append("")
        parts.append("```text")
        parts.extend(snippet)
        parts.append("```")
        parts.append("")

    (folder / REPORT_FILENAME).write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return not mismatch


def _dump_error_reports(
    pending_set: set[str],
    kept_rand: dict[Path, list[tuple[str, dict]]],
    kept_dragon: dict[Path, list[tuple[str, dict]]],
) -> tuple[int, int, int]:
    """Write one `_errors.md` per pending-model folder containing any ERROR OCCURED log.

    Returns ``(written, mismatches, skipped_non_pending)``. Iterates only the folders
    already kept by ``_aggregate_stats`` so error reports stay consistent with the table.
    """
    written = 0
    mismatches = 0
    skipped_non_pending = 0
    for folder_logs in (kept_rand, kept_dragon):
        for folder, logs in folder_logs.items():
            error_logs = [
                pair
                for pair in logs
                if pair[1].get("reason") == ERROR_REASON and pair[1].get("winner") == UNRESOLVED_WINNER
            ]
            if not error_logs:
                continue

            model = _folder_canonical_model(folder, logs[0][1])
            if model not in pending_set:
                skipped_non_pending += 1
                continue

            ok = _write_folder_error_report(folder, logs, error_logs)
            written += 1
            if not ok:
                mismatches += 1

    return written, mismatches, skipped_non_pending


def main() -> None:
    t0 = time.perf_counter()
    rand_folders, rand_seen = _scan_tree(RAND_DIR, "rand_vs_llm")
    dragon_folders, dragon_seen = _scan_tree(ENGINE_DIR, "engine_vs_llm")
    stats, kept_rand, kept_dragon = _aggregate_stats(rand_folders, dragon_folders)
    scanned_total = rand_seen + dragon_seen

    published = _read_column(ELO_REFINED_CSV, "Player")
    with_metadata = _read_column(MODELS_METADATA_CSV, "model")
    filtered = set(FILTER_OUT_MODELS)

    pending = sorted(set(stats.keys()) - published - filtered)

    header_lines = [
        ["model", "vs",   "vs",     "wins",    "wins",      "vs random", "vs dragon", "last",      "has",   "has"],
        ["",      "rand", "dragon", "vs rand", "vs dragon", "errors",    "errors",    "game date", "error", "metadata"],
    ]
    n_cols = len(header_lines[0])

    rows: list[list[str]] = []
    for model in pending:
        s = stats[model]
        last_date = s.last_time.split("_", 1)[0] if s.last_time else "-"
        err_total = s.errors_rand + s.errors_dragon
        rows.append([
            model,
            str(s.games_rand),
            str(s.games_dragon),
            str(s.wins_rand),
            str(s.wins_dragon),
            str(s.errors_rand),
            str(s.errors_dragon),
            last_date,
            "yes" if err_total > 0 else "no",
            "yes" if model in with_metadata else "no",
        ])

    widths: list[int] = []
    for i in range(n_cols):
        candidates = [len(header_lines[0][i]), len(header_lines[1][i])]
        candidates.extend(len(r[i]) for r in rows)
        widths.append(max(candidates))

    def fmt(cells: list[str]) -> str:
        return " | ".join(c.ljust(w) for c, w in zip(cells, widths))

    print(fmt(header_lines[0]))
    print(fmt(header_lines[1]))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))

    elapsed = time.perf_counter() - t0
    print(f"\n{len(pending)} pending model(s); scanned {scanned_total} files in {elapsed:.1f}s")

    removed = _delete_stale_reports()
    written, mismatches, skipped = _dump_error_reports(set(pending), kept_rand, kept_dragon)
    print(
        f"\nremoved {removed} stale {REPORT_FILENAME}; "
        f"wrote {written} new file(s) (skipped {skipped} non-pending folder(s), "
        f"{mismatches} had anchor mismatch)"
    )


if __name__ == "__main__":
    main()
