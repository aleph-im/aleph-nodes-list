import json

from nodes_list.main import find_in_aggr
from nodes_list.response_types import CRNSystemInfo

FAKE_GPU_AGGREGATE = """{
  "address": "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874",
  "data": {
    "settings": {
      "compatible_gpus": [
        { "name": "L40S", "model": "L40S", "vendor": "NVIDIA", "model_id": "26b9", "vendor_id": "10de" },
        { "name": "RTX 5090", "model": "RTX 5090", "vendor": "NVIDIA", "model_id": "2685", "vendor_id": "10de" },
        { "name": "RTX 5090 D", "model": "RTX 5090", "vendor": "NVIDIA", "model_id": "2687", "vendor_id": "10de" },
        { "name": "RTX 4090", "model": "RTX 4090", "vendor": "NVIDIA", "model_id": "2684", "vendor_id": "10de" },
        { "name": "RTX 4090 D", "model": "RTX 4090", "vendor": "NVIDIA", "model_id": "2685", "vendor_id": "10de" },
        { "name": "RTX 3090", "model": "RTX 3090", "vendor": "NVIDIA", "model_id": "2204", "vendor_id": "10de" },
        { "name": "RTX 3090 Ti", "model": "RTX 3090", "vendor": "NVIDIA", "model_id": "2203", "vendor_id": "10de" },
        { "name": "RTX 4000 SFF Ada Generation", "model": "RTX 4000 ADA", "vendor": "NVIDIA", "model_id": "27b0", "vendor_id": "10de" },
        { "name": "RTX 4000 Ada Generation", "model": "RTX 4000 ADA", "vendor": "NVIDIA", "model_id": "27b2", "vendor_id": "10de" },
        { "name": "H100", "model": "H100", "vendor": "NVIDIA", "model_id": "2336", "vendor_id": "10de" },
        { "name": "H100 NVSwitch", "model": "H100", "vendor": "NVIDIA", "model_id": "22a3", "vendor_id": "10de" },
        { "name": "H100 CNX", "model": "H100", "vendor": "NVIDIA", "model_id": "2313", "vendor_id": "10de" },
        { "name": "H100 SXM5 80GB", "model": "H100", "vendor": "NVIDIA", "model_id": "2330", "vendor_id": "10de" },
        { "name": "H100 PCIe", "model": "H100", "vendor": "NVIDIA", "model_id": "2331", "vendor_id": "10de" },
        { "name": "A100", "model": "A100", "vendor": "NVIDIA", "model_id": "2080", "vendor_id": "10de" },
        { "name": "A100", "model": "A100", "vendor": "NVIDIA", "model_id": "2081", "vendor_id": "10de" },
        { "name": "A100 SXM4 80GB", "model": "A100", "vendor": "NVIDIA", "model_id": "20b2", "vendor_id": "10de" },
        { "name": "A100 PCIe 80GB", "model": "A100", "vendor": "NVIDIA", "model_id": "20b5", "vendor_id": "10de" },
        { "name": "A100X", "model": "A100", "vendor": "NVIDIA", "model_id": "20b8", "vendor_id": "10de" }
      ],
      "community_wallet_address": "0x0000000000000000000000000000"
    }
  },
  "info": {}
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


def test_returns_filtered_gpu():
    sys_info: CRNSystemInfo = json.loads(_sample_system_info_with_gpu)
    aggr = json.loads(FAKE_GPU_AGGREGATE)
    gpu_info = sys_info.get("gpu")

    compat = [gpu for gpu in gpu_info["devices"] if find_in_aggr(aggr, gpu["device_id"])]
    assert len(compat) == 2
    assert compat == [
        {
            "vendor": "NVIDIA",
            "device_name": "AD104GL [RTX 4000 SFF Ada Generation]",
            "device_class": "0300",
            "pci_host": "01:00.0",
            "device_id": "10de:27b0",
        },
        {
            "vendor": "NVIDIA",
            "device_name": "AD104GL [RTX 4000 SFF Ada Generation]",
            "device_class": "0300",
            "pci_host": "01:00.0",
            "device_id": "10de:20b5",
        },
    ]
