# Fixtures and Reference Artifacts

These fixtures provide stable reference inputs and outputs for tests.

## Purpose

They are useful for checking:

- report format semantics
- campaign loading expectations
- CLI smoke references

They do not replace the full test suite.

## Included fixtures

### Report fixtures

- `reports/pyrit_attack_result_baseline.json`
  - normalized PyRIT-style report example
- `reports/garak_attack_result_baseline.json`
  - normalized Garak-style report example

## Reference campaigns

Useful campaign references:

- `examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml`
- `examples/campaigns/R5-indirect-prompt-injection/indirect_prompt_injection.yaml`

These files may require a real target and valid environment variables to execute end-to-end.

## Typical usage

Common checks using these fixtures:

1. run the test suite
2. ensure campaign loading still accepts the reference campaign files
3. compare produced normalized reports with the reference semantics captured here
4. ensure the dashboard can still read reports shaped like these fixtures
