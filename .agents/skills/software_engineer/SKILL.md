# Principal Software Engineer — Lifetime Skills Reference

> A living document of hard-won engineering wisdom. Not theory — practice.
> Apply these before writing a single line of code. Revisit often.

---

## 0. The Engineering Mindset

- **Simplicity is the ultimate sophistication.** The best code is the code you don't write.
- **Complexity is the enemy.** Every added abstraction, dependency, and clever trick has a cost. Pay it consciously.
- **Optimize for the reader, not the writer.** Code is read 10x more than it is written.
- **Make it work → Make it right → Make it fast.** In that order. Never skip ahead.
- **A good engineer solves the right problem.** Spend 20% of time understanding the problem before touching the keyboard.
- **Software rots.** Design it to be changed, not just to work today.

---

## 1. Core Principles (Non-Negotiable)

### SOLID
| Letter | Principle | One-Line Rule |
|--------|-----------|---------------|
| S | Single Responsibility | A class/module does ONE thing and has ONE reason to change. |
| O | Open/Closed | Open for extension, closed for modification. Add, don't edit. |
| L | Liskov Substitution | Subtypes must be substitutable for their base type without breaking behavior. |
| I | Interface Segregation | Many small interfaces beat one large general one. |
| D | Dependency Inversion | Depend on abstractions, not concretions. Inject dependencies. |

### KISS — Keep It Simple, Stupid
- If you can't explain what a function does in one sentence, split it.
- Clever code is a liability. Boring code is an asset.
- Prefer `if/else` over nested ternary chains.
- Prefer named functions over anonymous lambdas for anything non-trivial.

### DRY — Don't Repeat Yourself
- Every piece of knowledge has a single, authoritative representation.
- But: don't DRY too early. Wait for the third repetition before abstracting (Rule of Three).
- Premature DRY creates wrong abstractions. Wrong abstractions are worse than duplication.

### YAGNI — You Aren't Gonna Need It
- Don't build features for imagined future requirements.
- Delete code that isn't used. Dead code is a liability, not a safety net.

### Separation of Concerns
- Business logic, I/O, persistence, and presentation are separate layers.
- A function that reads a file, transforms data, and writes to a database is three functions.

---

## 2. Python-Specific Best Practices (3.10+)

### Project Structure (Standard)
```
my_app/
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── main.py            # Entry point
│       ├── config.py          # All config/env vars, one place
│       ├── models/            # Data models (dataclasses, Pydantic)
│       ├── services/          # Business logic (pure functions / classes)
│       ├── repositories/      # Data access layer (DB, files, APIs)
│       ├── api/               # HTTP layer (FastAPI/Flask routes)
│       └── utils/             # Shared helpers with no business logic
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml             # Single source of truth for metadata + deps
├── .env.example               # Committed. .env is NOT committed.
├── README.md
└── Makefile                   # Common tasks: make test, make lint, make run
```

### Code Style Rules
- **Type-hint everything.** Functions, return values, class attributes.
- Use `dataclasses` or `pydantic` for data containers. Never raw dicts as internal contracts.
- Use `pathlib.Path` not `os.path`. Always.
- Use `logging` not `print`. Configure once at the root.
- Use `Enum` for fixed sets of values, never magic strings.
- Prefer `match/case` (3.10+) over long `if/elif` chains for structural dispatch.
- Use context managers (`with`) for any resource that needs cleanup.
- Exceptions should be specific. Catch `ValueError`, not `Exception`.

### Configuration
```python
# config.py — one place, loaded once
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str
    debug: bool = False
    class Config:
        env_file = ".env"

settings = Settings()  # Singleton, import this everywhere
```

### Dependency Injection (Python Style)
```python
# Pass dependencies in; don't import/create them inside functions
def process_order(order: Order, repo: OrderRepository, notifier: Notifier) -> None:
    repo.save(order)
    notifier.send(order.user_email)
# Tests can pass mock repo and notifier — no patching needed
```

---

## 3. Design Patterns — When to Use Them

| Pattern | Use When | Avoid When |
|---------|----------|------------|
| Repository | Abstracting data access from business logic | You have one data source and no tests |
| Factory | Object creation logic is complex or varies | Simple `ClassName()` suffices |
| Strategy | You swap algorithms at runtime | You only ever use one algorithm |
| Observer/Event | Decoupling producers from consumers | Simple call chain is clear enough |
| Facade | Simplifying a complex subsystem's interface | The subsystem isn't complex |
| Decorator | Adding behavior without changing the class | One-off logic specific to one case |
| Singleton | True global state (config, logger) | You want to avoid writing tests |

**Rule:** Use patterns to solve a problem you have, not to demonstrate you know them.

---

## 4. Testing — The Non-Negotiable Contract

### Test Pyramid
```
         /\
        /E2E\         (few, slow, expensive — cover critical user journeys)
       /------\
      /Integr. \      (moderate — test boundaries: DB, HTTP, file I/O)
     /----------\
    /  Unit Tests \   (many, fast, cheap — test every function/branch)
   /--------------\
```

### Rules
- **Write tests before you consider a feature done.** Not after.
- Every public function gets a test. Every branch gets a test.
- **One assertion per test** (or one logical concept per test). Failing tests must be instantly readable.
- Tests must be **FAST** (unit tests < 1ms), **ISOLATED** (no shared state), **REPEATABLE** (same result every run), **READABLE** (test name = documentation).
- Test names: `test_<function>_<scenario>_<expected_outcome>` e.g. `test_parse_date_invalid_format_raises_value_error`
- Use `pytest` with `pytest-cov`. Aim for > 90% line AND branch coverage.
- Use `fixtures` for shared setup. Use `parametrize` for data-driven tests.
- **Mock at the boundary.** Mock I/O (DB, HTTP, files), not your own logic.

```python
# Good test: clear, isolated, one thing
def test_calculate_discount_vip_customer_returns_20_percent():
    customer = Customer(tier="VIP")
    assert calculate_discount(customer) == 0.20

# Bad test: multiple concerns, unclear failure point
def test_order():
    order = create_order_from_db()
    order.apply_discount()
    order.save()
    assert order.total < 100  # Which step failed?
```

---

## 5. Error Handling

- **Fail fast and loudly.** Silent failures cause the worst bugs.
- **Raise specific exceptions.** Define custom exceptions for your domain.
- **Never swallow exceptions** with bare `except: pass`.
- Handle errors at the boundary (API layer, CLI). Let them propagate internally.
- Log the full stack trace. Log the context (what data was being processed).
- **Return `Result` types or raise** — don't return `None` to signal failure.

```python
# Custom domain exception
class OrderNotFoundError(ValueError):
    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} not found")

# Correct pattern
def get_order(order_id: str) -> Order:
    order = repo.find(order_id)
    if order is None:
        raise OrderNotFoundError(order_id)   # Specific, informative
    return order
```

---

## 6. API Design (REST / Internal)

- **Resources are nouns, HTTP verbs are actions.** `GET /orders`, not `GET /getOrders`.
- Use standard HTTP status codes correctly. `200`, `201`, `400`, `401`, `403`, `404`, `422`, `500`.
- **Version your API from day one.** `/api/v1/...`
- Return consistent error envelopes: `{"error": {"code": "ORDER_NOT_FOUND", "message": "..."}}`
- Validate input at the boundary (Pydantic). Never trust input.
- Pagination, filtering, and sorting belong in query params.
- Document with OpenAPI/Swagger. FastAPI does this automatically.

---

## 7. Data & Persistence

- **Never store raw passwords.** Use `bcrypt` or `argon2`.
- Use migrations (Alembic for SQLAlchemy). Never alter the DB schema by hand in production.
- **Index foreign keys and any column you filter/sort by.**
- Prefer transactions when multiple writes must succeed together.
- Connection pooling is not optional in production.
- Validate data at the application layer. DB constraints are the safety net, not the first line.

---

## 8. Security Fundamentals

- **Never trust input.** Validate type, length, format, range.
- **Never hardcode secrets.** Use environment variables + secret managers.
- **Never log secrets, PII, or tokens.** Ever.
- Use parameterized queries. Never string-format SQL.
- Keep dependencies up to date. Run `pip audit` or `safety check` in CI.
- Principle of least privilege: services/users get only the permissions they need.
- HTTPS everywhere. Even internally.

---

## 9. Git & Version Control

```
# Commit message format (Conventional Commits)
feat: add user authentication via JWT
fix: handle empty cart in checkout flow
refactor: extract discount logic to DiscountService
test: add unit tests for OrderRepository
docs: update README with setup instructions
chore: upgrade pydantic to v2
```

- **Commit early, commit often.** Small, atomic commits.
- One logical change per commit. Don't bundle a refactor with a bug fix.
- Branch naming: `feat/add-login`, `fix/order-total-bug`, `chore/upgrade-deps`
- **Never commit directly to `main`.** Pull Request → Review → Merge.
- Squash or rebase before merging to keep history clean.
- `.gitignore` must exclude: `.env`, `__pycache__`, `.venv`, `*.pyc`, build artifacts.

---

## 10. CI/CD Pipeline (Minimum Viable)

Every push should trigger:
1. **Lint** — `ruff` or `flake8` (style + obvious errors)
2. **Type check** — `mypy` (catches type errors before runtime)
3. **Tests** — `pytest` with coverage report
4. **Security scan** — `pip audit`
5. **Build** — verify the package builds cleanly

```yaml
# .github/workflows/ci.yml (GitHub Actions sketch)
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy src/
      - run: pytest --cov=src --cov-report=term-missing
      - run: pip audit
```

---

## 11. Code Review — What to Look For

**As Author:**
- PR is small (< 400 lines diff). Large PRs don't get reviewed properly.
- Description explains *why*, not just *what*.
- Tests are included and pass.
- No commented-out code, no TODOs left for "later".

**As Reviewer:**
- Does the code do what the PR description says?
- Are edge cases handled?
- Are there tests for the new behavior?
- Is there a simpler way to achieve the same result?
- Would a new team member understand this in 6 months?
- Security: any new input that isn't validated? Any secrets exposed?

---

## 12. Performance — Think Before You Optimize

- **Measure first.** Use `cProfile`, `py-spy`, or `line_profiler`. Gut feel is usually wrong.
- The three common bottlenecks in order: **I/O** (DB queries, HTTP calls), **algorithm complexity**, **CPU**.
- N+1 query problem: use `JOIN` or `prefetch_related` / `selectinload`.
- Cache expensive, rarely-changing computations. Invalidate explicitly.
- Use generators for large datasets. Don't load a million rows into memory.
- Async I/O (`asyncio`, `httpx`, `asyncpg`) for high-concurrency I/O-bound work.
- **Premature optimization is the root of all evil** — Knuth. Don't abstract for performance before you have data.

---

## 13. Documentation

- **README must answer in under 2 minutes:** What does this do? How do I run it? How do I test it? How do I deploy it?
- Docstrings for every public function/class. Use Google or NumPy style consistently.
- Explain *why*, not *what*. The code says *what*. Comments explain *why it's done this way*.
- Architecture Decision Records (ADRs) for significant choices: `docs/decisions/001-use-postgres-over-mongodb.md`
- Keep docs next to the code they describe. Docs in a separate repo go stale.

```python
def calculate_tax(amount: float, region: str) -> float:
    """Calculate tax for a purchase amount in a given region.

    Args:
        amount: Pre-tax amount in USD.
        region: ISO 3166-2 region code (e.g., 'US-CA').

    Returns:
        Tax amount in USD, rounded to 2 decimal places.

    Raises:
        ValueError: If region is not supported.
    """
```

---

## 14. Logging & Observability

- Use structured logging (`structlog` or `python-json-logger`). Parse-able > readable.
- Log levels: `DEBUG` (dev only), `INFO` (normal operations), `WARNING` (unexpected but handled), `ERROR` (needs attention), `CRITICAL` (system is broken).
- Every log entry should answer: *What happened? When? In what context? On which request/job?*
- Add a `request_id` / `correlation_id` to every log in a web app.
- **Metrics** (counters, histograms) + **Logs** + **Traces** = full observability.
- Never log PII (emails, passwords, credit card numbers).

---

## 15. Dependency Management

- Pin exact versions in production (`requirements.lock` or `poetry.lock`).
- Separate dev dependencies from runtime dependencies.
- Audit dependencies regularly. Fewer dependencies = smaller attack surface.
- Prefer stdlib over a package for small needs. Prefer a well-maintained package over writing your own for complex needs.
- `pyproject.toml` is the modern standard. Use it.

---

## 16. The Art of Refactoring

- **Refactor in a separate commit from feature work.** Never mix.
- The boy scout rule: leave the code cleaner than you found it.
- Refactoring steps: write tests first → refactor → verify tests still pass.
- Common refactors: Extract Function, Extract Class, Rename Variable, Replace Magic Number with Constant, Replace Conditional with Polymorphism.
- **Never refactor without tests.** You're just moving bugs.

---

## 17. Communication & Collaboration

- A great engineer writes great prose. Clarity in code ↔ clarity in communication.
- When estimating: give a range. Add 30% for unknowns. Add 20% for integration.
- When stuck > 30 minutes: ask. Document what you tried.
- In design discussions: separate *what* (requirements) from *how* (implementation). Agree on *what* first.
- Give feedback on code, not on people. "This function has three responsibilities" not "you wrote bad code."
- Disagree and commit. Debate vigorously, then align and execute.

---

## 18. The Launch Checklist

Before any production release:
- [ ] All tests pass in CI.
- [ ] No hardcoded secrets or credentials.
- [ ] Environment variables documented in `.env.example`.
- [ ] DB migrations are backward-compatible (or downtime window planned).
- [ ] Error handling covers failure modes (what happens when the DB is down?).
- [ ] Logs are in place for key operations.
- [ ] Health check endpoint exists.
- [ ] Rollback plan documented.
- [ ] Feature flags for risky changes.
- [ ] Stakeholders notified of changes.

---

## 19. Principal Engineer Meta-Skills

- **Think in systems.** Every change has second-order effects.
- **Raise the floor, not just the ceiling.** Make the whole team better.
- **Write RFCs for large changes.** Proposal → Discussion → Decision → Implementation.
- **Know when to say no.** "Not now" and "this adds complexity we can't afford" are valid engineering answers.
- **Seek boring technology for the foundation.** Use exciting tech only at the edge, consciously.
- **The technical debt ledger is real.** Track it. Pay it down deliberately.
- **Mentorship is a core output.** Teaching solidifies your own understanding.

---

## 20. Quick Reference — Python Tools

| Purpose | Tool |
|---------|------|
| Linting | `ruff` |
| Type checking | `mypy` |
| Testing | `pytest` + `pytest-cov` |
| HTTP client | `httpx` |
| Data validation | `pydantic` v2 |
| Settings/Config | `pydantic-settings` |
| Web framework | `FastAPI` (async) or `Flask` (simple) |
| ORM | `SQLAlchemy` 2.x |
| DB migrations | `Alembic` |
| CLI | `typer` |
| Logging | `structlog` |
| Formatting | `black` |
| Dependency mgmt | `uv` (modern) or `poetry` |
| Security audit | `pip-audit` |
| Task runner | `Makefile` or `invoke` |

---

> "Any fool can write code that a computer can understand.  
>  Good programmers write code that humans can understand."  
> — Martin Fowler

> "The most important property of a program is whether it accomplishes  
>  the intention of its user."  
> — C.A.R. Hoare

> "Simplicity is a prerequisite for reliability."  
> — Edsger W. Dijkstra

---

*Last updated: 2026. Language: Python 3.12. This document is version-controlled alongside the project.*
