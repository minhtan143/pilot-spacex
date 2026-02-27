"""RSA key pair loader for RS256 JWT signing."""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from authcore.config import Settings


class KeyManager:
    """Load RS256 RSA key pair from Settings (PEM strings). Cached in-process."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._private_key: RSAPrivateKey | None = None
        self._public_key: RSAPublicKey | None = None

    def get_private_key(self) -> RSAPrivateKey:
        """Return cached RSA private key, loading from PEM on first call.

        Returns:
            RSA private key for JWT signing.

        Raises:
            ValueError: If the configured key is not an RSA private key.
        """
        if self._private_key is None:
            pem = self._settings.jwt_private_key.get_secret_value().encode()
            key = serialization.load_pem_private_key(pem, password=None)
            if not isinstance(key, RSAPrivateKey):
                raise ValueError("jwt_private_key must be an RSA private key")
            self._private_key = key
        return self._private_key

    def get_public_key(self) -> RSAPublicKey:
        """Return cached RSA public key, loading from PEM on first call.

        Returns:
            RSA public key for JWT verification.

        Raises:
            ValueError: If the configured key is not an RSA public key.
        """
        if self._public_key is None:
            pem = self._settings.jwt_public_key.encode()
            key = serialization.load_pem_public_key(pem)
            if not isinstance(key, RSAPublicKey):
                raise ValueError("jwt_public_key must be an RSA public key")
            self._public_key = key
        return self._public_key
