import asyncio
import datetime
import logging
import resource
from collections import defaultdict
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from typing import TypeVar, Generic
from urllib.parse import ParseResult, urlparse

import aiohttp
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from nodes_list.response_types import (
    CrnConfig,
    CRNSystemInfo,
    NodeAggregate,
    SettingsAggregate,
    CheckIPv6,
)

logger = logging.getLogger(__name__)

API_HOST = "https://api2.aleph.im"
SETTING_AGGREGATE_URL = (
    API_HOST.rstrip("/") + "/api/v0/aggregates/0xA07B1214bAe0D5ccAA25449C3149c0aC83658874.json?keys=settings"
)

PATH_STATUS_CONFIG = "/status/config"
PATH_ABOUT_USAGE_SYSTEM = "/about/usage/system"
PATH_IPv6_CHECK = "/status/check/ipv6"

# Some users had fun adding URLs that are obviously not CRNs.
# If you work for one of these companies, please send a large check to the Aleph team,
# and we may consider removing your domain from the blacklist. Or just use a subdomain.
FORBIDDEN_HOSTS = [
    "amazon.com",
    "apple.com",
    "facebook.com",
    "google.com",
    "google.es",
    "microsoft.com",
    "openai.com",
    "twitter.com",
    "x.com",
    "youtube.com",
]

app = fastapi.FastAPI(debug=True)

# This is a  pure readonly API service without auth, allow all CORS so frontends can use it without restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a semaphore based on the limit of openable fd
# This is used so we don't open too many connection in parallel which block due to too many fd.

## Uncomment to Change limit for testing
# resource.setrlimit(resource.RLIMIT_NOFILE, (1000, 1048576))
# Get the system's open file descriptor limit
soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
print(f"Soft limit: {soft_limit}, Hard limit: {hard_limit}")

# Limit the number of concurrent open file descriptors
MAX_CONCURRENT_FILES = min(soft_limit // 2, 100)  # Safety margin
semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILES)
"Semaphore to limit conccurent connection to CRN as to not reach Too many open file errors"


def find_in_aggr(aggr: SettingsAggregate, gpu_device_id) -> bool:
    """Find if gpu is present in the Settings aggregate compatible gpus list"""
    compatibility_list = aggr["data"]["settings"]["compatible_gpus"]
    for compatible_gpu in compatibility_list:
        if compatible_gpu["device_id"] == gpu_device_id:
            return True
    return False


def sanitize_url(url: str) -> str:
    """Ensure that the URL is valid and not obviously irrelevant.

    Args:
        url: URL to sanitize.
    Returns:
        Sanitized URL.
    """
    if not url:
        raise Exception("Invalid url")
    parsed_url: ParseResult = urlparse(url)
    if parsed_url.scheme not in ["http", "https"]:
        raise aiohttp.InvalidURL(f"Invalid URL scheme: {parsed_url.scheme}")
    if parsed_url.hostname in FORBIDDEN_HOSTS:
        logger.debug(
            f"Invalid URL {url} hostname {parsed_url.hostname} is in the forbidden host list "
            f"({', '.join(FORBIDDEN_HOSTS)})"
        )
        raise Exception(f"Forbidden host: {parsed_url.hostname}")
    return url


def is_url_valid(url: str) -> bool:
    """Ensure that the URL is valid and not obviously irrelevant.

    Args:
        url: URL to sanitize.
    Returns:
        Sanitized URL.
    """
    # noinspection PyBroadException
    try:
        sanitize_url(url)
        return True
    except Exception:
        return False


async def _fetch_node_list() -> NodeAggregate | None:
    """Fetch node aggregates"""
    aggregate_endpoint = "/api/v0/aggregates/0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10.json?keys=corechannel"
    node_link = API_HOST.rstrip("/") + aggregate_endpoint
    logger.info("Fetching node list from %s", node_link)

    async with aiohttp.ClientSession() as session:
        async with session.get(node_link) as resp:
            if resp.status != 200:
                logger.error("Unable to fetch node information")
                return None

            data = await resp.json()
            return data


async def fetch_crn_endpoint(node_url: str, endpoint: str) -> dict:
    """
    Call api endpoint on CRN

    Args:
        node_url: URL of the compute node.
        endpoint: endpoint to call.
    Returns:
        CRN information.
    """
    url = ""
    try:
        base_url: str = sanitize_url(node_url.rstrip("/"))
        async with semaphore:  # Ensures limited concurrency
            url = base_url + endpoint
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.debug(f"Fetching node information from {url}")
                info: dict
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    info = await resp.json()  # type: ignore
                    logger.info(f"Received response from node {url}")
                    return info
    except aiohttp.InvalidURL as e:
        logger.info(f"Invalid CRN URL: {url}: {e}")
        raise
    except TimeoutError as e:
        logger.info(f"Timeout while fetching CRN: {url}: {e}")
        raise
    except aiohttp.ClientConnectionError as e:
        logger.info(f"Error on CRN connection: {url}: {e}")
        raise
    except aiohttp.ClientResponseError as e:
        logger.info(f"Error on CRN response: {url}: {e}")
        raise
    except JSONDecodeError as e:
        logger.info(f"Error decoding CRN JSON: {url}: {e}")
        raise
    except Exception as e:
        logger.info(f"Unexpected error when fetching CRN: {url}: {e}")
        raise


async def fetch_crn_config(node_url: str) -> CrnConfig:
    """
    Fetches compute node config.

    Args:
        node_url: URL of the compute node.
    Returns:
        CRN information.
    """
    data: CrnConfig = await fetch_crn_endpoint(node_url, PATH_STATUS_CONFIG)  # type: ignore
    return data


async def fetch_crn_system(node_url: str) -> CRNSystemInfo:
    """
    Fetches compute node  system information: resource and usage.

    Args:
        node_url: URL of the compute node.
    Returns:
        CRN dict.
    """
    data: CRNSystemInfo = await fetch_crn_endpoint(node_url, PATH_ABOUT_USAGE_SYSTEM)  # type: ignore
    return data


T = TypeVar("T")  #


class CachedResponse(Generic[T]):
    """Cache for a JSON. Keep previous response in case of error"""

    data: T | None = None
    fetched_at: datetime.datetime | None = None
    error: Exception | None = None
    error_at: datetime.datetime | None

    def set_data(self, new_data: T):
        self.data = new_data
        self.fetched_at = datetime.datetime.now(datetime.UTC)
        # clear last error
        self.error = None
        self.error_at = None

    def set_error(self, e: Exception):
        self.error = e
        self.error_at = datetime.datetime.now(datetime.UTC)

    def is_older_than(self, **timedelta_args) -> bool:
        return self.data is None or (
            self.fetched_at is not None
            and datetime.datetime.now(datetime.UTC) - self.fetched_at > datetime.timedelta(**timedelta_args)
        )


class CRNData:
    """Data fetched from CRN endpoints"""

    config: CachedResponse[CrnConfig]
    system: CachedResponse[CRNSystemInfo]
    check_ipv6: CachedResponse[CheckIPv6]
    config_fetched_at: datetime.datetime | None = None  # Last successful data
    error: Exception | None = None
    error_at: datetime.datetime | None
    node_url: str
    system_data: CRNSystemInfo | None = None
    system_data_fetched_at: datetime.datetime | None = None  # Last successful data
    system_error: Exception | None = None
    system_error_at: datetime.datetime | None

    def __init__(self):
        self.config = CachedResponse()
        self.system = CachedResponse()
        self.check_ipv6 = CachedResponse()

    @property
    def is_valid(self):
        return is_url_valid(self.node_url)

    async def fetch_config(self) -> None:
        try:
            fetched_info = await fetch_crn_config(self.node_url)
            self.config.set_data(fetched_info)
        except Exception as e:
            self.config.set_error(e)

    async def fetch_ipv6(self) -> None:
        try:
            fetched_info: CheckIPv6 = await fetch_crn_endpoint(self.node_url, PATH_IPv6_CHECK)  # type: ignore
            self.check_ipv6.set_data(fetched_info)
        except Exception as e:
            self.check_ipv6.set_error(e)

    async def fetch_system(self) -> None:
        try:
            fetched_info = await fetch_crn_system(self.node_url)
            self.system.set_data(fetched_info)
        except Exception as e:
            self.system.set_error(e)

    @property
    def gpu_support(self):
        return self.config.data and self.config.data["computing"].get("ENABLE_GPU_SUPPORT")

    @property
    def confidential_support(self):
        return self.config.data and self.config.data["computing"].get("ENABLE_CONFIDENTIAL_COMPUTING")

    @property
    def qemu_support(self):
        return self.config.data and self.config.data["computing"].get("ENABLE_QEMU_SUPPORT")

    @property
    async def compatible_gpus(self) -> list[dict]:
        if not (self.system.data and "gpu" in self.system.data):
            return []

        devices: list[Any] = self.system.data["gpu"]["devices"]

        aggr = await data_cache.get_gpu_aggregate()
        if not aggr:
            logger.error("No settings aggregate, cannot filter devices.")
            return []
        compatible_gpu = [gpu for gpu in devices if find_in_aggr(aggr, gpu["device_id"])]
        return compatible_gpu

    @property
    async def compatible_available_gpus(self) -> list[dict]:
        if not (self.system.data and "gpu" in self.system.data):
            return []

        devices: list[Any] = self.system.data["gpu"]["available_devices"]

        aggr = await data_cache.get_gpu_aggregate()
        if not aggr:
            logger.error("No settings aggregate, cannot filter devices.")
            return []
        compatible_gpu = [gpu for gpu in devices if find_in_aggr(aggr, gpu["device_id"])]
        return compatible_gpu


class DataCache:
    node_list: CachedResponse[NodeAggregate]
    gpu_aggregate: CachedResponse[SettingsAggregate]
    crn_infos: defaultdict[str, CRNData] = defaultdict(CRNData)

    refresh_task: asyncio.Task | None = None

    def __init__(self):
        self.gpu_aggregate = CachedResponse()
        self.node_list = CachedResponse()

    async def ensure_fresh_data(self) -> tuple[NodeAggregate | None, dict]:
        """Ensure we refresh the data and return it

        1. if data is older than big threshold. Wait till we have refreshed the whole data set or max 10s
        2. if data is older than small threshold, launch cache refresh in background and use data already in cache
        3. else return data directly
        """
        if self.node_list.is_older_than(seconds=60):
            if not self.refresh_task_is_running():
                self.refresh_task = asyncio.create_task(self.fetch_node_list_and_node_data())
                done, pending = await asyncio.wait(
                    [self.refresh_task],
                    timeout=10,
                )
                logger.debug("done %s pending %s", done, pending)
                if pending:
                    logger.info(
                        "Returning data from cache, continue fetch in background task %s",
                        pending,
                    )
        elif self.node_list.is_older_than(seconds=31):
            if not self.refresh_task_is_running():
                logger.info("Launching background refresh task")
                self.refresh_task = asyncio.create_task(self.fetch_node_list_and_node_data())
        else:
            logger.info("Getting data from cache")
        return self.node_list.data, self.crn_infos

    def refresh_task_is_running(self):
        return self.refresh_task and not self.refresh_task.done()

    async def fetch_node_list_and_node_data(self):
        """Retrieve the node list and data from each node"""
        logger.info("%s , fetch_node_list_and_node_data start", asyncio.current_task())
        node_list = await _fetch_node_list()
        if node_list:
            self.node_list.set_data(node_list)
        assert node_list
        crns = node_list["data"]["corechannel"]["resource_nodes"]
        # sort by score
        crns.sort(key=lambda crn: crn["score"], reverse=True)

        # crns = crns[:10]
        # self.node_list.data["data"]["corechannel"]["resource_nodes"] = crns = [
        #     crn for crn in crns if "nerg" in crn["address"]
        # ]
        futures = []
        for node in crns:
            crn_hash = node["hash"]
            crn_config = self.crn_infos[crn_hash]
            crn_config.node_url = node["address"]
            futures.append(crn_config.fetch_system())
            futures.append(crn_config.fetch_config())
            futures.append(crn_config.fetch_ipv6())

        await asyncio.gather(*futures)
        logger.info("%s , fetch_node_list_and_node_data end", asyncio.current_task())

    async def format_response(self, filter_inactive: bool):
        resp: dict[str, list[Any] | datetime.datetime | None]
        crns_resp: list[dict] = []
        resp = {"last_refresh": self.node_list.fetched_at, "crns": crns_resp}

        if not self.node_list.data:
            return resp
        for crn in self.node_list.data["data"]["corechannel"]["resource_nodes"]:
            try:
                if filter_inactive and crn["inactive_since"] is not None:
                    continue
                crn_hash = crn["hash"]
                crn_info = self.crn_infos[crn_hash]
                crn_resp = {
                    **crn,
                    "config_from_crn": crn_info.config is not None,
                    "debug_config_from_crn_at": crn_info.config.fetched_at,
                    "debug_config_from_crn_error": str(crn_info.config.error),
                    "version": crn_info.config.data and crn_info.config.data["version"],
                    "payment_receiver_address": crn_info.config.data
                    and crn_info.config.data["payment"]["PAYMENT_RECEIVER_ADDRESS"],
                    "gpu_support": crn_info.gpu_support,
                    "confidential_support": crn_info.confidential_support,
                    "qemu_support": crn_info.qemu_support,
                    "system_usage": crn_info.system.data,
                    "compatible_gpus": await crn_info.compatible_gpus,
                    "compatible_available_gpus": await crn_info.compatible_available_gpus,
                    "ipv6_check": crn_info.check_ipv6.data,
                }
                crns_resp.append(crn_resp)
            except Exception as e:
                logger.error("Error formatting crn %s: %s", crn.get("hash"), e)

        return resp

    async def fetch_gpu_aggregate(self):
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(SETTING_AGGREGATE_URL)
                resp.raise_for_status()

                data = await resp.json()
                self.gpu_aggregate.set_data(data)
        except Exception as e:
            logger.warning("error fetching gpu aggregate: %s", e)
            self.gpu_aggregate.set_error(e)

    async def get_gpu_aggregate(self) -> SettingsAggregate | None:
        if self.gpu_aggregate.is_older_than(minutes=5):
            await self.fetch_gpu_aggregate()
        return self.gpu_aggregate.data


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "templates/index.html").read_text()


@app.get("/crns.json")
async def root(filter_inactive: bool = False):
    await data_cache.ensure_fresh_data()
    response = await data_cache.format_response(filter_inactive=filter_inactive)

    return response


@app.get("/debug/nodes_aggregate")
async def debug_node_list():
    """Raw data"""
    data = await data_cache.ensure_fresh_data()
    return data


@app.get("/debug.html", response_class=HTMLResponse)
def debug_page() -> str:
    return (Path(__file__).parent / "templates/debug.html").read_text()


data_cache = DataCache()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s %(name)s:%(lineno)s | %(message)s ",
)
