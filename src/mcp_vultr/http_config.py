"""
Shared httpx client configuration for outbound HTTP calls.

Every outbound request in this package (Vultr API, ephemeral key broker,
OAuth JWKS fetch) routes through :func:`client_kwargs` so proxy behaviour is
configured in exactly one place.

By default httpx has ``trust_env=True``, which silently honours the ambient
``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``ALL_PROXY`` / ``NO_PROXY`` variables. That
stays true here, but ``VULTR_PROXY`` lets you set the proxy deliberately for
this package alone, and ``VULTR_PROXY=direct`` opts out of ambient proxying
entirely.

Precedence, highest first:

1. An explicit ``proxy=`` argument passed by the caller
2. ``VULTR_PROXY`` in the environment
3. The ambient httpx proxy variables (``ALL_PROXY`` and friends)
4. A direct connection

SOCKS5 requires the ``socks`` extra, which this package declares as
``httpx[socks]``. Both ``socks5://`` (client-side DNS) and ``socks5h://``
(proxy-side DNS) are supported.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from .vultr_logging import get_logger

logger = get_logger(__name__)

#: Environment variable that configures the proxy for this package only.
PROXY_ENV_VAR = "VULTR_PROXY"

#: Values of ``VULTR_PROXY`` that mean "connect directly, ignore ambient vars".
DIRECT_VALUES = frozenset({"direct", "none", "off"})

#: Proxy URL schemes httpx can route through.
SUPPORTED_SCHEMES = frozenset({"http", "https", "socks5", "socks5h"})


class ProxyConfigError(ValueError):
    """Raised when the configured proxy URL cannot be used."""


def _validate(proxy: str, source: str) -> str:
    """Validate a proxy URL, raising a message that names where it came from."""
    parsed = urlparse(proxy)

    if not parsed.scheme:
        raise ProxyConfigError(
            f"Proxy URL from {source} is missing a scheme: {proxy!r}. "
            f"Expected something like socks5://127.0.0.1:1080"
        )

    if parsed.scheme not in SUPPORTED_SCHEMES:
        supported = ", ".join(sorted(SUPPORTED_SCHEMES))
        raise ProxyConfigError(
            f"Unsupported proxy scheme {parsed.scheme!r} from {source}. "
            f"Supported schemes: {supported}"
        )

    if not parsed.hostname:
        raise ProxyConfigError(
            f"Proxy URL from {source} is missing a host: {proxy!r}"
        )

    return proxy


def get_proxy(explicit: str | None = None) -> str | None:
    """
    Resolve the proxy URL to use for outbound requests.

    Args:
        explicit: Proxy URL supplied by the caller, taking priority over the
            environment. ``None`` falls through to ``VULTR_PROXY``.

    Returns:
        The proxy URL, or ``None`` for a direct connection or to defer to the
        ambient httpx proxy variables.

    Raises:
        ProxyConfigError: If the resolved proxy URL is malformed or uses a
            scheme httpx cannot route through.
    """
    if explicit:
        return _validate(explicit, "the proxy argument")

    from_env = os.environ.get(PROXY_ENV_VAR, "").strip()
    if not from_env:
        return None

    if from_env.lower() in DIRECT_VALUES:
        return None

    return _validate(from_env, PROXY_ENV_VAR)


def is_direct() -> bool:
    """Return True if ``VULTR_PROXY`` explicitly opts out of all proxying."""
    return os.environ.get(PROXY_ENV_VAR, "").strip().lower() in DIRECT_VALUES


def client_kwargs(proxy: str | None = None, **overrides: Any) -> dict[str, Any]:
    """
    Build the keyword arguments for an ``httpx.AsyncClient``.

    Splat the result into the constructor so every client in the package
    resolves proxy settings identically::

        async with httpx.AsyncClient(**client_kwargs(timeout=timeout)) as client:
            ...

    Args:
        proxy: Explicit proxy URL, overriding ``VULTR_PROXY``.
        **overrides: Additional httpx client arguments, applied last so callers
            can override anything computed here.

    Returns:
        Keyword arguments ready to pass to ``httpx.AsyncClient``.

    Raises:
        ProxyConfigError: If the resolved proxy URL is invalid.
    """
    kwargs: dict[str, Any] = {}

    resolved = get_proxy(proxy)
    if resolved:
        kwargs["proxy"] = resolved
        logger.debug("Routing HTTP requests through proxy", proxy=redact(resolved))
    elif is_direct():
        # Ambient HTTP_PROXY/ALL_PROXY would otherwise still apply.
        kwargs["trust_env"] = False
        logger.debug("Proxying disabled, ignoring ambient proxy variables")

    kwargs.update(overrides)
    return kwargs


def redact(proxy: str) -> str:
    """
    Strip credentials from a proxy URL so it is safe to log.

    ``socks5://user:secret@host:1080`` becomes ``socks5://user:***@host:1080``.
    """
    parsed = urlparse(proxy)
    if not parsed.password:
        return proxy

    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"

    return f"{parsed.scheme}://{parsed.username or ''}:***@{host}{parsed.path}"


def describe() -> str:
    """Return a human-readable summary of the active proxy configuration."""
    try:
        resolved = get_proxy()
    except ProxyConfigError as exc:
        return f"invalid ({exc})"

    if resolved:
        return f"{redact(resolved)} (via {PROXY_ENV_VAR})"
    if is_direct():
        return f"direct, ambient proxy variables ignored (via {PROXY_ENV_VAR})"

    ambient = [
        var
        for var in ("ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "all_proxy", "https_proxy", "http_proxy")
        if os.environ.get(var)
    ]
    if ambient:
        return f"inherited from the environment ({', '.join(ambient)})"

    return "direct"
