from levels_api import create_app


def test_app_factory_serves_bootstrap_response() -> None:
    client = create_app().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {"name": "LEVELS API", "status": "bootstrapped"}
