import os
from ..data_processing.aggregate_logs_to_csv import aggregate_models_to_csv
from ..data_processing.aggr_to_refined import convert_aggregate_to_refined

LOGS_DIR = "_logs/no_reflection"
AGGREGATE_CSV = os.path.join(LOGS_DIR, "aggregate_models.csv")
REFINED_CSV = "data_processing/refined.csv"


def main():
    # Step 1: Aggregate logs to CSV
    aggregate_models_to_csv(LOGS_DIR, AGGREGATE_CSV)
