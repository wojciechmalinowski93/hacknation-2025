from functools import reduce

import marshmallow as ma
import marshmallow_jsonapi as ja

from mcod.lib.serializers import ArgsListToDict, BasicSerializer, BucketItem, SearchMeta


class StatsBucketItem(BucketItem):
    key = ma.fields.Raw(data_key="id")
    doc_count = ma.fields.Integer(data_key="count")


class KeywordBucketItem(ma.Schema):
    name = ma.fields.Raw()
    count = ma.fields.Integer()

    @ma.pre_dump(pass_many=True)
    def create_items(self, data, many, **kwargs):
        ret = []
        for row in data:
            item = {
                "name": row["key"],
                "count": row["doc_count"],
            }
            ret.append(item)
        return ret


class InstitutionStatsBucketItem(StatsBucketItem):
    slug = ma.fields.String(attribute="slug")


class ByMonthItem(StatsBucketItem):
    title = ma.fields.String(data_key="date", attribute="key_as_string")


class DocumentsByTypeBucketItem(StatsBucketItem):
    title = ma.fields.String(data_key="type")
    by_month = ma.fields.Nested(ByMonthItem(), attribute="by_month.buckets", many=True)
    monthly_avg = ma.fields.Method("get_monthly_avg", deserialize="load_monthly_avg")

    def get_monthly_avg(self, obj):
        lst = [item["doc_count"] for item in obj["by_month"]["buckets"]]
        avg = reduce(lambda x, y: x + y, lst) / len(lst)
        return avg

    def load_monthly_avg(self, value):
        return float(value)


class StatsAggregations(ArgsListToDict):
    documents_by_type = ma.fields.Nested(DocumentsByTypeBucketItem(), attribute="documents_by_type.buckets", many=True)
    datasets_by_institution = ma.fields.Nested(
        InstitutionStatsBucketItem(app="organizations", model="Organization", with_slug=True),
        attribute="datasets_by_institution.inner.buckets",
        many=True,
    )
    datasets_by_category = ma.fields.Nested(
        StatsBucketItem(app="categories", model="Category"),
        attribute="datasets_by_category.inner.buckets",
        many=True,
    )
    datasets_by_categories = ma.fields.Nested(
        StatsBucketItem(app="categories", model="Category"),
        attribute="datasets_by_categories.inner.buckets",
        many=True,
    )
    datasets_by_formats = ma.fields.Nested(StatsBucketItem(), attribute="datasets_by_formats.buckets", many=True)
    datasets_by_tag = ma.fields.Nested(StatsBucketItem(), attribute="datasets_by_tag.buckets", many=True)
    datasets_by_keyword = ma.fields.Nested(
        KeywordBucketItem(),
        attribute="datasets_by_keyword.inner.inner.buckets",
        many=True,
    )
    datasets_by_openness_scores = ma.fields.Nested(StatsBucketItem(), attribute="datasets_by_openness_scores.buckets", many=True)
    resources_by_type = ma.fields.Nested(BucketItem(), attribute="resources_by_type.buckets", many=True)


class StatsMeta(SearchMeta):
    aggs = ma.fields.Nested(StatsAggregations, attribute="aggregations")


class StatsSchema(ja.Schema):
    id = ma.fields.Int()

    class Meta:
        type_ = "stats"
        strict = True
        self_url = "/stats"


class StatsSerializer(StatsSchema, BasicSerializer):
    pass
