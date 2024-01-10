import typing
from datetime import datetime

import starlette.authentication
from starlette.authentication import requires  # noqa: F401
from starlette.requests import HTTPConnection

from ai_gateway.deps import CloudConnectorContainer


def has_required_scope(conn: HTTPConnection, scopes: typing.Sequence[str]) -> bool:
    if conn.user.is_debug is True:
        return True

    for scope in scopes:
        sub_scopes = scope.split("|")
        sub_scopes.extend(allowed_beta_scopes(sub_scopes))
        inside_scopes = [scope in conn.auth.scopes for scope in sub_scopes]

        if not any(inside_scopes):
            return False
    return True


def allowed_beta_scopes(scopes: typing.Sequence[str]) -> typing.Sequence[str]:
    allowed_services = list(
        filter(lambda x: x in scopes, CloudConnectorContainer.services.keys())
    )
    return [
        service + "_beta"
        for service in allowed_services
        if in_beta(CloudConnectorContainer.services[service]["service_start_time"])
    ]


def in_beta(time: str) -> bool:
    if time is None:
      return False

    service_start_time = datetime.strptime(time, "%Y-%m-%d %H:%MZ")

    return service_start_time > datetime.today()


starlette.authentication.has_required_scope = has_required_scope
