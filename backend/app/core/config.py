from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    enabled_engines: tuple[str, ...]
    artifact_store_kind: str
    s3_endpoint_url: str | None
    s3_access_key_id: str | None
    s3_secret_access_key: str | None
    s3_bucket: str | None
    api_keys: dict[str, tuple[str, ...]]


def _parse_api_keys(raw: str) -> dict[str, tuple[str, ...]]:
    raw = raw.strip()
    if not raw:
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise ValueError("Invalid TODISCOPE_API_KEYS entry (expected key:role1|role2)")
        key, roles_part = entry.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError("Invalid TODISCOPE_API_KEYS entry (empty key)")
        roles = tuple(r.strip() for r in roles_part.split("|") if r.strip())
        if not roles:
            roles = ("read",)
        out[key] = roles
    return out


def get_settings() -> Settings:
    enabled = os.getenv("TODISCOPE_ENABLED_ENGINES", "")
    enabled_engines = tuple([e.strip() for e in enabled.split(",") if e.strip()])
    return Settings(
        database_url=os.getenv("TODISCOPE_DATABASE_URL"),
        enabled_engines=enabled_engines,
        artifact_store_kind=os.getenv("TODISCOPE_ARTIFACT_STORE_KIND", "memory"),
        s3_endpoint_url=os.getenv("TODISCOPE_S3_ENDPOINT_URL"),
        s3_access_key_id=os.getenv("TODISCOPE_S3_ACCESS_KEY_ID"),
        s3_secret_access_key=os.getenv("TODISCOPE_S3_SECRET_ACCESS_KEY"),
        s3_bucket=os.getenv("TODISCOPE_S3_BUCKET"),
        api_keys=_parse_api_keys(os.getenv("TODISCOPE_API_KEYS", "")),
    )
