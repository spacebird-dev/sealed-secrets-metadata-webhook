import argparse
import os
from pathlib import Path

import uvicorn

from sealed_secrets_mdhook import make_app

_ENV_PREFIX = "SEALED_SECRETS_MDHOOK"


def main():
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
    server.run()


if __name__ == "__main__":
    main()
