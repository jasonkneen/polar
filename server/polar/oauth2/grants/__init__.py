import typing

from .authorization_code import (
    AuthorizationCodeGrant,
    CodeChallenge,
    OpenIDCode,
    OpenIDToken,
    ValidateSubAndPrompt,
)
from .refresh_token import RefreshTokenGrant

if typing.TYPE_CHECKING:
    from ..authorization_server import AuthorizationServer


def register_grants(server: "AuthorizationServer") -> None:
    server.register_grant(
        AuthorizationCodeGrant,
        [
            CodeChallenge(),
            OpenIDCode(server.session, require_nonce=False),
            OpenIDToken(),
            ValidateSubAndPrompt(server.session),
        ],
    )
    server.register_grant(RefreshTokenGrant)


__all__ = ["register_grants", "AuthorizationCodeGrant", "CodeChallenge"]
