from elasticsearch_dsl import normalizer

keyword_uppercase = normalizer("keyword_uppercase", type="custom", filter=["uppercase"])
