#!/bin/python
import asyncio
import logging
import os
import sys
from base64 import b16decode, b32encode
from pathlib import Path
from shutil import make_archive
from zipfile import BadZipFile

# import magic
from aleph.sdk import AuthenticatedAlephHttpClient
from aleph.sdk.account import _load_account
from aleph.sdk.conf import settings
from aleph.sdk.types import AccountFromPrivateKey, StorageEnum
from aleph.sdk.utils import try_open_zip
from aleph_message.models import ItemHash, StoreMessage
from aleph_message.models.execution import Encoding
from aleph_message.status import MessageStatus

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

channel = "aleph-infrastructure"


def create_archive(path: Path) -> tuple[Path, Encoding]:
    """Create a zip archive from a directory"""
    if os.path.isdir(path):
        if settings.CODE_USES_SQUASHFS:
            logger.debug("Creating squashfs archive...")
            archive_path = Path(f"{path}.squashfs")
            os.system(f"mksquashfs {path} {archive_path} -noappend")
            assert archive_path.is_file()
            return archive_path, Encoding.squashfs
        else:
            logger.debug("Creating zip archive...")
            make_archive(str(path), "zip", path)
            archive_path = Path(f"{path}.zip")
            return archive_path, Encoding.zip
    elif os.path.isfile(path):
        if path.suffix == ".squashfs" or (magic and magic.from_file(path).startswith("Squashfs filesystem")):
            return path, Encoding.squashfs
        else:
            try_open_zip(Path(path))
            return path, Encoding.zip
    else:
        raise FileNotFoundError("No file or directory to create the archive from")


async def deploy_program():
    path = Path(__file__).parent / "src"
    try:
        path_object, encoding = create_archive(path)
    except BadZipFile:
        print("Invalid zip archive")
        sys.exit(3)
    except FileNotFoundError:
        print("No such file or directory")
        sys.exit(4)

    account: AccountFromPrivateKey = _load_account()
    runtime = settings.DEFAULT_RUNTIME_ID

    async with AuthenticatedAlephHttpClient(account=account, api_server=settings.API_HOST) as client:
        # Upload the source code
        with open(path_object, "rb") as fd:
            logger.debug("Reading file")
            # TODO: Read in lazy mode instead of copying everything in memory
            file_content = fd.read()
            storage_engine = StorageEnum.ipfs
            logger.debug("Uploading file")
            user_code: StoreMessage
            status: MessageStatus
            user_code, status = await client.create_store(
                file_content=file_content,
                storage_engine=storage_engine,
                channel=channel,
                guess_mime_type=True,
                ref=None,
            )
            print(f"{user_code.json(indent=4)}")
            logger.debug("Upload finished")
            program_ref = user_code.item_hash

        # Register the program
        message, status = await client.create_program(
            program_ref=program_ref,
            entrypoint="nodes_list:app",
            runtime=runtime,
            storage_engine=StorageEnum.storage,
            channel=channel,
            memory=512,
            vcpus=1,
            timeout_seconds=60,
            persistent=False,
            encoding=encoding,
            volumes=None,
            subscriptions=None,
        )
        logger.debug("Upload finished")

        print(f"{message.json(indent=4)}")

        item_hash: ItemHash = message.item_hash
        hash_base32 = b32encode(b16decode(item_hash.upper())).strip(b"=").lower().decode()

        print(
            f"Your program has been uploaded on aleph.im\n\n"
            "Available on:\n"
            f"  {settings.VM_URL_PATH.format(hash=item_hash)}\n"
            f"  {settings.VM_URL_HOST.format(hash_base32=hash_base32)}\n"
            "Visualise on:\n  https://explorer.aleph.im/address/"
            f"{message.chain.value}/{message.sender}/message/PROGRAM/{item_hash}\n"
        )


if __name__ == "__main__":
    asyncio.run(deploy_program())
