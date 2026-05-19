# Target Contract

This document describes the HTTP target contract expected by the framework.

## Target model

The framework uses a concrete HTTP target implementation defined by `AttackTarget` in:

- `src/redteaming/infrastructure/http_attack_target.py`

Current target fields:

- `name`
- `chat_url`
- `reset_memory_url` (optional)
- `input_field`
- `output_field`
- `model` (optional metadata)
- `architecture_type` (optional metadata)

The target also exposes:

- `url` → same value as `chat_url`

## Minimal contract

A target must provide an HTTP endpoint that accepts a POST request with a JSON body containing one text field.

### Request shape

```json
{
  "<input_field>": "<prompt text>"
}
```

### Response shape

```json
{
  "<output_field>": "<assistant response>"
}
```

Everything else in the response is ignored.

## Example

If the campaign target declares:

```yaml
target:
  name: "CustomerBot"
  chat_url: "http://localhost:8000/api/chat"
  reset_memory_url: "http://localhost:8000/api/reset"
  input_field: "message"
  output_field: "response"
```

Then the framework sends:

```http
POST /api/chat
Content-Type: application/json
```

```json
{
  "message": "hello"
}
```

And expects something like:

```json
{
  "response": "hello, how can I help you?"
}
```

## Request behavior

### Chat request

The framework currently:

- sends `POST chat_url`
- sends `json={input_field: prompt}`
- uses a timeout of `(5, 50)`
- parses the response as JSON
- returns `body.get(output_field, "")`

### Reset request

If `reset_memory_url` is configured, the framework:

- sends `POST reset_memory_url`
- sends no JSON payload
- uses a timeout of `(5, 10)`

If `reset_memory_url` is absent, reset is skipped.

## Supported features

The target contract supports:

- HTTP POST chat endpoint
- JSON request body
- one configurable input field
- one configurable output field
- optional reset endpoint
- optional target metadata (`model`, `architecture_type`)

## Current limits

The target contract does not currently support:

- request templates
- nested response paths
- target headers configured in campaign YAML
- multiple required input fields
- non-JSON chat payloads
