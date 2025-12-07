from typing import Callable, List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from mcod.core.api.search.helpers import ElasticsearchHit


class ElasticsearchHitFactory:

    @staticmethod
    def create(
        id=None,
        institution="Fake institution",
        dataset="Fake dataset",
        title="Fake title",
        portal_data_link="https://provider.com/fake-file",
        link="https://fake.broken.link",
    ) -> ElasticsearchHit:
        return ElasticsearchHit(
            id=id or str(uuid4())[:8],
            source={
                "institution": institution,
                "dataset": dataset,
                "title": title,
                "portal_data_link": portal_data_link,
                "link": link,
            },
        )

    @classmethod
    def create_many(cls, count=3) -> List[ElasticsearchHit]:
        return [cls.create() for _ in range(count)]


@pytest.fixture
def es_hit_factory() -> ElasticsearchHitFactory:
    return ElasticsearchHitFactory()


class FakeHit:
    def __init__(self, id: str):
        self.meta = MagicMock()
        self.meta.id = id

    def to_dict(self):
        return {"some_field": "some_value"}


class FakeResponse:
    def __init__(self, hits: List[FakeHit]):
        self.hits = hits

    def success(self) -> bool:
        return True


@pytest.fixture
def es_hits_response_factory() -> Callable[..., FakeResponse]:

    def _make(count: int = 3) -> FakeResponse:
        hits = [FakeHit(str(uuid4())[:8]) for _ in range(count)]
        return FakeResponse(hits)

    return _make
