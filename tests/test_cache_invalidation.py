"""
A write must invalidate the reads it changes.

Nothing on the write path ever called `CacheManager.invalidate()`, so a
successful create was followed by up to `ttl` seconds of listings that did not
contain the new object. That reads as a *failed* write rather than a stale one,
and the obvious recovery is to issue the create again.

Reported from live use on 2026-09-12: two `firewall_create_rule` calls returned
fresh rule ids and the rules were reachable, while `firewall_list_rules`
returned byte-identical stale lists. The same shape on a delete invites a
second delete.

The end-to-end tests here are the ones that matter: they assert that a create
is visible in the very next list call on the same client, which is exactly the
sequence that failed in the field.
"""

import httpx
import pytest

from mcp_vultr.cache import CacheManager
from mcp_vultr.server import VultrDNSServer


@pytest.mark.unit
class TestEndpointMatching:
    """Which cached reads a write is considered to touch."""

    @pytest.mark.parametrize(
        ("written", "cached"),
        [
            # the collection listing and the object written to it
            ("/domains/example.com/records", "/domains/example.com/records"),
            ("/domains/example.com/records/rec-1", "/domains/example.com/records"),
            ("/firewalls/g1/rules", "/firewalls/g1/rules"),
            ("/firewalls/g1/rules/47", "/firewalls/g1/rules"),
            # a write below a collection invalidates the collection above it
            ("/instances/abc-123/start", "/instances"),
            ("/firewalls/g1/rules", "/firewalls"),
            # query strings on the cached read are ignored
            ("/instances/abc-123", "/instances?per_page=100"),
        ],
    )
    def test_related_endpoints_are_invalidated(self, written, cached):
        assert CacheManager._touches(written, cached) is True

    @pytest.mark.parametrize(
        ("written", "cached"),
        [
            # sibling resources under the same collection are independent
            ("/firewalls/g1/rules", "/firewalls/g2/rules"),
            ("/domains/a.com/records", "/domains/b.com/records"),
            ("/instances/abc/start", "/instances/def"),
            # unrelated collections entirely
            ("/domains/a.com/records", "/instances"),
            ("/snapshots", "/plans"),
        ],
    )
    def test_unrelated_endpoints_survive(self, written, cached):
        assert CacheManager._touches(written, cached) is False


@pytest.mark.unit
class TestInvalidateEndpoint:
    """The cache-level operation."""

    def test_drops_the_matching_read_and_keeps_the_rest(self):
        cache = CacheManager()
        cache.set("GET", "/firewalls/g1/rules", None, ["stale"])
        cache.set("GET", "/firewalls/g2/rules", None, ["other group"])
        cache.set("GET", "/domains", None, ["unrelated"])

        removed = cache.invalidate_endpoint("/firewalls/g1/rules")

        assert removed == 1
        assert cache.get("GET", "/firewalls/g1/rules") is None
        assert cache.get("GET", "/firewalls/g2/rules") == ["other group"]
        assert cache.get("GET", "/domains") == ["unrelated"]

    def test_drops_every_param_variant_of_the_same_endpoint(self):
        cache = CacheManager()
        cache.set("GET", "/instances", {"page": 1}, ["p1"])
        cache.set("GET", "/instances", {"page": 2}, ["p2"])

        assert cache.invalidate_endpoint("/instances/abc/start") == 2
        assert cache.get("GET", "/instances", {"page": 1}) is None
        assert cache.get("GET", "/instances", {"page": 2}) is None

    def test_counts_invalidations_in_stats(self):
        cache = CacheManager()
        cache.set("GET", "/domains/a.com/records", None, ["x"])
        cache.invalidate_endpoint("/domains/a.com/records")
        assert cache.get_stats()["invalidations"] == 1

    def test_index_does_not_grow_without_bound(self):
        """Dangling index entries are pruned rather than accumulating."""
        cache = CacheManager()
        cache.set("GET", "/domains", None, ["x"])
        cache.domain_cache.clear()  # simulate TTL expiry behind our back

        cache.invalidate_endpoint("/instances")

        assert cache._key_endpoints == {}

    def test_clear_all_resets_the_index(self):
        cache = CacheManager()
        cache.set("GET", "/domains", None, ["x"])
        cache.invalidate()
        assert cache._key_endpoints == {}


@pytest.mark.integration
class TestWriteThenReadEndToEnd:
    """
    The sequence that failed in the field: create, then list, on one client.

    These drive VultrDNSServer itself rather than the cache, so they cover the
    wiring in _make_request as well as the cache logic.
    """

    @pytest.fixture
    def server(self, monkeypatch):
        state = {"rules": [{"id": 1}]}
        calls = {"GET": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                calls["GET"] += 1
                return httpx.Response(200, json={"firewall_rules": list(state["rules"])})
            state["rules"].append({"id": 47})
            return httpx.Response(201, json={"firewall_rule": {"id": 47}})

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient

        def fake_client(**kwargs):
            kwargs.pop("transport", None)
            return real_client(transport=transport, **kwargs)

        monkeypatch.setattr("mcp_vultr.server.httpx.AsyncClient", fake_client)
        srv = VultrDNSServer("test-key")
        srv._calls = calls
        return srv

    async def test_create_is_visible_in_the_very_next_list(self, server):
        before = await server._make_request("GET", "/firewalls/g1/rules")
        assert [r["id"] for r in before["firewall_rules"]] == [1]

        # warm the cache the way the field report did
        cached = await server._make_request("GET", "/firewalls/g1/rules")
        assert cached == before
        assert server._calls["GET"] == 1, "second read should have been a cache hit"

        await server._make_request("POST", "/firewalls/g1/rules", {"port": "22"})

        after = await server._make_request("GET", "/firewalls/g1/rules")
        assert [r["id"] for r in after["firewall_rules"]] == [1, 47], (
            "the rule was created successfully but the listing did not show it"
        )
        assert server._calls["GET"] == 2, "the read after the write must hit the API"

    async def test_delete_invalidates_too(self, server):
        await server._make_request("GET", "/firewalls/g1/rules")
        await server._make_request("DELETE", "/firewalls/g1/rules/1")
        assert server.cache.get("GET", "/firewalls/g1/rules") is None

    async def test_unrelated_reads_stay_cached(self, server):
        await server._make_request("GET", "/firewalls/g1/rules")
        await server._make_request("POST", "/domains/example.com/records", {"type": "A"})
        assert server.cache.get("GET", "/firewalls/g1/rules") is not None
