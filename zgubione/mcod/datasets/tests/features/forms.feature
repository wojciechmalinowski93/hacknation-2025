Feature: Dataset forms

  Scenario: No title
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": null}
    Then form is not valid

  Scenario: Too long title - 301 chars
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"}
    Then form is not valid

  Scenario: No slug
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "no slug", "slug": null}
    Then form is valid
    And form is saved
    And latest dataset attribute title is no slug

  Scenario: Wrong category
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"category": "XXX"}
    Then form is not valid

  Scenario: No status choice
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "no status", "status": null}
    Then form is not valid

  Scenario: Wrong status
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "wrong status", "status": "XXX"}
    Then form is not valid

  Scenario: Wrong app url format
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "wrong app url format", "url": "wrong format"}
    Then form is not valid

  Scenario: Dataset form add tags
    Given tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    And form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "Test add tags", "slug": "test-add-tags", "tags_pl": [999]}
    Then form is valid
    And form is saved
    And latest dataset attribute slug is test-add-tags
    And latest dataset attribute tags_list_as_str is Tag1

  Scenario: Dataset form add categories
    Given category with id 998
    And category created with params {"id": 999, "title": "Kategoria Test"}
    And form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "Test add categories", "slug": "test-add-categories", "categories": [998,999]}
    Then form is valid
    And form is saved
    And latest dataset has categories with ids 998,999

  Scenario: Dataset form add category
    Given category with id 998
    And category created with params {"id": 999, "title": "Kategoria Test", "code": ""}
    And form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "Test add categories", "slug": "test-add-categories", "category": 999, "categories": [998]}
    Then form is valid
    And form is saved
    And latest dataset attribute category_id is 999

  Scenario: Dataset form with image upload
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "Test image upload", "slug": "test-image-upload"}
    And form has image to upload
    Then form is valid

  Scenario: Dataset form promotion if status is draft
    Given form class is mcod.datasets.forms.DatasetForm
    And form dataset data is {"title": "Test dataset is promoted", "slug": "test-dataset-is-promoted", "status": "draft", "is_promoted": "on"}
    Then form field is_promoted error is Tylko opublikowany zbiór danych może być oznaczony jako promowany!
