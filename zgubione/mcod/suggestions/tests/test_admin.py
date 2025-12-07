from pytest_bdd import scenarios

scenarios(
    "features/admin/accepteddatasetsubmission_list.feature",
    "features/admin/datasetcomment_list.feature",
    "features/admin/datasetsubmission_list.feature",
    "features/admin/resourcecomment_list.feature",
)
