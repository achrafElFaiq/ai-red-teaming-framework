# Report Model

This document describes the normalized report model produced by the framework.

## Source of truth

The normalized report model is defined by `AttackResult` in:

- `src/redteaming/domain/models/attack_result.py`

Persisted JSON files are produced by:

- `src/redteaming/infrastructure/persistence/json_report_store.py`

The dashboard reads those files from:

- `src/redteaming/ui/streamlit_dashboard.py`

## Top-level report fields

Every normalized report currently serializes the following fields:

- `framework`
- `attack_name`
- `target_url`
- `campaign_name`
- `campaign_run_id`
- `campaign_run_timestamp`
- `target_model`
- `target_architecture_type`
- `timestamp`
- `prompts`
- `conversation`

Important behavior:

- `prompts` may be `null`
- `conversation` may be `null`
- the model does not currently serialize an explicit `schema_version` field

## Garak-style payload

Garak-style normalized results use:

- `framework = "garak"`
- `prompts = [...]`
- `conversation = null`

Each prompt entry currently contains:

- `prompt`
- `response`
- `passed`
- `score`
- `rationale`
- `detector`

## PyRIT-style payload

PyRIT-style normalized results use:

- `framework = "pyrit"`
- `conversation = {...}`
- `prompts = null`

The conversation object currently contains:

- `conversation_id`
- `objective`
- `achieved`
- `turns`

Each turn currently contains:

- `turn`
- `prompt`
- `response`
- `score`
- `rationale`

## Semantic invariants

The report model currently guarantees:

- dashboard grouping uses `campaign_run_id` when present
- PyRIT results are conversation-oriented
- Garak results are prompt-list-oriented
- timestamps are serialized as ISO-compatible datetimes
- the dashboard reads the same normalized JSON structure written by the report store

## Related artifacts

Additional static contract artifacts live in:

- `schemas/report.schema.json`
