from asgiref.testing import ApplicationCommunicator
from asgi_cors import asgi_cors
import pytest


async def hello_world_app(scope, receive, send):
    assert scope["type"] == "http"
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": b'{"hello": "world"}'})


@pytest.mark.asyncio
async def test_hello_world_app_has_no_cors_header():
    instance = ApplicationCommunicator(
        hello_world_app,
        {"type": "http", "http_version": "1.0", "method": "GET", "path": "/"},
    )
    await instance.send_input({"type": "http.request"})
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [[b"content-type", b"application/json"]],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b'{"hello": "world"}',
    }


@pytest.mark.asyncio
async def test_allow_all():
    app = asgi_cors(hello_world_app, allow_all=True)
    header = await get_cors_header(app)
    assert b"*" == header


EXAMPLE_HOST = b"http://example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_origin,expected_cors_header",
    [(None, None), (EXAMPLE_HOST, EXAMPLE_HOST), (b"http://foo.com", None)],
)
async def test_whitelisted_hosts(request_origin, expected_cors_header):
    app = asgi_cors(hello_world_app, hosts=[EXAMPLE_HOST])
    assert expected_cors_header == await get_cors_header(app, request_origin)


SUBDOMAIN_WILDCARD = [b"https://*.example.com"]
PORT_WILDCARD = [b"http://localhost:8*"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wildcards,request_origin,expected_cors_header",
    [
        (SUBDOMAIN_WILDCARD, None, None),
        (SUBDOMAIN_WILDCARD, b"https://www.example.com", b"https://www.example.com"),
        (SUBDOMAIN_WILDCARD, b"https://foo.com", None),
        (PORT_WILDCARD, b"http://foo.com", None),
        (PORT_WILDCARD, b"http://localhost:8000", b"http://localhost:8000"),
    ],
)
async def test_wildcard_hosts(wildcards, request_origin, expected_cors_header):
    app = asgi_cors(hello_world_app, host_wildcards=wildcards)
    assert expected_cors_header == await get_cors_header(app, request_origin)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback_return,expected_cors_header", [(True, EXAMPLE_HOST), (False, None)]
)
async def test_callback(callback_return, expected_cors_header):
    was_called = False

    def callback(origin):
        nonlocal was_called
        was_called = True
        return callback_return

    app = asgi_cors(hello_world_app, callback=callback)
    assert expected_cors_header == await get_cors_header(app, EXAMPLE_HOST)
    assert was_called


async def get_cors_header(app, request_origin=None, expected_status=200):
    scope = {"type": "http", "http_version": "1.0", "method": "GET", "path": "/"}
    if request_origin is not None:
        scope["headers"] = [[b"origin", request_origin]]
    instance = ApplicationCommunicator(app, scope)
    await instance.send_input({"type": "http.request"})
    event = await instance.receive_output(1)
    assert expected_status == event["status"]
    return dict(event.get("headers") or []).get(b"access-control-allow-origin")


@pytest.mark.asyncio
async def test_callback_async():
    was_called = False

    async def callback_true(origin):
        nonlocal was_called
        was_called = True
        return True

    async def callback_false(origin):
        return False

    assert EXAMPLE_HOST == await get_cors_header(
        asgi_cors(hello_world_app, callback=callback_true), EXAMPLE_HOST
    )
    assert None == await get_cors_header(
        asgi_cors(hello_world_app, callback=callback_false), EXAMPLE_HOST
    )
    assert was_called
