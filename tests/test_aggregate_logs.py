import unittest
import math
from statistics import stdev
from data_processing.aggregate_logs_to_csv import GameLog, PlayerStats, UsageStats


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

    def test_std_dev_and_moe_black_llm_draws_percent(self):
        logs = [
            create_mock_game_log(winner="Draw"),
            create_mock_game_log(winner="Draw"),
            create_mock_game_log(winner="Player_Black"),
            create_mock_game_log(winner="Random_Player"),
        ]
        black_llm_draws_percent = [100, 100, 0, 0]
        std_dev = stdev(black_llm_draws_percent)
        moe = 1.96 * (std_dev / math.sqrt(len(black_llm_draws_percent)))
        self.assertAlmostEqual(std_dev, 57.735026918962575)
        self.assertAlmostEqual(moe, 56.5803263805833)
        logs = [create_mock_game_log(completion_tokens=100, number_of_moves=40)]
        tokens_per_move = sum(
            log.usage_stats_black.details["completion_tokens"] / log.number_of_moves
            for log in logs
        ) / len(logs)
        self.assertAlmostEqual(tokens_per_move, 2.5)

    def test_std_dev_and_moe_black_llm_wins_percent(self):
        logs = [
            create_mock_game_log(winner="Player_Black"),
            create_mock_game_log(winner="Player_Black"),
            create_mock_game_log(winner="Random_Player"),
            create_mock_game_log(winner="Draw"),
        ]
        black_llm_wins_percent = [100, 100, 0, 0]
        std_dev = stdev(black_llm_wins_percent)
        moe = 1.96 * (std_dev / math.sqrt(len(black_llm_wins_percent)))
        self.assertAlmostEqual(std_dev, 57.735026918962575)
        self.assertAlmostEqual(moe, 56.58032638058332)
        logs = [
            create_mock_game_log(material_black=20, material_white=18)
            for _ in range(10)
        ]
        material_diffs = [
            log.material_count["black"] - log.material_count["white"] for log in logs
        ]
        std_dev = stdev(material_diffs)
        moe = 1.96 * (std_dev / math.sqrt(len(logs)))
        self.assertAlmostEqual(moe, 0.0)  # All logs have the same material diff


if __name__ == "__main__":
    unittest.main()
