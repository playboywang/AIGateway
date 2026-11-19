"""AIGateway application entry point."""

import uvicorn

from api.app import app
from config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.app_log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
