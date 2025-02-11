import json

from nodes_list.main import find_in_aggr
from nodes_list.response_types import CRNSystemInfo

FAKE_GPU_AGGREGATE = """{
    "community_wallet_address": "0x0000000000000000000000000000",
    "compatible_standard_gpus": [
        { "vendor": "NVIDIA", "model": "L40S", "name": "L40S", "vendor_id": "10de", "device_id": "26b9" },
        { "vendor": "NVIDIA", "model": "RTX 4090", "name": "RTX 4090", "vendor_id": "10de", "device_id": "2684" },
        { "vendor": "NVIDIA", "model": "RTX 4090", "name": "RTX 4090 D", "vendor_id": "10de", "device_id": "2685" },
        { "vendor": "NVIDIA", "model": "RTX 3090", "name": "RTX 3090", "vendor_id": "10de", "device_id": "2204" },
        { "vendor": "NVIDIA", "model": "RTX 3090", "name": "RTX 3090 Ti", "vendor_id": "10de", "device_id": "2203" },
        { "vendor": "NVIDIA", "model": "RTX 4000 ADA", "name": "RTX 4000 SFF Ada Generation", "vendor_id": "10de", "device_id": "27b0" },
        { "vendor": "NVIDIA", "model": "RTX 4000 ADA", "name": "RTX 4000 Ada Generation", "vendor_id": "10de", "device_id": "27b2" }
    ],
    "compatible_premium_gpus": [
        { "vendor": "NVIDIA", "model": "H100", "name": "H100", "vendor_id": "10de", "device_id": "2336" },
        { "vendor": "NVIDIA", "model": "H100", "name": "H100 NVSwitch", "vendor_id": "10de", "device_id": "22a3" },
        { "vendor": "NVIDIA", "model": "H100", "name": "H100 CNX", "vendor_id": "10de", "device_id": "2313" },
        { "vendor": "NVIDIA", "model": "H100", "name": "H100 SXM5 80GB", "vendor_id": "10de", "device_id": "2330" },
        { "vendor": "NVIDIA", "model": "H100", "name": "H100 PCIe", "vendor_id": "10de", "device_id": "2331" },
        { "vendor": "NVIDIA", "model": "A100", "name": "A100", "vendor_id": "10de", "device_id": "2080" },
        { "vendor": "NVIDIA", "model": "A100", "name": "A100", "vendor_id": "10de", "device_id": "2081" },
        { "vendor": "NVIDIA", "model": "A100", "name": "A100 SXM4 80GB", "vendor_id": "10de", "device_id": "20b2" },
        { "vendor": "NVIDIA", "model": "A100", "name": "A100 PCIe 80GB", "vendor_id": "10de", "device_id": "20b5" },
        { "vendor": "NVIDIA", "model": "A100", "name": "A100X", "vendor_id": "10de", "device_id": "20b8" }
    ]
}"""

_sample_system_info_with_gpu = """
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
      },
      {
        "vendor": "NVIDIA",
        "device_name": "AD104GL [RTX 4000 SFF Ada Generation]",
        "device_class": "0300",
        "pci_host": "01:00.0",
        "device_id": "10de:20b5"
      },
      {
        "vendor": "unkown",
        "device_name": "AD104GL [RTX 4000 SFF Ada Generation]",
        "device_class": "0000",
        "pci_host": "01:00.0",
        "device_id": "1111:1111"
      }
    ],
    "available_devices": []
  },
  "active": true
}
"""


# @pytest.mark.asyncio
def test_returns_filtered_gpu():
    sys_info: CRNSystemInfo = json.loads(_sample_system_info_with_gpu)
    aggr = json.loads(FAKE_GPU_AGGREGATE)
    gpu_info = sys_info.get("gpu")

    for gpu in gpu_info["devices"]:
        found = find_in_aggr(aggr, gpu["device_id"])
        gpu["compatible"] = found or "not_compatible"
    for gpu in gpu_info["available_devices"]:
        found = find_in_aggr(aggr, gpu["device_id"])
        gpu["compatible"] = found or "not_compatible"
    assert gpu_info["devices"][0]["compatible"] == "compatible_standard_gpus"
    assert gpu_info["devices"][1]["compatible"] == "compatible_premium_gpus"
    assert gpu_info["devices"][2]["compatible"] == "not_compatible"
