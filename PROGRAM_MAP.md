# Program Map: Foundation Operator Console

<!--GENERATED:BEGIN hash=27ae9df425dbc25dd7f9a86c25023a70ccb7f811eb7fefd942872623a2f39653 sig= job=0 commit=1c9557eb173c41e4375d9eb0d9b4bd1af316fcbb-->
<!--Generated 2026-07-05T02:32:49.585785+00:00. Do not edit — will be overwritten.-->

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
app/routers/build_monitor.py
app/routers/living.py
app/routers/needs_you.py
app/routers/portfolio.py
app/routers/vision.py
app/static/index.html
app/test_assurance.py
app/test_auth.py
app/test_build_monitor.py
app/test_living.py
app/test_needs_you.py
app/test_vision.py
app/trust_strip.py
docker-compose.yml
docs/design-refs/console-design-language.md
docs/design-refs/console-gui-architecture.md
docs/mockups-v2/build-monitor-v2.html
docs/mockups-v2/idea-to-vision-v2.html
docs/mockups-v2/living-program-v2.html
docs/mockups-v2/needs-you-v2.html
docs/mockups/slice1-idea-to-vision.html
docs/mockups/slice2-needs-you.html
docs/mockups/slice3-build-monitor.html
docs/mockups/slice4-living-program.html
main.py
pyproject.toml
requirements.in
requirements.lock
scripts/setup.py
scripts/smoke_boot.py
scripts/test_unit.py
scripts/tests/test_build_monitor_ui.py
scripts/tests/test_idea_vision_ui.py
scripts/tests/test_living_honesty.py
scripts/tests/test_living_ui.py
scripts/tests/test_needs_you_honesty.py
scripts/tests/test_needs_you_resolve.py
scripts/tests/test_needs_you_ui.py
scripts/tests/test_shell_heartbeat_honesty.py
scripts/tests/test_shell_v2.py
scripts/tests/test_vision_grade_honesty.py
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
| GET | `/programs/{code}/build` | 200 |
| GET | `/programs/{code}/living` | 200 |
| POST | `/vision/draft` | 200 |

<!--GENERATED:END-->

---

## V. Architectural Decisions [CURATED]
_No decisions recorded yet._

---

## VI. Planned Work [CURATED]
_To be populated by the spec planner._
