from urllib.parse import parse_qs, urlparse

from django_redis import get_redis_connection

from mcod.core.tasks import extended_shared_task
from mcod.searchhistories.models import SearchHistory
from mcod.users.models import User


@extended_shared_task
def save_searchhistories_task():
    key_pattern = "search_history_user_*"

    con = get_redis_connection()
    keys = con.keys(key_pattern)

    for k in keys:
        user_id = int(k.decode().split("_")[-1])
        if User.objects.filter(pk=user_id).exists():
            while True:
                url = con.lpop(k)
                if url:
                    url = url.decode()
                    o = urlparse(url)
                    query_sentence = parse_qs(o.query).get("q")
                    if query_sentence:

                        if isinstance(query_sentence, list):
                            query_sentence = query_sentence[0]

                        SearchHistory.objects.create(url=url, query_sentence=query_sentence, user_id=user_id)

                else:
                    break
        else:
            con.delete(k)
    return {}
