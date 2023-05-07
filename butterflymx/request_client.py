import time
from typing import Any

import aiohttp
from aiohttp import FormData
import bs4

from butterflymx.models import EmailAndPassword
from butterflymx.models.login import AccessToken, OauthCredentials
from butterflymx.utils import get_query_params

SPOOF_USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_1_1 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
)


class ButterflyMXRequestClient:
    def __init__(
        self,
        *,
        http: aiohttp.ClientSession,
        oauth_credentials: OauthCredentials | None = None,
        email_and_password: EmailAndPassword | None = None,
        access_token: AccessToken | None = None,
        refresh_token: str | None = None,
    ):
        if not (refresh_token or email_and_password):
            raise TypeError('Either refresh_token or email_and_password must be specified.')

        self.__http = http
        self.__oauth_credentials = oauth_credentials
        self.__email_and_password = email_and_password
        self.__refresh_token = refresh_token

        self.__access_token = access_token

    @property
    def access_token(self) -> AccessToken:
        if self.__access_token is None:
            raise RuntimeError('access_token has not yet been initialized.')

        return self.__access_token

    @property
    def refresh_token(self) -> str:
        if self.__refresh_token is None:
            raise RuntimeError('refresh_token has not yet been initialized.')

        return self.__refresh_token

    async def __oauth_login(self) -> tuple[AccessToken, str]:
        if not self.__email_and_password:
            raise RuntimeError('Oauth login requires email and password to be supplied.')

        if not self.__oauth_credentials:
            raise RuntimeError('Oauth login requires oauth credentials to be supplied.')

        # Start oauth flow
        await self.request(
            'GET',
            'https://accounts.butterflymx.com/oauth/authorize',
            params={
                'client_id': self.__oauth_credentials.client_id,
                'redirect_uri': 'com.butterflymx.oauth://oauth',
                'response_type': 'code',
            },
            authenticate=False,
            allow_redirects=False,
        )

        # Fetch authenticity token from login page
        response = await self.request(
            'GET', 'https://accounts.butterflymx.com/login/new', authenticate=False
        )

        authenticity_token_input = bs4.BeautifulSoup(await response.text(), 'html.parser').find(
            'input', attrs={'name': 'authenticity_token'}
        )
        assert isinstance(authenticity_token_input, bs4.Tag)

        # Submit email and password
        response = await self.request(
            'POST',
            'https://accounts.butterflymx.com/login',
            data=FormData(
                {
                    'utf8': '✓',  # Wtf is this
                    'authenticity_token': authenticity_token_input.attrs['value'],
                    'account[email]': self.__email_and_password.email,
                    'account[password]': self.__email_and_password.password,
                    'button': '',
                }
            ),
            headers={
                'Referer': 'https://accounts.butterflymx.com/login/new',
                'Origin': 'https://accounts.butterflymx.com',
                'User-Agent': SPOOF_USER_AGENT,
            },
            authenticate=False,
            allow_redirects=False,
        )

        # Oauth flow
        response = await self.request(
            'GET',
            response.headers['Location'],
            headers={
                'User-Agent': SPOOF_USER_AGENT,
                'Referer': 'https://accounts.butterflymx.com/login/new',
            },
            authenticate=False,
            allow_redirects=False,
        )
        oauth_code = get_query_params(response.headers['Location'])['code']

        # Retrieve access and refresh tokens
        response = await self.request(
            'POST',
            'https://accounts.butterflymx.com/oauth/token',
            params={
                'client_secret': self.__oauth_credentials.client_secret,
                'grant_type': 'authorization_code',
                'client_id': self.__oauth_credentials.client_id,
                'redirect_uri': 'com.butterflymx.oauth://oauth',
                'code': oauth_code,
            },
            authenticate=False,
            allow_redirects=False,
        )
        token_data = await response.json()

        return (
            AccessToken(
                token=token_data['access_token'],
                expires_at=(token_data['created_at'] + token_data['expires_in']),
            ),
            token_data['refresh_token'],
        )

    async def __oauth_refresh(self) -> tuple[AccessToken, str]:
        if not self.__oauth_credentials:
            raise RuntimeError('Oauth login requires oauth credentials to be supplied.')

        response = await self.request(
            'POST',
            'https://accounts.butterflymx.com/oauth/token',
            json={
                'refresh_token': self.__refresh_token,
                'client_id': self.__oauth_credentials.client_id,
                'grant_type': 'refresh_token',
            },
            authenticate=False,
        )
        token_data = await response.json()

        return (
            AccessToken(
                token=token_data['access_token'],
                expires_at=(token_data['created_at'] + token_data['expires_in']),
            ),
            token_data['refresh_token'],
        )

    async def ensure_access_token(self) -> None:
        if (
            self.__access_token is None
            or time.time() > self.access_token.expires_at
        ):
            access_token: AccessToken
            refresh_token: str

            if self.__refresh_token is None:
                (access_token, refresh_token) = await self.__oauth_login()
            else:
                (access_token, refresh_token) = await self.__oauth_refresh()

            self.__access_token = access_token
            self.__refresh_token = refresh_token

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        authenticate: bool = True,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        if headers is None:
            headers = {}

        if authenticate:
            await self.ensure_access_token()
            headers['Authorization'] = self.access_token.token

        return await self.__http.request(
            method, url, data=data, json=json, params=params, headers=headers, **kwargs
        )
