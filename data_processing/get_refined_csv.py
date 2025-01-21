import os
from aggregate_logs_to_csv import aggregate_models_to_csv, MODEL_OVERRIDES
from aggr_to_refined import convert_aggregate_to_refined

LOGS_DIR = "_logs/no_reflection"
AGGREGATE_CSV = os.path.join(LOGS_DIR, "aggregate_models.csv")
REFINED_CSV = "data_processing/refined.csv"


def main():
    # Step 1: Aggregate logs to CSV
    aggregate_models_to_csv(LOGS_DIR, AGGREGATE_CSV, MODEL_OVERRIDES)

    # Step 2: Convert aggregated CSV to refined CSV
    convert_aggregate_to_refined(AGGREGATE_CSV, REFINED_CSV)


if __name__ == "__main__":
    main()
