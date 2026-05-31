"""Configuration + secret resolution.

`.env` holds NAMES/PATHS only. In LIVE mode, `config.py` resolves the actual
secret values from Vault/KMS at runtime. In MOCK mode, no real secrets are
needed and adapters run simulated. This module is the single place that knows
how to turn a secret *path* into a secret *value*.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["MOCK", "LIVE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIP_", env_file=".env", extra="ignore")

    mode: Mode = "MOCK"

    database_url: str = "sqlite:///./data/cip.db"
    bus_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"

    secrets_backend: str = "env"
    vault_addr: str = "http://localhost:8200"
    vault_token_path: str = "secret/data/cip/vault-token"

    venafi_platform: str = "VCP"
    venafi_base_url: str = "https://api.venafi.cloud"
    venafi_apikey_path: str = "secret/data/cip/venafi/apikey"
    venafi_tpp_token_path: str = "secret/data/cip/venafi/tpp-oauth"

    jira_base_url: str = "https://your-org.atlassian.net"
    jira_user_path: str = "secret/data/cip/jira/user"
    jira_token_path: str = "secret/data/cip/jira/token"
    jira_default_project: str = "CERT"

    teams_p1_webhook_path: str = "secret/data/cip/teams/p1"
    teams_p2_webhook_path: str = "secret/data/cip/teams/p2"
    teams_p3_webhook_path: str = "secret/data/cip/teams/p3"

    cmdb_kind: str = "mock"
    cmdb_base_url: str = "https://your-org.service-now.com"
    cmdb_token_path: str = "secret/data/cip/cmdb/token"

    openai_apikey_path: str = "secret/data/cip/openai/apikey"
    openai_model: str = "gpt-4o-mini"

    tool_signing_key_path: str = "secret/data/cip/tool-signing-key"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Comma-separated allowed origins. Defaults cover the common local dev ports
    # so the dashboard works without Docker even if Next.js falls back from 3000
    # to 3001/3002 when a port is busy. Override via CIP_CORS_ORIGINS in prod.
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    )

    scan_cron: str = "0 6 * * *"
    scan_windows: str = "7,30,60,90"

    @property
    def scan_window_list(self) -> list[int]:
        return [int(x) for x in self.scan_windows.split(",") if x.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


class SecretResolver:
    """Resolves a secret *path* to its value.

    - env backend (MOCK/dev): reads an env var derived from the path, else "".
    - vault backend (LIVE): reads from HashiCorp Vault KV v2.

    A missing secret in MOCK mode returns "" and adapters fall back to simulation.
    In LIVE mode a missing required secret raises.
    """

    def __init__(self, settings: Settings):
        self.s = settings
        self._vault = None

    def _env_key(self, path: str) -> str:
        # secret/data/cip/jira/token -> CIP_SECRET_JIRA_TOKEN
        tail = path.replace("secret/data/cip/", "").replace("secret/data/", "")
        return "CIP_SECRET_" + tail.upper().replace("/", "_").replace("-", "_")

    def get(self, path: str, *, required: bool = False) -> str:
        if self.s.secrets_backend == "vault" and self.s.mode == "LIVE":
            return self._get_vault(path, required=required)
        val = os.getenv(self._env_key(path), "")
        if not val and required and self.s.mode == "LIVE":
            raise RuntimeError(f"Required secret not found: {path}")
        return val

    def _get_vault(self, path: str, *, required: bool) -> str:
        try:  # lazy import; hvac optional
            import hvac  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("vault backend selected but hvac not installed") from e
        if self._vault is None:  # pragma: no cover - needs live vault
            token = os.getenv("VAULT_TOKEN", "")
            self._vault = hvac.Client(url=self.s.vault_addr, token=token)
        mount, _, secret_path = path.replace("secret/data/", "").partition("/")
        resp = self._vault.secrets.kv.v2.read_secret_version(  # pragma: no cover
            path=secret_path or mount
        )
        data = resp["data"]["data"]
        value = next(iter(data.values()), "")
        if not value and required:
            raise RuntimeError(f"Required secret empty in Vault: {path}")
        return value


@lru_cache
def get_secrets() -> SecretResolver:
    return SecretResolver(get_settings())
