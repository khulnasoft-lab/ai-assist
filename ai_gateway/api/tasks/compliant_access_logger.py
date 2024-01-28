import structlog

access_logger = structlog.stdlib.get_logger("api.access")


def info(event: str | None = None, *args, **kw):
    access_logger.info(event, *args, **kw)
