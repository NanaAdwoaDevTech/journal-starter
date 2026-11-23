"""The API must send Strict-Transport-Security on every response."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import app as real_app
from api.security_headers import HSTS_VALUE, add_security_headers


def test_header_is_added_to_a_plain_app() -> None:
    app = FastAPI()
    add_security_headers(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    response = TestClient(app).get("/ping")
    assert response.headers["strict-transport-security"] == HSTS_VALUE


def test_header_is_sent_by_the_real_app() -> None:
    response = TestClient(real_app).get("/version")
    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == HSTS_VALUE


def test_max_age_is_at_least_one_year() -> None:
    max_age = int(HSTS_VALUE.split(";")[0].split("=")[1])
    assert max_age >= 31536000
