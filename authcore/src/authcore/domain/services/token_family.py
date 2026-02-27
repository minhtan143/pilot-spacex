"""Pure domain service for token family theft detection.

No I/O. No external dependencies.
"""

from authcore.domain.models.refresh_token import RefreshTokenEntity


class TokenFamilyPolicy:
    """Determines whether a token reuse indicates theft.

    Token rotation: each refresh issues a new token and revokes the old one.
    If a revoked token is presented, the entire family is revoked (theft signal).
    """

    @staticmethod
    def is_reuse_attack(token: RefreshTokenEntity) -> bool:
        """Return True if presenting this token indicates a token theft attack.

        A revoked token being re-presented means the old token was leaked —
        revoke the entire family to invalidate all derived sessions.

        Args:
            token: The refresh token being presented.

        Returns:
            True if the token is revoked (reuse attack detected).
        """
        return token.is_revoked

    @staticmethod
    def is_expired(token: RefreshTokenEntity) -> bool:
        """Return True if the token has passed its expiry time.

        Args:
            token: The refresh token being validated.

        Returns:
            True if token is expired.
        """
        return token.is_expired()
