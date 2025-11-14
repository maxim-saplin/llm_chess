#!/usr/bin/env python3
"""
Compare old and new elo_refined.csv files to identify differences.

Usage:
    python data_processing/compare_elo_refined.py

Expects:
    - data_processing/old_elo_refined.csv (renamed from previous elo_refined.csv)
    - data_processing/elo_refined.csv (newly generated)
"""

import csv
import os
import sys
from typing import Dict, List, Set, Tuple, Any


# Tolerance for floating-point comparisons
FLOAT_TOLERANCE = 1e-6
# Tolerance for percentage comparisons (0.01 = 1%)
PERCENT_TOLERANCE = 0.01


def safe_float(value: str | None, default: float = 0.0) -> float:
    """Convert a CSV value to float, handling empty strings and None."""
    if not value or value.strip() == "" or value.lower() == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: str | None, default: int = 0) -> int:
    """Convert a CSV value to int, handling empty strings and None."""
    if not value or value.strip() == "":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def load_csv(file_path: str) -> Tuple[List[Dict[str, str]], Set[str]]:
    """Load a CSV file and return rows and column names."""
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
    
    rows = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        for row in reader:
            rows.append(row)
    
    return rows, columns


def compare_values(
    old_val: str | None,
    new_val: str | None,
    field_name: str,
    is_percent: bool = False,
) -> Tuple[bool, str]:
    """
    Compare two values and return (match, message).
    
    Args:
        old_val: Value from old CSV
        new_val: Value from new CSV
        field_name: Name of the field being compared
        is_percent: If True, use percent tolerance
    
    Returns:
        (is_match, message)
    """
    old_f = safe_float(old_val)
    new_f = safe_float(new_val)
    
    # Handle empty/NaN cases
    old_empty = not old_val or old_val.strip() == "" or old_val.lower() == "nan"
    new_empty = not new_val or new_val.strip() == "" or new_val.lower() == "nan"
    
    if old_empty and new_empty:
        return True, "both empty"
    
    if old_empty or new_empty:
        return False, f"old={old_val}, new={new_val}"
    
    # Compare with appropriate tolerance
    tolerance = PERCENT_TOLERANCE if is_percent else FLOAT_TOLERANCE
    diff = abs(old_f - new_f)
    
    if diff <= tolerance:
        return True, f"match ({old_f:.6f} vs {new_f:.6f}, diff={diff:.6f})"
    else:
        return False, f"old={old_f:.6f}, new={new_f:.6f}, diff={diff:.6f}"


def compare_rows(
    old_row: Dict[str, str],
    new_row: Dict[str, str],
    common_fields: Set[str],
) -> List[Tuple[str, bool, str]]:
    """
    Compare two rows and return list of (field_name, is_match, message).
    
    Returns:
        List of (field_name, is_match, message) tuples
    """
    differences = []
    
    # Fields that should use percent tolerance
    percent_fields = {
        "player_wins_percent",
        "player_draws_percent",
        "games_interrupted_percent",
        "games_not_interrupted_percent",
    }
    
    for field in sorted(common_fields):
        if field == "Player":
            continue  # Skip player name, already matched
        
        old_val = old_row.get(field, "")
        new_val = new_row.get(field, "")
        
        is_percent = field in percent_fields
        is_match, message = compare_values(old_val, new_val, field, is_percent)
        
        if not is_match:
            differences.append((field, is_match, message))
    
    return differences


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    old_csv = os.path.join(script_dir, "old_elo_refined.csv")
    new_csv = os.path.join(script_dir, "elo_refined.csv")
    
    print("=" * 80)
    print("ELO REFINED CSV COMPARISON")
    print("=" * 80)
    print(f"Old file: {old_csv}")
    print(f"New file: {new_csv}")
    print()
    
    # Load both CSVs
    old_rows, old_columns = load_csv(old_csv)
    new_rows, new_columns = load_csv(new_csv)
    
    # Create player lookup dictionaries
    old_by_player: Dict[str, Dict[str, str]] = {
        row["Player"]: row for row in old_rows if row.get("Player")
    }
    new_by_player: Dict[str, Dict[str, str]] = {
        row["Player"]: row for row in new_rows if row.get("Player")
    }
    
    old_players = set(old_by_player.keys())
    new_players = set(new_by_player.keys())
    
    # Report basic statistics
    print("SUMMARY")
    print("-" * 80)
    print(f"Old CSV: {len(old_rows)} rows, {len(old_columns)} columns")
    print(f"New CSV: {len(new_rows)} rows, {len(new_columns)} columns")
    print(f"Old players: {len(old_players)}")
    print(f"New players: {len(new_players)}")
    print()
    
    # Find common and unique players
    common_players = old_players & new_players
    only_old = old_players - new_players
    only_new = new_players - old_players
    
    print(f"Common players: {len(common_players)}")
    print(f"Only in old: {len(only_old)}")
    print(f"Only in new: {len(only_new)}")
    print()
    
    # Report unique players
    if only_old:
        print("PLAYERS ONLY IN OLD CSV:")
        print("-" * 80)
        for player in sorted(only_old):
            print(f"  - {player}")
        print()
    
    if only_new:
        print("PLAYERS ONLY IN NEW CSV:")
        print("-" * 80)
        for player in sorted(only_new):
            print(f"  - {player}")
        print()
    
    # Compare common players
    common_fields = old_columns & new_columns
    only_old_fields = old_columns - new_columns
    only_new_fields = new_columns - old_columns
    
    if only_old_fields:
        print("FIELDS ONLY IN OLD CSV:")
        print("-" * 80)
        for field in sorted(only_old_fields):
            print(f"  - {field}")
        print()
    
    if only_new_fields:
        print("FIELDS ONLY IN NEW CSV:")
        print("-" * 80)
        for field in sorted(only_new_fields):
            print(f"  - {field}")
        print()
    
    # Compare each common player
    print("COMPARING COMMON PLAYERS")
    print("-" * 80)
    
    players_with_differences = []
    total_differences = 0
    
    for player in sorted(common_players):
        old_row = old_by_player[player]
        new_row = new_by_player[player]
        
        differences = compare_rows(old_row, new_row, common_fields)
        
        if differences:
            players_with_differences.append((player, differences))
            total_differences += len(differences)
    
    if not players_with_differences:
        print("✓ All common players match exactly!")
        print()
    else:
        print(f"Found {len(players_with_differences)} players with differences")
        print(f"Total field differences: {total_differences}")
        print()
        
        # Show detailed differences for each player
        for player, differences in players_with_differences:
            print(f"PLAYER: {player}")
            print(f"  Differences: {len(differences)}")
            
            # Group by severity (key metrics vs others)
            key_metrics = {
                "elo",
                "elo_moe_95",
                "games_vs_random",
                "games_vs_dragon",
                "total_games",
                "player_wins",
                "opponent_wins",
                "draws",
                "win_loss",
                "player_wins_percent",
            }
            
            key_diffs = [d for d in differences if d[0] in key_metrics]
            other_diffs = [d for d in differences if d[0] not in key_metrics]
            
            if key_diffs:
                print("  Key metrics:")
                for field, is_match, message in key_diffs:
                    print(f"    - {field}: {message}")
            
            if other_diffs:
                print(f"  Other fields ({len(other_diffs)}):")
                # Show first 5 other differences
                for field, is_match, message in other_diffs[:5]:
                    print(f"    - {field}: {message}")
                if len(other_diffs) > 5:
                    print(f"    ... and {len(other_diffs) - 5} more")
            print()
    
    # Final summary
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total players in old: {len(old_players)}")
    print(f"Total players in new: {len(new_players)}")
    print(f"Common players: {len(common_players)}")
    print(f"Players only in old: {len(only_old)}")
    print(f"Players only in new: {len(only_new)}")
    print(f"Players with differences: {len(players_with_differences)}")
    print(f"Total field differences: {total_differences}")
    
    if not players_with_differences and not only_old and not only_new:
        print("\n✓ Files are identical!")
        return 0
    else:
        print("\n⚠ Files differ (see details above)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

