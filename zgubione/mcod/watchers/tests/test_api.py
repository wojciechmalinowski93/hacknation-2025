from pytest_bdd import scenarios

scenarios(
    "features/notifications_api.feature",
    "features/query_watcher.feature",
    "features/subscriptions_api.feature",
)
