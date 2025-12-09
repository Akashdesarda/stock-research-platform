import httpx
import orjson


def rest_request_sync(
    url: str,
    method: str = "GET",
    payload_data: dict | None = None,
    query_params: dict | None = None,
    headers: dict | None = None,
    timeout: int | httpx.Timeout | None = httpx.Timeout(
        read=None, write=None, connect=3, pool=10
    ),
    **kwargs,
) -> httpx.Response:
    timeout = httpx.Timeout(timeout)
    params = httpx.QueryParams(query_params) if query_params else None

    with httpx.Client(timeout=timeout, **kwargs) as client:
        response = client.request(
            method=method,
            url=url,
            params=params,
            content=orjson.dumps(payload_data) if payload_data else None,
            headers=headers,
        )

    return response
