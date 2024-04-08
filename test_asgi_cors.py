from asgi_cors import asgi_cors
import pytest
import httpx


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
    async with httpx.AsyncClient(app=hello_world_app) as client:
        response = await client.get("http://localhost/")
        assert response.status_code == 200
        assert response.json() == {"hello": "world"}
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_allow_all():
    app = asgi_cors(hello_world_app, allow_all=True)
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get("http://localhost/")
        assert response.headers["access-control-allow-origin"] == "*"


EXAMPLE_HOST = "http://example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_origin,expected_cors_header",
    [(None, None), (EXAMPLE_HOST, EXAMPLE_HOST), ("http://foo.com", None)],
)
async def test_allowlisted_hosts(request_origin, expected_cors_header):
    app = asgi_cors(hello_world_app, hosts=[EXAMPLE_HOST])
    async with httpx.AsyncClient(app=app) as client:
        headers = {"origin": request_origin} if request_origin else {}
        response = await client.get("http://localhost/", headers=headers)
        assert (
            response.headers.get("access-control-allow-origin") == expected_cors_header
        )


SUBDOMAIN_WILDCARD = ["https://*.example.com"]
PORT_WILDCARD = ["http://localhost:8*"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wildcards,request_origin,expected_cors_header",
    [
        (SUBDOMAIN_WILDCARD, None, None),
        (SUBDOMAIN_WILDCARD, "https://www.example.com", "https://www.example.com"),
        (SUBDOMAIN_WILDCARD, "https://foo.com", None),
        (PORT_WILDCARD, "http://foo.com", None),
        (PORT_WILDCARD, "http://localhost:8000", "http://localhost:8000"),
    ],
)
async def test_wildcard_hosts(wildcards, request_origin, expected_cors_header):
    app = asgi_cors(hello_world_app, host_wildcards=wildcards)
    async with httpx.AsyncClient(app=app) as client:
        headers = {"origin": request_origin} if request_origin else {}
        response = await client.get("http://localhost/", headers=headers)
        assert (
            response.headers.get("access-control-allow-origin") == expected_cors_header
        )


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
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get(
            "http://localhost/", headers={"origin": EXAMPLE_HOST}
        )
        assert (
            response.headers.get("access-control-allow-origin") == expected_cors_header
        )
        assert was_called


@pytest.mark.asyncio
async def test_callback_async():
    was_called = False

    async def callback_true(origin):
        nonlocal was_called
        was_called = True
        return True

    async def callback_false(origin):
        return False

    app_true = asgi_cors(hello_world_app, callback=callback_true)
    app_false = asgi_cors(hello_world_app, callback=callback_false)

    async with httpx.AsyncClient(app=app_true) as client:
        response = await client.get(
            "http://localhost/", headers={"origin": EXAMPLE_HOST}
        )
        assert response.headers.get("access-control-allow-origin") == EXAMPLE_HOST

    async with httpx.AsyncClient(app=app_false) as client:
        response = await client.get(
            "http://localhost/", headers={"origin": EXAMPLE_HOST}
        )
        assert "access-control-allow-origin" not in response.headers

    assert was_called
