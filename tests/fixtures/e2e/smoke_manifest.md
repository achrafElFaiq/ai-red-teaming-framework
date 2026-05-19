# Smoke Manifest

This file records representative end-to-end smoke commands for the current CLI.

## Primary smoke command

```zsh
redteaming run examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --no-dashboard --skip-checks
```

Expected outcome:

- campaign YAML loads successfully when environment and target are available
- attacks execute in configured order
- normalized JSON reports are generated
- no dashboard is launched because `--no-dashboard` is set

## Secondary smoke command

```zsh
redteaming run examples/campaigns/R5-indirect-prompt-injection/indirect_prompt_injection.yaml --no-dashboard --skip-checks
```

Expected outcome:

- campaign file loads successfully
- R5 attack references resolve correctly
- normalized JSON reports are produced

## Additional smoke commands

### Validate command

```zsh
redteaming validate examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
```

Expected outcome:

- campaign and referenced attack files load successfully
- no execution is performed

### Doctor command

```zsh
redteaming doctor examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
```

Expected outcome:

- campaign loads successfully
- preflight checks run without executing attacks

## Why this file exists

These smoke references help detect breakage in:

- CLI argument handling
- campaign loading
- attack file resolution
- orchestration entrypoint behavior
- report generation path
