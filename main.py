import argparse
import asyncio
import logging
import os
from pathlib import Path
import sys

import uvicorn

from sealed_secrets_mdhook import make_app

_ENV_PREFIX = "SEALED_SECRETS_MDHOOK"

logger = logging.getLogger("sealed-secrets-mdhook")
logger.addHandler(logging.StreamHandler(sys.stdout))


async def watch_files(files: list[Path], callback, reason: str):
    def _read_file_mtime(file: Path):
        try:
            return file.stat().st_mtime
        except OSError as e:
            logger.warning(
                f"Could not read mtime of {file}, automatic reload on change may not work. Error: {e}")
            return 0

    logger.info(f"Watching {files} for changes to trigger automatic reload")
    old_mtimes = {f: _read_file_mtime(f) for f in files}

    while True:
        new_mtimes = {f: _read_file_mtime(f) for f in files}
        if new_mtimes != old_mtimes:
            await callback(reason)
        old_mtimes = new_mtimes
        await asyncio.sleep(10)


async def start_server(args):
    app = make_app(args.config)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=args.bind,
            port=args.port,
            ssl_keyfile=args.tls_key,
            ssl_certfile=args.tls_cert,
            log_level=args.loglevel.lower(),
        )
    )
    asyncio.create_task(server.serve())
    return server


async def main():
    parser = argparse.ArgumentParser(
        description="Add metadata to SealedSecret templates"
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Location of the configuration file",
        default=Path(os.environ.get(f"{_ENV_PREFIX}_CONFIG", "./config.json")),
    )
    parser.add_argument(
        "--bind",
        help="Address to bind to",
        default=os.environ.get(f"{_ENV_PREFIX}_BIND", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        help="Port to bind to",
        default=int(os.environ.get(f"{_ENV_PREFIX}_BIND", "8443")),
    )
    parser.add_argument(
        "--tls-key",
        help="Path to TLS private key",
        default=Path(os.environ.get(f"{_ENV_PREFIX}_TLS_KEY", "./tls.key")),
    )
    parser.add_argument(
        "--tls-cert",
        help="Path to TLS certificate",
        default=Path(os.environ.get(f"{_ENV_PREFIX}_TLS_CERT", "./tls.cert")),
    )
    parser.add_argument(
        "--loglevel",
        help="Loglevel",
        default=os.environ.get(f"{_ENV_PREFIX}_LOGLEVEL", "INFO"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    # Gracefully handle certificates or config changing
    change_event = asyncio.Event()

    async def trigger_reload(reason: str):
        logger.info(f"Reloading server. Reason: {reason}")
        change_event.set()

    while True:
        change_event.clear()
        server = await start_server(args)
        tls_watcher = asyncio.create_task(watch_files([Path(args.tls_cert), Path(
            args.tls_key)], trigger_reload, "TLS Certificate changed"))
        config_watcher = asyncio.create_task(watch_files(
            [Path(args.config)], trigger_reload, "Configuration changed"))

        await change_event.wait()  # blocks until a watcher reports change

        await server.shutdown()
        tls_watcher.cancel()
        config_watcher.cancel()

        try:
            await asyncio.gather(tls_watcher, config_watcher)
        except asyncio.CancelledError:
            pass

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
