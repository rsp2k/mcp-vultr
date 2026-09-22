"""
Name-to-ID resolution, and the instance tools that were missing.

The resolver's job is to refuse an ambiguous name rather than silently pick
one. Every service module used to do its own first-match search, so two
resources sharing a label resolved to whichever the API listed first. That
nearly stopped a live mail host during a decommission, where the retired and
replacement instances answered to the same hostname.
"""

import json

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_vultr.instances import create_instances_mcp
from mcp_vultr.lookup import is_uuid_format, resolve_id, resolve_unique
from mcp_vultr.server import VultrDNSServer

WEB = {
    "id": "11111111-1111-1111-1111-111111111111",
    "label": "web",
    "hostname": "web-01",
    "region": "ewr",
    "plan": "vc2-1c-1gb",
    "power_status": "running",
    "main_ip": "203.0.113.5",
}
MAIL_NEW = {
    "id": "22222222-2222-2222-2222-222222222222",
    "label": "mail-new",
    "hostname": "mail",
    "region": "ewr",
    "plan": "vc2-2c-4gb",
    "power_status": "running",
    "main_ip": "203.0.113.6",
}
MAIL_OLD = {
    "id": "33333333-3333-3333-3333-333333333333",
    "label": "mail-old",
    "hostname": "mail",
    "region": "ewr",
    "plan": "vc2-2c-4gb",
    "power_status": "stopped",
    "main_ip": "203.0.113.7",
}
INSTANCES = [WEB, MAIL_NEW, MAIL_OLD]


@pytest.mark.unit
class TestIsUuidFormat:
    @pytest.mark.parametrize("value", [WEB["id"], MAIL_NEW["id"]])
    def test_accepts_ids(self, value):
        assert is_uuid_format(value) is True

    @pytest.mark.parametrize("value", ["web", "mail", "", "1234", "a" * 36])
    def test_rejects_names(self, value):
        assert is_uuid_format(value) is False


@pytest.mark.unit
class TestResolveUnique:
    def test_single_match_returns_its_id(self):
        assert (
            resolve_unique(INSTANCES, "web", ("label", "hostname"), "Instance")
            == WEB["id"]
        )

    def test_matches_any_listed_field(self):
        assert (
            resolve_unique(INSTANCES, "web-01", ("label", "hostname"), "Instance")
            == WEB["id"]
        )

    def test_no_match_names_the_fields_searched(self):
        with pytest.raises(ValueError, match="searched by label or hostname"):
            resolve_unique(INSTANCES, "ghost", ("label", "hostname"), "Instance")

    def test_ambiguous_name_is_refused(self):
        with pytest.raises(ValueError) as exc:
            resolve_unique(INSTANCES, "mail", ("label", "hostname"), "Instance")

        message = str(exc.value)
        assert "matches 2 instances" in message
        assert MAIL_NEW["id"] in message and MAIL_OLD["id"] in message
        assert "203.0.113.6" in message, "the IP is how a human tells them apart"
        assert "Pass the ID" in message

    def test_ambiguity_is_refused_even_when_one_match_would_do(self):
        """Never quietly prefer the first, the newest, or the running one."""
        with pytest.raises(ValueError):
            resolve_unique(INSTANCES, "mail", ("hostname",), "Instance")

    def test_respects_a_custom_id_field(self):
        items = [{"sshkey_id": "k1", "name": "deploy"}]
        assert (
            resolve_unique(items, "deploy", ("name",), "SSH key", id_field="sshkey_id")
            == "k1"
        )


@pytest.mark.unit
class TestResolveId:
    async def test_uuid_shortcuts_without_listing(self):
        async def must_not_be_called():
            raise AssertionError("passing an ID must not cost an API call")

        got = await resolve_id(
            WEB["id"], must_not_be_called, ("label",), "Instance"
        )
        assert got == WEB["id"]

    async def test_name_triggers_a_lookup(self):
        async def listing():
            return INSTANCES

        assert await resolve_id("web", listing, ("label",), "Instance") == WEB["id"]


@pytest.fixture
def instances_mcp(monkeypatch):
    """An instances server backed by an in-process Vultr."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/instances":
            return httpx.Response(200, json={"instances": INSTANCES})
        ident = request.url.path.rsplit("/", 1)[-1]
        match = next((i for i in INSTANCES if i["id"] == ident), None)
        if match is None:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"instance": match})

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient

    def fake(**kwargs):
        kwargs.pop("transport", None)
        return real(transport=transport, **kwargs)

    monkeypatch.setattr("mcp_vultr.server.httpx.AsyncClient", fake)
    return create_instances_mcp(VultrDNSServer("test-key"))


@pytest.mark.mcp
class TestInstanceListAndGet:
    """The two tools an agent reaches for first, which did not exist."""

    async def test_list_is_compact_by_default(self, instances_mcp):
        async with Client(instances_mcp) as c:
            result = await c.call_tool("list", {})

        text = result.content[0].text
        assert "3 instance(s)" in text
        # the fields fleet work actually needs
        assert WEB["id"] in text
        assert "running" in text and "stopped" in text
        assert "203.0.113.5" in text

    async def test_list_json_format(self, instances_mcp):
        async with Client(instances_mcp) as c:
            result = await c.call_tool("list", {"format": "json"})

        parsed = json.loads(result.content[0].text)
        assert {i["id"] for i in parsed} == {i["id"] for i in INSTANCES}

    async def test_get_by_id(self, instances_mcp):
        async with Client(instances_mcp) as c:
            result = await c.call_tool("get", {"instance_id": WEB["id"]})
        assert result.data["hostname"] == "web-01"

    async def test_get_by_label(self, instances_mcp):
        async with Client(instances_mcp) as c:
            result = await c.call_tool("get", {"instance_id": "web"})
        assert result.data["id"] == WEB["id"]

    async def test_get_refuses_an_ambiguous_name(self, instances_mcp):
        async with Client(instances_mcp) as c:
            with pytest.raises(ToolError, match="matches 2 instances"):
                await c.call_tool("get", {"instance_id": "mail"})


@pytest.mark.mcp
class TestDestructiveToolsRefuseAmbiguity:
    """
    The tools that made this worth fixing.

    Stopping or deleting the wrong one of two same-named hosts is not
    recoverable by retrying, so these must refuse rather than choose.
    """

    @pytest.mark.parametrize("tool", ["stop", "start", "reboot", "delete"])
    async def test_ambiguous_name_never_reaches_the_api(self, instances_mcp, tool):
        async with Client(instances_mcp) as c:
            with pytest.raises(ToolError) as exc:
                await c.call_tool(tool, {"instance_id": "mail"})

        message = str(exc.value)
        assert "matches 2 instances" in message
        assert MAIL_NEW["id"] in message and MAIL_OLD["id"] in message
