import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, JWSError, jwt  # <--- I guess we can rely on it as dependency? (will list in requirements.txt?)

__all__ = [
    "TokenAuthority",
    "RS256_ALGORITHM",
    "SELF_SIGNED_TOKEN_ISSUER"
]

from ai_gateway.cloud_connector.service_response import ServiceResponse
from ai_gateway.cloud_connector.unit_primitive import GitLabUnitPrimitive

RS256_ALGORITHM = "RS256"  # This should move a couple layers up, when we'll extract decoding code into package as well
SELF_SIGNED_TOKEN_ISSUER = "gitlab-ai-gateway"  # This should passed into constructor of TokenAuthority!

class TokenAuthority:
    def __init__(self, signing_key):
        self.signing_key = signing_key

    # def encode(self, sub, gitlab_realm) -> tuple[str, int]:
    def encode(self, sub, gitlab_realm) -> ServiceResponse:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        try:
            claims = {
                "iss": SELF_SIGNED_TOKEN_ISSUER,
                "sub": sub,
                "aud": SELF_SIGNED_TOKEN_ISSUER,
                "exp": expires_at,
                "nbf": datetime.now(timezone.utc),
                "iat": datetime.now(timezone.utc),
                "jti": str(uuid.uuid4()),
                "gitlab_realm": gitlab_realm,
                "scopes": [GitLabUnitPrimitive.CODE_SUGGESTIONS],
            }

            token = jwt.encode(claims, self.signing_key, algorithm=RS256_ALGORITHM)
            result = [token, int(expires_at.timestamp())]

            return ServiceResponse(success=True, result=result)
        except (JWTError, JWSError) as err: # Interesting, that it is JW(S)Eror, not JW(T). Did we have a bug here?
            # log_exception(err) <--- ??? we can't rely on that when we'll move this code to the package
            # Ideally, we should delegate any logging-related decisions to the backend that uses the library.
            # Our components should return a status object - OK/Fail + error message/object.
            # It should be up to the backend to decide what to do in case of Failure.

            x = 1
            return ServiceResponse(success=False, error=str(err))
