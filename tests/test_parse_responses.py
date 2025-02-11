import pytest
from aioresponses import aioresponses
from nodes_list.main import DataCache, _fetch_node_list

mock_node_aggr = """
{
  "address": "0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10",
  "data": {
    "corechannel": {
      "resource_nodes": [
        {
          "hash": "e9423d9f9fd27cdc9c4c27d5cf3120ef573eece260d44e6df76b3c27569a3154",
          "name": "Andres test node instance",
          "time": 1734453024.6,
          "type": "compute",
          "owner": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
          "score": 0,
          "banner": "",
          "locked": false,
          "parent": null,
          "reward": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
          "status": "waiting",
          "address": "https://gpu-test-02.nergame.app/",
          "manager": "",
          "picture": "",
          "authorized": "",
          "description": "This is a test CRN, please don't use it",
          "performance": 0.875798448016674,
          "multiaddress": "",
          "score_updated": true,
          "stream_reward": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
          "inactive_since": 21424667,
          "decentralization": 0.8393111079955136,
          "registration_url": "",
          "terms_and_conditions": "a5e9c41304c53cef9764c87e66f70e822934e2111ee0eb33a063102af8a06180"
        }
        ]}}}
"""

mock_usage_system = """
{
  "cpu": {
    "count": 20,
    "load_average": {
      "load1": 2.283203125,
      "load5": 2.27490234375,
      "load15": 2.27001953125
    },
    "core_frequencies": {
      "min": 800,
      "max": 4280
    }
  },
  "mem": {
    "total_kB": 67219543,
    "available_kB": 40982622
  },
  "disk": {
    "total_kB": 1853812338,
    "available_kB": 1450697875
  },
  "period": {
    "start_timestamp": "2025-02-10T13:43:00+00:00",
    "duration_seconds": 60
  },
  "properties": {
    "cpu": {
      "architecture": "x86_64",
      "vendor": "GenuineIntel",
      "features": []
    }
  },
  "gpu": {
    "devices": [
      {
        "vendor": "NVIDIA",
        "device_name": "AD104GL [RTX 4000 SFF Ada Generation]",
        "device_class": "0300",
        "pci_host": "01:00.0",
        "device_id": "10de:27b0"
      }
    ],
    "available_devices": []
  },
  "active": true
}"""

mock_status_config = """
{
  "DOMAIN_NAME": "gpu-test-02.nergame.app",
  "version": "1.3.0-41-g7303587",
  "references": {
    "API_SERVER": "https://official.aleph.cloud",
    "CHECK_FASTAPI_VM_ID": "63faf8b5db1cf8d965e6a464a0cb8062af8e7df131729e48738342d956f29ace",
    "CONNECTOR_URL": "http://localhost:4021"
  },
  "security": {
    "USE_JAILER": true,
    "PRINT_SYSTEM_LOGS": true,
    "WATCH_FOR_UPDATES": true,
    "ALLOW_VM_NETWORKING": true,
    "USE_DEVELOPER_SSH_KEYS": false
  },
  "networking": {
    "IPV6_ADDRESS_POOL": "2a01:4f8:110:142e::/64",
    "IPV6_ALLOCATION_POLICY": "IPv6AllocationPolicy.static",
    "IPV6_SUBNET_PREFIX": 124,
    "IPV6_FORWARDING_ENABLED": true,
    "USE_NDP_PROXY": true
  },
  "debug": {
    "SENTRY_DSN_CONFIGURED": false,
    "DEBUG_ASYNCIO": false,
    "EXECUTION_LOG_ENABLED": false
  },
  "payment": {
    "PAYMENT_RECEIVER_ADDRESS": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
    "AVAILABLE_PAYMENTS": {
      "Chain.AVAX": {
        "chain_id": 43114,
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "standard_token": null,
        "super_token": "0xc0Fbc4967259786C743361a5885ef49380473dCF",
        "testnet": false,
        "active": true
      },
      "Chain.BASE": {
        "chain_id": 8453,
        "rpc": "https://base-mainnet.public.blastapi.io",
        "standard_token": null,
        "super_token": "0xc0Fbc4967259786C743361a5885ef49380473dCF",
        "testnet": false,
        "active": true
      }
    },
    "PAYMENT_MONITOR_INTERVAL": 60
  },
  "computing": {
    "ENABLE_QEMU_SUPPORT": true,
    "INSTANCE_DEFAULT_HYPERVISOR": "firecracker",
    "ENABLE_CONFIDENTIAL_COMPUTING": false,
    "ENABLE_GPU_SUPPORT": true
  }
}"""


mock_ipv6_check = """{"host": true, "vm": true}"""


@pytest.mark.asyncio
async def test_fetch_node_list():
    with aioresponses() as mock_responses:
        mock_responses.get(
            "https://api2.aleph.im/api/v0/aggregates/0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10.json?keys=corechannel",
            body=mock_node_aggr,
        )
        await _fetch_node_list()


@pytest.mark.asyncio
async def test_fetch_node_data():
    with aioresponses() as mock_responses:
        mock_responses.get(
            "https://api2.aleph.im/api/v0/aggregates/0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10.json?keys=corechannel",
            body=mock_node_aggr,
        )
        mock_responses.get("https://gpu-test-02.nergame.app/about/usage/system", body=mock_usage_system)
        mock_responses.get("https://gpu-test-02.nergame.app/status/config", body=mock_status_config)
        mock_responses.get("https://gpu-test-02.nergame.app/status/check/ipv6", body=mock_ipv6_check)

        cache = DataCache()
        await cache.fetch_node_list_and_node_data()
        assert len(cache.node_list.data["data"]["corechannel"]["resource_nodes"]) == 1
        assert len(cache.crn_infos) == 1
        assert cache.crn_infos["e9423d9f9fd27cdc9c4c27d5cf3120ef573eece260d44e6df76b3c27569a3154"].gpu_support is True
        assert cache.crn_infos["e9423d9f9fd27cdc9c4c27d5cf3120ef573eece260d44e6df76b3c27569a3154"].config.error == None
        assert (
            cache.crn_infos["e9423d9f9fd27cdc9c4c27d5cf3120ef573eece260d44e6df76b3c27569a3154"].system.data["mem"][
                "total_kB"
            ]
            == 67219543
        )
