from __future__ import annotations

import uuid
from typing import Any, Type

import aiohttp

from butterflymx.graphql import Func, Q
from butterflymx.models import (
    AccessToken,
    EmailAndPassword,
    OauthCredentials,
    AccessPoint,
    Building,
    Tenant,
)
from butterflymx.request_client import ButterflyMXRequestClient


class ButterflyMX:
    def __init__(
            self,
            *,
            oauth_credentials: OauthCredentials | None = None,
            email_and_password: EmailAndPassword | None = None,
            access_token: AccessToken | None = None,
            refresh_token: str | None = None,
    ):
        self.__oauth_credentials = oauth_credentials
        self.__email_and_password = email_and_password
        self.__access_token = access_token
        self.__refresh_token = refresh_token

        self.__http: aiohttp.ClientSession | None = None
        self.__client: ButterflyMXRequestClient | None = None

    @property
    def client(self) -> ButterflyMXRequestClient:
        if self.__client is None:
            raise RuntimeError('You must use this class as an async context manager')

        return self.__client

    async def __aenter__(self) -> ButterflyMX:
        self.__http = aiohttp.ClientSession()

        self.__client = ButterflyMXRequestClient(
            http=self.__http,
            oauth_credentials=self.__oauth_credentials,
            email_and_password=self.__email_and_password,
            access_token=self.__access_token,
            refresh_token=self.__refresh_token,
        )

        return self

    async def __aexit__(
            self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: Any
    ) -> None:
        assert self.__http is not None
        await self.__http.close()
        self.__http = None

    async def graphql_query(self, query: str | Q) -> dict[str, Any]:
        response = await self.client.request(
            'POST',
            'https://api.butterflymx.com/denizen/v1/graphql',
            json={'query': str(query)},
        )

        data = await response.json()

        if len(data) == 1 and 'data' in data:
            data = data['data']

        return data

    async def get_types_introspection(self, *types: str) -> dict[str, Any]:
        """
        Retrieves information on the specified types from the ButterflyMX
        GraphQL API including their fields and information about those fields
        such as types and descriptions.
        """

        q_introspection = Q([
            Q([
                'name',
                Q(
                    ['name', Q(['name', 'kind', Q(['name', 'kind'], name='ofType')], name='type')],
                    name='fields',
                ),
            ], name=f'{t}: __type(name: "{t}")')
            for t in types
        ])

        return await self.graphql_query(q_introspection)

    async def get_tenants(self) -> list[Tenant]:
        """
        Retrieves a tenant (the logged-in user most likely) and related data
        """

        q_access_points = Q(
            Q(
                [
                    'id',
                    'legacyId',
                    'name',
                    'capabilities',
                    Q(['id', 'name'], name='building'),
                ],
                name='nodes'
            ),
            name='accessPoints',
        )

        q_tenants_access_points = Q(Q(
            Q(['id', 'name', q_access_points], name='nodes'),
            name='tenants',
        ))

        data = await self.graphql_query(q_tenants_access_points)

        return [
            Tenant(
                id=tenant['id'],
                name=tenant['name'],
                access_points=[
                    AccessPoint(
                        id=access_point['id'],
                        legacy_id=access_point['legacyId'],
                        name=access_point['name'],
                        building=Building(
                            id=access_point['building']['id'],
                            name=access_point['building']['name'],
                        ),
                        capabilities=access_point['capabilities'],
                    )
                    for access_point in tenant['accessPoints']['nodes']
                ],
            )
            for tenant in data['tenants']['nodes']
        ]

    async def open_access_point(
            self,
            tenant: str | Tenant,
            access_point: str | AccessPoint
    ) -> None:
        tenant = tenant if isinstance(tenant, str) else tenant.id
        access_point = access_point if isinstance(access_point, str) else access_point.id

        await self.graphql_query(
            query=Q(
                Func(
                    "swipeToOpen",
                    {
                        "input": {
                            "tenantId": tenant,
                            "accessPointId": access_point,
                            "deviceId": None,
                            "clientMutationId": str(uuid.uuid4()),
                        }
                    },
                    ['clientMutationId'],
                ),
                name="mutation",
            )
        )
