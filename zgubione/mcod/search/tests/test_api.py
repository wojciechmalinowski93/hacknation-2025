from pytest_bdd import scenarios

scenarios(
    "features/search.feature",
    "features/sparql.feature",
    "features/suggest.feature",
    "features/other_sparql_endpoints.feature",
)
