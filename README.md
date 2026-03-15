# Cash Canvas

A family budget app for labelling bank transactions and analysing household spending.

Import CSV exports from your bank, assign category labels to transactions, and view spending breakdowns by category. An LLM assist feature suggests labels automatically — with PII stripped before any data leaves your machine.

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React 19, Vite 8, Tailwind CSS v4 |
| Backend | Python 3.12, FastAPI, uvicorn |
| Database | SQLite |
| LLM | litellm (OpenRouter-compatible, pluggable) |

### Frontend build tooling

The Vite frontend uses `@vitejs/plugin-react` which uses [Oxc](https://oxc.rs) for fast transforms. The React Compiler is not enabled. No TypeScript — plain JSX throughout.

## Repo Structure

```
cash-canvas/
├── src/                  # React frontend
├── server/               # FastAPI backend
├── config/               # categories.yaml and other config
├── tests/                # pytest tests and Playwright e2e specs
├── .github/              # CI workflow and PR template
└── data/                 # SQLite db (gitignored)
```

## How It's Being Developed

- **AI-assisted:** Built with [OpenCode](https://opencode.ai) (coding agent) via [Kimaki](https://kimaki.dev) (Discord interface)
- **Test-driven:** Every feature starts with a GitHub Issue for scoping, followed by failing Playwright e2e and pytest tests before any implementation
- **CI enforced:** GitHub Actions runs the full test suite on every PR; both jobs must pass before merge
- **Privacy-first:** Raw transaction data never leaves the machine — a server-side PII stripper runs before any LLM call
