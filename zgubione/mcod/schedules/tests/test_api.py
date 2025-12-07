from pytest_bdd import scenarios

scenarios(
    "features/extra.feature",
    "features/schedule_agents_api.feature",
    "features/schedule_details_api.feature",
    "features/user_schedule_details_api.feature",
    "features/user_schedule_item_details_api.feature",
    "features/user_schedule_item_update_api.feature",
    "features/schedules_list_api.feature",
    "features/user_schedule_items_list_api.feature",
)
