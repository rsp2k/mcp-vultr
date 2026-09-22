"""
Resolving a human-friendly name to a resource ID.

Every service module lets you pass a label, description or hostname instead of
a UUID. Each one used to do its own linear search and return the first match,
which is fine until two resources share a name. That happens routinely during
a migration, and the failure is silent: the call succeeds against whichever
resource happened to come back first.

It nearly stopped a live mail host during a decommission, where the retired
and replacement instances both answered to the same hostname. So a name that
matches more than one resource is an error here, and the error names the
candidates so the caller can pick one.
"""

from __future__ import annotations

from typing import Any


def is_uuid_format(value: str) -> bool:
    """
    Check whether a string looks like a UUID.

    Deliberately shape-only rather than a real parse: Vultr IDs are opaque and
    the point is just to skip the lookup when the caller clearly passed an ID.
    """
    return bool(len(value) == 36 and value.count("-") == 4)


def describe_candidate(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    """Render one ambiguous match as `id (name, ip)` for an error message."""
    parts: list[str] = []

    name = next((item[f] for f in fields if item.get(f)), None)
    if name:
        parts.append(str(name))

    # Not every resource has one; when it does it is the fastest way for a
    # human to tell two same-named hosts apart.
    ip = item.get("main_ip")
    if ip:
        parts.append(str(ip))

    ident = str(item.get("id", "unknown"))
    return f"{ident} ({', '.join(parts)})" if parts else ident


def resolve_unique(
    items: list[dict[str, Any]],
    identifier: str,
    fields: tuple[str, ...],
    kind: str,
    id_field: str = "id",
) -> str:
    """
    Find the one resource named `identifier` and return its ID.

    Args:
        items: Candidate resources, as returned by the matching list call
        identifier: The label, description, hostname or name to match
        fields: Field names to match against, in display preference order
        kind: Human-readable resource name for error messages, e.g. "Instance"
        id_field: Field holding the resource ID

    Returns:
        The resource ID

    Raises:
        ValueError: If nothing matches, or more than one thing does. An
            ambiguous name is never resolved to one of the candidates.
    """
    matches = [
        item
        for item in items
        if any(item.get(field) == identifier for field in fields)
    ]

    if not matches:
        searched = " or ".join(fields)
        raise ValueError(
            f"{kind} '{identifier}' not found (searched by {searched})"
        )

    if len(matches) > 1:
        listed = ", ".join(describe_candidate(item, fields) for item in matches)
        raise ValueError(
            f"'{identifier}' matches {len(matches)} {kind.lower()}s: {listed}. "
            f"Pass the ID to say which one you mean."
        )

    return matches[0][id_field]


async def resolve_id(
    identifier: str,
    list_call,
    fields: tuple[str, ...],
    kind: str,
    id_field: str = "id",
) -> str:
    """
    Resolve an identifier that may already be an ID.

    Returns `identifier` untouched when it looks like a UUID, so the common
    case costs no API call.

    Args:
        identifier: A resource ID, or a name to look up
        list_call: Zero-argument coroutine function returning the candidates
        fields: Field names to match against
        kind: Human-readable resource name for error messages
        id_field: Field holding the resource ID

    Returns:
        The resource ID
    """
    if is_uuid_format(identifier):
        return identifier

    return resolve_unique(await list_call(), identifier, fields, kind, id_field)
