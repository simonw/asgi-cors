import fnmatch
import asyncio
from functools import wraps


def asgi_cors_decorator(
    allow_all=False,
    hosts=None,
    host_wildcards=None,
    callback=None,
    headers=None,
    methods=None,
    max_age=None,
):
    hosts = hosts or []
    host_wildcards = host_wildcards or []
    headers = headers or []
    methods = methods or []

    # We need hosts and host_wildcards to be b""
    hosts = set(h.encode("utf8") if isinstance(h, str) else h for h in hosts)
    host_wildcards = [
        h.encode("utf8") if isinstance(h, str) else h for h in host_wildcards
    ]
    headers = [h.encode("utf8") if isinstance(h, str) else h for h in headers]
    methods = [h.encode("utf8") if isinstance(h, str) else h for h in methods]

    if any(h.endswith(b"/") for h in (hosts or [])) or any(
        h.endswith(b"/") for h in (host_wildcards or [])
    ):
        assert False, "Error: CORS origin rules should never end in a /"

    def _asgi_cors_decorator(app):
        @wraps(app)
        async def app_wrapped_with_cors(scope, receive, send):
            async def wrapped_send(event):
                if event["type"] == "http.response.start":
                    original_headers = event.get("headers") or []
                    access_control_allow_origin = None
                    if allow_all:
                        access_control_allow_origin = b"*"
                    elif hosts or host_wildcards or callback:
                        incoming_origin = dict(scope.get("headers") or []).get(
                            b"origin"
                        )
                        if incoming_origin:
                            matches_hosts = incoming_origin in hosts
                            matches_wildcards = any(
                                fnmatch.fnmatch(incoming_origin, host_wildcard)
                                for host_wildcard in host_wildcards
                            )
                            matches_callback = False
                            if callback is not None:
                                if asyncio.iscoroutinefunction(callback):
                                    matches_callback = await callback(incoming_origin)
                                else:
                                    matches_callback = callback(incoming_origin)
                            if matches_hosts or matches_wildcards or matches_callback:
                                access_control_allow_origin = incoming_origin

                    if access_control_allow_origin is not None:
                        # Construct a new event with new headers
                        new_headers = [
                            p
                            for p in original_headers
                            if p[0]
                            not in (
                                b"access-control-allow-origin",
                                b"access-control-allow-headers",
                                b"access-control-allow-methods",
                                b"access-control-max-age",
                            )
                        ]
                        if access_control_allow_origin:
                            new_headers.append(
                                [
                                    b"access-control-allow-origin",
                                    access_control_allow_origin,
                                ]
                            )
                        if headers:
                            new_headers.append(
                                [
                                    b"access-control-allow-headers",
                                    b", ".join(
                                        h.encode("utf-8") if isinstance(h, str) else h
                                        for h in headers
                                    ),
                                ]
                            )
                        if methods:
                            new_headers.append(
                                [
                                    b"access-control-allow-methods",
                                    b", ".join(
                                        m.encode("utf-8") if isinstance(m, str) else m
                                        for m in methods
                                    ),
                                ]
                            )
                        if max_age:
                            new_headers.append(
                                [b"access-control-max-age", str(max_age)]
                            )
                        event = {
                            "type": "http.response.start",
                            "status": event["status"],
                            "headers": new_headers,
                        }
                await send(event)

            await app(scope, receive, wrapped_send)

        return app_wrapped_with_cors

    return _asgi_cors_decorator


def asgi_cors(
    app,
    allow_all=False,
    hosts=None,
    host_wildcards=None,
    callback=None,
    headers=None,
    methods=None,
    max_age=None,
):
    return asgi_cors_decorator(
        allow_all, hosts, host_wildcards, callback, headers, methods, max_age
    )(app)
