@elasticsearch
Feature: Organization details page in admin panel
  Scenario: Organization created without translation fields have i18n field empty
    When admin's request method is POST
    And admin's request posted institution data is {"title": "POLSKI TYTUŁ 1", "description": "POLSKI OPIS 1", "slug": "polski-tytul-1"}
    And 'mcod.organizations.admin.OrganizationAdmin' creation page is requested
    Then admin's response status code is 200
    And 'i18n' field of created object is '{}'
    Then set language to 'en'
    And check if queryset.values match '{"title_i18n": "POLSKI TYTUŁ 1", "description_i18n": "POLSKI OPIS 1", "slug_i18n": "polski-tytul-1"}'

  Scenario: Organization created with translation fields have i18n field filled properly
    When admin's request method is POST
    And admin's request posted institution data is {"title": "POLSKI TYTUŁ 2", "description": "POLSKI OPIS 2", "slug": "polski-tytul-2", "title_en": "ENGLISH TITLE 2", "description_en": "ENGLISH DESCRIPTION 2", "slug_en": "english-title-2"}
    And 'mcod.organizations.admin.OrganizationAdmin' creation page is requested
    Then admin's response status code is 200
    And 'i18n' field of created object is '{"title_en": "ENGLISH TITLE 2", "slug_en": "english-title-2", "description_en": "ENGLISH DESCRIPTION 2"}'
    Then set language to 'en'
    And check if queryset.values match '{"title_i18n": "ENGLISH TITLE 2", "slug_i18n": "english-title-2", "description_i18n": "ENGLISH DESCRIPTION 2"}'

  Scenario: Organization creation is ok when already existing slug is used
    Given institution created with params {"id": 999, "slug": "test-institution-slug"}
    When admin's request method is POST
    And admin's request posted institution data is {"title": "Test dodania instytucji z istniejącym slugiem", "slug": "test-institution-slug"}
    And admin's page /organizations/organization/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Test dodania instytucji z istniejącym slugiem</a>" został pomyślnie dodany.

  Scenario: Organization creation is ok even if abbreviation is empty
    Given institution created with params {"id": 999, "slug": "test-institution-slug"}
    When admin's request method is POST
    And admin's request posted institution data is {"title": "Test dodania instytucji bez skrótu", "abbreviation": ""}
    And admin's page /organizations/organization/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Test dodania instytucji bez skrótu</a>" został pomyślnie dodany.

  Scenario: Organization creation is ok for very long organization title - 110 chars
    When admin's request method is POST
    And admin's request posted institution data is {"title": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"}
    And admin's page /organizations/organization/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</a>" został pomyślnie dodany.

  Scenario: Organization creation returns error when no tag in related dataset
    When admin's request method is POST
    And admin's request posted institution data is {"title": "Test dodania instytucji ze zbiorem bez tagów", "datasets-2-TOTAL_FORMS": "1"}
    And admin's page /organizations/organization/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains <label class="required" for="id_datasets-2-0-tags_pl">Słowa kluczowe (PL):<span>(pole wymagane)</span></label></div><div class="controls"><div class="inline error errors">

  Scenario: Dataset title on inline list redirects to dataset admin edit page
    Given dataset with id 998 and title Title as link ds and institution 999
    When admin's page /organizations/organization/999/change/#datasets is requested
    Then admin's response page contains <a href="/datasets/dataset/998/change/">Title as link ds</a>

  Scenario: Organization creation with related datasets at once
    Given admin's request logged admin user created with params {"id": 999}
    And category with id 999
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted institution data is {"institution_type": "local", "title": "Miasto Brańsk","slug": "miasto-bransk","status": "published","description": "","abbreviation": "MB","image": "","postal_code": "17-120","city": "Brańsk","street_type": "ul","street": "Rynek","street_number": "1","flat_number": "1","email": "admin@bransk.eu","tel": "123123123","fax": "123123123","epuap": "123123123","regon": "123456785","website": "http://bransk.eu","datasets-TOTAL_FORMS": "0","datasets-INITIAL_FORMS": "0","datasets-MIN_NUM_FORMS": "0","datasets-MAX_NUM_FORMS": "0","datasets-2-TOTAL_FORMS": "1","datasets-2-INITIAL_FORMS": "0","datasets-2-MIN_NUM_FORMS": "0","datasets-2-MAX_NUM_FORMS": "1000","datasets-2-0-title": "test","datasets-2-0-notes": "<p>more than 20 characters</p>","datasets-2-0-url": "","json_key[datasets-2-0-customfields]": "key","json_value[datasets-2-0-customfields]": "value","datasets-2-0-update_frequency": "weekly",  "datasets-2-0-update_notification_recipient_email": "test@test.com", "datasets-2-0-category": "", "datasets-2-0-categories": [999], "datasets-2-0-status": "published","datasets-2-0-license_condition_responsibilities": "","datasets-2-0-license_condition_db_or_copyrighted": "","datasets-2-0-license_condition_personal_data": "","datasets-2-0-id": "","datasets-2-0-organization": "","datasets-2-0-tags_pl": [999]}
    And admin's page /organizations/organization/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Miasto Brańsk</a>" został pomyślnie dodany.
