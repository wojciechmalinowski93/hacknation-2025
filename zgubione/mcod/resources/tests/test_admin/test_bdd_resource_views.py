from pytest_bdd import scenarios

scenarios(
    "../features/resource_creation.feature",
    "../features/resource_change.feature",
    "../features/resource_delete.feature",
    "../features/resource_validation.feature",
    "../features/resource_details_admin.feature",
    "../features/resources_list_admin.feature",
)
