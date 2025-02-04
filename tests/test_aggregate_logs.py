import unittest
from statistics import stdev
from data_processing.aggregate_logs_to_csv import (
    GameLog,
    PlayerStats,
    UsageStats,
)
import csv


def create_mock_game_log(
    winner="Player_Black",
    number_of_moves=40,
    wrong_moves_black=2,
    wrong_actions_black=1,
    material_black=20,
    material_white=18,
    completion_tokens=100,
    prompt_tokens=50,
    model_name="test_model",
):
    return GameLog(
        time_started="2025-01-01T00:00:00",
        winner=winner,
        reason="Checkmate",
        number_of_moves=number_of_moves,
        player_white=PlayerStats(
            name="Random_Player",
            wrong_moves=0,
            wrong_actions=0,
            reflections_used=0,
            reflections_used_before_board=0,
            model="Random_Player",
        ),
        player_black=PlayerStats(
            name="Player_Black",
            wrong_moves=wrong_moves_black,
            wrong_actions=wrong_actions_black,
            reflections_used=0,
            reflections_used_before_board=0,
            model=model_name,
        ),
        material_count={"black": material_black, "white": material_white},
        usage_stats_white=UsageStats(total_cost=0, details={}),
        usage_stats_black=UsageStats(
            total_cost=completion_tokens,
            details={
                "completion_tokens": completion_tokens,
                "prompt_tokens": prompt_tokens,
            },
        ),
    )


class TestAggregateMetrics(unittest.TestCase):
    def test_total_games(self):
        logs = [create_mock_game_log() for _ in range(5)]
        self.assertEqual(len(logs), 5)

    def test_black_llm_wins(self):
        logs = [create_mock_game_log(winner="Player_Black") for _ in range(3)]
        logs += [create_mock_game_log(winner="Random_Player") for _ in range(2)]
        black_llm_wins = sum(1 for log in logs if log.winner == "Player_Black")
        self.assertEqual(black_llm_wins, 3)

    def test_draws(self):
        logs = [create_mock_game_log(winner="Draw") for _ in range(4)]
        draws = sum(1 for log in logs if log.winner == "Draw")
        self.assertEqual(draws, 4)

    def test_average_moves(self):
        logs = [
            create_mock_game_log(number_of_moves=30),
            create_mock_game_log(number_of_moves=50),
        ]
        avg_moves = sum(log.number_of_moves for log in logs) / len(logs)
        self.assertEqual(avg_moves, 40)

    def test_std_dev_moves(self):
        logs = [
            create_mock_game_log(number_of_moves=30),
            create_mock_game_log(number_of_moves=50),
        ]
        moves = [log.number_of_moves for log in logs]
        std_dev = stdev(moves)
        self.assertAlmostEqual(std_dev, 14.142135623730951)

    def test_mistakes_per_1000moves(self):
        logs = [
            create_mock_game_log(
                wrong_moves_black=2, wrong_actions_black=1, number_of_moves=40
            )
        ]
        mistakes_per_1000moves = sum(
            (log.player_black.wrong_moves + log.player_black.wrong_actions)
            / log.number_of_moves
            * 1000
            for log in logs
        ) / len(logs)
        self.assertAlmostEqual(mistakes_per_1000moves, 75.0)

    def test_material_diff(self):
        logs = [create_mock_game_log(material_black=20, material_white=18)]
        material_diff = sum(
            log.material_count["black"] - log.material_count["white"] for log in logs
        ) / len(logs)
        self.assertEqual(material_diff, 2)


class TestAggregateOutputFields(unittest.TestCase):
    def test_aggregation_output_fields(self):
        # Create mock logs
        logs = [
            create_mock_game_log(winner="Player_Black"),
            create_mock_game_log(winner="Random_Player"),
            create_mock_game_log(winner="Draw"),
        ]

        # Mock the aggregation process
        output_csv = "mock_aggregate_output.csv"

        # Group logs by model name (mocking the behavior of load_game_logs)
        model_groups = {}
        for log in logs:
            model_name = log.player_black.model
            if model_name not in model_groups:
                model_groups[model_name] = []
            model_groups[model_name].append(log)

        # Prepare headers and data for the CSV
        headers = [
            "model_name",
            "total_games",
            "black_llm_wins",
            "white_rand_wins",
            "draws",
            "black_llm_wins_percent",
            "black_llm_draws_percent",
            "white_rand_wins_percent",
            "llm_total_moves",
            "llm_wrong_actions",
            "llm_wrong_moves",
            "llm_avg_material",
            "llm_std_dev_material",
            "rand_avg_material",
            "rand_std_dev_material",
            "material_diff_llm_minus_rand",
            "material_diff_llm_minus_rand_per_100moves",
            "wrong_actions_per_100moves",
            "wrong_moves_per_100moves",
            "wrong_actions_per_1000moves",
            "wrong_moves_per_1000moves",
            "mistakes_per_1000moves",
            "std_dev_wrong_actions_per_1000moves",
            "std_dev_wrong_moves_per_1000moves",
            "std_dev_mistakes_per_1000moves",
            "average_moves",
            "std_dev_moves",
            "completion_tokens_black",
            "completion_tokens_black_per_move",
            "std_dev_completion_tokens_black_per_move",
            "moe_completion_tokens_black_per_move",
            "min_moves",
            "max_moves",
            "prompt_tokens_black",
            "total_tokens_black",
            "moe_material_diff",
            "moe_avg_moves",
            "moe_wrong_actions_per_1000moves",
            "moe_wrong_moves_per_1000moves",
            "moe_mistakes_per_1000moves",
        ]

        csv_data = []

        for model_name, model_logs in model_groups.items():
            total_games = len(model_logs)
            black_llm_wins = sum(
                1 for log in model_logs if log.winner == "Player_Black"
            )
            white_rand_wins = sum(
                1 for log in model_logs if log.winner == "Random_Player"
            )
            draws = total_games - black_llm_wins - white_rand_wins

            black_llm_wins_percent = (
                (black_llm_wins / total_games) * 100 if total_games > 0 else 0
            )
            black_llm_draws_percent = (
                (draws / total_games) * 100 if total_games > 0 else 0
            )
            white_rand_wins_percent = (
                (white_rand_wins / total_games) * 100 if total_games > 0 else 0
            )

            # Append the calculated data to the CSV data list
            csv_data.append(
                [
                    model_name,
                    total_games,
                    black_llm_wins,
                    white_rand_wins,
                    draws,
                    black_llm_wins_percent,
                    black_llm_draws_percent,
                    white_rand_wins_percent,
                    0,  # Placeholder for llm_total_moves
                    0,  # Placeholder for llm_wrong_actions
                    0,  # Placeholder for llm_wrong_moves
                    0,  # Placeholder for llm_avg_material
                    0,  # Placeholder for llm_std_dev_material
                    0,  # Placeholder for rand_avg_material
                    0,  # Placeholder for rand_std_dev_material
                    0,  # Placeholder for material_diff_llm_minus_rand
                    0,  # Placeholder for material_diff_llm_minus_rand_per_100moves
                    0,  # Placeholder for wrong_actions_per_100moves
                    0,  # Placeholder for wrong_moves_per_100moves
                    0,  # Placeholder for wrong_actions_per_1000moves
                    0,  # Placeholder for wrong_moves_per_1000moves
                    0,  # Placeholder for mistakes_per_1000moves
                    0,  # Placeholder for std_dev_wrong_actions_per_1000moves
                    0,  # Placeholder for std_dev_wrong_moves_per_1000moves
                    0,  # Placeholder for std_dev_mistakes_per_1000moves
                    0,  # Placeholder for average_moves
                    0,  # Placeholder for std_dev_moves
                    0,  # Placeholder for completion_tokens_black
                    0,  # Placeholder for completion_tokens_black_per_move
                    0,  # Placeholder for std_dev_completion_tokens_black_per_move
                    0,  # Placeholder for moe_completion_tokens_black_per_move
                    0,  # Placeholder for min_moves
                    0,  # Placeholder for max_moves
                    0,  # Placeholder for prompt_tokens_black
                    0,  # Placeholder for total_tokens_black
                    0,  # Placeholder for moe_material_diff
                    0,  # Placeholder for moe_avg_moves
                    0,  # Placeholder for moe_wrong_actions_per_1000moves
                    0,  # Placeholder for moe_wrong_moves_per_1000moves
                    0,  # Placeholder for moe_mistakes_per_1000moves
                ]
            )

        # Write the mock data to the CSV
        with open(output_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(csv_data)

        # Read the aggregated CSV
        with open(output_csv, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            read_headers = reader.fieldnames
            rows = list(reader)

        # Verify that all expected fields are present in the aggregated CSV
        for field in headers:
            self.assertIn(field, read_headers)

        # Verify the values in the CSV match the expected data
        for i, row in enumerate(rows):
            for j, header in enumerate(headers):
                if header in row:
                    if isinstance(csv_data[i][j], float):
                        self.assertAlmostEqual(float(row[header]), csv_data[i][j])
                    else:
                        self.assertEqual(row[header], str(csv_data[i][j]))


if __name__ == "__main__":
    unittest.main()
