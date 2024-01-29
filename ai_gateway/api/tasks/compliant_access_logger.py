import structlog
from sanityze.cleanser import *

access_logger = structlog.stdlib.get_logger("api.access")


def info(event: str | None = None, *args, **kw):
    cleansed_args = cleanse_tuple(args)
    cleansed_kw = cleanse_dicts(kw)
    access_logger.info(event, *cleansed_args, **cleansed_kw)


def cleanse_tuple(data: tuple) -> tuple:
    cleanser = Cleanser()
    dataframe = pd.DataFrame(data)
    return tuple(cleanser.clean(dataframe).to_dict().values())


def cleanse_dicts(data: dict) -> dict:
    cleanser = Cleanser()
    dataframe = pd.DataFrame(data)
    return cleanser.clean(dataframe).to_dict()
