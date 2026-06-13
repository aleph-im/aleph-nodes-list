import pytest

from nodes_list.main import CRNData, DataCache


@pytest.mark.asyncio
async def test_format_response_reports_config_and_system_independently():
    """config and usage debug fields must reflect their own fetch, not each other's.

    Regression test for the copy-paste bug where the usage debug fields read
    from the config CachedResponse, and for config_from_crn always being True.
    """
    cache = DataCache()
    node = {"hash": "abc", "inactive_since": None}
    cache.node_list.set_data({"data": {"corechannel": {"resource_nodes": [node]}}})

    crn = CRNData()
    crn.node_url = "https://node.example/"
    crn.config.set_error(Exception("config boom"))  # config failed: no data
    crn.system.set_data({"mem": {"total_kB": 1}, "active": True})  # system succeeded
    cache.crn_infos["abc"] = crn

    resp = await cache.format_response(filter_inactive=False)
    [crn_resp] = resp["crns"]

    assert crn_resp["config_from_crn"] is False
    assert crn_resp["debug_config_from_crn_error"] == "config boom"
    assert crn_resp["usage_from_crn_error"] == "None"
    assert crn_resp["debug_usage_from_crn_at"] is not None
    assert crn_resp["system_usage"] == {"mem": {"total_kB": 1}, "active": True}
