import csv
import os
import tempfile
import unittest

from data.model_metadata import (
    load_metadata_rows,
    normalize_release_date,
    split_model_identity,
    write_docs_metadata_js,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METADATA_CSV = os.path.join(ROOT, "data", "models_metadata.csv")


class TestModelMetadata(unittest.TestCase):
    def test_all_metadata_rows_have_derived_fields(self):
        fieldnames, rows = load_metadata_rows(METADATA_CSV)

        self.assertIn("mode_family", fieldnames)
        self.assertIn("reasoning_level", fieldnames)
        self.assertEqual(len(rows), 309)
        self.assertTrue(all(row["model"] for row in rows))
        self.assertTrue(all(row["mode_family"] for row in rows))
        self.assertTrue(all(row["reasoning_level"] for row in rows))
        self.assertTrue(all("adaptive_thinking" not in row["reasoning_level"] for row in rows))
        muse_row = next(row for row in rows if row["model"] == "muse-glimmer-30b@q4_k_m")
        self.assertEqual(normalize_release_date(muse_row["date_released"]), "2026-08-01")

    def test_effort_and_anthropic_normalization(self):
        self.assertEqual(
            split_model_identity("claude-sonnet-5_adaptive-thinking-high", "reasoning"),
            ("claude-sonnet-5", "high"),
        )
        self.assertEqual(
            split_model_identity("claude-3-7-sonnet_thinking_10000", "reasoning"),
            ("claude-3-7-sonnet", "budget_10000"),
        )
        self.assertEqual(
            split_model_identity("gpt-5.6-luna-2026-07-09-xhigh", "reasoning"),
            ("gpt-5.6-luna-2026-07-09", "xhigh"),
        )
        self.assertEqual(
            split_model_identity("qwen-max", "not_reasoning"),
            ("qwen-max", "none"),
        )
        self.assertEqual(
            split_model_identity("deepseek-V3.2_non-reasoning", "reasoning"),
            ("deepseek-V3.2", "none"),
        )
        self.assertEqual(
            split_model_identity("o4-mini-low@PGN", "reasoning"),
            ("o4-mini@PGN", "low"),
        )

    def test_generated_browser_asset_contains_all_models_and_alias(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = os.path.join(temporary_directory, "model_metadata.js")
            write_docs_metadata_js(METADATA_CSV, output_path)

            with open(output_path, "r", encoding="utf-8") as output_file:
                javascript = output_file.read()

            self.assertIn('"models"', javascript)
            self.assertIn('"claude-sonnet-5_adaptive-thinking-high"', javascript)
            self.assertIn('"claude-opus-4-5-20251101_thinking_16000"', javascript)
            self.assertIn('"date_released": "2025-02-01"', javascript)
            self.assertIn('"date_released": "2026-08-01"', javascript)
            self.assertIn('"pricing_known": true', javascript)

    def test_release_date_normalization(self):
        self.assertEqual(normalize_release_date(" 2024-03"), "2024-03-01")
        self.assertEqual(normalize_release_date("2025/7/9"), "2025-07-09")
        self.assertEqual(normalize_release_date("2026"), "2026-01-01")
        self.assertEqual(normalize_release_date("2024-02-30"), "")
        self.assertEqual(normalize_release_date("0000-01-01"), "")
        self.assertEqual(normalize_release_date("not-a-date"), "")

    def test_csv_header_is_read_without_changing_model_names(self):
        with open(METADATA_CSV, "r", encoding="utf-8", newline="") as metadata_file:
            models = [row["model"] for row in csv.DictReader(metadata_file)]

        _, rows = load_metadata_rows(METADATA_CSV)
        self.assertEqual(models, [row["model"] for row in rows])


if __name__ == "__main__":
    unittest.main()
