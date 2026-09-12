"""Tests for shared httpx client configuration and proxy resolution."""

import httpx
import pytest

from mcp_vultr.http_config import (
    PROXY_ENV_VAR,
    ProxyConfigError,
    client_kwargs,
    describe,
    get_proxy,
    is_direct,
    redact,
)

AMBIENT_VARS = [
    "ALL_PROXY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "http_proxy",
    "https_proxy",
]


@pytest.fixture(autouse=True)
def clean_proxy_env(monkeypatch):
    """Start every test from a known-clean proxy environment."""
    for var in [PROXY_ENV_VAR, *AMBIENT_VARS]:
        monkeypatch.delenv(var, raising=False)


@pytest.mark.unit
class TestGetProxy:
    """Proxy URL resolution and precedence."""

    def test_returns_none_when_unconfigured(self):
        assert get_proxy() is None

    def test_reads_env_var(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://127.0.0.1:1080")
        assert get_proxy() == "socks5://127.0.0.1:1080"

    def test_explicit_argument_beats_env_var(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://127.0.0.1:1080")
        assert get_proxy("http://198.51.100.1:3128") == "http://198.51.100.1:3128"

    def test_empty_and_whitespace_env_var_is_unset(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "   ")
        assert get_proxy() is None

    def test_env_var_is_stripped(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "  socks5://127.0.0.1:1080  ")
        assert get_proxy() == "socks5://127.0.0.1:1080"

    @pytest.mark.parametrize("value", ["direct", "none", "off", "DIRECT", "Off"])
    def test_direct_values_resolve_to_no_proxy(self, monkeypatch, value):
        monkeypatch.setenv(PROXY_ENV_VAR, value)
        assert get_proxy() is None
        assert is_direct() is True

    @pytest.mark.parametrize(
        "scheme",
        ["socks5://host:1080", "socks5h://host:1080", "http://host:8080", "https://host:8443"],
    )
    def test_supported_schemes_accepted(self, monkeypatch, scheme):
        monkeypatch.setenv(PROXY_ENV_VAR, scheme)
        assert get_proxy() == scheme

    def test_rejects_unsupported_scheme(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "ftp://127.0.0.1:21")
        with pytest.raises(ProxyConfigError, match="Unsupported proxy scheme"):
            get_proxy()

    def test_rejects_missing_scheme(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "127.0.0.1:1080")
        with pytest.raises(ProxyConfigError, match="missing a scheme"):
            get_proxy()

    def test_rejects_missing_host(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://")
        with pytest.raises(ProxyConfigError, match="missing a host"):
            get_proxy()

    def test_error_names_the_source(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "ftp://127.0.0.1:21")
        with pytest.raises(ProxyConfigError, match=PROXY_ENV_VAR):
            get_proxy()


@pytest.mark.unit
class TestClientKwargs:
    """The kwargs handed to httpx.AsyncClient."""

    def test_empty_when_unconfigured(self):
        assert client_kwargs() == {}

    def test_sets_proxy_from_env(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://127.0.0.1:1080")
        assert client_kwargs() == {"proxy": "socks5://127.0.0.1:1080"}

    def test_direct_disables_trust_env(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "direct")
        assert client_kwargs() == {"trust_env": False}

    def test_overrides_are_merged(self):
        timeout = httpx.Timeout(30.0, connect=10.0)
        assert client_kwargs(timeout=timeout) == {"timeout": timeout}

    def test_overrides_win_over_computed_values(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://127.0.0.1:1080")
        assert client_kwargs(proxy="http://198.51.100.1:3128")["proxy"] == "http://198.51.100.1:3128"

    def test_ambient_proxy_left_alone_by_default(self, monkeypatch):
        """Without VULTR_PROXY we must not touch trust_env, so ALL_PROXY still applies."""
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")
        assert client_kwargs() == {}


@pytest.mark.unit
class TestHttpxIntegration:
    """Verify httpx actually routes the way client_kwargs intends."""

    def _proxy_urls(self, client: httpx.AsyncClient) -> list[str]:
        return [
            str(getattr(getattr(transport, "_pool", None), "_proxy_url", ""))
            for transport in client._mounts.values()
        ]

    def test_env_proxy_produces_proxy_mount(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "http://127.0.0.1:1111")
        client = httpx.AsyncClient(**client_kwargs())
        assert any("1111" in url for url in self._proxy_urls(client))

    def test_configured_proxy_overrides_ambient(self, monkeypatch):
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")
        monkeypatch.setenv(PROXY_ENV_VAR, "http://127.0.0.1:1111")
        client = httpx.AsyncClient(**client_kwargs())
        urls = self._proxy_urls(client)
        assert any("1111" in url for url in urls)
        assert not any("9999" in url for url in urls)

    def test_direct_ignores_ambient(self, monkeypatch):
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")
        monkeypatch.setenv(PROXY_ENV_VAR, "direct")
        client = httpx.AsyncClient(**client_kwargs())
        assert client._mounts == {}

    @pytest.mark.parametrize("scheme", ["socks5", "socks5h"])
    def test_socks_extra_is_installed(self, monkeypatch, scheme):
        """Without httpx[socks] this raises ImportError at construction."""
        monkeypatch.setenv(PROXY_ENV_VAR, f"{scheme}://127.0.0.1:1080")
        client = httpx.AsyncClient(**client_kwargs())
        assert client._mounts


@pytest.mark.unit
class TestRedact:
    """Credentials must never reach the logs."""

    def test_passthrough_without_credentials(self):
        assert redact("socks5://127.0.0.1:1080") == "socks5://127.0.0.1:1080"

    def test_masks_password(self):
        assert redact("socks5://user:hunter2@127.0.0.1:1080") == (
            "socks5://user:***@127.0.0.1:1080"
        )

    def test_password_absent_from_output(self):
        assert "hunter2" not in redact("http://admin:hunter2@proxy.internal:3128")

    def test_describe_redacts(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "socks5://user:hunter2@127.0.0.1:1080")
        summary = describe()
        assert "hunter2" not in summary
        assert "***" in summary


@pytest.mark.unit
class TestDescribe:
    """Human-readable diagnostics."""

    def test_direct_when_unconfigured(self):
        assert describe() == "direct"

    def test_names_ambient_source(self, monkeypatch):
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")
        assert "ALL_PROXY" in describe()

    def test_reports_direct_override(self, monkeypatch):
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")
        monkeypatch.setenv(PROXY_ENV_VAR, "direct")
        assert "ignored" in describe()

    def test_reports_invalid_config_without_raising(self, monkeypatch):
        monkeypatch.setenv(PROXY_ENV_VAR, "ftp://127.0.0.1:21")
        assert describe().startswith("invalid")
