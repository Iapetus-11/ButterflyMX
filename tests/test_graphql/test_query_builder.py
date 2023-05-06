import pytest

from butterflymx.graphql import Func, Q


@pytest.fixture
def swipe_to_open_func() -> Func:
    return Func(
        'swipeToOpen',
        {
            'input': {
                'tenantId': 'test-tenant-123',
                'accessPointId': 'test-access_point-123',
                'deviceId': None,
                'clientMutationId': '00000000-0000-0000-0000-000000000000',
            }
        },
        ['clientMutationId'],
    )


def test_render_q():
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

    assert q_tenants_access_points.render() == (
        # Python multi-line strings are kinda dumb
        'query {\n'
        '  tenants {\n'
        '    nodes {\n'
        '      id\n'
        '      name\n'
        '      accessPoints {\n'
        '        nodes {\n'
        '          id\n'
        '          legacyId\n'
        '          name\n'
        '          capabilities\n'
        '          building {\n'
        '            id\n'
        '            name\n'
        '          }\n'
        '        }\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '}'
    )


def test_render_func(swipe_to_open_func):
    assert swipe_to_open_func.render() == (
        'swipeToOpen(input: {\n'
        '  tenantId: "test-tenant-123"\n'
        '  accessPointId: "test-access_point-123"\n'
        '  deviceId: null\n'
        '  clientMutationId: "00000000-0000-0000-0000-000000000000"\n'
        '}) {\n'
        '  clientMutationId\n'
        '}'
    )


def test_render_func_in_q(swipe_to_open_func):
    func_in_q = Q(swipe_to_open_func, name="mutation")

    assert func_in_q.render() == (
        'mutation {\n'
        '  swipeToOpen(input: {\n'
        '    tenantId: "test-tenant-123"\n'
        '    accessPointId: "test-access_point-123"\n'
        '    deviceId: null\n'
        '    clientMutationId: "00000000-0000-0000-0000-000000000000"\n'
        '  }) {\n'
        '    clientMutationId\n'
        '  }\n'
        '}'
    )
