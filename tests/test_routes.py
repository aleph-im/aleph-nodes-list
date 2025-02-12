import datetime

import pytest
from aioresponses import aioresponses
from fastapi.testclient import TestClient
from nodes_list import main
from nodes_list.main import app, SETTING_AGGREGATE_URL
from .test_gpu_aggregate import FAKE_GPU_AGGREGATE

from .test_parse_responses import (
    mock_node_aggr,
    mock_status_config,
    mock_usage_system,
    mock_ipv6_check,
)

client = TestClient(app)

FAKE_TIME = datetime.datetime(2020, 12, 25, 17, 5, 55)


@pytest.fixture
def patch_datetime_now(monkeypatch):
    class mydatetime:
        @classmethod
        def now(cls, tz=None):
            if tz:
                return FAKE_TIME.replace(tzinfo=tz)
            return FAKE_TIME

    monkeypatch.setattr(datetime, "datetime", mydatetime)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "<h1>" in response.text


def test_crn():
    """Basic check that the endpoint don't crash.
    TEST WITH REAL ENDPOINTS so might be slow"""
    response = client.get("/crns.json")
    assert response.status_code == 200
    assert response.json()


def test_mock_data(patch_datetime_now):
    with aioresponses() as mock_responses:
        main.data_cache = main.DataCache()
        mock_responses.get(
            "https://api2.aleph.im/api/v0/aggregates/0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10.json?keys=corechannel",
            body=mock_node_aggr,
        )
        mock_responses.get(
            SETTING_AGGREGATE_URL,
            body=FAKE_GPU_AGGREGATE,
        )
        mock_responses.get("https://gpu-test-02.nergame.app/about/usage/system", body=mock_usage_system)
        mock_responses.get("https://gpu-test-02.nergame.app/status/config", body=mock_status_config)
        mock_responses.get("https://gpu-test-02.nergame.app/status/check/ipv6", body=mock_ipv6_check)
        "Basic check that the endpoint don't crash"
        response = client.get("/crns.json")
        assert response.status_code == 200
        expected_response = {
            "crns": [
                {
                    "address": "https://gpu-test-02.nergame.app/",
                    "authorized": "",
                    "banner": "",
                    "compatible_available_gpus": [],
                    "compatible_gpus": [
                        {
                            "device_class": "0300",
                            "device_id": "10de:27b0",
                            "device_name": "AD104GL [RTX 4000 SFF Ada " "Generation]",
                            "pci_host": "01:00.0",
                            "vendor": "NVIDIA",
                        }
                    ],
                    "confidential_support": False,
                    "config_from_crn": True,
                    "debug_config_from_crn_at": "2020-12-25T17:05:55+00:00",
                    "debug_config_from_crn_error": "None",
                    "decentralization": 0.8393111079955136,
                    "description": "This is a test CRN, please don't use it",
                    "gpu_support": True,
                    "hash": "e9423d9f9fd27cdc9c4c27d5cf3120ef573eece260d44e6df76b3c27569a3154",
                    "inactive_since": 21424667,
                    "ipv6_check": {"host": True, "vm": True},
                    "locked": False,
                    "manager": "",
                    "multiaddress": "",
                    "name": "Andres test node instance",
                    "owner": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
                    "parent": None,
                    "payment_receiver_address": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
                    "performance": 0.875798448016674,
                    "picture": "",
                    "qemu_support": True,
                    "registration_url": "",
                    "reward": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
                    "score": 0,
                    "score_updated": True,
                    "status": "waiting",
                    "stream_reward": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
                    "system_usage": {
                        "active": True,
                        "cpu": {
                            "core_frequencies": {"max": 4280, "min": 800},
                            "count": 20,
                            "load_average": {
                                "load1": 2.283203125,
                                "load15": 2.27001953125,
                                "load5": 2.27490234375,
                            },
                        },
                        "disk": {"available_kB": 1450697875, "total_kB": 1853812338},
                        "gpu": {
                            "available_devices": [],
                            "devices": [
                                {
                                    "device_class": "0300",
                                    "device_id": "10de:27b0",
                                    "device_name": "AD104GL [RTX " "4000 SFF Ada " "Generation]",
                                    "pci_host": "01:00.0",
                                    "vendor": "NVIDIA",
                                }
                            ],
                        },
                        "mem": {"available_kB": 40982622, "total_kB": 67219543},
                        "period": {
                            "duration_seconds": 60,
                            "start_timestamp": "2025-02-10T13:43:00+00:00",
                        },
                        "properties": {
                            "cpu": {
                                "architecture": "x86_64",
                                "features": [],
                                "vendor": "GenuineIntel",
                            }
                        },
                    },
                    "terms_and_conditions": "a5e9c41304c53cef9764c87e66f70e822934e2111ee0eb33a063102af8a06180",
                    "time": 1734453024.6,
                    "type": "compute",
                    "version": "1.3.0-41-g7303587",
                }
            ],
            "last_refresh": "2020-12-25T17:05:55+00:00",
        }
        assert response.json() == expected_response
