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
async def test_app_has_no_cors_header():
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
async def test_app_with_cors_header():
    instance = ApplicationCommunicator(
        asgi_cors(hello_world_app, allow_all=True),
        {"type": "http", "http_version": "1.0", "method": "GET", "path": "/"},
    )
    await instance.send_input({"type": "http.request"})
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"application/json"],
            [b"access-control-allow-origin", b"*"],
        ],
    }
