## PR Checklist

### Code quality
- [ ] Code follows the style conventions in AGENTS.md
- [ ] No hardcoded values that belong in config (categories, API keys, ports)
- [ ] No dead code, commented-out blocks, or debug logging left in

### Privacy & security
- [ ] No `.env` or `data/*.db` files staged or committed
- [ ] Any LLM call goes through `pii_strip.py` first
- [ ] No raw transaction descriptions, account numbers, or names sent to external services

### Correctness
- [ ] The feature works as described in the PR title/body
- [ ] Edge cases considered (empty CSV, unlabelled transactions, missing config, etc.)
- [ ] No regressions to existing functionality

### Tests
- [ ] New feature has a Playwright e2e spec in `tests/e2e/`
- [ ] `pii_strip.py` changes (if any) are covered by unit tests
- [ ] `uv run pytest` passes with no failures
- [ ] `npx playwright test` passes with no failures

### Scope
- [ ] Change is within phase 1 scope (nothing from the "Explicitly Out" list has been added)
- [ ] No new dependencies added without prior discussion
