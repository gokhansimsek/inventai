# Retail Analytics Pipeline

Case-study submission (brief: `case_study.md`). Graded on data-quality handling
and architecture equally, and on pragmatism — size abstractions to 2 MB of CSV.

Every design decision, with its reasoning, is in `docs/design-session.md`.
Read it before changing validation rules, KPI formulas, filters or outputs;
an answer there is settled — raise a conflict with the user rather than
re-deciding it.

## Commands

Python 3.14 via uv, project-local `.venv`. Windows host: no `make`.

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
uv run mypy src tests tools    # strict
uv run pyright                 # Pylance engine; standard mode, same as the editor
uv run retail-analytics run --help  # settings: config/default.yaml, flags override
```

A change is done when all four checks pass. The pre-commit hook
(`.pre-commit-config.yaml`) enforces them plus a Google-style docstring on every
function and method in `src/` and `tools/`, private and nested ones included
(test functions are exempt; their names are the spec). Each parameter is
documented as `name (type): description` and the return as
`type: description`, with the type text identical to the annotation
(`Annotated[T, ...]` is written `T`); add `Raises:` for exceptions callers
handle. `tools/check_docstrings.py` holds the exact rules. Write the docstring
as you write the function. Run the hooks on untracked files with
`uv run pre-commit run --files <paths>` (`--all-files` sees only tracked files).

## Validation contract

- A rule is a small class satisfying `validation.base.Rule`, registered in
  order in `validation/registry.py`, with one of three severities:
  - **fix**: provably recoverable (backed by an exact rule or evidence across
    the whole file); value corrected in place, count recorded.
  - **reject**: unusable for any KPI; row goes to that table's quarantine with
    a `reason`.
  - **flag**: suspicious but usable; row stays and is recorded in that table's
    issues output.
- **Reconciliation invariant:** for every table, raw = clean + rejected. Every
  removed row is accounted for by a rule.
- Validation always runs on the full files; store/region/date filters apply
  afterwards, so the data-quality section is identical for every run.
- Structural problems (missing file or column, invalid config, unknown filter
  value) raise a `PipelineError` subclass and stop the run. An empty filter
  result is a valid report, not an error.

## Testing

Test-first, red → green, one behaviour per cycle, at these agreed seams only:
a rule's `apply`, the validation engine, KPI functions, `run_pipeline`
(real `data/`), and the CLI. Expected values come from hand-worked examples or
the independent data profile in `docs/design-session.md` — never recomputed the
way the code computes them. HTML layout and chart rendering are untested by
design.

## Working agreements

- Commit only when the user asks; keep commits small and milestone-shaped so
  the history tells the build story.
- Update `AI_USAGE.md` at each milestone: what the AI did, where the user
  overrode it, and AI errors caught. It is a graded deliverable.
- Record new data findings and assumptions in the docs as they are made
  (`docs/data-quality.md`, `docs/assumptions.md`, short ADRs in `docs/adr/`).
