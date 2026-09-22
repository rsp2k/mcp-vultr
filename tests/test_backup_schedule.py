"""
Per-instance automatic backup schedules.

The schedule endpoints are separate from the instance's `backups` flag: this
sets *when* backups run, while turning them on is `instance_update`. A
schedule on an instance with backups disabled never fires, which is why
`get_schedule` surfaces `enabled` rather than hiding it.

Contract taken from the official Go SDK (`vultr/govultr`, `BackupSchedule` and
`BackupScheduleReq`) and cross-checked against the Terraform provider's
`backups_schedule` block and `vultr-cli`, since Vultr publishes no fetchable
OpenAPI document.
"""

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_vultr.backups import SCHEDULE_TYPES, create_backups_mcp
from mcp_vultr.server import VultrDNSServer

WEB_ID = "11111111-1111-1111-1111-111111111111"
DUPE_A = "22222222-2222-2222-2222-222222222222"
DUPE_B = "33333333-3333-3333-3333-333333333333"

INSTANCES = [
    {"id": WEB_ID, "label": "web", "hostname": "web-01", "main_ip": "203.0.113.5"},
    # Two hosts answering to the same hostname, the migration case that makes
    # first-match resolution dangerous.
    {"id": DUPE_A, "label": "mail-new", "hostname": "mail", "main_ip": "203.0.113.6"},
    {"id": DUPE_B, "label": "mail-old", "hostname": "mail", "main_ip": "203.0.113.7"},
]


@pytest.fixture
def api(monkeypatch):
    """A VultrDNSServer wired to an in-process Vultr, recording writes."""
    state = {
        "schedule": {
            "enabled": True,
            "type": "daily",
            "hour": 3,
            "dow": 0,
            "dom": 0,
            "next_scheduled_time_utc": "2026-09-22 03:00:00",
        },
        "writes": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/instances":
            return httpx.Response(200, json={"instances": INSTANCES})
        if request.method == "GET":
            return httpx.Response(200, json={"backup_schedule": state["schedule"]})
        body = httpx.Request("POST", "http://x", content=request.read()).read()
        import json as _json

        payload = _json.loads(body)
        state["writes"].append((request.url.path, payload))
        state["schedule"] = {**state["schedule"], **payload}
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient

    def fake(**kwargs):
        kwargs.pop("transport", None)
        return real(transport=transport, **kwargs)

    monkeypatch.setattr("mcp_vultr.server.httpx.AsyncClient", fake)
    state["mcp"] = create_backups_mcp(VultrDNSServer("test-key"))
    return state


@pytest.mark.mcp
class TestReadSchedule:
    async def test_get_by_instance_id(self, api):
        async with Client(api["mcp"]) as c:
            result = await c.call_tool("get_schedule", {"instance_identifier": WEB_ID})

        assert result.data["type"] == "daily"
        assert result.data["hour"] == 3
        assert result.data["enabled"] is True

    async def test_get_by_label(self, api):
        async with Client(api["mcp"]) as c:
            result = await c.call_tool("get_schedule", {"instance_identifier": "web"})
        assert result.data["type"] == "daily"

    async def test_get_by_hostname(self, api):
        async with Client(api["mcp"]) as c:
            result = await c.call_tool("get_schedule", {"instance_identifier": "web-01"})
        assert result.data["type"] == "daily"

    async def test_unknown_name_is_reported(self, api):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="not found"):
                await c.call_tool("get_schedule", {"instance_identifier": "nope"})


@pytest.mark.mcp
class TestWriteSchedule:
    async def test_sets_daily_and_reads_back(self, api):
        async with Client(api["mcp"]) as c:
            result = await c.call_tool(
                "set_schedule",
                {"instance_identifier": WEB_ID, "schedule_type": "daily", "hour": 7},
            )

        path, payload = api["writes"][-1]
        assert path == f"/v2/instances/{WEB_ID}/backup-schedule"
        assert payload == {"type": "daily", "hour": 7}
        # read back rather than echoing the request
        assert result.data["hour"] == 7
        assert "next_scheduled_time_utc" in result.data

    async def test_weekly_sends_dow(self, api):
        async with Client(api["mcp"]) as c:
            await c.call_tool(
                "set_schedule",
                {
                    "instance_identifier": WEB_ID,
                    "schedule_type": "weekly",
                    "hour": 5,
                    "dow": 2,
                },
            )
        assert api["writes"][-1][1] == {"type": "weekly", "hour": 5, "dow": 2}

    async def test_monthly_sends_dom(self, api):
        async with Client(api["mcp"]) as c:
            await c.call_tool(
                "set_schedule",
                {
                    "instance_identifier": WEB_ID,
                    "schedule_type": "monthly",
                    "hour": 1,
                    "dom": 15,
                },
            )
        assert api["writes"][-1][1] == {"type": "monthly", "hour": 1, "dom": 15}

    async def test_omitted_fields_are_not_sent(self, api):
        """Sending hour=0 and type only must not smuggle in dow/dom defaults."""
        async with Client(api["mcp"]) as c:
            await c.call_tool(
                "set_schedule",
                {"instance_identifier": WEB_ID, "schedule_type": "daily_alt_even"},
            )
        assert api["writes"][-1][1] == {"type": "daily_alt_even"}


@pytest.mark.mcp
class TestRefusals:
    """Bad input is refused locally, with a message that says what to do."""

    @pytest.mark.parametrize("schedule_type", SCHEDULE_TYPES)
    async def test_every_documented_type_is_accepted(self, api, schedule_type):
        args = {"instance_identifier": WEB_ID, "schedule_type": schedule_type, "hour": 4}
        if schedule_type == "weekly":
            args["dow"] = 1
        if schedule_type == "monthly":
            args["dom"] = 1

        async with Client(api["mcp"]) as c:
            await c.call_tool("set_schedule", args)

        assert api["writes"][-1][1]["type"] == schedule_type

    async def test_unknown_type_lists_the_valid_ones(self, api):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="daily_alt_even"):
                await c.call_tool(
                    "set_schedule",
                    {"instance_identifier": WEB_ID, "schedule_type": "hourly"},
                )
        assert api["writes"] == []

    @pytest.mark.parametrize("hour", [-1, 24, 99])
    async def test_hour_out_of_range(self, api, hour):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="hour must be between 0 and 23"):
                await c.call_tool(
                    "set_schedule",
                    {
                        "instance_identifier": WEB_ID,
                        "schedule_type": "daily",
                        "hour": hour,
                    },
                )

    @pytest.mark.parametrize("dom", [0, 29, 31])
    async def test_dom_out_of_range(self, api, dom):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="dom must be between 1 and 28"):
                await c.call_tool(
                    "set_schedule",
                    {
                        "instance_identifier": WEB_ID,
                        "schedule_type": "monthly",
                        "dom": dom,
                    },
                )

    async def test_weekly_without_dow(self, api):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="weekly schedule needs dow"):
                await c.call_tool(
                    "set_schedule",
                    {"instance_identifier": WEB_ID, "schedule_type": "weekly"},
                )

    async def test_monthly_without_dom(self, api):
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError, match="monthly schedule needs dom"):
                await c.call_tool(
                    "set_schedule",
                    {"instance_identifier": WEB_ID, "schedule_type": "monthly"},
                )

    async def test_ambiguous_hostname_is_refused_not_guessed(self, api):
        """
        Two hosts answering to the same name must not resolve to whichever is first.

        This is the shape that nearly stopped a live mail host during a
        decommission: the old and new box shared a name, and a first-match
        resolver picks one of them silently.
        """
        async with Client(api["mcp"]) as c:
            with pytest.raises(ToolError) as exc:
                await c.call_tool(
                    "set_schedule",
                    {
                        "instance_identifier": "mail",
                        "schedule_type": "daily",
                        "hour": 3,
                    },
                )

        message = str(exc.value)
        assert "matches 2 instances" in message
        assert DUPE_A in message and DUPE_B in message, "must name the candidates"
        assert api["writes"] == [], "nothing may be written when the target is unclear"
