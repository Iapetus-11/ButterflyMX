from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class EmailAndPassword:
    email: str
    password: str


@dataclass(frozen=True, kw_only=True, slots=True)
class OauthCredentials:
    """
    Oauth credentials used for login flow, these can be obtained by using a debugging proxy while
    logging in via the mobile app.
    """

    client_id: str
    client_secret: str


@dataclass(frozen=True, kw_only=True, slots=True)
class AccessToken:
    token: str
    expires_at: float
