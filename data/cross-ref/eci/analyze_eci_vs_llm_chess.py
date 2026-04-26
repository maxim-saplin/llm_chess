from __future__ import annotations

import argparse
import html
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ARTIFACT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ARTIFACT_DIR.parents[2]
ELO_CSV = REPO_ROOT / "data" / "elo_refined.csv"
ECI_CSV = ARTIFACT_DIR / "epoch_eci_apr_2026.csv"
METADATA_CSV = REPO_ROOT / "data" / "models_metadata.csv"

TOP_N_COVERAGE = [10, 20, 30, 40, 50, 75, 100]
GAME_THRESHOLDS = [0, 20, 30, 40, 50, 60]
SELECTED_METRICS = [
    "elo",
    "player_wins_percent",
    "player_draws_percent",
    "games_interrupted_percent",
    "wrong_moves_per_1000moves",
    "mistakes_per_1000moves",
    "average_moves",
    "average_time_per_game_seconds",
    "average_game_cost",
    "completion_tokens_black_per_move",
    "material_diff_player_llm_minus_opponent",
]
MULTIFACTOR_METRICS = [
    "player_wins_percent",
    "games_interrupted_percent",
    "average_time_per_game_seconds",
    "average_game_cost",
    "completion_tokens_black_per_move",
    "material_diff_player_llm_minus_opponent",
    "elo",
]
RIDGE_ALPHA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
PREDICTION_CV_SEEDS = [11, 23, 37]
PREDICTION_OUTER_FOLDS = 5
PREDICTION_INNER_FOLDS = 3
COMPACT_SCREEN_METRIC_LIMIT = 10
PREDICTOR_FAMILIES = {
    "outcome": [
        "elo",
        "player_wins_percent",
        "win_loss",
        "win_loss_non_interrupted",
        "player_draws_percent",
    ],
    "board_control": [
        "material_diff_player_llm_minus_opponent",
        "player_avg_material",
        "opponent_avg_material",
    ],
    "reliability": [
        "games_interrupted_percent",
        "wrong_actions_per_1000moves",
        "wrong_moves_per_1000moves",
        "mistakes_per_1000moves",
    ],
    "deliberation_resources": [
        "average_time_per_game_seconds",
        "completion_tokens_black_per_move",
        "average_game_cost",
        "price_per_1000_moves",
        "game_duration",
    ],
}
PREDICTOR_METRICS = [
    metric
    for family_metrics in PREDICTOR_FAMILIES.values()
    for metric in family_metrics
]
DATE_SANITY_FEATURES = ["release_month_index", "release_month_sq"]


def _clean_key_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        return
    df[column] = df[column].astype(str).str.strip()
    df[column] = df[column].replace({"": np.nan, "nan": np.nan, "NaN": np.nan})


def _parse_epoch_ci(value: object) -> tuple[float | None, float | None]:
    if pd.isna(value):
        return (None, None)
    raw = str(value).strip()
    if not raw or raw.upper() == "NA":
        return (None, None)
    raw = raw.strip("()")
    try:
        low, high = [float(part.strip()) for part in raw.split("-")]
    except ValueError:
        return (None, None)
    return (low, high)


def _series_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _named_corr(name: str, x: pd.Series, y: pd.Series) -> dict[str, float | int | str]:
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 3:
        return {"name": name, "n": int(len(valid))}

    pearson = stats.pearsonr(valid["x"], valid["y"])
    spearman = stats.spearmanr(valid["x"], valid["y"])
    slope, intercept, r_value, p_value, stderr = stats.linregress(valid["x"], valid["y"])
    return {
        "name": name,
        "n": int(len(valid)),
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman_r": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r_value**2),
        "linregress_p": float(p_value),
        "slope_stderr": float(stderr),
    }


def _partial_corr_release_month(
    score: pd.Series,
    metric: pd.Series,
    release_month_index: pd.Series,
) -> dict[str, float | int] | None:
    valid = pd.DataFrame(
        {
            "score": score,
            "metric": metric,
            "release_month_index": release_month_index,
        }
    ).dropna()
    if len(valid) < 4:
        return None

    x = np.column_stack(
        [np.ones(len(valid)), valid["release_month_index"].to_numpy(dtype=float)]
    )
    score_beta = np.linalg.lstsq(x, valid["score"].to_numpy(dtype=float), rcond=None)[0]
    metric_beta = np.linalg.lstsq(x, valid["metric"].to_numpy(dtype=float), rcond=None)[0]
    score_resid = valid["score"].to_numpy(dtype=float) - x.dot(score_beta)
    metric_resid = valid["metric"].to_numpy(dtype=float) - x.dot(metric_beta)

    pearson = stats.pearsonr(score_resid, metric_resid)
    spearman = stats.spearmanr(score_resid, metric_resid)
    return {
        "n": int(len(valid)),
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman_r": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
    }


def _dedupe_epoch_bridge(
    epoch: pd.DataFrame,
    method: str,
) -> pd.DataFrame:
    bridge = epoch.dropna(subset=["llm_chess_model", "Score"]).copy()
    if method == "max":
        return (
            bridge.sort_values(["llm_chess_model", "Score"], ascending=[True, False])
            .drop_duplicates("llm_chess_model", keep="first")
            .reset_index(drop=True)
        )
    if method == "min":
        return (
            bridge.sort_values(["llm_chess_model", "Score"], ascending=[True, True])
            .drop_duplicates("llm_chess_model", keep="first")
            .reset_index(drop=True)
        )
    if method in {"mean", "median"}:
        return (
            bridge.groupby("llm_chess_model", as_index=False)
            .agg(
                {
                    "Score": method,
                    "Model": "first",
                }
            )
            .reset_index(drop=True)
        )
    raise ValueError(f"Unsupported dedupe method: {method}")


def _vendor_from_label(label: str) -> str:
    raw = label.lower()
    if raw.startswith(("gpt", "o1", "o3", "o4")):
        return "OpenAI"
    if raw.startswith("claude"):
        return "Anthropic"
    if raw.startswith(("gemini", "gemma")):
        return "Google"
    if raw.startswith("grok"):
        return "xAI"
    if raw.startswith("deepseek"):
        return "DeepSeek"
    if raw.startswith("kimi"):
        return "Moonshot"
    if raw.startswith("minimax"):
        return "MiniMax"
    if raw.startswith("qwen"):
        return "Qwen"
    if raw.startswith("glm"):
        return "ZAI"
    if raw.startswith("llama"):
        return "Meta"
    if "mistral" in raw or "magistral" in raw:
        return "Mistral"
    return "Other"


def _split_contiguous_folds(n_rows: int, n_folds: int) -> list[list[int]]:
    return [fold.tolist() for fold in np.array_split(np.arange(n_rows), n_folds)]


def _regression_score(
    y_true: list[float] | np.ndarray,
    y_pred: list[float] | np.ndarray,
) -> dict[str, float | None]:
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    sse = np.square(y_true_arr - y_pred_arr).sum()
    sst = np.square(y_true_arr - y_true_arr.mean()).sum()
    true_ranks = pd.Series(y_true_arr).rank(method="average").to_numpy(dtype=float)
    pred_ranks = pd.Series(y_pred_arr).rank(method="average").to_numpy(dtype=float)
    if np.std(pred_ranks) == 0 or np.std(true_ranks) == 0:
        spearman = np.nan
    else:
        spearman = np.corrcoef(true_ranks, pred_ranks)[0, 1]
    return {
        "r2": float(1.0 - sse / sst),
        "rmse": float(np.sqrt(np.mean(np.square(y_true_arr - y_pred_arr)))),
        "mae": float(np.mean(np.abs(y_true_arr - y_pred_arr))),
        "rank_spearman": None if np.isnan(spearman) else float(spearman),
    }


def _ols_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
) -> np.ndarray:
    train_x = np.column_stack([np.ones(len(train_df)), train_df[features].to_numpy(dtype=float)])
    train_y = train_df["Score"].to_numpy(dtype=float)
    beta = np.linalg.lstsq(train_x, train_y, rcond=None)[0]
    test_x = np.column_stack([np.ones(len(test_df)), test_df[features].to_numpy(dtype=float)])
    return test_x @ beta


def _ridge_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
    alpha: float,
) -> np.ndarray:
    train_x = train_df[features].to_numpy(dtype=float)
    test_x = test_df[features].to_numpy(dtype=float)
    train_y = train_df["Score"].to_numpy(dtype=float)

    feature_mean = train_x.mean(axis=0)
    feature_std = train_x.std(axis=0, ddof=0)
    feature_std = np.where(feature_std == 0, 1.0, feature_std)

    train_x_scaled = (train_x - feature_mean) / feature_std
    test_x_scaled = (test_x - feature_mean) / feature_std
    y_mean = train_y.mean()
    beta = np.linalg.solve(
        train_x_scaled.T @ train_x_scaled + alpha * np.eye(train_x_scaled.shape[1]),
        train_x_scaled.T @ (train_y - y_mean),
    )
    return test_x_scaled @ beta + y_mean


def _pcr_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
    n_components: int,
) -> np.ndarray:
    train_x = train_df[features].to_numpy(dtype=float)
    test_x = test_df[features].to_numpy(dtype=float)
    train_y = train_df["Score"].to_numpy(dtype=float)

    feature_mean = train_x.mean(axis=0)
    feature_std = train_x.std(axis=0, ddof=0)
    feature_std = np.where(feature_std == 0, 1.0, feature_std)
    train_x_scaled = (train_x - feature_mean) / feature_std
    test_x_scaled = (test_x - feature_mean) / feature_std

    _, _, vt = np.linalg.svd(train_x_scaled, full_matrices=False)
    components = vt[:n_components].T
    train_scores = train_x_scaled @ components
    test_scores = test_x_scaled @ components
    train_design = np.column_stack([np.ones(len(train_df)), train_scores])
    beta = np.linalg.lstsq(train_design, train_y, rcond=None)[0]
    test_design = np.column_stack([np.ones(len(test_df)), test_scores])
    return test_design @ beta


def _split_random_folds(n_rows: int, n_folds: int, seed: int) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(n_rows)
    rng.shuffle(indices)
    return [fold.tolist() for fold in np.array_split(indices, min(n_folds, n_rows))]


def _random_cv_ols(
    df: pd.DataFrame,
    features: list[str],
    seed: int,
    n_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, float | None]:
    y_true: list[float] = []
    y_pred: list[float] = []
    for test_idx in _split_random_folds(len(df), n_folds, seed):
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ols_predict(train_df, test_df, features).tolist())
    return _regression_score(y_true, y_pred)


def _random_cv_ridge(
    df: pd.DataFrame,
    features: list[str],
    alpha: float,
    seed: int,
    n_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, float | None]:
    y_true: list[float] = []
    y_pred: list[float] = []
    for test_idx in _split_random_folds(len(df), n_folds, seed):
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ridge_predict(train_df, test_df, features, alpha=alpha).tolist())
    return _regression_score(y_true, y_pred)


def _random_cv_pcr(
    df: pd.DataFrame,
    features: list[str],
    n_components: int,
    seed: int,
    n_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, float | None]:
    y_true: list[float] = []
    y_pred: list[float] = []
    for test_idx in _split_random_folds(len(df), n_folds, seed):
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_pcr_predict(train_df, test_df, features, n_components=n_components).tolist())
    return _regression_score(y_true, y_pred)


def _prediction_summary_from_rows(
    sample: pd.DataFrame,
    prediction_rows: list[dict[str, float | int]],
) -> dict[str, object]:
    prediction_df = pd.DataFrame(prediction_rows)
    score = _regression_score(
        prediction_df["actual"].to_numpy(dtype=float),
        prediction_df["predicted"].to_numpy(dtype=float),
    )
    per_model = (
        prediction_df.groupby("row_index", as_index=False)
        .agg(
            actual=("actual", "first"),
            predicted=("predicted", "mean"),
            prediction_sd=("predicted", "std"),
            n_predictions=("predicted", "size"),
        )
    )
    label_columns = ["llm_chess_model", "Model", "Score", "elo"]
    sample_labels = sample.copy()
    for column in label_columns:
        if column not in sample_labels.columns:
            sample_labels[column] = None
    per_model = per_model.merge(
        sample_labels[label_columns].reset_index(names="row_index"),
        on="row_index",
        how="left",
    )
    per_model["residual"] = per_model["actual"] - per_model["predicted"]
    per_model["abs_error"] = per_model["residual"].abs()
    top_misses = (
        per_model.sort_values("abs_error", ascending=False)
        [
            [
                "llm_chess_model",
                "Model",
                "Score",
                "elo",
                "predicted",
                "residual",
                "abs_error",
                "prediction_sd",
                "n_predictions",
            ]
        ]
        .head(12)
        .to_dict(orient="records")
    )
    return {
        **score,
        "top_prediction_misses": top_misses,
    }


def _repeated_cv_mean(
    df: pd.DataFrame,
    seeds: list[int] = PREDICTION_CV_SEEDS,
    n_folds: int = PREDICTION_OUTER_FOLDS,
) -> dict[str, object]:
    prediction_rows: list[dict[str, float | int]] = []
    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(_split_random_folds(len(df), n_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_mean = float(df.iloc[train_idx]["Score"].mean())
            for row_idx in test_idx:
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx]["Score"]),
                        "predicted": train_mean,
                    }
                )
    return _prediction_summary_from_rows(df, prediction_rows)


def _repeated_cv_ols(
    df: pd.DataFrame,
    features: list[str],
    seeds: list[int] = PREDICTION_CV_SEEDS,
    n_folds: int = PREDICTION_OUTER_FOLDS,
) -> dict[str, object]:
    prediction_rows: list[dict[str, float | int]] = []
    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(_split_random_folds(len(df), n_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]
            predictions = _ols_predict(train_df, test_df, features)
            for row_idx, predicted in zip(test_idx, predictions, strict=True):
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx]["Score"]),
                        "predicted": float(predicted),
                    }
                )
    return _prediction_summary_from_rows(df, prediction_rows)


def _screen_candidate_metrics(
    train_df: pd.DataFrame,
    candidate_metrics: list[str],
    max_metrics: int,
) -> list[str]:
    if len(candidate_metrics) <= max_metrics:
        return candidate_metrics

    scored_metrics = []
    target = train_df["Score"].to_numpy(dtype=float)
    for metric in candidate_metrics:
        values = train_df[metric].to_numpy(dtype=float)
        if np.std(values) == 0:
            score = 0.0
        else:
            score = abs(stats.pearsonr(target, values).statistic)
            if np.isnan(score):
                score = 0.0
        scored_metrics.append((score, metric))
    return [
        metric
        for _, metric in sorted(scored_metrics, key=lambda row: (-row[0], row[1]))[:max_metrics]
    ]


def _nested_random_subset_search(
    df: pd.DataFrame,
    candidate_metrics: list[str],
    subset_size: int,
    seeds: list[int] = PREDICTION_CV_SEEDS,
    outer_folds: int = PREDICTION_OUTER_FOLDS,
    inner_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, object]:
    prediction_rows: list[dict[str, float | int]] = []
    chosen_subsets: list[dict[str, object]] = []

    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(_split_random_folds(len(df), outer_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_df = df.iloc[train_idx].reset_index(drop=True)
            test_df = df.iloc[test_idx]

            best_subset = None
            best_r2 = None
            inner_seed = seed * 100 + fold_idx
            screened_metrics = _screen_candidate_metrics(
                train_df,
                candidate_metrics,
                max_metrics=max(COMPACT_SCREEN_METRIC_LIMIT, subset_size),
            )
            for subset in itertools.combinations(screened_metrics, subset_size):
                result = _random_cv_ols(
                    train_df,
                    list(subset),
                    seed=inner_seed,
                    n_folds=min(inner_folds, len(train_df)),
                )
                if best_r2 is None or float(result["r2"]) > best_r2:
                    best_subset = subset
                    best_r2 = float(result["r2"])

            selected_features = list(best_subset)
            chosen_subsets.append(
                {
                    "metrics": selected_features,
                    "screened_metrics": screened_metrics,
                    "inner_cv_r2": float(best_r2),
                }
            )
            predictions = _ols_predict(train_df, test_df, selected_features)
            for row_idx, predicted in zip(test_idx, predictions, strict=True):
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx]["Score"]),
                        "predicted": float(predicted),
                    }
                )

    combo_counts: dict[tuple[str, ...], int] = {}
    metric_counts: dict[str, int] = {}
    for row in chosen_subsets:
        metrics = tuple(sorted(row["metrics"]))
        combo_counts[metrics] = combo_counts.get(metrics, 0) + 1
        for metric in metrics:
            metric_counts[metric] = metric_counts.get(metric, 0) + 1

    return {
        **_prediction_summary_from_rows(df, prediction_rows),
        "chosen_subsets": chosen_subsets,
        "combination_frequency": [
            {"metrics": list(metrics), "count": count}
            for metrics, count in sorted(
                combo_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "metric_selection_frequency": [
            {"metric": metric, "count": count}
            for metric, count in sorted(
                metric_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
    }


def _nested_random_ridge(
    df: pd.DataFrame,
    features: list[str],
    alpha_grid: list[float],
    seeds: list[int] = PREDICTION_CV_SEEDS,
    outer_folds: int = PREDICTION_OUTER_FOLDS,
    inner_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, object]:
    prediction_rows: list[dict[str, float | int]] = []
    chosen_alphas: list[float] = []

    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(_split_random_folds(len(df), outer_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_df = df.iloc[train_idx].reset_index(drop=True)
            test_df = df.iloc[test_idx]

            best_alpha = None
            best_r2 = None
            inner_seed = seed * 100 + fold_idx
            for alpha in alpha_grid:
                result = _random_cv_ridge(
                    train_df,
                    features,
                    alpha=alpha,
                    seed=inner_seed,
                    n_folds=min(inner_folds, len(train_df)),
                )
                if best_r2 is None or float(result["r2"]) > best_r2:
                    best_alpha = alpha
                    best_r2 = float(result["r2"])

            chosen_alphas.append(float(best_alpha))
            predictions = _ridge_predict(train_df, test_df, features, alpha=float(best_alpha))
            for row_idx, predicted in zip(test_idx, predictions, strict=True):
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx]["Score"]),
                        "predicted": float(predicted),
                    }
                )

    alpha_counts = {
        alpha: chosen_alphas.count(alpha)
        for alpha in sorted(set(chosen_alphas))
    }
    return {
        **_prediction_summary_from_rows(df, prediction_rows),
        "chosen_alphas": chosen_alphas,
        "alpha_frequency": [
            {"alpha": alpha, "count": count}
            for alpha, count in alpha_counts.items()
        ],
    }


def _nested_random_pcr(
    df: pd.DataFrame,
    features: list[str],
    component_grid: list[int],
    seeds: list[int] = PREDICTION_CV_SEEDS,
    outer_folds: int = PREDICTION_OUTER_FOLDS,
    inner_folds: int = PREDICTION_INNER_FOLDS,
) -> dict[str, object]:
    prediction_rows: list[dict[str, float | int]] = []
    chosen_components: list[int] = []

    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(_split_random_folds(len(df), outer_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_df = df.iloc[train_idx].reset_index(drop=True)
            test_df = df.iloc[test_idx]

            best_components = None
            best_r2 = None
            inner_seed = seed * 100 + fold_idx
            for n_components in component_grid:
                result = _random_cv_pcr(
                    train_df,
                    features,
                    n_components=n_components,
                    seed=inner_seed,
                    n_folds=min(inner_folds, len(train_df)),
                )
                if best_r2 is None or float(result["r2"]) > best_r2:
                    best_components = n_components
                    best_r2 = float(result["r2"])

            chosen_components.append(int(best_components))
            predictions = _pcr_predict(train_df, test_df, features, n_components=int(best_components))
            for row_idx, predicted in zip(test_idx, predictions, strict=True):
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx]["Score"]),
                        "predicted": float(predicted),
                    }
                )

    component_counts = {
        n_components: chosen_components.count(n_components)
        for n_components in sorted(set(chosen_components))
    }
    return {
        **_prediction_summary_from_rows(df, prediction_rows),
        "chosen_components": chosen_components,
        "component_frequency": [
            {"n_components": n_components, "count": count}
            for n_components, count in component_counts.items()
        ],
    }


def _in_sample_mean(df: pd.DataFrame) -> dict[str, float | None]:
    mean_prediction = np.full(len(df), float(df["Score"].mean()))
    return _regression_score(df["Score"].to_numpy(dtype=float), mean_prediction)


def _in_sample_ols(df: pd.DataFrame, features: list[str]) -> dict[str, float | None]:
    predictions = _ols_predict(df, df, features)
    return _regression_score(df["Score"].to_numpy(dtype=float), predictions)


def _in_sample_ridge(
    df: pd.DataFrame,
    features: list[str],
    alpha: float,
) -> dict[str, float | None]:
    predictions = _ridge_predict(df, df, features, alpha=alpha)
    return _regression_score(df["Score"].to_numpy(dtype=float), predictions)


def _in_sample_pcr(
    df: pd.DataFrame,
    features: list[str],
    n_components: int,
) -> dict[str, float | None]:
    predictions = _pcr_predict(df, df, features, n_components=n_components)
    return _regression_score(df["Score"].to_numpy(dtype=float), predictions)


def _most_frequent_subset(search_result: dict[str, object]) -> list[str]:
    frequencies = search_result["combination_frequency"]
    if not frequencies:
        return []
    return list(frequencies[0]["metrics"])


def _most_frequent_alpha(search_result: dict[str, object]) -> float:
    frequencies = search_result["alpha_frequency"]
    if not frequencies:
        return float(RIDGE_ALPHA_GRID[0])
    return float(max(frequencies, key=lambda row: row["count"])["alpha"])


def _most_frequent_components(search_result: dict[str, object]) -> int:
    frequencies = search_result["component_frequency"]
    if not frequencies:
        return 1
    return int(max(frequencies, key=lambda row: row["count"])["n_components"])


def _leaderboard_row(
    name: str,
    model_type: str,
    cv_result: dict[str, object],
    in_sample_result: dict[str, float | None],
    features: list[str] | None = None,
    family: str | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    row = {
        "name": name,
        "type": model_type,
        "cv": {
            "r2": cv_result["r2"],
            "rmse": cv_result["rmse"],
            "mae": cv_result["mae"],
            "rank_spearman": cv_result["rank_spearman"],
        },
        "in_sample": in_sample_result,
    }
    if features is not None:
        row["features"] = features
    if family is not None:
        row["family"] = family
    if notes is not None:
        row["notes"] = notes
    return row


def _build_prediction_summary(merged: pd.DataFrame) -> dict[str, object]:
    numeric_columns = sorted(set(PREDICTOR_METRICS + DATE_SANITY_FEATURES + ["Score"]))
    sample = merged.copy()
    for column in numeric_columns:
        sample[column] = pd.to_numeric(sample[column], errors="coerce")
    sample = (
        sample.dropna(subset=["Score"] + PREDICTOR_METRICS)
        .sort_values("llm_chess_model")
        .reset_index(drop=True)
    )

    model_results: dict[str, dict[str, object]] = {}
    leaderboard: list[dict[str, object]] = []

    mean_result = _repeated_cv_mean(sample)
    model_results["mean_only"] = mean_result
    leaderboard.append(
        _leaderboard_row(
            "Mean only",
            "baseline",
            mean_result,
            _in_sample_mean(sample),
            notes="Training-fold mean ECI; no chess information.",
        )
    )

    elo_result = _repeated_cv_ols(sample, ["elo"])
    model_results["elo_only"] = elo_result
    leaderboard.append(
        _leaderboard_row(
            "Elo only",
            "baseline",
            elo_result,
            _in_sample_ols(sample, ["elo"]),
            features=["elo"],
        )
    )

    single_result = _nested_random_subset_search(sample, PREDICTOR_METRICS, subset_size=1)
    single_features = _most_frequent_subset(single_result)
    model_results["best_single_metric"] = single_result
    leaderboard.append(
        _leaderboard_row(
            "Best single metric",
            "nested_subset_search",
            single_result,
            _in_sample_ols(sample, single_features),
            features=single_features,
            notes="Metric is selected inside each training fold.",
        )
    )

    compact_results = {}
    for subset_size in [2, 3, 4]:
        result = _nested_random_subset_search(sample, PREDICTOR_METRICS, subset_size=subset_size)
        features = _most_frequent_subset(result)
        key = f"best_{subset_size}_metric_combo"
        compact_results[key] = result
        model_results[key] = result
        leaderboard.append(
            _leaderboard_row(
                f"Best {subset_size}-metric combo",
                "nested_subset_search",
                result,
                _in_sample_ols(sample, features),
                features=features,
                notes="Combination is selected inside each training fold.",
            )
        )

    ridge_all = _nested_random_ridge(sample, PREDICTOR_METRICS, RIDGE_ALPHA_GRID)
    ridge_all_alpha = _most_frequent_alpha(ridge_all)
    model_results["ridge_all_chess_metrics"] = ridge_all
    leaderboard.append(
        _leaderboard_row(
            "Ridge, all chess metrics",
            "nested_ridge",
            ridge_all,
            _in_sample_ridge(sample, PREDICTOR_METRICS, alpha=ridge_all_alpha),
            features=PREDICTOR_METRICS,
            notes=f"Most frequent alpha: {ridge_all_alpha:g}.",
        )
    )

    ridge_family_results = {}
    for family, features in PREDICTOR_FAMILIES.items():
        result = _nested_random_ridge(sample, features, RIDGE_ALPHA_GRID)
        alpha = _most_frequent_alpha(result)
        key = f"ridge_{family}"
        ridge_family_results[key] = result
        model_results[key] = result
        leaderboard.append(
            _leaderboard_row(
                f"Ridge, {family.replace('_', ' ')} metrics",
                "nested_ridge_family",
                result,
                _in_sample_ridge(sample, features, alpha=alpha),
                features=features,
                family=family,
                notes=f"Most frequent alpha: {alpha:g}.",
            )
        )

    component_grid = list(range(1, min(len(PREDICTOR_METRICS), 8) + 1))
    pcr_all = _nested_random_pcr(sample, PREDICTOR_METRICS, component_grid)
    pcr_components = _most_frequent_components(pcr_all)
    model_results["pcr_all_chess_metrics"] = pcr_all
    leaderboard.append(
        _leaderboard_row(
            "PCR latent factor, all chess metrics",
            "nested_pcr",
            pcr_all,
            _in_sample_pcr(sample, PREDICTOR_METRICS, n_components=pcr_components),
            features=PREDICTOR_METRICS,
            notes=f"Most frequent component count: {pcr_components}.",
        )
    )

    leaderboard.sort(key=lambda row: float(row["cv"]["r2"]), reverse=True)
    best_model_name = leaderboard[0]["name"]
    best_model_key = next(
        key
        for key, result in model_results.items()
        if result["r2"] == leaderboard[0]["cv"]["r2"]
    )

    best_alpha_for_stability = _most_frequent_alpha(ridge_all)
    coefficient_stability = _bootstrap_ridge_coefficients(
        sample,
        PREDICTOR_METRICS,
        alpha=best_alpha_for_stability,
        n_bootstrap=1000,
        seed=17,
    )
    coefficient_stability.sort(
        key=lambda row: (row["sign_stability"], abs(row["median"])),
        reverse=True,
    )

    loo_rows = []
    best_features = leaderboard[0].get("features", PREDICTOR_METRICS)
    best_type = leaderboard[0]["type"]
    for test_idx in range(len(sample)):
        train_df = sample.drop(index=test_idx).reset_index(drop=True)
        test_df = sample.iloc[[test_idx]]
        if best_type == "nested_ridge":
            predicted = _ridge_predict(train_df, test_df, best_features, alpha=best_alpha_for_stability)[0]
        elif best_type == "nested_pcr":
            predicted = _pcr_predict(train_df, test_df, best_features, n_components=pcr_components)[0]
        else:
            predicted = _ols_predict(train_df, test_df, best_features)[0]
        loo_rows.append(
            {
                "llm_chess_model": sample.iloc[test_idx]["llm_chess_model"],
                "Model": sample.iloc[test_idx]["Model"],
                "actual": float(sample.iloc[test_idx]["Score"]),
                "predicted": float(predicted),
                "residual": float(sample.iloc[test_idx]["Score"] - predicted),
            }
        )

    loo_score = _regression_score(
        [row["actual"] for row in loo_rows],
        [row["predicted"] for row in loo_rows],
    )
    for row in loo_rows:
        row["abs_error"] = abs(row["residual"])

    date_sanity_sample = sample.dropna(subset=DATE_SANITY_FEATURES).reset_index(drop=True)
    date_only = _repeated_cv_ols(date_sanity_sample, DATE_SANITY_FEATURES)
    best_chess_features = list(leaderboard[0].get("features", []))
    date_plus_best_chess = _repeated_cv_ols(
        date_sanity_sample,
        DATE_SANITY_FEATURES + best_chess_features,
    )

    return {
        "target": "Epoch Score",
        "sample_n": int(len(sample)),
        "cv_protocol": {
            "outer_folds": PREDICTION_OUTER_FOLDS,
            "inner_folds": PREDICTION_INNER_FOLDS,
            "repeats": len(PREDICTION_CV_SEEDS),
            "seeds": PREDICTION_CV_SEEDS,
            "selection": "Any best metric/combo, ridge alpha, or PCR component count is selected inside the outer training fold.",
            "compact_search_screen": f"Compact subset search screens to the top {COMPACT_SCREEN_METRIC_LIMIT} metrics by training-fold absolute Pearson association before inner-CV combination search.",
        },
        "predictor_families": PREDICTOR_FAMILIES,
        "best_model": {
            "name": best_model_name,
            "key": best_model_key,
            "cv": leaderboard[0]["cv"],
            "features": leaderboard[0].get("features", []),
        },
        "model_leaderboard": leaderboard,
        "selected_metric_combinations": {
            "best_single_metric": {
                "combination_frequency": single_result["combination_frequency"],
                "metric_selection_frequency": single_result["metric_selection_frequency"],
            },
            **{
                key: {
                    "combination_frequency": result["combination_frequency"],
                    "metric_selection_frequency": result["metric_selection_frequency"],
                }
                for key, result in compact_results.items()
            },
        },
        "feature_stability": {
            "model": "Ridge over all chess metrics on full sample",
            "alpha": best_alpha_for_stability,
            "coefficients": coefficient_stability,
        },
        "top_prediction_misses": model_results[best_model_key]["top_prediction_misses"],
        "leave_one_out_sensitivity": {
            **loo_score,
            "top_misses": sorted(
                loo_rows,
                key=lambda row: row["abs_error"],
                reverse=True,
            )[:12],
        },
        "date_sanity_check": {
            "sample_n": int(len(date_sanity_sample)),
            "date_features": DATE_SANITY_FEATURES,
            "date_only_repeated_cv": {
                key: date_only[key]
                for key in ["r2", "rmse", "mae", "rank_spearman"]
            },
            "date_plus_best_chess_repeated_cv": {
                key: date_plus_best_chess[key]
                for key in ["r2", "rmse", "mae", "rank_spearman"]
            },
        },
    }


def _blocked_cv_ols(
    df: pd.DataFrame,
    features: list[str],
    n_folds: int = 5,
) -> dict[str, float]:
    folds = _split_contiguous_folds(len(df), n_folds)
    y_true: list[float] = []
    y_pred: list[float] = []
    for test_idx in folds:
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ols_predict(train_df, test_df, features).tolist())
    return _regression_score(y_true, y_pred)


def _blocked_cv_ridge(
    df: pd.DataFrame,
    features: list[str],
    alpha: float,
    n_folds: int = 5,
) -> dict[str, float]:
    folds = _split_contiguous_folds(len(df), n_folds)
    y_true: list[float] = []
    y_pred: list[float] = []
    for test_idx in folds:
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ridge_predict(train_df, test_df, features, alpha=alpha).tolist())
    return _regression_score(y_true, y_pred)


def _nested_blocked_ridge(
    df: pd.DataFrame,
    features: list[str],
    alpha_grid: list[float],
    outer_folds: int = 5,
    inner_folds: int = 4,
) -> dict[str, object]:
    outer = _split_contiguous_folds(len(df), outer_folds)
    y_true: list[float] = []
    y_pred: list[float] = []
    chosen_alphas: list[float] = []

    for test_idx in outer:
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx].reset_index(drop=True)
        test_df = df.iloc[test_idx].reset_index(drop=True)

        best_alpha = None
        best_r2 = None
        for alpha in alpha_grid:
            inner_result = _blocked_cv_ridge(
                train_df,
                features,
                alpha=alpha,
                n_folds=min(inner_folds, len(train_df)),
            )
            if best_r2 is None or inner_result["r2"] > best_r2:
                best_alpha = alpha
                best_r2 = inner_result["r2"]

        chosen_alphas.append(float(best_alpha))
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ridge_predict(train_df, test_df, features, alpha=float(best_alpha)).tolist())

    return {
        **_regression_score(y_true, y_pred),
        "chosen_alphas": chosen_alphas,
    }


def _nested_blocked_subset_search(
    df: pd.DataFrame,
    base_features: list[str],
    candidate_metrics: list[str],
    subset_size: int,
    outer_folds: int = 5,
    inner_folds: int = 4,
) -> dict[str, object]:
    outer = _split_contiguous_folds(len(df), outer_folds)
    y_true: list[float] = []
    y_pred: list[float] = []
    chosen_subsets: list[dict[str, object]] = []

    for test_idx in outer:
        train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
        train_df = df.iloc[train_idx].reset_index(drop=True)
        test_df = df.iloc[test_idx].reset_index(drop=True)

        best_subset = None
        best_r2 = None
        for subset in itertools.combinations(candidate_metrics, subset_size):
            features = base_features + list(subset)
            result = _blocked_cv_ols(
                train_df,
                features,
                n_folds=min(inner_folds, len(train_df)),
            )
            if best_r2 is None or result["r2"] > best_r2:
                best_subset = subset
                best_r2 = result["r2"]

        features = base_features + list(best_subset)
        chosen_subsets.append(
            {
                "metrics": list(best_subset),
                "inner_cv_r2": float(best_r2),
            }
        )
        y_true.extend(test_df["Score"].tolist())
        y_pred.extend(_ols_predict(train_df, test_df, features).tolist())

    return {
        **_regression_score(y_true, y_pred),
        "chosen_subsets": chosen_subsets,
    }


def _ridge_coefficients(
    df: pd.DataFrame,
    features: list[str],
    alpha: float,
) -> np.ndarray:
    x = df[features].to_numpy(dtype=float)
    y = df["Score"].to_numpy(dtype=float)
    feature_mean = x.mean(axis=0)
    feature_std = x.std(axis=0, ddof=0)
    feature_std = np.where(feature_std == 0, 1.0, feature_std)
    x_scaled = (x - feature_mean) / feature_std
    y_centered = y - y.mean()
    return np.linalg.solve(
        x_scaled.T @ x_scaled + alpha * np.eye(x_scaled.shape[1]),
        x_scaled.T @ y_centered,
    )


def _bootstrap_ridge_coefficients(
    df: pd.DataFrame,
    features: list[str],
    alpha: float,
    n_bootstrap: int = 2000,
    seed: int = 0,
) -> list[dict[str, object]]:
    rng = np.random.default_rng(seed)
    coefficients = []
    for _ in range(n_bootstrap):
        sample_idx = rng.integers(0, len(df), len(df))
        sample_df = df.iloc[sample_idx].reset_index(drop=True)
        coefficients.append(_ridge_coefficients(sample_df, features, alpha=alpha))

    coefficient_matrix = np.vstack(coefficients)
    rows = []
    for idx, feature in enumerate(features):
        feature_values = coefficient_matrix[:, idx]
        positive_share = float((feature_values > 0).mean())
        negative_share = float((feature_values < 0).mean())
        rows.append(
            {
                "feature": feature,
                "median": float(np.quantile(feature_values, 0.5)),
                "ci_95": [
                    float(np.quantile(feature_values, 0.025)),
                    float(np.quantile(feature_values, 0.975)),
                ],
                "sign_stability": float(max(positive_share, negative_share)),
            }
        )
    return rows


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    elo = pd.read_csv(ELO_CSV)
    epoch = pd.read_csv(ECI_CSV)
    metadata = pd.read_csv(METADATA_CSV)

    _clean_key_column(elo, "Player")
    _clean_key_column(epoch, "llm_chess_model")
    _clean_key_column(metadata, "model")

    elo["elo"] = pd.to_numeric(elo["elo"], errors="coerce")
    elo["elo_moe_95"] = pd.to_numeric(elo["elo_moe_95"], errors="coerce")
    elo["total_games"] = pd.to_numeric(elo["total_games"], errors="coerce")
    epoch["Score"] = pd.to_numeric(epoch["Score"], errors="coerce")

    cis = epoch["90% CI"].apply(_parse_epoch_ci)
    epoch["eci_ci_low"] = [low for low, _ in cis]
    epoch["eci_ci_high"] = [high for _, high in cis]
    epoch["eci_ci90_half_width"] = (
        epoch["eci_ci_high"] - epoch["eci_ci_low"]
    ) / 2.0

    metadata["date_released"] = metadata["date_released"].astype(str).str.strip()
    return elo, epoch, metadata


def build_summary() -> dict[str, object]:
    elo, epoch, metadata = load_data()

    elo_valid = elo.dropna(subset=["Player", "elo"]).copy()
    epoch_valid = epoch.dropna(subset=["Score"]).copy()
    epoch_bridge = epoch_valid.dropna(subset=["llm_chess_model"]).copy()

    duplicate_counts = epoch_bridge["llm_chess_model"].value_counts()
    duplicate_keys = duplicate_counts[duplicate_counts > 1]

    raw_direct_matches = epoch_bridge.merge(
        elo_valid[["Player", "elo"]],
        left_on="llm_chess_model",
        right_on="Player",
        how="inner",
    )

    merged = _dedupe_epoch_bridge(epoch_valid, "max").merge(
        elo_valid,
        left_on="llm_chess_model",
        right_on="Player",
        how="inner",
    )
    merged = merged.merge(
        metadata[["model", "date_released", "reasoning_status"]],
        left_on="Player",
        right_on="model",
        how="left",
    )
    merged["release_month"] = pd.to_datetime(
        merged["date_released"], format="%Y-%m", errors="coerce"
    )
    release_min = merged["release_month"].min()
    merged["release_month_index"] = (
        (merged["release_month"].dt.year - release_min.year) * 12
        + (merged["release_month"].dt.month - release_min.month)
    ).astype(float)
    merged["release_month_sq"] = np.square(merged["release_month_index"])

    relationship = _named_corr("eci_vs_elo", merged["Score"], merged["elo"])

    weights = 1.0 / np.square(
        merged["elo_moe_95"]
        .fillna(merged["elo_moe_95"].median())
        .replace(0, merged["elo_moe_95"].median())
    )
    weighted_coef = np.polyfit(merged["Score"], merged["elo"], 1, w=weights)
    weighted_pred = np.polyval(weighted_coef, merged["Score"])
    weighted_ss_res = np.sum(weights * np.square(merged["elo"] - weighted_pred))
    weighted_mean = np.average(merged["elo"], weights=weights)
    weighted_ss_tot = np.sum(weights * np.square(merged["elo"] - weighted_mean))

    release_confound = {
        "eci_vs_release_month": _named_corr(
            "eci_vs_release_month",
            merged["release_month_index"],
            merged["Score"],
        ),
        "elo_vs_release_month": _named_corr(
            "elo_vs_release_month",
            merged["release_month_index"],
            merged["elo"],
        ),
        "eci_vs_elo_partial_release_month": _partial_corr_release_month(
            merged["Score"],
            merged["elo"],
            merged["release_month_index"],
        ),
    }

    bootstrap_rng = np.random.default_rng(0)
    bootstrap_pearson = []
    bootstrap_spearman = []
    bootstrap_slope = []
    for _ in range(5000):
        sample_idx = bootstrap_rng.integers(0, len(merged), len(merged))
        sample = merged.iloc[sample_idx]
        bootstrap_pearson.append(stats.pearsonr(sample["Score"], sample["elo"]).statistic)
        bootstrap_spearman.append(stats.spearmanr(sample["Score"], sample["elo"]).statistic)
        bootstrap_slope.append(stats.linregress(sample["Score"], sample["elo"]).slope)

    leave_one_out = []
    base_r = relationship["pearson_r"]
    base_slope = relationship["slope"]
    for index, row in merged.iterrows():
        sample = merged.drop(index=index)
        loo_r = stats.pearsonr(sample["Score"], sample["elo"]).statistic
        loo_slope = stats.linregress(sample["Score"], sample["elo"]).slope
        leave_one_out.append(
            {
                "llm_chess_model": row["llm_chess_model"],
                "pearson_delta": float(loo_r - base_r),
                "slope_delta": float(loo_slope - base_slope),
            }
        )

    metric_relationships = []
    for metric in SELECTED_METRICS:
        metric_corr = _named_corr(metric, merged["Score"], merged[metric])
        metric_corr["partial_release_month"] = _partial_corr_release_month(
            merged["Score"],
            merged[metric],
            merged["release_month_index"],
        )
        metric_relationships.append(metric_corr)

    thresholds = []
    for threshold in GAME_THRESHOLDS:
        sample = merged[merged["total_games"] >= threshold]
        thresholds.append(
            {
                "min_total_games": threshold,
                **_named_corr(f"eci_vs_elo_min_games_{threshold}", sample["Score"], sample["elo"]),
            }
        )

    coverage = []
    ranked_epoch = epoch_valid.sort_values("Score", ascending=False).reset_index(drop=True)
    matched_keys = set(merged["llm_chess_model"])
    for top_n in TOP_N_COVERAGE:
        top = ranked_epoch.head(top_n)
        matched_count = int(top["llm_chess_model"].isin(matched_keys).sum())
        bridged_count = int(top["llm_chess_model"].notna().sum())
        coverage.append(
            {
                "top_n": top_n,
                "matched_count": matched_count,
                "matched_pct": matched_count / top_n,
                "bridged_count": bridged_count,
                "bridged_pct": bridged_count / top_n,
            }
        )

    dedupe_sensitivity = []
    for method in ["max", "min", "mean", "median"]:
        sample = _dedupe_epoch_bridge(epoch_valid, method).merge(
            elo_valid[["Player", "elo"]],
            left_on="llm_chess_model",
            right_on="Player",
            how="inner",
        )
        dedupe_sensitivity.append(
            {
                "method": method,
                **_named_corr(f"eci_vs_elo_{method}", sample["Score"], sample["elo"]),
            }
        )

    matchedness = epoch_valid.copy()
    matchedness["vendor"] = matchedness["Model"].map(_vendor_from_label)
    matchedness["has_bridge"] = matchedness["llm_chess_model"].notna()
    matchedness["matched"] = matchedness["llm_chess_model"].isin(matched_keys)

    slope = relationship["slope"]
    intercept = relationship["intercept"]
    merged["predicted_elo"] = intercept + slope * merged["Score"]
    merged["residual"] = merged["elo"] - merged["predicted_elo"]
    merged["eci_rank"] = merged["Score"].rank(ascending=False, method="min")
    merged["elo_rank"] = merged["elo"].rank(ascending=False, method="min")
    merged["rank_gap"] = merged["elo_rank"] - merged["eci_rank"]
    merged["vendor"] = merged["Model"].map(_vendor_from_label)

    missing_bridge = (
        epoch_valid[epoch_valid["llm_chess_model"].isna()]
        .sort_values("Score", ascending=False)[["Model", "Score"]]
        .head(20)
        .to_dict(orient="records")
    )
    bridged_unmatched = (
        epoch_bridge.merge(
            elo_valid[["Player"]],
            left_on="llm_chess_model",
            right_on="Player",
            how="left",
            indicator=True,
        )
        .query("_merge == 'left_only'")
        .sort_values("Score", ascending=False)[["Model", "llm_chess_model", "Score"]]
        .head(20)
        .to_dict(orient="records")
    )

    matchedness_summary = (
        matchedness.groupby(["has_bridge", "matched"], as_index=False)
        .agg(
            n=("Model", "size"),
            mean_score=("Score", "mean"),
            median_score=("Score", "median"),
        )
        .to_dict(orient="records")
    )
    vendor_mix = []
    vendor_table = pd.crosstab(matchedness["vendor"], [matchedness["has_bridge"], matchedness["matched"]])
    for vendor_name, row in vendor_table.iterrows():
        vendor_mix.append(
            {
                "vendor": vendor_name,
                "no_bridge_unmatched": int(row.get((False, False), 0)),
                "has_bridge_unmatched": int(row.get((True, False), 0)),
                "matched": int(row.get((True, True), 0)),
            }
        )

    vendor_residuals = (
        merged.groupby("vendor", as_index=False)
        .agg(
            n=("vendor", "size"),
            avg_residual=("residual", "mean"),
            median_residual=("residual", "median"),
            avg_score=("Score", "mean"),
        )
        .sort_values("avg_residual", ascending=False)
        .to_dict(orient="records")
    )

    prediction = _build_prediction_summary(merged)

    return {
        "files": {
            "elo_refined_csv": str(ELO_CSV.relative_to(REPO_ROOT)),
            "epoch_eci_csv": str(ECI_CSV.relative_to(REPO_ROOT)),
            "models_metadata_csv": str(METADATA_CSV.relative_to(REPO_ROOT)),
        },
        "counts": {
            "elo_rows": int(len(elo)),
            "epoch_rows": int(len(epoch)),
            "epoch_rows_with_numeric_score": int(len(epoch_valid)),
            "epoch_rows_with_bridge": int(epoch_valid["llm_chess_model"].notna().sum()),
            "raw_direct_matches": int(len(raw_direct_matches)),
            "matched_sample_max_dedupe": int(len(merged)),
        },
        "duplicate_bridge_keys": {
            "n_keys": int(len(duplicate_keys)),
            "n_extra_rows": int((duplicate_keys - 1).sum()),
            "counts": {key: int(value) for key, value in duplicate_keys.items()},
        },
        "relationship": {
            **relationship,
            "weighted_fit": {
                "slope": float(weighted_coef[0]),
                "intercept": float(weighted_coef[1]),
                "weighted_r2": float(1.0 - weighted_ss_res / weighted_ss_tot),
            },
            "bootstrap_95": {
                "pearson_r": [
                    float(np.quantile(bootstrap_pearson, 0.025)),
                    float(np.quantile(bootstrap_pearson, 0.975)),
                ],
                "spearman_r": [
                    float(np.quantile(bootstrap_spearman, 0.025)),
                    float(np.quantile(bootstrap_spearman, 0.975)),
                ],
                "slope": [
                    float(np.quantile(bootstrap_slope, 0.025)),
                    float(np.quantile(bootstrap_slope, 0.975)),
                ],
            },
            "leave_one_out_top_influence": sorted(
                leave_one_out,
                key=lambda row: abs(row["pearson_delta"]),
                reverse=True,
            )[:12],
        },
        "release_confound": release_confound,
        "selected_metric_relationships": metric_relationships,
        "game_threshold_sensitivity": thresholds,
        "coverage": coverage,
        "dedupe_sensitivity": dedupe_sensitivity,
        "selection_bias": {
            "matchedness_summary": matchedness_summary,
            "vendor_mix": vendor_mix,
            "top_missing_bridge_models": missing_bridge,
            "top_bridged_but_unmatched_models": bridged_unmatched,
        },
        "residuals": {
            "top_positive": (
                merged.sort_values("residual", ascending=False)[
                    ["llm_chess_model", "Model", "Score", "elo", "residual", "eci_rank", "elo_rank", "rank_gap"]
                ]
                .head(12)
                .to_dict(orient="records")
            ),
            "top_negative": (
                merged.sort_values("residual", ascending=True)[
                    ["llm_chess_model", "Model", "Score", "elo", "residual", "eci_rank", "elo_rank", "rank_gap"]
                ]
                .head(12)
                .to_dict(orient="records")
            ),
            "vendor_summary": vendor_residuals,
        },
        "prediction": prediction,
    }


def _html(value: object) -> str:
    if value is None:
        return "n/a"
    return html.escape(str(value), quote=True)


def _format_number(value: object, digits: int = 3, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _html(value)
    sign = "+" if signed else ""
    return f"{number:{sign}.{digits}f}"


def _format_percent(value: object, digits: int = 0) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return _html(value)


def _format_metric_name(value: object) -> str:
    return _html(str(value).replace("_", " "))


def _join_features(features: object) -> str:
    if not features:
        return "n/a"
    return ", ".join(str(feature) for feature in features)


def _table(headers: list[str], rows: list[list[object]], empty: str = "No rows.") -> str:
    if not rows:
        return f'<p class="muted">{_html(empty)}</p>'
    header_html = "".join(f"<th>{_html(header)}</th>" for header in headers)
    body_html = "\n".join(
        "<tr>"
        + "".join(f"<td>{_html(cell)}</td>" for cell in row)
        + "</tr>"
        for row in rows
    )
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody>"
        "</table></div>"
    )


def _section(section_id: str, title: str, content: str, note: str | None = None) -> str:
    note_html = f'<p class="section-note">{_html(note)}</p>' if note else ""
    return (
        f'<section id="{_html(section_id)}">'
        f"<h2>{_html(title)}</h2>"
        f"{note_html}"
        f"{content}"
        "</section>"
    )


def _card(label: str, value: object, detail: str | None = None) -> str:
    detail_html = f'<div class="card-detail">{_html(detail)}</div>' if detail else ""
    return (
        '<div class="card">'
        f'<div class="card-label">{_html(label)}</div>'
        f'<div class="card-value">{_html(value)}</div>'
        f"{detail_html}"
        "</div>"
    )


def _render_overview(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    relationship = summary["relationship"]
    prediction = summary["prediction"]
    best = prediction["best_model"]
    date = prediction["date_sanity_check"]
    date_only = date["date_only_repeated_cv"]["r2"]
    date_plus = date["date_plus_best_chess_repeated_cv"]["r2"]
    date_lift = float(date_plus) - float(date_only)

    cards = [
        _card(
            "Matched sample",
            counts["matched_sample_max_dedupe"],
            f"{counts['raw_direct_matches']} raw bridge matches",
        ),
        _card(
            "ECI vs Elo",
            _format_number(relationship["pearson_r"]),
            f"R2 {_format_number(relationship['r2'])}",
        ),
        _card(
            "Best chess-only model",
            best["name"],
            f"CV R2 {_format_number(best['cv']['r2'])}",
        ),
        _card(
            "Date + chess lift",
            _format_number(date_lift, digits=3, signed=True),
            f"date-only R2 {_format_number(date_only)}",
        ),
    ]
    return '<div class="cards">' + "".join(cards) + "</div>"


def _render_sample_quality(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    duplicate = summary["duplicate_bridge_keys"]
    count_rows = [
        ["LLM chess rows", counts["elo_rows"]],
        ["Epoch ECI rows", counts["epoch_rows"]],
        ["Epoch rows with numeric score", counts["epoch_rows_with_numeric_score"]],
        ["Epoch rows with bridge key", counts["epoch_rows_with_bridge"]],
        ["Raw direct matches", counts["raw_direct_matches"]],
        ["Matched sample after dedupe", counts["matched_sample_max_dedupe"]],
    ]
    duplicate_rows = [
        [key, count]
        for key, count in sorted(
            duplicate["counts"].items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    return (
        "<div class=\"grid two\">"
        "<div><h3>Input Counts</h3>"
        + _table(["Measure", "Value"], count_rows)
        + "</div><div><h3>Duplicate Bridge Keys</h3>"
        + _table(["Bridge key", "Rows"], duplicate_rows)
        + "</div></div>"
    )


def _render_relationship(summary: dict[str, object]) -> str:
    relationship = summary["relationship"]
    bootstrap = relationship["bootstrap_95"]
    core_rows = [
        ["n", relationship["n"]],
        ["Pearson r", _format_number(relationship["pearson_r"])],
        ["Spearman rho", _format_number(relationship["spearman_r"])],
        ["OLS slope: Elo per ECI", _format_number(relationship["slope"], digits=2)],
        ["OLS R2", _format_number(relationship["r2"])],
        [
            "Pearson bootstrap 95%",
            f"{_format_number(bootstrap['pearson_r'][0])} to {_format_number(bootstrap['pearson_r'][1])}",
        ],
        [
            "Slope bootstrap 95%",
            f"{_format_number(bootstrap['slope'][0], digits=2)} to {_format_number(bootstrap['slope'][1], digits=2)}",
        ],
        [
            "Weighted R2",
            _format_number(relationship["weighted_fit"]["weighted_r2"]),
        ],
    ]
    influence_rows = [
        [
            row["llm_chess_model"],
            _format_number(row["pearson_delta"], signed=True),
            _format_number(row["slope_delta"], digits=2, signed=True),
        ]
        for row in relationship["leave_one_out_top_influence"]
    ]
    return (
        "<div class=\"grid two\">"
        "<div><h3>Headline Fit</h3>"
        + _table(["Metric", "Value"], core_rows)
        + "</div><div><h3>Leave-One-Out Influence</h3>"
        + _table(["Model", "Delta r", "Delta slope"], influence_rows)
        + "</div></div>"
    )


def _render_release_confound(summary: dict[str, object]) -> str:
    release = summary["release_confound"]
    partial = release["eci_vs_elo_partial_release_month"]
    rows = [
        [
            "ECI vs release month",
            release["eci_vs_release_month"]["n"],
            _format_number(release["eci_vs_release_month"]["pearson_r"]),
            _format_number(release["eci_vs_release_month"]["spearman_r"]),
        ],
        [
            "Elo vs release month",
            release["elo_vs_release_month"]["n"],
            _format_number(release["elo_vs_release_month"]["pearson_r"]),
            _format_number(release["elo_vs_release_month"]["spearman_r"]),
        ],
        [
            "ECI vs Elo, release controlled",
            partial["n"],
            _format_number(partial["pearson_r"]),
            _format_number(partial["spearman_r"]),
        ],
    ]
    return _table(["View", "n", "Pearson r", "Spearman rho"], rows)


def _render_prediction(summary: dict[str, object]) -> str:
    prediction = summary["prediction"]
    leaderboard_rows = [
        [
            row["name"],
            _format_number(row["cv"]["r2"]),
            _format_number(row["cv"]["rmse"], digits=2),
            _format_number(row["cv"]["mae"], digits=2),
            _format_number(row["cv"]["rank_spearman"]),
            _join_features(row.get("features")),
        ]
        for row in prediction["model_leaderboard"]
    ]

    combo_rows = []
    for search_name, search in prediction["selected_metric_combinations"].items():
        frequencies = search["combination_frequency"]
        top = frequencies[0] if frequencies else {"metrics": [], "count": 0}
        combo_rows.append(
            [
                search_name.replace("_", " "),
                _join_features(top["metrics"]),
                top["count"],
            ]
        )

    date = prediction["date_sanity_check"]
    date_rows = [
        [
            "Date only",
            _format_number(date["date_only_repeated_cv"]["r2"]),
            _format_number(date["date_only_repeated_cv"]["rmse"], digits=2),
            _format_number(date["date_only_repeated_cv"]["mae"], digits=2),
            _format_number(date["date_only_repeated_cv"]["rank_spearman"]),
        ],
        [
            "Date + best chess bundle",
            _format_number(date["date_plus_best_chess_repeated_cv"]["r2"]),
            _format_number(date["date_plus_best_chess_repeated_cv"]["rmse"], digits=2),
            _format_number(date["date_plus_best_chess_repeated_cv"]["mae"], digits=2),
            _format_number(date["date_plus_best_chess_repeated_cv"]["rank_spearman"]),
        ],
    ]

    return (
        "<h3>Model Leaderboard</h3>"
        + _table(["Model", "CV R2", "RMSE", "MAE", "Rank rho", "Features"], leaderboard_rows)
        + "<div class=\"grid two\"><div><h3>Compact Bundle Stability</h3>"
        + _table(["Search", "Most frequent metrics", "Count"], combo_rows)
        + "</div><div><h3>Date Sanity Check</h3>"
        + _table(["Model", "R2", "RMSE", "MAE", "Rank rho"], date_rows)
        + "</div></div>"
    )


def _render_metric_signal(summary: dict[str, object]) -> str:
    rows = []
    for metric in summary["selected_metric_relationships"]:
        partial = metric.get("partial_release_month") or {}
        rows.append(
            [
                _format_metric_name(metric["name"]),
                metric["n"],
                _format_number(metric.get("pearson_r")),
                _format_number(partial.get("pearson_r")),
                _format_number(partial.get("spearman_r")),
            ]
        )

    rows.sort(
        key=lambda row: abs(float(row[3])) if row[3] != "n/a" else -1,
        reverse=True,
    )
    return _table(
        ["Metric", "n", "Raw Pearson r", "Partial Pearson r", "Partial Spearman rho"],
        rows,
    )


def _render_sensitivity(summary: dict[str, object]) -> str:
    dedupe_rows = [
        [
            row["method"],
            row["n"],
            _format_number(row["pearson_r"]),
            _format_number(row["spearman_r"]),
            _format_number(row["slope"], digits=2),
            _format_number(row["r2"]),
        ]
        for row in summary["dedupe_sensitivity"]
    ]
    threshold_rows = [
        [
            row["min_total_games"],
            row["n"],
            _format_number(row.get("pearson_r")),
            _format_number(row.get("spearman_r")),
        ]
        for row in summary["game_threshold_sensitivity"]
    ]
    return (
        "<div class=\"grid two\"><div><h3>Dedupe Rule</h3>"
        + _table(["Rule", "n", "Pearson r", "Spearman rho", "Slope", "R2"], dedupe_rows)
        + "</div><div><h3>Minimum Game Count</h3>"
        + _table(["Min games", "n", "Pearson r", "Spearman rho"], threshold_rows)
        + "</div></div>"
    )


def _render_coverage(summary: dict[str, object]) -> str:
    coverage_rows = [
        [
            row["top_n"],
            f"{row['matched_count']} ({_format_percent(row['matched_pct'])})",
            f"{row['bridged_count']} ({_format_percent(row['bridged_pct'])})",
        ]
        for row in summary["coverage"]
    ]
    matched_rows = [
        [
            str(row["has_bridge"]),
            str(row["matched"]),
            row["n"],
            _format_number(row["mean_score"], digits=1),
            _format_number(row["median_score"], digits=1),
        ]
        for row in summary["selection_bias"]["matchedness_summary"]
    ]
    vendor_rows = [
        [
            row["vendor"],
            row["matched"],
            row["has_bridge_unmatched"],
            row["no_bridge_unmatched"],
        ]
        for row in summary["selection_bias"]["vendor_mix"]
    ]
    return (
        "<h3>Top-ECI Coverage</h3>"
        + _table(["ECI slice", "Matched", "Bridged"], coverage_rows)
        + "<div class=\"grid two\"><div><h3>Matchedness</h3>"
        + _table(["Has bridge", "Matched", "n", "Mean ECI", "Median ECI"], matched_rows)
        + "</div><div><h3>Vendor Mix</h3>"
        + _table(["Vendor", "Matched", "Bridged unmatched", "No bridge"], vendor_rows)
        + "</div></div>"
    )


def _render_outliers(summary: dict[str, object]) -> str:
    miss_rows = [
        [
            row["llm_chess_model"],
            row["Model"],
            _format_number(row["Score"], digits=1),
            _format_number(row["predicted"], digits=1),
            _format_number(row["residual"], digits=1, signed=True),
        ]
        for row in summary["prediction"]["top_prediction_misses"][:10]
    ]
    positive_rows = [
        [
            row["llm_chess_model"],
            row["Model"],
            _format_number(row["Score"], digits=1),
            _format_number(row["elo"], digits=1),
            _format_number(row["residual"], digits=1, signed=True),
        ]
        for row in summary["residuals"]["top_positive"][:10]
    ]
    negative_rows = [
        [
            row["llm_chess_model"],
            row["Model"],
            _format_number(row["Score"], digits=1),
            _format_number(row["elo"], digits=1),
            _format_number(row["residual"], digits=1, signed=True),
        ]
        for row in summary["residuals"]["top_negative"][:10]
    ]
    return (
        "<h3>Prediction Misses</h3>"
        + _table(["LLM chess model", "Epoch model", "Actual ECI", "Predicted ECI", "Residual"], miss_rows)
        + "<div class=\"grid two\"><div><h3>Above Elo Trend</h3>"
        + _table(["LLM chess model", "Epoch model", "ECI", "Elo", "Residual"], positive_rows)
        + "</div><div><h3>Below Elo Trend</h3>"
        + _table(["LLM chess model", "Epoch model", "ECI", "Elo", "Residual"], negative_rows)
        + "</div></div>"
    )


def render_html_dashboard(summary: dict[str, object]) -> str:
    embedded_json = json.dumps(summary, indent=2, sort_keys=False).replace("</", "<\\/")
    sections = [
        _section("overview", "Overview", _render_overview(summary)),
        _section(
            "sample",
            "Sample And Data Quality",
            _render_sample_quality(summary),
            "Counts, bridge coverage, and duplicate bridge keys that shape every downstream view.",
        ),
        _section(
            "relationship",
            "ECI vs Chess Elo",
            _render_relationship(summary),
            "Headline association and leave-one-out stability for the matched sample.",
        ),
        _section(
            "release",
            "Release-Date Confounding",
            _render_release_confound(summary),
            "The dashboard separates raw cross-model association from the shared release-time trend.",
        ),
        _section(
            "prediction",
            "Predicting ECI From Chess",
            _render_prediction(summary),
            "Out-of-sample model comparison using chess metrics only unless the row says date.",
        ),
        _section(
            "metrics",
            "Metric Signal",
            _render_metric_signal(summary),
            "Chess metrics sorted by release-controlled Pearson association with ECI.",
        ),
        _section(
            "sensitivity",
            "Sensitivity",
            _render_sensitivity(summary),
            "How bridge deduping and minimum game counts affect the headline relationship.",
        ),
        _section(
            "coverage",
            "Coverage And Selection",
            _render_coverage(summary),
            "What part of Epoch's frontier is represented in the chess benchmark bridge.",
        ),
        _section(
            "outliers",
            "Outliers",
            _render_outliers(summary),
            "Models where chess metrics and ECI disagree most strongly.",
        ),
    ]
    nav = "".join(
        f'<a href="#{section_id}">{_html(label)}</a>'
        for section_id, label in [
            ("overview", "Overview"),
            ("sample", "Sample"),
            ("relationship", "ECI vs Elo"),
            ("release", "Release"),
            ("prediction", "Prediction"),
            ("metrics", "Metrics"),
            ("sensitivity", "Sensitivity"),
            ("coverage", "Coverage"),
            ("outliers", "Outliers"),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LLM Chess vs Epoch ECI</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f7f5ef;
      --panel: #fffdf8;
      --ink: #1f2428;
      --muted: #6b7280;
      --line: #d8d1c3;
      --accent: #234f9f;
      --accent-soft: #e8eefc;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #111315;
        --panel: #181b1f;
        --ink: #eceff3;
        --muted: #a5acb8;
        --line: #323842;
        --accent: #8fb4ff;
        --accent-soft: #1c2942;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 32px max(24px, calc((100vw - 1180px) / 2));
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3 {{ line-height: 1.15; margin: 0; }}
    h1 {{ font-size: clamp(2rem, 5vw, 4rem); letter-spacing: -0.04em; }}
    h2 {{ font-size: 1.5rem; letter-spacing: -0.02em; }}
    h3 {{ font-size: 1rem; margin: 0 0 12px; }}
    .subtitle {{ color: var(--muted); max-width: 820px; margin: 12px 0 0; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; }}
    nav a {{
      color: var(--accent);
      background: var(--accent-soft);
      border: 1px solid transparent;
      border-radius: 999px;
      padding: 6px 11px;
      text-decoration: none;
      font-size: 0.88rem;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      margin: 18px 0;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }}
    .section-note, .muted {{ color: var(--muted); }}
    .section-note {{ margin: 8px 0 18px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: color-mix(in srgb, var(--panel) 90%, var(--accent-soft));
    }}
    .card-label {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .card-value {{ font-size: 1.5rem; font-weight: 700; margin-top: 8px; }}
    .card-detail {{ color: var(--muted); margin-top: 4px; }}
    .grid {{ display: grid; gap: 18px; margin-top: 16px; }}
    .grid.two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 560px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ background: var(--accent-soft); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    tr:last-child td {{ border-bottom: 0; }}
    td:not(:first-child), th:not(:first-child) {{ white-space: nowrap; }}
    details {{
      max-width: 1180px;
      margin: 18px auto 40px;
      padding: 0 24px;
      color: var(--muted);
    }}
    summary {{ cursor: pointer; color: var(--accent); }}
    pre {{
      overflow-x: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      color: var(--ink);
    }}
    @media (max-width: 900px) {{
      .cards, .grid.two {{ grid-template-columns: 1fr; }}
      section {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>LLM Chess vs Epoch ECI</h1>
    <p class="subtitle">Static dashboard generated from <code>eci_prediction_summary.json</code>. The layout is fixed; the numbers come from the current analysis run.</p>
    <nav>{nav}</nav>
  </header>
  <main>
    {''.join(sections)}
  </main>
  <details>
    <summary>Embedded JSON payload</summary>
    <pre id="summary-json"></pre>
  </details>
  <script id="summary-data" type="application/json">{embedded_json}</script>
  <script>
    const summaryText = document.getElementById("summary-data").textContent;
    document.getElementById("summary-json").textContent = summaryText;
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze the relationship between LLM Chess metrics and Epoch ECI."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. Defaults to stdout.",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        default=ARTIFACT_DIR / "index.html",
        help="HTML dashboard output path. Defaults to data/cross-ref/eci/index.html.",
    )
    args = parser.parse_args()

    summary = build_summary()
    payload = json.dumps(summary, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    args.html_output.write_text(render_html_dashboard(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
