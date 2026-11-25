from fastapi.testclient import TestClient
import pytest
from main import app
import psycopg
import os
from urllib.parse import urlsplit
from schemas import PAGE_SIZE

@pytest.fixture(scope="module")
def client():
    url = os.environ["DATABASE_URL"]
    # Prevent accidentally clearing normal database.
    assert urlsplit(url).path.endswith("_test"), "Use a dedicated test database"
    assert os.getenv("ALLOW_TEST_DB_RESET") == "1"
    
    from main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_database(client):
    with psycopg.connect(
        os.environ["DATABASE_URL"], autocommit=True
    ) as conn:
        database = conn.execute("SELECT current_database()").fetchone()[0]
        assert database.endswith("_test")
        conn.execute("TRUNCATE TABLE users RESTART IDENTITY")
        yield
        conn.execute("TRUNCATE TABLE users RESTART IDENTITY")


@pytest.fixture
def create_user(client):
    def create(name="Alice", age=25, birth_state="NJ"):
        response = client.post("/api/users", json={
            "name": name,
            "age": age,
            "birth_state": birth_state,
        })
        assert response.status_code == 201, response.text
        return response.json()

    return create


def test_create_user(client):
    response = client.post("/api/users", json={
        "name": " Alice ",
        "age": 25,
        "birth_state": " nj "
    })
    created = response.json()
    assert response.status_code == 201
    assert created["name"] == "Alice"
    assert created["age"] == 25
    assert created["birth_state"] == "NJ"
    assert isinstance(created["id"], int)


def test_get_user(client, create_user):
    user = create_user()
    response = client.get(f"/api/users/{user['id']}")
    print(response.json())
    assert response.status_code == 200
    assert response.json() == user


def test_update_user(client, create_user):
    user = create_user()
    payload = {"name": "Hannah Gallagher ", "age" : 32, "birth_state": "  pa"}
    response = client.put(f"api/users/{user['id']}", json=payload)
    assert response.status_code == 200
    expected = {
            "id": user["id"],
            "name": "Hannah Gallagher",
            "age": 32,
            "birth_state": "PA",
        }
    assert response.json() == expected
    assert client.get(f"/api/users/{user['id']}").json() == expected

def test_partial_update(client, create_user):
    user = create_user()
    response = client.put(
        f"/api/users/{user['id']}", json={"age": 0}
    )
    assert response.status_code == 200
    assert response.json() == {**user, "age": 0}


def test_delete_user(client, create_user):
    user = create_user()
    response = client.delete(f"/api/users/{user['id']}")
    assert response.status_code == 200
    assert client.get(f"/api/users/{user['id']}").status_code == 404
    assert client.get("/api/users").json() == []


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_nonexistent_user(client, method):
    kwargs = {"json": {"age": 30}} if method == "PUT" else {}
    response = client.request(
        method, "/api/users/999999", **kwargs
    )
    assert response.status_code == 404


@pytest.mark.parametrize("age", [-1, 32768, "not-an-age"])
def test_invalid_age(client, age):
    response = client.post("/api/users", json={
        "name": "Alice", "age": age, "birth_state": "NJ",
    })
    assert response.status_code == 422
    assert client.get("/api/users").json() == []


@pytest.mark.parametrize("state", ["XX", "", "New Jersey"])
def test_invalid_state(client, state):
    response = client.post("/api/users", json={
        "name": "Alice", "age": 25, "birth_state": state,
    })
    assert response.status_code == 422
    assert client.get("/api/users").json() == []


@pytest.mark.parametrize("name", ["", "   ", "a" * 1001])
def test_invalid_name(client, name):
    response = client.post("/api/users", json={
        "name": name, "age": 25, "birth_state": "NJ",
    })
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["name", "age", "birth_state"])
def test_missing_required_field(client, field):
    payload = {"name": "Alice", "age": 25, "birth_state": "NJ"}
    del payload[field]
    assert client.post("/api/users", json=payload).status_code == 422


@pytest.mark.parametrize("payload", [
    {"age": -1},
    {"birth_state": "XX"},
])
def test_invalid_update(client, create_user, payload):
    user = create_user()
    response = client.put(
        f"/api/users/{user['id']}", json=payload
    )
    assert response.status_code == 422
    assert client.get(f"/api/users/{user['id']}").json() == user


def test_filter_users_by_state(client, create_user):
    first = create_user(name="Alice", birth_state="NJ")
    create_user(name="Bob", birth_state="PA")
    second = create_user(name="Carol", birth_state="NJ")
    response = client.get(
        "/api/users", params={"birth_state": " nj "}
    )
    assert response.status_code == 200
    assert {user["id"] for user in response.json()} == {
        first["id"], second["id"],
    }
    assert all(
        user["birth_state"] == "NJ" for user in response.json()
    )


def test_filter_with_no_matches(client, create_user):
    create_user(birth_state="NJ")
    response = client.get(
        "/api/users", params={"birth_state": "CA"}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_pagination(client, create_user):
    users = [ create_user(name=f"User {i}") for i in range(PAGE_SIZE * 2 + 1) ]
    expected_pages = [
        users[start:start + PAGE_SIZE]
        for start in range(0, len(users), PAGE_SIZE)
    ]
    expected_pages.append([])  # Page after the final results.
    for page_number, expected_users in enumerate(
        expected_pages, start=1
    ):
        response = client.get(
            "/api/users",
            params={
                "page": page_number,
                "sort_by": "id",
                "order": "asc",
            },
        )
        assert response.status_code == 200
        assert response.json() == expected_users


@pytest.mark.parametrize("page", [0, -1, "abc"])
def test_invalid_page(client, page):
    response = client.get("/api/users", params={"page": page})
    assert response.status_code == 422


@pytest.mark.parametrize("sort_by", [
    "id", "name", "age", "birth_state",
])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_sorting(client, create_user, sort_by, order):
    users = [
        create_user(name="Zoe", age=40, birth_state="NJ"),
        create_user(name="Amy", age=20, birth_state="CA"),
    ]
    response = client.get("/api/users", params={
        "sort_by": sort_by, "order": order,
    })
    assert response.status_code == 200
    assert response.json() == sorted(
        users,
        key=lambda user: user[sort_by],
        reverse=(order == "desc"),
    )


@pytest.mark.parametrize("params", [
    {"sort_by": "invalid_column"},
    {"order": "sideways"},
    {"birth_state": "XX"},
])
def test_invalid_query_parameters(client, params):
    response = client.get("/api/users", params=params)
    assert response.status_code == 422


def test_health_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}