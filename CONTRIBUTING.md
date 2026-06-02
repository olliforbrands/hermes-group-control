# Contributing

Thanks for your interest in improving hermes-group-control.

## Scope

This plugin intentionally stays **minimal**: archive, media copy, observe/mention gate, and `/gc mode` only. Features like search, export, dashboards, or LLM summarization belong in separate tools or Hermes skills — open an issue first before large PRs.

## Development setup

1. Clone into `~/.hermes/plugins/group-control/`
2. Enable in `~/.hermes/config.yaml` (see README)
3. Run tests from a Hermes checkout:

   ```bash
   cd /path/to/hermes-agent
   ./venv/bin/pytest /path/to/hermes-group-control/tests/test_group_control.py -q
   ```

## Pull requests

- Keep changes focused
- Add or update tests for behavior changes
- Do not commit real phone numbers, `.env`, or `data.db` files
