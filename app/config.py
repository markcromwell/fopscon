from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Foundation Operator Console"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./app.db"  # override via env for Postgres

    # ── BFF upstreams (the thin BFF aggregates SOV state + CoEv2 judgment) ──
    # SOV/MCP: program state, build, deliver, deploy, promote, health, comms.
    sov_base_url: str = "http://host.docker.internal:8765"
    sov_api_key: str = ""  # X-API-Key for SOV; set via env (SOV_API_KEY) — never hard-coded
    # CoEv2: judgment — vision/draft, grade, assurance, gate-integrity, calibration.
    council_base_url: str = "http://council-v2-api:3000"
    council_api_key: str = ""
    # /v1/vision/draft + /v1/grade REQUIRE a program_id, but the Idea→Vision screen shapes an idea
    # BEFORE a program exists. We draft/grade under a persistent SANDBOX program so stray idea-grades
    # never pollute a real program's grade history; "Start this program" (AC4) creates the real program
    # and re-grades under its own id. Overridable via VISION_SANDBOX_PROGRAM_ID (CoEv2 to confirm the id).
    vision_sandbox_program_id: int = 1019  # IDEASANDBOX — a persistent, junk-tolerant grade sandbox (never builds)
    council_max_cost_usd: float = 1.0      # per draft/grade call; the council caps at 30
    council_poll_timeout_s: float = 600.0  # draft+grade are async (2.5–5 min each) — the "shaping…" wait
    council_poll_interval_s: float = 5.0

    # ── Google sign-in (id_token pattern; NO client secret) ──
    google_client_id: str = "914839164404-675qnmh7juchfrsh89674dat47qelbg7.apps.googleusercontent.com"
    # Email allowlist (comma-separated in env ALLOWED_EMAILS). Empty => auth-disabled DEV mode only.
    allowed_emails: str = ""
    # Set AUTH_ENABLED=true once the allowlist is populated; DEV default is off so Phase-A build/test
    # doesn't need a live Google token. PROD MUST run with AUTH_ENABLED=true (enforced at deploy).
    auth_enabled: bool = False

    @property
    def allowed_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}


settings = Settings()
