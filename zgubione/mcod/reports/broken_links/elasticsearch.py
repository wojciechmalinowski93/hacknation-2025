import logging
from typing import Dict, Tuple

import pandas as pd
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import Connections

logger = logging.getLogger("mcod")


def generate_index_from_pandas_df(
    es_handler: Elasticsearch,
    index_name: str,
    df: pd.DataFrame,
) -> Tuple[int, int]:
    def _generate_documents(df_data: pd.DataFrame, index_name: str):
        for i, row in df_data.iterrows():
            yield {
                "_index": index_name,
                "_type": "doc",
                "_source": row.to_dict(),
            }

    created, failed = bulk(es_handler, _generate_documents(df, index_name), stats_only=True)
    return created, failed


def create_mapping(col_names_and_types: Dict[str, str]) -> Dict:
    mapping = {
        "mappings": {
            "doc": {
                "properties": {},
            }
        }
    }

    type_mappings = {
        "integer": {"type": "integer"},
        "float": {"type": "float"},
        "text": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "date": {"type": "date"},
        "boolean": {"type": "boolean"},
    }

    for col_name, type_info in col_names_and_types.items():
        try:
            mapping_for_field = type_mappings[type_info]
        except KeyError:
            raise Exception(f"Unknown type for column:{col_name}")
        mapping["mappings"]["doc"]["properties"][col_name] = mapping_for_field
    return mapping


def rebuild_brokenlinks_es_index(
    index_name: str,
    index_fields_names_and_types: Dict[str, str],
    dataframe: pd.DataFrame,
    change_cols_name_data: Dict[str, str],
) -> Tuple[int, int]:
    es_connections = Connections()
    es_connections.configure(**settings.ELASTICSEARCH_DSL)
    es_handler: Elasticsearch = es_connections.get_connection()

    # delete old index if exists
    if es_handler.indices.exists(index=index_name):
        es_handler.indices.delete(index=index_name)
        logger.info(f"Deleted index for broken links: {index_name}")

    # create mapping and empty index
    mapping: Dict = create_mapping(index_fields_names_and_types)
    es_handler.indices.create(index=index_name, body=mapping)
    logger.info(f"Created index for broken links: {index_name}")

    # change index fields name to mapping
    dataframe.rename(columns=change_cols_name_data, inplace=True)

    # fill index with data
    documents_created, documents_failed = generate_index_from_pandas_df(es_handler, index_name, dataframe)
    logger.info(f"Filled index for broken links: {index_name}")
    return documents_created, documents_failed
