# RedTeaming Framework

A Python framework for running red teaming campaigns against HTTP/JSON chatbot targets, using `PyRIT` and `Garak`, then normalizing results into one report model.

## Overview

This repository provides:

- campaign-driven execution from YAML files
- `PyRIT` attacks (`dataset`, `crescendo`, `red_teaming`)
- `Garak` probe-based attacks
- normalized JSON reports written to `reports/`
- a Streamlit dashboard for report exploration
- CLI commands for run / validate / doctor / dashboard

## Supported frameworks

- `pyrit`
- `garak`

## Quickstart

### 1. Create a virtual environment

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the package

```zsh
pip install -e .
```

For test tooling:

```zsh
pip install -e '.[dev]'
```

Framework runtimes are installed separately when needed:

```zsh
pip install pyrit
pip install garak
```

### 3. Copy the environment template

```zsh
cp .env.example .env
```

For PyRIT campaigns, fill at least:

```dotenv
PYRIT_ATTACKER_ENDPOINT=...
PYRIT_ATTACKER_MODEL=...
PYRIT_ATTACKER_API_KEY=...
PYRIT_SCORER_ENDPOINT=...
PYRIT_SCORER_MODEL=...
PYRIT_SCORER_API_KEY=...
```

### 4. Run a campaign

```zsh
redteaming run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
```

Repository entrypoint:

```zsh
python main.py run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
```

## CLI

```text
redteaming run <campaign.yaml>
redteaming validate <campaign.yaml>
redteaming doctor <campaign.yaml>
redteaming dashboard
```

Useful variants:

```zsh
redteaming run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --log-level DEBUG
redteaming run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --skip-checks
redteaming run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --no-dashboard
redteaming validate examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
redteaming doctor examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
redteaming dashboard
```

## Campaign model

A campaign YAML defines:

- one target
- an ordered list of attack YAML files
- optional campaign metadata

Reference templates live in:

- `examples/templates/campaign.yaml`
- `examples/templates/attack_pyrit_dataset.yaml`
- `examples/templates/attack_pyrit_crescendo.yaml`
- `examples/templates/attack_pyrit_red_teaming.yaml`
- `examples/templates/attack_garak.yaml`

## Target contract summary

Targets are currently modeled as HTTP JSON chat endpoints.

The framework sends:

```json
{
  "<input_field>": "<prompt>"
}
```

and expects:

```json
{
  "<output_field>": "<response>"
}
```

Supported target features today:

- HTTP POST chat endpoint
- configurable input field
- configurable output field
- optional reset endpoint
- optional metadata (`model`, `architecture_type`)

See `docs/target-contract.md` for the full target contract.

## Architecture at a glance

Current high-level structure:

```text
src/redteaming/
├── application/      # campaign loading, orchestration, health checks
├── domain/           # models and contracts
├── infrastructure/   # config, HTTP target, persistence
├── plugins/          # pyrit and garak integrations
└── ui/               # streamlit dashboard
```

Execution flow:

```text
campaign YAML
→ target + attack definitions
→ plugin runner execution (PyRIT / Garak)
→ normalized AttackResult objects
→ JSON reports in reports/
→ dashboard analysis
```

## Reports

Normalized reports are written to:

```text
reports/
```

The report model is documented in:

- `docs/report-model.md`

The dashboard reads those normalized JSON files.

## Development

Run the full test suite:

```zsh
pytest -q
```

Examples:

```zsh
pytest tests/frameworks/test_pyrit_runner.py -q
pytest tests/frameworks/test_garak_runner.py -q
```

## Limitations

Current assumptions and constraints:

- targets are HTTP/JSON chat endpoints only
- target request/response semantics are simple field-based JSON
- framework-specific dependencies must be installed separately
- PyRIT and Garak execution models differ, but are normalized into one reporting layer
- reports are always written to `reports/`
- the Garak runtime config is internal and generated automatically under `.runtime/`

## Repository map

Top-level directories worth reading first:

- `src/redteaming/`
- `examples/`
- `docs/`
- `schemas/`
- `tests/`

## Documentation

For deeper detail, use:

- `docs/architecture.md`
- `docs/campaign-spec.md`
- `docs/target-contract.md`
- `docs/report-model.md`
- `docs/plugin-development.md`
