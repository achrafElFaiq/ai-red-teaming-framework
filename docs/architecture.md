# Architecture

This document describes the current runtime architecture of the framework.

## Repository shape

The implementation lives under `src/redteaming/`.

High-level structure:

```text
main.py
src/
  redteaming/
    application/
    cli/
    domain/
    infrastructure/
    plugins/
    ui/
examples/
  campaigns/
  attacks/
  templates/
reports/
tests/
```

Key directories:

- `application/` — campaign loading, orchestration, health checks
- `cli/` — command routing and user-facing commands
- `domain/` — core models and contracts
- `infrastructure/` — runtime config, HTTP target, persistence
- `plugins/` — `pyrit` and `garak`
- `ui/` — Streamlit dashboard

## Runtime flow

The end-to-end execution flow is:

```text
campaign YAML
→ load_campaign()
→ CampaignConfig
→ AttackTarget
→ AttackOrchestrator
→ Attack.execute(target)
→ plugin runner (PyRIT or Garak)
→ normalizer
→ AttackResult
→ JsonReportStore
→ Streamlit dashboard
```

More explicitly:

1. the CLI loads a campaign file
2. campaign and attack YAML files are validated and parsed
3. an `AttackTarget` is built from the target section
4. `AttackOrchestrator` executes attacks in order
5. each attack delegates to its framework-specific runner
6. raw framework results are normalized into `AttackResult`
7. normalized reports are stored as JSON
8. the dashboard reads those reports for exploration

## Architectural responsibilities

### CLI

Main modules:

- `src/redteaming/cli/main.py`
- `src/redteaming/cli/run.py`
- `src/redteaming/cli/validate.py`
- `src/redteaming/cli/doctor.py`
- `src/redteaming/cli/dashboard.py`

Responsibilities:

- parse user commands
- configure logging
- load campaigns
- run validation and preflight checks
- launch execution or dashboard flows

Official CLI surface:

```text
redteaming run <campaign.yaml>
redteaming validate <campaign.yaml>
redteaming doctor <campaign.yaml>
redteaming dashboard
```

`main.py` at repository root forwards to the packaged CLI.

### Application layer

Main modules:

- `src/redteaming/application/campaign_loader.py`
- `src/redteaming/application/campaign_config.py`
- `src/redteaming/application/health_check.py`
- `src/redteaming/application/orchestrator.py`

Responsibilities:

- load and validate campaign YAML
- resolve attack file references
- build attack objects through the plugin registry
- run preflight diagnostics
- orchestrate attack execution order
- stamp run-level metadata on normalized results

### Domain layer

Main modules:

- `src/redteaming/domain/models/attack.py`
- `src/redteaming/domain/models/attack_result.py`
- `src/redteaming/domain/contracts/adapter.py`
- `src/redteaming/domain/contracts/normalizer.py`
- `src/redteaming/domain/contracts/runner.py`

Responsibilities:

- define the abstract attack model
- define the normalized result model
- define contracts for framework integrations

### Infrastructure layer

Main modules:

- `src/redteaming/infrastructure/http_attack_target.py`
- `src/redteaming/infrastructure/persistence/json_report_store.py`
- `src/redteaming/infrastructure/config/`
- `src/settings/`

Responsibilities:

- concrete HTTP target transport
- report persistence
- runtime configuration loading
- environment-backed settings

### Plugin layer

Main modules:

- `src/redteaming/plugins/registry.py`
- `src/redteaming/plugins/pyrit/`
- `src/redteaming/plugins/garak/`

Responsibilities:

- register supported frameworks
- build attack objects from YAML entries
- host framework-specific runners, adapters, and normalizers

Built-in frameworks:

- `pyrit`
- `garak`

### Reporting and UI

Main modules:

- `src/redteaming/infrastructure/persistence/json_report_store.py`
- `src/redteaming/ui/streamlit_dashboard.py`

Responsibilities:

- persist normalized reports to `reports/`
- load, group, and display reports in the dashboard

## User-visible behavior

The framework currently provides:

- campaign-driven execution from YAML
- explicit CLI commands for run / validate / doctor / dashboard
- HTTP/JSON target execution
- PyRIT dataset, crescendo, and red-teaming attack modes
- Garak probe execution
- normalized JSON reporting
- dashboard exploration of generated report files

## External boundaries

Provided by the user or environment:

- the target HTTP chatbot/API
- PyRIT attacker model endpoint
- PyRIT scorer model endpoint
- optional dynamic API key command
- PyRIT installation for PyRIT campaigns
- Garak installation for Garak campaigns

Not part of the framework core:

- target implementation
- backend LLM infrastructure
- enterprise token-generation scripts
- generated reports
- generated runtime files under `.runtime/`

## Design constraints

The current design assumes:

- targets are HTTP POST endpoints with JSON request/response payloads
- the target contract uses one configurable input field and one configurable output field
- PyRIT and Garak execution models differ, but both normalize into the same `AttackResult` model
- reports are stored on disk and later read by the dashboard
