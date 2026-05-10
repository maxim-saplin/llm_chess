from __future__ import annotations

import html
import json
import math


def _esc(value: object) -> str:
  if value is None:
    return "n/a"
  if isinstance(value, float) and math.isnan(value):
    return "n/a"
  return html.escape(str(value), quote=True)


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return _esc(value)


def _table_from_dicts(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return '<p class="muted">No rows.</p>'
    header = "".join(f"<th>{_esc(column)}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_esc(row.get(column))}</td>" for column in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def render_summary_html(summary: dict[str, object]) -> str:
    mapping = summary.get("mapping", {})
    mapping_source = summary.get("mapping_source_of_truth", {})
    coverage = summary.get("coverage", {})
    analysis_surfaces = summary.get("analysis_surfaces", {})
    funnel = summary.get("funnel", {})
    relationships = summary.get("relationships", {})
    prediction = summary.get("prediction", {})
    verification = summary.get("verification", {})
    primary = relationships.get("raw_elo", {})
    unresolved = mapping.get("unresolved_high_impact_rows", [])
    mapping_source_rows = [
        {
            key: ", ".join(value) if isinstance(value, list) else value
            for key, value in mapping_source.items()
            if key != "changed_source_bridge_examples"
        }
    ] if mapping_source else []
    mapping_source_examples = mapping_source.get("changed_source_bridge_examples", []) if isinstance(mapping_source, dict) else []
    analysis_surface_rows = []
    for surface in analysis_surfaces.values():
        analysis_surface_rows.append(
            {
                **surface,
                "used_by": ", ".join(surface.get("used_by", [])),
            }
        )
    funnel_rows = funnel.get("stages", []) if isinstance(funnel, dict) else []
    metric_sample = analysis_surfaces.get("metric_analysis", {}) if isinstance(analysis_surfaces, dict) else {}
    elo_sample = analysis_surfaces.get("elo_analysis", {}) if isinstance(analysis_surfaces, dict) else {}
    embedded_json = json.dumps(summary, indent=2, sort_keys=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{_esc(summary.get('eval_label', 'Cross Ref'))}</title>
  <style>
    :root {{
      --bg: #f2efe7;
      --panel: #fffdf7;
      --ink: #1f1f1b;
      --muted: #676252;
      --line: #d8d1c3;
      --accent: #15546f;
      --accent-soft: #dbeef3;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: radial-gradient(circle at top left, #fffef9, var(--bg)); color: var(--ink); font: 15px/1.5 Georgia, Cambria, serif; }}
    header {{ padding: 32px max(24px, calc((100vw - 1100px) / 2)); border-bottom: 1px solid var(--line); }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    h1, h2, h3 {{ line-height: 1.15; margin: 0; }}
    h1 {{ font-size: clamp(2rem, 5vw, 3.8rem); letter-spacing: -0.03em; }}
    h2 {{ font-size: 1.4rem; margin-bottom: 12px; }}
    p {{ margin: 0; }}
    nav {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }}
    nav a {{ color: var(--accent); background: var(--accent-soft); padding: 6px 10px; border-radius: 999px; text-decoration: none; font-size: 0.9rem; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 20px; margin: 18px 0; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04); }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid var(--line); border-radius: 14px; padding: 14px; background: color-mix(in srgb, var(--panel) 90%, var(--accent-soft)); }}
    .card .label {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .card .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 8px; }}
    .muted {{ color: var(--muted); }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 560px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: var(--accent-soft); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    tr:last-child td {{ border-bottom: 0; }}
    pre {{ overflow-x: auto; background: #f7f3ea; border: 1px solid var(--line); border-radius: 12px; padding: 16px; }}
    @media (max-width: 900px) {{ .cards {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{_esc(summary.get('eval_label', 'Cross Ref'))}</h1>
    <p class=\"muted\">{_esc(summary.get('summary_tagline', 'Cross-reference analysis output.'))}</p>
    <nav>
      <a href=\"#overview\">Overview</a>
      <a href=\"#mapping-source\">Mapping Source</a>
      <a href=\"#funnel\">Funnel</a>
      <a href=\"#mapping\">Mapping</a>
      <a href=\"#coverage\">Coverage</a>
      <a href=\"#relationships\">Relationships</a>
      <a href=\"#prediction\">Prediction</a>
      <a href=\"#verification\">Verification</a>
    </nav>
  </header>
  <main>
    <section id=\"overview\">
      <h2>Overview</h2>
      <div class=\"cards\">
        <div class=\"card\"><div class=\"label\">Metric analysis sample</div><div class=\"value\">{_esc(metric_sample.get('count'))}</div></div>
        <div class=\"card\"><div class=\"label\">Elo analysis sample</div><div class=\"value\">{_esc(elo_sample.get('count'))}</div></div>
        <div class=\"card\"><div class=\"label\">Numeric external rows</div><div class=\"value\">{_esc(coverage.get('numeric_score_rows'))}</div></div>
        <div class=\"card\"><div class=\"label\">Pearson r vs Elo</div><div class=\"value\">{_fmt(primary.get('pearson_r'))}</div></div>
      </div>
      <p class=\"muted\">{_esc(funnel.get('analysis_split_note', {}).get('metric_analysis'))}</p>
      <p class=\"muted\">{_esc(funnel.get('analysis_split_note', {}).get('elo_analysis'))}</p>
    </section>
    <section id=\"mapping-source\">
      <h2>Mapping Source Of Truth</h2>
      {_table_from_dicts(mapping_source_rows, list(mapping_source_rows[0].keys()) if mapping_source_rows else ['status'])}
      <h3>Source-bridge changes</h3>
      {_table_from_dicts(mapping_source_examples, ['eval_row_id', 'eval_model_label', 'source_llm_chess_model', 'llm_chess_player', 'mapping_status'])}
    </section>
    <section id=\"funnel\">
      <h2>Analysis Funnel</h2>
      {_table_from_dicts(funnel_rows, ['label', 'branch', 'count', 'filter_side', 'required_condition', 'dropped_from_previous'])}
      <h3>Analysis Surfaces</h3>
      {_table_from_dicts(analysis_surface_rows, ['stage_id', 'count', 'used_by', 'description'])}
    </section>
    <section id=\"mapping\">
      <h2>Mapping</h2>
      <p class=\"muted\">QA verdict: {_esc(mapping.get('qa_verdict'))}</p>
      {_table_from_dicts([mapping.get('mapping_file_status_counts', {})], list(mapping.get('mapping_file_status_counts', {}).keys()) or ['status'])}
      <h3>Unresolved high-impact rows</h3>
      {_table_from_dicts(unresolved, ['eval_row_id', 'eval_model_label', summary.get('target_score_column', 'score_numeric'), 'mapping_status', 'confidence', 'open_questions'])}
    </section>
    <section id=\"coverage\">
      <h2>Coverage</h2>
      {_table_from_dicts([coverage], list(coverage.keys()))}
    </section>
    <section id=\"relationships\">
      <h2>Relationships</h2>
      {_table_from_dicts([primary], list(primary.keys()))}
      <h3>Selected metrics</h3>
      {_table_from_dicts(relationships.get('selected_metrics', [])[:12], ['name', 'n', 'pearson_r', 'spearman_r', 'r2'])}
    </section>
    <section id=\"prediction\">
      <h2>Prediction</h2>
      {_table_from_dicts([prediction], [key for key in prediction.keys() if key != 'ols' and key != 'baseline_mean'])}
      <h3>Baseline</h3>
      {_table_from_dicts([prediction.get('baseline_mean', {})], list(prediction.get('baseline_mean', {}).keys()) or ['status'])}
      <h3>OLS</h3>
      {_table_from_dicts([prediction.get('ols', {})], [key for key in prediction.get('ols', {}).keys() if key != 'top_prediction_misses' and key != 'in_sample'] or ['status'])}
    </section>
    <section id=\"verification\">
      <h2>Verification</h2>
      {_table_from_dicts([verification], list(verification.keys()))}
    </section>
    <section>
      <h2>Embedded JSON</h2>
      <pre>{_esc(embedded_json)}</pre>
    </section>
  </main>
</body>
</html>
"""