from logging.config import dictConfig

import uvicorn
from dotenv import load_dotenv

from ai_gateway.api import create_fast_api_server
from ai_gateway.config import Config

# load env variables from .env if exists
load_dotenv()

# prepare configuration settings
config = Config()

# configure logging
dictConfig(config.fastapi.uvicorn_logger)


def main():
    # For now, trust all IPs for proxy headers until https://github.com/encode/uvicorn/pull/1611 is available.
    uvicorn.run(
        create_fast_api_server(config),
        host=config.fastapi.api_host,
        port=config.fastapi.api_port,
        log_config=config.fastapi.uvicorn_logger,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
