import os
from aggregate_logs_to_csv import aggregate_models_to_csv, MODEL_OVERRIDES
from aggr_to_refined import convert_aggregate_to_refined

LOGS_DIR = "_logs/no_reflection"
AGGREGATE_CSV = os.path.join(LOGS_DIR, "aggregate_models.csv")
REFINED_CSV = "data_processing/refined.csv"
FILTER_OUT_MODELS = [
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp03",
    "deepseek-r1-distill-qwen-32b@q4_k_m|noisol_temp06",
    "anthropic.claude-v3-5-sonnet",
    "llama-3.1-tulu-3-8b@q4_k_m",
    "llama-3.1-8b-instant",  # Groq
    "meta-llama-3.1-8b-instruct-fp16",  # local
    "gemini-2.0-pro-exp-02-05", # to many errors, I'm done with EXP models, to much trouble, going to use only release versions
    "ignore",  # models marked to be ignored via aggregate_models_to_csv.MODEL_OVERRIDES
]

ALIASES = {
    "deepseek-r1-distill-qwen-32b@q4_k_m|isol_temp06": "deepseek-r1-distill-qwen-32b@q4_k_m",
    "deepseek-reasoner": "deepseek-reasoner-r1",  # at the time of testing (Jan 2025) R1 was called "deepseek-reasoner"
    "deepseek-chat": "deepseek-chat-v3",  # at the time of testing (Jan 2025) V3 was called "deepseek-chat"
    "gemma2-9b-it": "gemma2-9b-it-groq",
    "anthropic.claude-v3-5-sonnet-v1": "claude-v3-5-sonnet-v1",
    "anthropic.claude-v3-5-sonnet-v2": "claude-v3-5-sonnet-v2",
    "anthropic.claude-v3-haiku": "claude-v3-haiku",
    "anthropic.claude-v3-opus": "claude-v3-opus",
}


def main():
    # Step 1: Aggregate logs to CSV
    aggregate_models_to_csv(LOGS_DIR, AGGREGATE_CSV, MODEL_OVERRIDES)

    # Step 2: Convert aggregated CSV to refined CSV
    convert_aggregate_to_refined(
        AGGREGATE_CSV,
        REFINED_CSV,
        filter_out_below_n=30,
        filter_out_models=FILTER_OUT_MODELS,
        model_aliases=ALIASES,
    )


if __name__ == "__main__":
    main()
