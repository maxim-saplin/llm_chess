### Log structure (as of Aug 8, 2025)

- **Timestamp format**: Each run is saved under `<YYYY-MM-DD-HH-MM-SS>` (local time, with seconds).
- **Model name suffixes**:
  - `-<reasoning_effort>` when set: `-low`, `-medium`, `-high`
  - `-tb_<budget>` when thinking mode is enabled with `budget_tokens`, e.g. `-tb_4096`
  - Order is always: effort first, then budget. Example: `o3-low-tb_4096`

### Top-level categories

- **rand_vs_llm**: One player is random, the other is an LLM (color-agnostic)
  - `_logs/rand_vs_llm/<llmModel+suffixes>/<YYYY-MM-DD-HH-MM-SS>/`

- **engine_vs_llm**: Chess engine vs LLM (color-agnostic; engine segment first)
  - `_logs/engine_vs_llm/<engineId>-lvl-<N>/<llmModel+suffixes>/<YYYY-MM-DD-HH-MM-SS>/`
  - `engineId` is `stockfish` or `dragon`

- **engine_vs_engine**: Engine vs engine (ordered by color)
  - `_logs/engine_vs_engine/<whiteEngineId>-lvl-<W>_vs_<blackEngineId>-lvl-<B>/<YYYY-MM-DD-HH-MM-SS>/`

- **llm_vs_llm**: LLM vs LLM (ordered by color)
  - `_logs/llm_vs_llm/<whiteModel+suffixes>_vs_<blackModel+suffixes>/<YYYY-MM-DD-HH-MM-SS>/`

- **misc**: Fallbacks such as engine_vs_random and random_vs_random
  - `_logs/misc/<YYYY-MM-DD-HH-MM-SS>/`

### Files inside a run folder

- `_run.json`: Run metadata (player types, configs, engine levels, etc.).
- `_aggregate_results.json`: Summary across all games in the run.
- `*.json`: Individual game logs named by game start time.
- `videos/` (optional): Per-game MP4s when visualization frames are captured.

### Migration note

On Aug 8, 2025, legacy logs were archived to `_logs/_pre_aug_2025/`. New runs follow the structure above.


