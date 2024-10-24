import base64
import urllib.parse
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import cryptography.x509.verification as x509v
import requests
from cryptography import x509
from jose import JWTError, jwk, jwt
from jose.backends.cryptography_backend import CryptographyRSAKey
from jose.exceptions import JWKError

from ai_gateway.cloud_connector.cache import LocalAuthCache
from ai_gateway.cloud_connector.user import User, UserClaims
from ai_gateway.tracking.errors import log_exception

__all__ = [
    "AuthProvider",
    "GitLabOidcProvider",
    "CompositeProvider",
    "LocalAuthProvider",
    "JwksProvider",
]

REQUEST_TIMEOUT_SECONDS = 10
UNAUTHENTICATED_USER = User(authenticated=False, claims=UserClaims(**{}))


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, *args, **kwargs) -> User:
        pass


# Decorator that takes a list of actual authentication providers,
# runs them in sequence, and returns the first user that is authenticated.
# If no authenticated user is found, it returns a default user object with
# authenticated=False.
class AuthProviderChain(AuthProvider):
    def __init__(self, providers: list[AuthProvider]) -> None:
        self.providers = providers

    def authenticate(self, *args, **kwargs) -> User:
        for provider in self.providers:
            user = provider.authenticate(*args, **kwargs)
            if user.authenticated:
                return user

        return UNAUTHENTICATED_USER


class JwksProvider:
    def __init__(self, log_provider) -> None:
        self.logger = log_provider.getLogger("cloud_connector")

    def jwks(self, token: str) -> dict:
        cached_jwks = self.cached_jwks()
        if cached_jwks and len(cached_jwks) > 0:
            return cached_jwks

        new_jwks = self.load_jwks(token)
        self._log_keyset_update(new_jwks)
        return new_jwks

    @abstractmethod
    def cached_jwks(self) -> dict:
        pass

    @abstractmethod
    def load_jwks(self, token: str) -> dict:
        pass

    def _log_keyset_update(self, jwks):
        kids = [key["kid"] for key in jwks["keys"]]
        self.logger.info("JWKS refreshed", kids=kids, provider=self.__class__.__name__)


# An AuthProvider that uses a JSON Web Key Set (JWKS) to authenticate users.
class JwksAuthProvider(AuthProvider, JwksProvider):
    RS256_ALGORITHM = "RS256"
    SUPPORTED_ALGORITHMS = [RS256_ALGORITHM]
    AUDIENCE = "gitlab-ai-gateway"

    class CriticalAuthError(Exception):
        pass

    def authenticate(self, token: str) -> User:
        jwks = self.jwks(token)
        if len(jwks.get("keys", [])) == 0:
            self.logger(
                "No keys founds in JWKS; provider might be unreachable",
                provider=self.__class__.__name__,
            )
            return UNAUTHENTICATED_USER

        is_allowed = False
        gitlab_realm = ""
        subject = ""
        issuer = ""
        scopes = []
        duo_seat_count = ""
        gitlab_instance_id = ""

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


# A JwksAuthProvider that composes a list of concrete JwksAuthProviders,
# merges their JWKSs, caches this set, and uses it to authenticate users.
class CompositeProvider(JwksAuthProvider):
    CACHE_KEY = "jwks"

    def __init__(
        self, providers: list[JwksProvider], log_provider, expiry_seconds: int = 86400
    ):
        super().__init__(log_provider)
        self.providers = providers
        self.expiry_seconds = expiry_seconds
        self.cache = LocalAuthCache()

    def cached_jwks(self) -> dict:
        jwks_record = self.cache.get(self.CACHE_KEY)
        if jwks_record and jwks_record.exp > datetime.now():
            return jwks_record.value

        return defaultdict()

    def load_jwks(self, token: str) -> dict:
        jwks: dict[str, list] = defaultdict()
        jwks["keys"] = []
        for provider in self.providers:
            try:
                provider_jwks = provider.jwks(token)
                jwks["keys"] += provider_jwks["keys"]
            except Exception as e:
                log_exception(e)

        self._cache_jwks(jwks)
        return jwks

    def _cache_jwks(self, jwks):
        exp = datetime.now() + timedelta(seconds=self.expiry_seconds)
        self.cache.set(self.CACHE_KEY, jwks, exp)


class LocalAuthProvider(JwksProvider):
    ALGORITHM = JwksAuthProvider.RS256_ALGORITHM

    def __init__(self, log_provider, signing_key: str, validation_key: str) -> None:
        super().__init__(log_provider)
        self.signing_key = signing_key
        self.validation_key = validation_key

    def load_jwks(self, _) -> dict:
        jwks: dict[str, list] = defaultdict(list)
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
    def __init__(self, log_provider, oidc_providers: dict[str, str]):
        super().__init__(log_provider)
        self.oidc_providers = oidc_providers

    def load_jwks(self, _) -> dict:
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


# A JwksAuthProvider that produces the JWKS by parsing it from the x5c
# certificate chain claim embedded in a JWT (self-contained token).
#
# The x5c claim contains a list of DER-encoded X.509 certificates,
# which can be used to create a JWK to validate the token.
class CertificateChainProvider(JwksAuthProvider):
    def __init__(self, log_provider, root_cert: str):
        super().__init__(log_provider)
        trusted_certs = x509.load_pem_x509_certificates(root_cert.encode())
        self.trust_store = x509v.Store(trusted_certs)

    # We should never cache these values since they change with every request.
    def cached_jwks(self) -> dict:
        return defaultdict()

    # Constructs a JWKS from a certificate embedded in the x5c token claim.
    def load_jwks(self, token: str) -> dict:
        claims = jwt.get_unverified_claims(token)

        jwks: dict[str, list] = defaultdict(list)
        jwks["keys"] = []

        cert_chain = claims.get("x5c", None)
        self.logger.info("x5c cert chain", cert_chain=cert_chain)
        if not cert_chain:
            return jwks

        cert = self._verify_cert_chain(cert_chain)
        if not cert:
            return jwks

        rsa_key = cert.public_key()
        jose_key: CryptographyRSAKey = jwk.construct(
            rsa_key, algorithm=self.RS256_ALGORITHM
        )
        key_dict = jose_key.to_dict()
        key_dict.update(
            {
                "kid": jwt.get_unverified_header(token).get("kid"),
                "use": "sig",
            }
        )
        self.logger.info("x5c JWK", key=key_dict)

        jwks["keys"].append(key_dict)

        return jwks

    def _verify_cert_chain(
        self, x5c_cert_chain: list[str]
    ) -> Optional[x509.Certificate]:
        cert_chain = [self._x5c_str_to_cert(cert_str) for cert_str in x5c_cert_chain]

        builder = x509v.PolicyBuilder()
        builder = builder.store(self.trust_store)
        verifier = builder.build_client_verifier()

        leaf_cert = cert_chain[0]

        try:
            _ = verifier.verify(leaf_cert, cert_chain[1:])
            return leaf_cert
        except x509v.VerificationError as err:
            log_exception(err)
            return None

    def _x5c_str_to_cert(self, cert_str: str) -> x509.Certificate:
        cert_der = base64.urlsafe_b64decode(cert_str)
        return x509.load_der_x509_certificate(cert_der)
