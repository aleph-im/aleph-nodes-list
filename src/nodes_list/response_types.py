"""Response format we expect from the Aggregate and CRN apis.

This is mainly for typing we don't enforce it as to be liberal in the format we accept"""

from typing import Literal, NotRequired, TypedDict


# Aggregate
# {data: corechannel: {resource_nodes : [ResourceNodeInfo], nodes: [NodeInfo]}}
class CommonNodeInfo(TypedDict):
    hash: str
    name: str
    time: float
    owner: str
    score: float
    banner: str
    locked: bool | Literal[""]  # Can be a boolean or an empty string
    reward: str
    status: str
    address: str  # URL
    manager: str
    picture: str
    authorized: list[str] | str  # List of address or empty string
    description: str
    performance: float
    multiaddress: str
    score_updated: NotRequired[bool]
    stream_reward: str
    inactive_since: float | None  # Can be None
    decentralization: float
    registration_url: str
    terms_and_conditions: str


class ResourceNodeInfo(CommonNodeInfo):
    type: str
    parent: str | None


class NodeInfo(CommonNodeInfo):
    stakers: dict[str, float]  # Address and amount
    has_bonus: bool
    total_staked: float
    resource_nodes: list


class CoreChannelData(TypedDict):
    nodes: list[NodeInfo]
    resource_nodes: list[ResourceNodeInfo]


class NodeData(TypedDict):
    corechannel: CoreChannelData


class NodeAggregate(TypedDict):
    data: NodeData
    address: str
    info: dict


###  CRN "/status/config"


class PaymentDetails(TypedDict):
    chain_id: int
    rpc: str
    standard_token: str | None
    super_token: str
    testnet: bool
    active: bool


class PaymentConfig(TypedDict):
    PAYMENT_RECEIVER_ADDRESS: str
    AVAILABLE_PAYMENTS: dict[str, PaymentDetails]
    PAYMENT_MONITOR_INTERVAL: float


class SecurityConfig(TypedDict):
    USE_JAILER: bool
    PRINT_SYSTEM_LOGS: bool
    WATCH_FOR_UPDATES: bool
    ALLOW_VM_NETWORKING: bool
    USE_DEVELOPER_SSH_KEYS: bool


class NetworkingConfig(TypedDict):
    IPV6_ADDRESS_POOL: str
    IPV6_ALLOCATION_POLICY: str
    IPV6_SUBNET_PREFIX: int
    IPV6_FORWARDING_ENABLED: bool
    USE_NDP_PROXY: bool


class DebugConfig(TypedDict):
    SENTRY_DSN_CONFIGURED: bool
    DEBUG_ASYNCIO: bool
    EXECUTION_LOG_ENABLED: bool


class ComputingConfig(TypedDict):
    ENABLE_QEMU_SUPPORT: bool
    INSTANCE_DEFAULT_HYPERVISOR: str
    ENABLE_CONFIDENTIAL_COMPUTING: bool
    ENABLE_GPU_SUPPORT: bool


class ReferencesConfig(TypedDict):
    API_SERVER: str
    CHECK_FASTAPI_VM_ID: str
    CONNECTOR_URL: str


class CrnConfig(TypedDict):
    DOMAIN_NAME: str
    version: str
    references: ReferencesConfig
    security: SecurityConfig
    networking: NetworkingConfig
    debug: DebugConfig
    payment: PaymentConfig
    computing: ComputingConfig


## End about config

## CRN "/about/usage/system"


class LoadAverage(TypedDict):
    load1: float
    load5: float
    load15: float


class CoreFrequencies(TypedDict):
    min: float
    max: float


class CPUInfo(TypedDict):
    count: int
    load_average: LoadAverage
    core_frequencies: CoreFrequencies


class MemoryInfo(TypedDict):
    total_kB: int
    available_kB: int


class DiskInfo(TypedDict):
    total_kB: int
    available_kB: int


class PeriodInfo(TypedDict):
    start_timestamp: str
    duration_seconds: float


class CPUProperties(TypedDict):
    architecture: str
    vendor: str
    features: list[str]


class Properties(TypedDict):
    cpu: CPUProperties


class GPUDevice(TypedDict):
    vendor: str
    device_name: str
    device_class: str
    pci_host: str
    device_id: str


class GPUInfo(TypedDict):
    devices: list[GPUDevice]
    available_devices: list[GPUDevice]


class CRNSystemInfo(TypedDict):
    cpu: CPUInfo
    mem: MemoryInfo
    disk: DiskInfo
    period: PeriodInfo
    properties: Properties
    gpu: GPUInfo
    active: bool


_sample_system_info = """
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
}
"""


class CompatibleGPUInfo(TypedDict):
    name: str
    model: str
    vendor: str
    model_id: str
    vendor_id: str


class Settings(TypedDict):
    compatible_gpus: list[CompatibleGPUInfo]
    community_wallet_address: str


class Data(TypedDict):
    settings: Settings


class SettingsAggregate(TypedDict):
    address: str
    data: Data
    info: dict  # Assuming "info" is a generic dictionary with unknown structure
