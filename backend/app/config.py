from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

#: Resolved from this file, not from the working directory. `env_file=".env"` is
#: relative to wherever the process was started, so running the server from the
#: repository root instead of backend/ silently loaded no file at all — and the
#: first symptom was "ANTHROPIC_API_KEY not set", which points at the wrong thing
#: entirely.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


#: The value shipped in the repo. Anything equal to this is not a secret — it is
#: a placeholder that has been read by everyone who has seen the source.
INSECURE_SECRET = "change-this-in-production"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://nebular:nebular@localhost:5432/nebulardb"
    secret_key: str = INSECURE_SECRET
    access_token_expire_minutes: int = 10080  # 7 days

    #: "development" or "production". Only used to decide how strict to be about
    #: configuration that is survivable locally and fatal in public.
    env: str = "development"

    anthropic_api_key: str = ""
    # Claude only names and describes the build now; the plan itself is computed.
    # Sonnet rather than Opus: the job is recognising a landmark and writing three
    # sentences, which Sonnet does about as well, at 60% of the price. Opus earns
    # its cost on reasoning, and there is none left in this call.
    claude_model: str = "claude-sonnet-5"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "nebular-design-uploads"
    use_s3: bool = False
    #: Set to point boto3 somewhere other than AWS. For Cloudflare R2 that is
    #: https://<account-id>.r2.cloudflarestorage.com — the bucket name is *not*
    #: part of it. Empty means real S3. See services/storage.py for why the two
    #: cases need different addressing.
    s3_endpoint_url: str = ""

    enable_depth_estimation: bool = True
    depth_model: str = "depth-anything/Depth-Anything-V2-Small-hf"

    # SegFormer size sets both the download and the per-request latency:
    #   b0   3.8M params    14 MB   ~0.5s
    #   b2  27.4M params   105 MB   ~1.0s
    #   b4  64.1M params   245 MB   ~1.7s
    # b0 matched b4 closely on the buildings tested so far, so it is the default.
    # Compare them on your own photos with tools/preview_server.py before moving up.
    segmentation_model: str = "nvidia/segformer-b0-finetuned-ade-512-512"

    # Comma-separated list of allowed frontend origins
    frontend_url: str = "http://localhost:3000"

    port: int = 8000

    class Config:
        env_file = str(ENV_FILE)

    @property
    def async_database_url(self) -> str:
        """The DATABASE_URL a host hands out, in the dialect asyncpg accepts.

        Every managed Postgres gives you a libpq connection string, and asyncpg is
        not libpq. Two differences matter and both fail at connect time, before a
        single line of this application runs:

          * `postgresql://` names the psycopg dialect. The async engine needs
            `postgresql+asyncpg://`.
          * `?sslmode=require` — which Neon, Supabase and Render all append — is a
            libpq spelling. asyncpg calls it `ssl`, and passes anything it does not
            recognise straight into `asyncpg.connect()`, where it surfaces as
            `TypeError: connect() got an unexpected keyword argument 'sslmode'`.
            The same goes for `channel_binding`, which asyncpg has no notion of.

        Neither is a warning. Both are a container that will not start, with a
        traceback pointing at SQLAlchemy rather than at the pasted URL.
        """
        from urllib.parse import parse_qsl, urlencode

        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix):]
                break

        base, sep, query = url.partition("?")
        if not sep:
            return url

        kept: list[tuple[str, str]] = []
        for key, value in parse_qsl(query, keep_blank_values=True):
            if key == "sslmode":
                # libpq's disable/allow/prefer/require/verify-* map onto asyncpg's
                # ssl= well enough for the two ends of the range, which is all any
                # of these providers use.
                kept.append(("ssl", "disable" if value == "disable" else "require"))
            elif key == "channel_binding":
                continue  # asyncpg negotiates SCRAM without being told to
            else:
                kept.append((key, value))

        return f"{base}?{urlencode(kept)}" if kept else base

    @property
    def allowed_origins(self) -> list[str]:
        origins = [o.strip() for o in self.frontend_url.split(",") if o.strip()]
        # Always allow localhost for local dev. 3100 is here because 3000 is often
        # taken by another project — a missing port shows up in the browser only as
        # an opaque "Failed to fetch", with no clue that CORS was the cause.
        for port in (3000, 3001, 3100):
            for host in ("localhost", "127.0.0.1"):
                origins.append(f"http://{host}:{port}")
        return list(dict.fromkeys(origins))  # deduplicate, preserve order


    def check_production(self) -> None:
        """Refuse to serve the public internet with a known secret.

        The signing key was in the repo, which means it was in every clone, every
        screenshot and every conversation about this code. A JWT signed with a
        known key is not a credential — anyone can mint one for any user id and
        log in as them, and nothing in the logs distinguishes that from a real
        login. Crashing at startup is the only failure mode that cannot be
        ignored; a warning would scroll past and the site would be open.
        """
        if self.env != "production":
            return
        problems = []
        if self.secret_key == INSECURE_SECRET or len(self.secret_key) < 32:
            problems.append(
                "SECRET_KEY is the shipped placeholder or too short. Generate one "
                "with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        if any(o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o
               for o in self.allowed_origins):
            problems.append("FRONTEND_URL contains a plaintext http:// origin")
        if problems:
            raise RuntimeError("Refusing to start in production:\n  - " + "\n  - ".join(problems))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.check_production()
    return settings
