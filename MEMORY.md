# Cash Canvas — Agent Memory

Persistent notes for agents working on this project. Update this file when you learn something important.

---

## Workflow rules

- **Scope before code.** Always agree on feature scope and create a GitHub Issue before writing any implementation or test code. This was violated in the CSV import session — code was written before scope was confirmed. Don't repeat this.
- **ATDD order:** GitHub Issue → failing tests → implementation → PR. Tests are committed on the feature branch before any implementation exists.
- **Plan mode = no file edits.** Use plan mode for scoping conversations. Switch to build mode before touching files.

---

## GitHub Issue writing guidelines

Learned from: https://github.blog/ai-and-ml/github-copilot/assigning-and-completing-issues-with-coding-agent-in-github-copilot/

A good issue includes:
- **Background** — what the app is, what already exists, why this feature matters
- **User journey** — step-by-step flow, including UI states and error cases
- **Technical details** — exact file paths, function names, DB schema changes, new dependencies
- **Acceptance criteria** — checkboxes, one per test case, covering both pytest and Playwright
- **Out of scope** — explicit list of what this issue does NOT include

Write it so a developer or agent with no prior context can execute it without asking questions.

---

## Feature #2: CSV Import — agreed decisions

### Architecture
- `/` — transaction list + "Import CSV" button
- `/import` — dedicated multi-step import page (not inline on home)
- Routing via **react-router v7** (`npm install react-router`)

### Import flow (4 steps)
1. Upload — file picker
2. Map columns — dropdowns pre-filled by heuristic function; amount supports single column OR credit−debit pair
3. Review — first 20 new rows previewed; duplicates listed with `[+ Include anyway]` per row
4. Done — "Imported X, skipped Y" + Undo button + link to `/`

### Column pre-fill heuristics
Pure JS function: `src/components/ImportFlow/guessColumns.js`
- `date` → `date`, `transaction date`, `trans date`, `tran_date`, `txn date`
- `description` → `description`, `narrative`, `details`, `memo`, `particulars`, `transaction details`
- `amount` → `amount`, `debit/credit`, `transaction amount`, `value`
- `balance` → `balance`, `running balance`, `closing balance`

Case-insensitive, first match wins.

### Deduplication
- Fingerprint = `sha256(date|description|amount|balance)` — use balance if mapped, omit if not
- Duplicates are **never silently dropped** — always surfaced to user in Step 3
- User can individually include flagged duplicates via `[+ Include anyway]`

### Batch tracking + undo
New table:
```sql
CREATE TABLE import_batches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    row_count   INTEGER NOT NULL
);
```
New columns on `transactions`: `batch_id INTEGER REFERENCES import_batches(id)`, `fingerprint TEXT`

Schema change handled by DROP + recreate in `init_db()` (no migrations for phase 1).

Undo = `DELETE FROM transactions WHERE batch_id = ?` + delete batch record.

### API
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/import/preview` | Parse CSV + mapping → `{ new: [...], duplicates: [...] }` |
| `POST` | `/api/import/confirm` | Write approved rows → `{ batch_id, imported, skipped }` |
| `DELETE` | `/api/import/batches/{batch_id}` | Undo a batch |
| `GET` | `/api/transactions` | Paginated, date DESC, `?limit=50&offset=0` |

### Files
```
server/db.py                              ← update schema
server/routes/import_csv.py              ← preview + confirm
server/routes/transactions.py            ← GET /api/transactions
server/main.py                           ← include routers
src/App.jsx                              ← router root
src/components/ImportFlow/StepUpload.jsx
src/components/ImportFlow/StepMapColumns.jsx
src/components/ImportFlow/StepReview.jsx
src/components/ImportFlow/StepDone.jsx
src/components/ImportFlow/guessColumns.js
src/components/TransactionList.jsx
tests/test_import_csv.py
tests/e2e/import_csv.spec.js
```

---

## Feature #3: Transaction Labelling — agreed decisions

### Storage: join table (Option B chosen over hardcoded columns or JSON blob)
- New table `transaction_labels`: `(transaction_id, layer_id, category_id)`
- `PRIMARY KEY (transaction_id, layer_id)` — one label per layer per transaction
- `transactions.label_broad TEXT` column **REMOVED** — replaced entirely by join table
- Schema handled by drop+recreate (same as existing behaviour — data loss acceptable in phase 1)
- Adding a new layer in future = add YAML entry only. No schema change, no API change.

### API shape (layer-generic by design)
- `PATCH /api/transactions/{id}/labels`
  - Body: `{ "layer": "broad", "category": "groceries" }` — upserts label
  - Body: `{ "layer": "broad", "category": null }` — clears label (deletes row)
  - 404 if transaction not found; 422 for invalid layer or category ID
- `GET /api/transactions` — each tx gets `"labels": { "broad": "groceries" }` (empty dict `{}` if none)
- Validation: `layer` must exist in `config/categories.yaml`; `category` must exist in that layer

### Frontend approach
- `LabelPicker.jsx` (new component) — generic select driven by `/api/categories`
- `TransactionList.jsx` — fetches categories once on mount; passes `labels.broad` to LabelPicker
- On PATCH success: update state. On failure: revert dropdown + show inline error.

### Files
```
server/db.py                          ← update _SCHEMA + _EXPECTED_COLUMNS
server/routes/transactions.py         ← update GET (LEFT JOIN pivot) + add PATCH endpoint
src/components/TransactionList.jsx    ← read labels.broad not label_broad
src/components/LabelPicker.jsx        ← new component
tests/test_labels.py                  ← pytest: CRUD + validation
tests/e2e/labelling.spec.js           ← playwright: assign label, persist on reload
```

### Impact on existing tests
- `test_transactions_list.py` — currently asserts `label_broad` in response keys; update to `labels` dict
- `test_import_confirm.py` — asserts `label_broad is None`; update to check `labels == {}`
- `test_db.py` — asserts `label_broad` in expected columns; update to `transaction_labels` table

---

## Tech stack reminders

- Python: snake_case, f-strings, type hints, docstrings, pure functions preferred
- JS: camelCase vars, PascalCase components, 2-space indent, no TypeScript, Tailwind only
- Never hardcode category lists — always load from `config/categories.yaml`
- Never send raw descriptions to LLM — always run `pii_strip.py` first (not built yet)
- Never commit `.env` or `data/*.db`
