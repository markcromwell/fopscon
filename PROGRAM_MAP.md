# Program Map: Foundation Operator Console

<!--GENERATED:BEGIN hash=e7e276a3247f31decd57c597e26fa68c2caa893e7a645df735eb0d1a3ab4c007 sig= job=0 commit=8f9e71c0b8438d2906309bed00ae81022f03a909-->
<!--Generated 2026-07-04T17:50:05.060697+00:00. Do not edit — will be overwritten.-->

## II. Canonical Data Schema [GENERATED — do not edit]

_No SQLAlchemy models found._

## III. File and Module Map [GENERATED — do not edit]

```
.dockerignore
.env.example
.github/workflows/ci.yml
.gitignore
Dockerfile
PROGRAM_MAP.md
README.md
app/__init__.py
app/assurance.py
app/auth.py
app/config.py
app/health.py
app/routers/__init__.py
app/routers/needs_you.py
app/routers/portfolio.py
app/routers/vision.py
app/static/index.html
app/test_assurance.py
app/test_auth.py
app/test_needs_you.py
app/test_vision.py
app/trust_strip.py
docker-compose.yml
docs/mockups/slice1-idea-to-vision.html
docs/mockups/slice2-needs-you.html
main.py
pyproject.toml
requirements.in
requirements.lock
scripts/setup.py
scripts/smoke_boot.py
scripts/test_unit.py
scripts/tests/test_idea_vision_ui.py
scripts/tests/test_needs_you_honesty.py
scripts/tests/test_needs_you_resolve.py
scripts/tests/test_needs_you_ui.py
```

## IV. API Surface [GENERATED — do not edit]

| Method | Path | Status Code |
|--------|------|-------------|
| GET | `/health` | 200 |
| GET | `/me` | 200 |
| GET | `/needs-you` | 200 |
| POST | `/needs-you/{item_id}/resolve` | 200 |
| GET | `/portfolio` | 200 |
| POST | `/programs` | 200 |
| POST | `/vision/draft` | 200 |

<!--GENERATED:END-->

---

## V. Architectural Decisions [CURATED]
_No decisions recorded yet._

---

## VI. Planned Work [CURATED]
_To be populated by the spec planner._
