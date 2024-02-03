import structlog
from detect_secrets.main import scan_adhoc_string
from sanityze.cleanser import *

access_logger = structlog.stdlib.get_logger("api.access")


class SecretSpotter(Spotter):
    def getSpotterUID(self) -> str:
        return "SECRET"

    def process(self, text: str) -> str:
        regex = re.compile(r"", re.VERBOSE | re.IGNORECASE)

        if self.isHashSpotted():
            text = re.sub(regex, lambda x:hashlib.md5(x.group().encode()).hexdigest(), text)
            new_text = text
        else:
            new_text = re.sub(regex, self.getSpotterUID(), text)

        return new_text


def info(event: str | None = None, *args, **kw):
    cleansed_args = cleanse_tuple(args)
    cleansed_kw = cleanse_dicts(kw)
    access_logger.info(event, *cleansed_args, **cleansed_kw)


def get_cleanser():
    cleanser = Cleanser()
    cleanser.add_spotter(EmailSpotter("EMAILS", True))
    cleanser.add_spotter(CreditCardSpotter("CCS", True))
    return cleanser


def cleanse_tuple(data: tuple) -> tuple:
    cleanser = get_cleanser()
    dataframe = pd.DataFrame(data)
    return tuple(cleanser.clean(dataframe).to_dict().values())


def cleanse_dicts(data: dict) -> dict:
    cleanser = get_cleanser()
    dataframe = pd.DataFrame(data)
    return cleanser.clean(dataframe).to_dict()


def mask_secrets(data: dict) -> dict:
    scan_adhoc_string
    cleanser = Cleanser()
    dataframe = pd.DataFrame(data)