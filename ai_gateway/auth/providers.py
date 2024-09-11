import json
import os
import urllib.parse
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta

import requests
from jose import JWTError, jwk, jwt
from jose.exceptions import JWKError

from ai_gateway.auth.cache import LocalAuthCache
from ai_gateway.auth.user import User, UserClaims
from ai_gateway.config import ConfigSelfSignedJwt
from ai_gateway.tracking.errors import log_exception

__all__ = [
    "AuthProvider",
    "GitLabOidcProvider",
    "CompositeProvider",
    "DiskKeyProvider",
    "LocalAuthProvider",
    "JwksProvider",
]

REQUEST_TIMEOUT_SECONDS = 10


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, *args, **kwargs) -> User:
        pass


class JwksProvider:
    @abstractmethod
    def jwks(self, *args, **kwargs) -> dict:
        pass


class CompositeProvider(AuthProvider):
    RS256_ALGORITHM = "RS256"
    SUPPORTED_ALGORITHMS = [RS256_ALGORITHM]
    AUDIENCE = "gitlab-ai-gateway"
    CACHE_KEY = "jwks"

    class CriticalAuthError(Exception):
        pass

    def __init__(self, providers: list[JwksProvider], expiry_seconds: int = 86400):
        self.providers = providers
        self.expiry_seconds = expiry_seconds
        self.cache = LocalAuthCache()

    def authenticate(self, token: str) -> User:
        jwks = self._jwks()
        is_allowed = False
        gitlab_realm = ""
        subject = ""
        issuer = ""
        scopes = []
        duo_seat_count = ""
        gitlab_instance_id = ""

        if len(jwks.get("keys", [])) == 0:
            raise self.CriticalAuthError(
                "No keys founds in JWKS; are OIDC providers up?"
            )

        try:
            jwt_claims = jwt.decode(
                token,
                jwks,
                audience=self.AUDIENCE,
                algorithms=self.SUPPORTED_ALGORITHMS,
            )
            gitlab_realm = jwt_claims.get("gitlab_realm", "")
            subject = jwt_claims.get("sub", "")
            issuer = jwt_claims.get("iss", "")
            scopes = jwt_claims.get("scopes", [])
            duo_seat_count = str(jwt_claims.get("duo_seat_count", ""))
            gitlab_instance_id = jwt_claims.get("gitlab_instance_id", "")

            is_allowed = True
        except JWTError as err:
            log_exception(err)

        return User(
            authenticated=is_allowed,
            claims=UserClaims(
                gitlab_realm=gitlab_realm,
                scopes=scopes,
                subject=subject,
                issuer=issuer,
                duo_seat_count=duo_seat_count,
                gitlab_instance_id=gitlab_instance_id,
            ),
        )

    def _jwks(self) -> dict:
        jwks_record = self.cache.get(self.CACHE_KEY)
        if jwks_record and jwks_record.exp > datetime.now():
            return jwks_record.value

        jwks = defaultdict()
        jwks["keys"] = []
        for provider in self.providers:
            try:
                provider_jwks = provider.jwks()
                print("Provider JWKS:", "provider=", provider, "; jwks=", provider_jwks)
                jwks["keys"] += provider_jwks["keys"]
            except Exception as e:
                log_exception(e)

        self._cache_jwks(jwks)
        return jwks

    def _cache_jwks(self, jwks):
        exp = datetime.now() + timedelta(seconds=self.expiry_seconds)
        self.cache.set(self.CACHE_KEY, jwks, exp)


class DiskKeyProvider(JwksProvider):
    ALGORITHM = CompositeProvider.RS256_ALGORITHM

    def __init__(self) -> None:
        self.jwks = defaultdict(list)
        self.jwks["keys"] = []

        try:
            # read key files from .cloud-connector local directory
            keys_dir = os.path.abspath("/app/.cloud-connector/keys")
            if not os.path.exists(keys_dir):
                raise Exception(".cloud-connector/keys not found")

            # iterate all key files in the keys directory
            for key_file in os.listdir(keys_dir):
                print("processing file:", key_file)
                # read key file into string

                with open(os.path.join(keys_dir, key_file), "r") as f:
                    # Parse the key content as JSON
                    key_data = json.loads(f.read())
                    print(key_data)
                    key = jwk.construct(key_data, algorithm=self.ALGORITHM)
                    self.jwks["keys"].append(key)
        except JWKError as e:
            log_exception(e)

    def jwks(self) -> dict:
        return self.jwks


class LocalAuthProvider(JwksProvider):
    ALGORITHM = CompositeProvider.RS256_ALGORITHM

    def __init__(self, self_signed_jwt: ConfigSelfSignedJwt) -> None:
        self.signing_key = self_signed_jwt.signing_key
        self.validation_key = self_signed_jwt.validation_key

    def jwks(self) -> dict:
        jwks = defaultdict(list)
        jwks["keys"] = []

        try:
            signing_key = (
                jwk.RSAKey(
                    algorithm=self.ALGORITHM,
                    key=self.signing_key,
                )
                .public_key()
                .to_dict()
            )
            signing_key.update(
                {
                    "kid": "gitlab_ai_gateway_signing_key",
                    "use": "sig",
                }
            )
        except JWKError as e:
            log_exception(e)

        try:
            validation_key = (
                jwk.RSAKey(
                    algorithm=self.ALGORITHM,
                    key=self.validation_key,
                )
                .public_key()
                .to_dict()
            )
            validation_key.update(
                {
                    "kid": "gitlab_ai_gateway_validation_key",
                    "use": "sig",
                }
            )
        except JWKError as e:
            log_exception(e)

        jwks["keys"].append(signing_key)
        jwks["keys"].append(validation_key)

        return jwks


class GitLabOidcProvider(JwksProvider):
    def __init__(self, oidc_providers: dict[str, str]):
        self.oidc_providers = oidc_providers

    def jwks(self) -> dict:
        jwks = defaultdict(list)

        for oidc_provider, base_url in self.oidc_providers.items():
            well_known = self._fetch_well_known(oidc_provider, base_url)
            for k, v in self._fetch_jwks(oidc_provider, well_known).items():
                jwks[k].extend(v)

        if jwks:
            return jwks

        return {}

    def _fetch_well_known(self, oidc_provider, base_url: str) -> dict:
        end_point = "/.well-known/openid-configuration"
        url = urllib.parse.urljoin(base_url, end_point)

        well_known = {}
        try:
            res = requests.get(url=url, timeout=REQUEST_TIMEOUT_SECONDS)
            well_known = res.json()
        except requests.exceptions.RequestException as err:
            log_exception(err, {"oidc_provider": oidc_provider})

        return well_known

    def _fetch_jwks(self, oidc_provider, well_known) -> dict:
        url = well_known.get("jwks_uri")
        if not url:
            return {}

        jwks = {}

        try:
            res = requests.get(url=url, timeout=REQUEST_TIMEOUT_SECONDS)
            jwks = res.json()
        except requests.exceptions.RequestException as err:
            log_exception(err, {"oidc_provider": oidc_provider})

        return jwks
