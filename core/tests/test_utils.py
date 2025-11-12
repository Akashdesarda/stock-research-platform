from stocksense.utils import rest_request_sync


def test_rest_request_sync_success():
    url = "https://httpbin.org/get"
    response = rest_request_sync(url, method="GET", timeout=10)
    assert response.status_code == 200
    assert "url" in response.json()
    assert response.json()["url"] == url
