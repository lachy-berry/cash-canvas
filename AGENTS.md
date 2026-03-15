# Cash Canvas

A family budget app for labelling bank transactions and analysing household spending. Mobile-browser-compatible frontend, local SQLite database, and privacy-first LLM assistance.

## Role

You are a full-stack developer working on Cash Canvas. You build features across a React 19 frontend and a FastAPI Python backend. You keep code simple and minimal — this is a phase 1 product with strict scope boundaries.

## Commands

```bash
# Frontend (Vite dev server, port 5173)
npm run dev

# Backend (FastAPI + uvicorn, port 8000)
uv run uvicorn server.main:app --reload --port 8000

# Run both together
make dev

# Install JS dependencies
npm install

# Install Python dependencies
uv sync

# Run Python tests
uv run pytest

# Lint JS
npm run lint
```

## Project Structure

```
cash-canvas/
├── src/                        # React 19 frontend
│   ├── components/
│   │   ├── ImportCSV.jsx       # CSV upload and column mapping
│   │   ├── TransactionList.jsx # Paginated transaction list
│   │   ├── LabelPicker.jsx     # Category label assignment
│   │   └── Dashboard.jsx       # Spending analysis view
│   ├── App.jsx                 # Top-level routing and layout
│   └── index.css               # Global styles and Tailwind import
├── server/                     # Python backend
│   ├── main.py                 # FastAPI app entry point
│   ├── db.py                   # SQLite schema and query helpers
│   ├── pii_strip.py            # PII stripper — pure function, no side effects
│   ├── categories.py           # Loads and serves categories from YAML
│   └── routes/
│       ├── transactions.py     # CRUD endpoints
│       ├── import_csv.py       # CSV upload and parse
│       └── llm.py              # LLM suggest-labels endpoint
├── config/
│   └── categories.yaml         # Editable category definitions
├── data/                       # SQLite .db file — gitignored, never committed
├── .env                        # LLM API keys — gitignored, never committed
├── pyproject.toml              # uv project config
└── Makefile                    # make dev, make install
```

## Tech Stack

- **Frontend:** React 19, Vite 8, Tailwind CSS v4, plain JSX (no TypeScript)
- **Backend:** Python 3.12+, FastAPI, uvicorn
- **Database:** SQLite via Python stdlib `sqlite3`
- **LLM:** `litellm` — pluggable, OpenRouter-compatible
- **CSV parsing:** Python stdlib `csv`
- **Package management:** `uv` (Python), `npm` (JS)

## API Endpoints

```
POST   /api/import                   Upload and parse a CSV file
GET    /api/transactions             List transactions (paginated)
PATCH  /api/transactions/:id/label  Assign a label to a transaction
GET    /api/categories              Return categories from YAML config
POST   /api/llm/suggest             Suggest labels for a batch of transactions
GET    /api/dashboard               Aggregated spending by category
```

## Code Style

### Python

```python
# ✅ Good — snake_case, f-strings, explicit return types, one concern per function
def strip_pii(description: str) -> str:
    """Remove personally identifiable information from a transaction description."""
    description = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD]', description)
    description = re.sub(r'\b\d{3}-\d{3}\b', '[BSB]', description)
    return description

# ❌ Bad — vague name, no docstring, side effects in a pure function
def clean(d):
    print(f"Cleaning: {d}")
    return re.sub(r'\d+', '', d)
```

- snake_case for all identifiers
- 4-space indent
- f-strings preferred over `.format()` or `%`
- No default exports from modules
- Pure functions preferred; side effects at the edges

### JavaScript / JSX

```jsx
// ✅ Good — PascalCase component, camelCase props, Tailwind for styling
export function LabelPicker({ transaction, onLabel }) {
  return (
    <div className="flex gap-2 p-4 border rounded-lg">
      <span className="text-sm text-gray-600">{transaction.description}</span>
    </div>
  )
}

// ❌ Bad — default export, inline styles, no prop names
export default function (t, fn) {
  return <div style={{padding: 16}}>{t.desc}</div>
}
```

- camelCase for variables and functions, PascalCase for components
- 2-space indent
- No TypeScript — plain JSX only
- One component per file, filename matches component name
- Tailwind utility classes first; custom CSS only when Tailwind can't do it

## Privacy Rules

`server/pii_strip.py` is a **pure function** — `strip_pii(description: str) -> str`. It must:
- Have unit tests
- Never make network calls
- Never have side effects

The LLM only ever receives: `date`, `amount`, `stripped_description`. It never receives raw descriptions, account numbers, names, or any other identifying fields.

Replacements applied before any LLM call:
- Card/account numbers → `[CARD]` / `[ACCT]`
- BSB patterns → `[BSB]`
- Names (heuristic regex) → `[NAME]`
- Postcodes → `[POSTCODE]`

## Categories Config

Categories are defined in `config/categories.yaml`. Never hardcode category lists in Python or JS — always load from the YAML. Phase 1 uses the `broad` layer only; the schema supports multiple layers for future use.

```yaml
version: 1
layers:
  - id: broad
    name: Broad Category
    categories:
      - id: groceries
        name: Groceries
  - id: tax
    name: Tax Treatment
    categories:
      - id: deductible
        name: Tax Deductible
```

## Git Workflow

- Branch from `main` for all features
- Commit messages follow conventional commits: `feat:`, `fix:`, `chore:`, `refactor:`
- Never commit `.env` or any file in `data/`
- Keep commits small and focused — one logical change per commit
- All feature branches require a PR before merging to `main`
- Every PR must be reviewed and approved — by a human or a review agent — before it can be merged

### PR Checklist

Every PR description must include the following checklist. No PR should be merged until all items are checked.

```markdown
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
- [ ] `pii_strip.py` changes (if any) are covered by unit tests
- [ ] `uv run pytest` passes with no failures

### Scope
- [ ] Change is within phase 1 scope (nothing from the "Explicitly Out" list has been added)
- [ ] No new dependencies added without prior discussion
```

## Boundaries

- ✅ **Always:** Use Tailwind for styling, load categories from YAML, run PII stripper before any LLM call, write tests for `pii_strip.py`
- ⚠️ **Ask first:** Adding a new dependency (Python or JS), changing the SQLite schema, modifying the categories YAML structure
- 🚫 **Never:** Commit `.env` or `data/*.db`, add TypeScript, hardcode category lists, send raw transaction descriptions to an LLM, add features that are out of scope for phase 1

## Phase 1 Scope — Explicitly Out

- Authentication or user accounts
- Multi-user support
- Cloud sync or remote database
- Rule-based auto-labelling (LLM suggestion only)
- Custom category editing via UI (edit `config/categories.yaml` directly)
- Export or reporting beyond the dashboard
- Mobile native app (mobile browser only)
