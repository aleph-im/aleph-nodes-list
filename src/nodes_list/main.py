import asyncio
import datetime
import logging
from collections import defaultdict
from json import JSONDecodeError
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult, urlparse

import aiohttp
import fastapi
from fastapi.responses import HTMLResponse

from nodes_list.response_types import (
    CrnConfig,
    CRNSystemInfo,
    NodeAggregate,
    ResourceNodeInfo,
)

logger = logging.getLogger(__name__)

FAKE_GPU_AGGREGATE = {
    "community_wallet_address": "0x0000000000000000000000000000",
    "compatible_standard_gpus": [
        {
            "vendor": "NVIDIA",
            "model": "L40S",
            "name": "L40S",
            "vendor_id": "10de",
            "device_id": "26b9",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 4090",
            "name": "RTX 4090",
            "vendor_id": "10de",
            "device_id": "2684",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 4090",
            "name": "RTX 4090 D",
            "vendor_id": "10de",
            "device_id": "2685",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 3090",
            "name": "RTX 3090",
            "vendor_id": "10de",
            "device_id": "2204",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 3090",
            "name": "RTX 3090 Ti",
            "vendor_id": "10de",
            "device_id": "2203",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 4000 ADA",
            "name": "RTX 4000 SFF Ada Generation",
            "vendor_id": "10de",
            "device_id": "27b0",
        },
        {
            "vendor": "NVIDIA",
            "model": "RTX 4000 ADA",
            "name": "RTX 4000 Ada Generation",
            "vendor_id": "10de",
            "device_id": "27b2",
        },
    ],
    "compatible_premium_gpus": [
        {
            "vendor": "NVIDIA",
            "model": "H100",
            "name": "H100",
            "vendor_id": "10de",
            "device_id": "2336",
        },
        {
            "vendor": "NVIDIA",
            "model": "H100",
            "name": "H100 NVSwitch",
            "vendor_id": "10de",
            "device_id": "22a3",
        },
        {
            "vendor": "NVIDIA",
            "model": "H100",
            "name": "H100 CNX",
            "vendor_id": "10de",
            "device_id": "2313",
        },
        {
            "vendor": "NVIDIA",
            "model": "H100",
            "name": "H100 SXM5 80GB",
            "vendor_id": "10de",
            "device_id": "2330",
        },
        {
            "vendor": "NVIDIA",
            "model": "H100",
            "name": "H100 PCIe",
            "vendor_id": "10de",
            "device_id": "2331",
        },
        {
            "vendor": "NVIDIA",
            "model": "A100",
            "name": "A100",
            "vendor_id": "10de",
            "device_id": "2080",
        },
        {
            "vendor": "NVIDIA",
            "model": "A100",
            "name": "A100",
            "vendor_id": "10de",
            "device_id": "2081",
        },
        {
            "vendor": "NVIDIA",
            "model": "A100",
            "name": "A100 SXM4 80GB",
            "vendor_id": "10de",
            "device_id": "20b2",
        },
        {
            "vendor": "NVIDIA",
            "model": "A100",
            "name": "A100 PCIe 80GB",
            "vendor_id": "10de",
            "device_id": "20b5",
        },
        {
            "vendor": "NVIDIA",
            "model": "A100",
            "name": "A100X",
            "vendor_id": "10de",
            "device_id": "20b8",
        },
    ],
}

PATH_STATUS_CONFIG = "/status/config"
PATH_ABOUT_USAGE_SYSTEM = "/about/usage/system"

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

API_HOST = "https://api2.aleph.im"


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


async def _fetch_node_list() -> Optional[NodeAggregate]:
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
            # return NodeInfo(**data)


async def fetch_crn_endpoint(node_url: str, endpoint: str) -> dict | None:
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
        url = base_url + endpoint
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Fetching node information from {url}")
            info: dict
            async with session.get(url) as resp:
                resp.raise_for_status()
                info = await resp.json()
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


async def fetch_crn_config(node_url: str) -> CrnConfig | None:
    """
    Fetches compute node config.

    Args:
        node_url: URL of the compute node.
    Returns:
        CRN information.
    """
    return await fetch_crn_endpoint(node_url, PATH_STATUS_CONFIG)


async def fetch_crn_system(node_url: str) -> CRNSystemInfo | None:
    """
    Fetches compute node  system information: resource and usage.

    Args:
        node_url: URL of the compute node.
    Returns:
        CRN dict.
    """
    return await fetch_crn_endpoint(node_url, PATH_ABOUT_USAGE_SYSTEM)


class CRNData:
    """Data fetched from CRN endpoints"""

    config: Optional[CrnConfig] = None
    config_fetched_at: Optional[datetime.datetime] = None  # Last successful data
    error: Optional[Exception] = None
    error_at: Optional[datetime.datetime]
    node_url: str
    system_data: Optional[CrnConfig] = None
    system_data_fetched_at: datetime.datetime = None  # Last successful data
    system_error: Optional[Exception] = None
    system_error_at: Optional[datetime.datetime]
    node_url: str

    @property
    def is_valid(self):
        return is_url_valid(self.node_url)

    @property
    def compatible_gpus(self):
        return
        # for gpu in self.system_data.
        # FAKE_GPU_AGGREGATE

    async def fetch_config(self) -> None:
        try:
            fetched_info = await fetch_crn_config(self.node_url)
            self.config = fetched_info
            self.config_fetched_at = datetime.datetime.now(datetime.UTC)
            # clear last error
            self.error = None
            self.error_at = None

        except Exception as e:
            self.error = e
            self.error_at = datetime.datetime.now(datetime.UTC)

    async def fetch_system(self) -> None:
        try:
            fetched_info = await fetch_crn_system(self.node_url)
            self.system_data = fetched_info
            self.system_data_fetched_at = datetime.datetime.now(datetime.UTC)
            # clear last error
            self.system_error = None
            self.system_error_at = None

        except Exception as e:
            self.system_error = e
            self.system_error_at = datetime.datetime.now(datetime.UTC)

    @property
    def gpu_support(self):
        return self.config and self.config["computing"].get("ENABLE_GPU_SUPPORT")

    @property
    def confidential_support(self):
        return self.config and self.config["computing"].get(
            "ENABLE_CONFIDENTIAL_COMPUTING"
        )

    @property
    def qemu_support(self):
        return self.config and self.config["computing"].get("ENABLE_QEMU_SUPPORT")


app = fastapi.FastAPI(debug=True)


class DataCache:
    node_list: NodeAggregate
    node_list_fetched_at: datetime.datetime = None
    crn_infos: defaultdict[str, CRNData] = defaultdict(CRNData)

    refresh_task: asyncio.Task = None

    async def ensure_fresh_data(self) -> tuple[NodeAggregate, dict]:
        """Ensure we refresh the data and return it

        1. if data is older than big threshold.
        Wait till we have refreshed the whole data
        2. if data is older than small threshold, launch refresh in background
        and use cached data for now
        3. else return data directly
        """
        if not self.node_list_fetched_at or datetime.datetime.now(
            datetime.UTC
        ) - self.node_list_fetched_at >= datetime.timedelta(seconds=60):
            if self.refresh_task:
                self.refresh_task.cancel()
            await self.fetch_node_list_and_node_data()
        elif not self.node_list_fetched_at or datetime.datetime.now(
            datetime.UTC
        ) - self.node_list_fetched_at >= datetime.timedelta(seconds=31):
            # If  data is between 30 and 61 seconds old
            # We return the cached version but launch a refresh in background
            logger.info("Launching background refresh task")

            self.refresh_task = asyncio.create_task(
                self.fetch_node_list_and_node_data()
            )

            await self.fetch_node_list_and_node_data()
        else:
            logger.info("Getting data from cache")
        return self.node_list, self.crn_infos

    async def fetch_node_list_and_node_data(self):
        """Retrieve the node list and data from each node"""
        node_list = await _fetch_node_list()
        if node_list:
            self.node_list = node_list
        crns = self.node_list["data"]["corechannel"]["resource_nodes"]
        self.node_list_fetched_at = datetime.datetime.now(datetime.UTC)

        async def retrieve_node_config(node: ResourceNodeInfo):
            crn_hash = node["hash"]
            crn_config = self.crn_infos[crn_hash]
            crn_config.node_url = node["address"]

            await crn_config.fetch_config()

        async def retrieve_system_info(node: ResourceNodeInfo):
            crn_hash = node["hash"]
            crn_config = self.crn_infos[crn_hash]
            crn_config.node_url = node["address"]

            await crn_config.fetch_system()

        crns = crns[:10]
        futures = [retrieve_node_config(node) for node in crns]
        futures += [retrieve_system_info(node) for node in crns]

        await asyncio.gather(*futures)

    def format_response(self):
        resp = {"last_refresh": self.node_list_fetched_at}
        crns_resp = []
        for crn in self.node_list["data"]["corechannel"]["resource_nodes"]:
            crn_hash = crn["hash"]
            crn_info = self.crn_infos[crn_hash]
            crn_resp = {
                **crn,
                "config_from_crn": crn_info.config is not None,
                "debug_config_from_crn_at": crn_info.config_fetched_at,
                "debug_config_from_crn_error": crn_info.error,
                "gpu_support": crn_info.gpu_support,
                "confidential_support": crn_info.confidential_support,
                "qemu_support": crn_info.qemu_support,
                "system_usage": crn_info.system_data,
            }
            crns_resp.append(crn_resp)

        resp["crns"] = crns_resp
        return resp


data_cache = DataCache()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "templates/index.html").read_text()


@app.get("/crns.json")
async def root():
    await data_cache.ensure_fresh_data()
    response = data_cache.format_response()

    return response


@app.get("/debug/nodes_aggregate")
async def debug_node_list():
    """Raw data"""
    data = await data_cache.ensure_fresh_data()
    return data


@app.get("/debug.html", response_class=HTMLResponse)
def debug_page() -> str:
    return (Path(__file__).parent / "templates/debug.html").read_text()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s %(name)s:%(lineno)s | %(message)s ",
)
