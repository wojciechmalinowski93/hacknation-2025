import pytest
from django_redis import get_redis_connection
from falcon import HTTP_201, HTTP_OK


@pytest.mark.redis
@pytest.mark.elasticsearch
def test_searchhistories_middleware_set_up_key_in_redis(client, active_editor):
    redis_con = get_redis_connection()
    keys = [k.decode() for k in redis_con.keys()]

    key = f"search_history_user_{active_editor.id}"
    assert key not in keys
    resp = client.simulate_post(
        path="/auth/login",
        json={
            "data": {
                "type": "user",
                "attributes": {
                    "email": active_editor.email,
                    "password": "12345.Abcde",
                },
            }
        },
    )

    token = resp.json["data"]["attributes"]["token"]

    assert resp.status == HTTP_201
    resp = client.simulate_get(
        "/1.4/search",
        query_string="q=testmiddleware",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert HTTP_OK == resp.status

    keys = [k.decode() for k in redis_con.keys()]
    assert key in keys
    redis_con.delete(key)  # clean for future tests


@pytest.mark.redis
@pytest.mark.elasticsearch
def test_searchhistories_middleware_ignore_search_without_query(client, active_editor):
    redis_con = get_redis_connection()
    key = f"search_history_user_{active_editor.id}"
    resp = client.simulate_post(
        path="/auth/login",
        json={
            "data": {
                "type": "user",
                "attributes": {
                    "email": active_editor.email,
                    "password": "12345.Abcde",
                },
            }
        },
    )

    token = resp.json["data"]["attributes"]["token"]

    resp = client.simulate_get(
        "/1.4/search",
        query_string="sort=relevance&page=1&per_page=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert HTTP_OK == resp.status

    keys = [k.decode() for k in redis_con.keys()]
    assert key not in keys
    redis_con.delete(key)  # clean for future tests


@pytest.mark.elasticsearch
def test_searchhistories_middleware_ignore_suggestion_path(client, active_editor):
    key = f"search_history_user_{active_editor.id}"
    resp = client.simulate_post(
        path="/auth/login",
        json={
            "data": {
                "type": "user",
                "attributes": {
                    "email": active_editor.email,
                    "password": "12345.Abcde",
                },
            }
        },
    )

    token = resp.json["data"]["attributes"]["token"]
    query_string = "q=test_phrase&models=dataset,institution,knowledge_base,resource,showcase&per_model=1"
    resp = client.simulate_get(
        "/1.4/search/suggest",
        query_string=query_string,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert HTTP_OK == resp.status
    redis_con = get_redis_connection()
    keys = [k.decode() for k in redis_con.keys()]
    assert key not in keys
