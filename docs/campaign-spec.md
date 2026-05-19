# Campaign Specification

This document describes the YAML contract accepted by the framework.

## Campaign file structure

A campaign YAML file must be a mapping with the following top-level keys:

- `campaign` (optional)
- `target` (required)
- `attacks` (required)

Unknown top-level keys are rejected.

### Minimal shape

```yaml
campaign:
  name: "My campaign"
  description: "Optional description"

target:
  name: "CustomerBot"
  chat_url: "http://localhost:8000/api/chat"
  reset_memory_url: "http://localhost:8000/api/reset"
  model: "gpt-4.1-nano"
  architecture_type: "RAG + System Prompt + Context Injected"
  input_field: "prompt"
  output_field: "response"

attacks:
  - examples/attacks/R1-prompt-leakage/r1_pyrit_direct_request.yaml
  - examples/attacks/R3-jailbreaking-guardrail-bypass/r3_pyrit_fictional_world.yaml
```

## `campaign` section

Supported fields:

- `name` — optional; defaults to the campaign file stem if omitted
- `description` — optional metadata

The loader currently uses `campaign.name` and accepts `campaign.description` as informational metadata.

## `target` section

The target section is required.

### Required fields

- `name`
- `chat_url`

### Optional fields

- `reset_memory_url`
- `model`
- `architecture_type`
- `input_field` (default: `prompt`)
- `output_field` (default: `response`)

### Validation rules

The loader enforces:

- `target.name` must be present
- `target.chat_url` must start with `http://` or `https://`
- `target.reset_memory_url`, if present, must start with `http://` or `https://`
- `target.model` must be a string
- `target.architecture_type` must be a string
- `target.input_field` must be a non-empty string
- `target.input_field` must be a single field name, not a JSON template
- `target.output_field` must be a non-empty string

### Current limitation

The target contract supports:

- one input JSON field
- one output JSON field
- flat field names

It does not currently support:

- request templates
- nested response paths
- headers/custom auth in campaign YAML
- multiple required input fields

## `attacks` section

The `attacks` section is required and must be a non-empty list of file paths.

For each item in `attacks:`:

- it must be a string path
- the loader first tries the path as written
- if it does not exist, it also tries `campaign_path.parent / ref`
- if both resolutions fail, campaign loading fails

Preferred convention:

- use root-relative paths such as `examples/attacks/...`

## Attack YAML — common fields

Every attack file must be a YAML mapping.

Common required fields:

- `framework`
- `intent`

Valid values for `framework`:

- `pyrit`
- `garak`

The attack name exposed by the framework is derived as:

```text
<framework> - <intent>
```

Example:

```text
pyrit - r1_direct_request
```

## PyRIT attack specification

A PyRIT attack uses:

```yaml
framework: pyrit
intent: "my_attack"
orchestrator: dataset | crescendo | red_teaming
objective: "..."
max_turns: 5
prompts:
  - "..."
scoring:
  true_description: "..."
  false_description: "..."
  category: "..."
```

### Required fields for PyRIT

- `framework: pyrit`
- `intent`
- `orchestrator`
- `objective`

### Optional fields

- `max_turns`
- `prompts`
- `scoring`

### Orchestrator semantics

#### `dataset`

- `prompts` should be a non-empty list
- each prompt is sent independently
- target reset is called after each prompt when configured
- results are normalized into one report entry per prompt

#### `crescendo`

- multi-turn attack
- uses `objective`
- may use `max_turns`
- does not reset between turns

#### `red_teaming`

- multi-turn adversarial execution
- uses `objective`
- may use `max_turns`
- does not reset between turns

### Scoring

If `scoring` is present, it must contain:

- `true_description`
- `false_description`
- `category`

The loader builds a PyRIT `TrueFalseQuestion` from that mapping.

## Garak attack specification

A Garak attack uses:

```yaml
framework: garak
intent: "promptinject_scan"
probe: "promptinject"
report_prefix: "reports/garak_promptinject"
```

### Required fields for Garak

- `framework: garak`
- `intent`
- `probe`

### Optional fields

- `report_prefix`

### Important rule

The following transport fields are forbidden inside Garak attack files and must be defined at campaign target level instead:

- `input_field`
- `output_field`
- `req_template`
- `response_json_field`

If these keys are present in a Garak attack file, loading fails.

## Reference examples

Useful campaign references in this repository:

- `examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml`
- `examples/campaigns/R5-indirect-prompt-injection/indirect_prompt_injection.yaml`

Useful templates:

- `examples/templates/campaign.yaml`
- `examples/templates/attack_pyrit_dataset.yaml`
- `examples/templates/attack_pyrit_crescendo.yaml`
- `examples/templates/attack_pyrit_red_teaming.yaml`
- `examples/templates/attack_garak.yaml`
