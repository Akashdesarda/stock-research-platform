import httpx


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
            json=payload_data,
            headers=headers,
        )

    return response


def rest_sync_client(base_url: str = "http://localhost:8001") -> httpx.Client:
    return httpx.Client(base_url=base_url)
