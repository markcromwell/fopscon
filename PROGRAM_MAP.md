# Program Map: Foundation Operator Console

<!--GENERATED:BEGIN hash=966c3377aca73bb939c5c62e00f4a205a620a4387f1d242c5509aa70e3a93241 sig= job=0 commit=2f96f17727b9b4a1b666c5db553d15240629798e-->
<!--Generated 2026-07-04T17:01:04.001535+00:00. Do not edit — will be overwritten.-->

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
app/routers/portfolio.py
app/routers/vision.py
app/static/index.html
app/test_assurance.py
app/test_auth.py
app/test_vision.py
app/trust_strip.py
docker-compose.yml
docs/mockups/slice1-idea-to-vision.html
main.py
pyproject.toml
requirements.in
requirements.lock
scripts/setup.py
scripts/smoke_boot.py
scripts/test_unit.py
scripts/tests/test_idea_vision_ui.py
```

## IV. API Surface [GENERATED — do not edit]

| Method | Path | Status Code |
|--------|------|-------------|
| GET | `/health` | 200 |
| GET | `/me` | 200 |
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
