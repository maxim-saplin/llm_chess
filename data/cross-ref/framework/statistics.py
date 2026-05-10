from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_SELECTED_METRICS = [
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
DEFAULT_GAME_THRESHOLDS = [0, 20, 30, 40, 50, 60]
DEFAULT_CV_SEEDS = [11, 23, 37]


def named_corr(name: str, x: pd.Series, y: pd.Series) -> dict[str, float | int | str]:
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


def partial_corr_release_month(
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
    x = np.column_stack([np.ones(len(valid)), valid["release_month_index"].to_numpy(dtype=float)])
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


def add_release_month_columns(df: pd.DataFrame, date_column: str = "date_released") -> pd.DataFrame:
    prepared = df.copy()
    prepared["release_month"] = pd.to_datetime(prepared[date_column], errors="coerce")
    release_min = prepared["release_month"].dropna().min()
    if pd.isna(release_min):
        prepared["release_month_index"] = np.nan
        prepared["release_month_sq"] = np.nan
        return prepared
    prepared["release_month_index"] = (
        (prepared["release_month"].dt.year - release_min.year) * 12
        + (prepared["release_month"].dt.month - release_min.month)
    ).astype(float)
    prepared["release_month_sq"] = np.square(prepared["release_month_index"])
    return prepared


def bootstrap_corr(x: pd.Series, y: pd.Series, *, seed: int = 0, n_bootstrap: int = 2000) -> dict[str, list[float]] | None:
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 4:
        return None
    rng = np.random.default_rng(seed)
    pearson_samples = []
    spearman_samples = []
    slope_samples = []
    for _ in range(n_bootstrap):
        sample_idx = rng.integers(0, len(valid), len(valid))
        sample = valid.iloc[sample_idx]
        pearson_samples.append(stats.pearsonr(sample["x"], sample["y"]).statistic)
        spearman_samples.append(stats.spearmanr(sample["x"], sample["y"]).statistic)
        slope_samples.append(stats.linregress(sample["x"], sample["y"]).slope)
    return {
        "pearson_r": [float(np.quantile(pearson_samples, 0.025)), float(np.quantile(pearson_samples, 0.975))],
        "spearman_r": [float(np.quantile(spearman_samples, 0.025)), float(np.quantile(spearman_samples, 0.975))],
        "slope": [float(np.quantile(slope_samples, 0.025)), float(np.quantile(slope_samples, 0.975))],
    }


def regression_score(y_true: list[float] | np.ndarray, y_pred: list[float] | np.ndarray) -> dict[str, float | None]:
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
        "r2": None if sst == 0 else float(1.0 - sse / sst),
        "rmse": float(np.sqrt(np.mean(np.square(y_true_arr - y_pred_arr)))),
        "mae": float(np.mean(np.abs(y_true_arr - y_pred_arr))),
        "rank_spearman": None if np.isnan(spearman) else float(spearman),
    }


def split_random_folds(n_rows: int, n_folds: int, seed: int) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(n_rows)
    rng.shuffle(indices)
    return [fold.tolist() for fold in np.array_split(indices, min(n_folds, n_rows))]


def ols_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
    *,
    target_column: str,
) -> np.ndarray:
    train_x = np.column_stack([np.ones(len(train_df)), train_df[features].to_numpy(dtype=float)])
    train_y = train_df[target_column].to_numpy(dtype=float)
    beta = np.linalg.lstsq(train_x, train_y, rcond=None)[0]
    test_x = np.column_stack([np.ones(len(test_df)), test_df[features].to_numpy(dtype=float)])
    return test_x @ beta


def _prediction_summary_from_rows(
    sample: pd.DataFrame,
    prediction_rows: list[dict[str, float | int]],
    *,
    target_column: str,
) -> dict[str, object]:
    prediction_df = pd.DataFrame(prediction_rows)
    score = regression_score(
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
    labels = sample.reset_index(drop=True).copy()
    label_columns = [
        column
        for column in ["llm_chess_player", "eval_model_label", target_column, "elo"]
        if column in labels.columns
    ]
    per_model = per_model.merge(labels[label_columns].reset_index(names="row_index"), on="row_index", how="left")
    per_model["residual"] = per_model["actual"] - per_model["predicted"]
    per_model["abs_error"] = per_model["residual"].abs()
    return {
        **score,
        "top_prediction_misses": per_model.sort_values("abs_error", ascending=False).head(10).to_dict(orient="records"),
    }


def repeated_cv_mean(
    df: pd.DataFrame,
    *,
    target_column: str,
    seeds: list[int] | None = None,
    n_folds: int = 5,
) -> dict[str, object]:
    seeds = seeds or DEFAULT_CV_SEEDS
    prediction_rows = []
    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(split_random_folds(len(df), n_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_mean = float(df.iloc[train_idx][target_column].mean())
            for row_idx in test_idx:
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx][target_column]),
                        "predicted": train_mean,
                    }
                )
    return _prediction_summary_from_rows(df, prediction_rows, target_column=target_column)


def repeated_cv_ols(
    df: pd.DataFrame,
    features: list[str],
    *,
    target_column: str,
    seeds: list[int] | None = None,
    n_folds: int = 5,
) -> dict[str, object]:
    seeds = seeds or DEFAULT_CV_SEEDS
    prediction_rows = []
    for repeat_idx, seed in enumerate(seeds):
        for fold_idx, test_idx in enumerate(split_random_folds(len(df), n_folds, seed)):
            train_idx = [idx for idx in range(len(df)) if idx not in test_idx]
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]
            predictions = ols_predict(train_df, test_df, features, target_column=target_column)
            for row_idx, predicted in zip(test_idx, predictions, strict=True):
                prediction_rows.append(
                    {
                        "repeat": repeat_idx,
                        "fold": fold_idx,
                        "row_index": row_idx,
                        "actual": float(df.iloc[row_idx][target_column]),
                        "predicted": float(predicted),
                    }
                )
    return _prediction_summary_from_rows(df, prediction_rows, target_column=target_column)


def choose_features(
    df: pd.DataFrame,
    *,
    target_column: str,
    candidate_metrics: list[str],
    max_metrics: int = 4,
) -> list[str]:
    scored = []
    for metric in candidate_metrics:
        valid = df[[target_column, metric]].dropna()
        if len(valid) < 4 or valid[metric].std(ddof=0) == 0:
            continue
        corr = stats.pearsonr(valid[target_column], valid[metric]).statistic
        if np.isnan(corr):
            continue
        scored.append((abs(float(corr)), metric))
    return [metric for _, metric in sorted(scored, key=lambda row: (-row[0], row[1]))[:max_metrics]]


def build_metric_relationships(
    df: pd.DataFrame,
    *,
    target_column: str,
    candidate_metrics: list[str] | None = None,
) -> list[dict[str, object]]:
    candidate_metrics = candidate_metrics or DEFAULT_SELECTED_METRICS
    rows = []
    for metric in candidate_metrics:
        if metric not in df.columns:
            continue
        relationship = named_corr(metric, df[target_column], df[metric])
        if "release_month_index" in df.columns:
            relationship["partial_release_month"] = partial_corr_release_month(
                df[target_column], df[metric], df["release_month_index"]
            )
        rows.append(relationship)
    return rows


def build_game_threshold_sensitivity(
    df: pd.DataFrame,
    *,
    target_column: str,
    thresholds: list[int] | None = None,
) -> list[dict[str, object]]:
    thresholds = thresholds or DEFAULT_GAME_THRESHOLDS
    rows = []
    for threshold in thresholds:
        sample = df[df["total_games"] >= threshold]
        rows.append(
            {
                "min_total_games": threshold,
                **named_corr(f"{target_column}_vs_elo_min_games_{threshold}", sample[target_column], sample["elo"]),
            }
        )
    return rows


def build_prediction_summary(
    df: pd.DataFrame,
    *,
    target_column: str,
    candidate_metrics: list[str] | None = None,
) -> dict[str, object]:
    candidate_metrics = candidate_metrics or DEFAULT_SELECTED_METRICS
    features = choose_features(df, target_column=target_column, candidate_metrics=candidate_metrics)
    if not features:
        return {
            "status": "insufficient_features",
            "n": int(len(df)),
            "features": [],
        }
    model_df = df.dropna(subset=[target_column, *features]).reset_index(drop=True)
    if len(model_df) < 8:
        return {
            "status": "insufficient_sample",
            "n": int(len(model_df)),
            "features": features,
        }
    baseline = repeated_cv_mean(model_df, target_column=target_column)
    ols = repeated_cv_ols(model_df, features, target_column=target_column)
    in_sample = regression_score(
        model_df[target_column].to_numpy(dtype=float),
        ols_predict(model_df, model_df, features, target_column=target_column),
    )
    return {
        "status": "ok",
        "n": int(len(model_df)),
        "features": features,
        "baseline_mean": baseline,
        "ols": {
            **ols,
            "in_sample": in_sample,
        },
    }