@elasticsearch
Feature: Showcase details admin
  Scenario: Showcase creation with auto slug
    When admin's request method is POST
    And admin's request posted showcase data is {"title": "Test with showcase title", "slug": "test-with-showcase-title"}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test with showcase title</a>" zostało pomyślnie dodane.
    And latest showcase attribute slug is test-with-showcase-title

  Scenario: Showcase slug is automatically created from title if needed
    When admin's request method is POST
    And admin's request posted showcase data is {"title": "Test with showcase title", "slug": ""}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test with showcase title</a>" zostało pomyślnie dodane.
    And latest showcase attribute slug is test-with-showcase-title

  Scenario: Showcase creation with manual slug
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted showcase data is {"title": "Test with showcase title", "slug": "manual-name", "category": "other", "datasets": [999], "external_datasets": [{"url": "https://example.com", "title": "test"}]}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test with showcase title</a>" zostało pomyślnie dodane.
    And latest showcase attribute slug is manual-name

  Scenario: Showcase creation requires license_type if category is app or www
    When admin's request method is POST
    And admin's request posted showcase data is {"title": "Test showcase without license_type", "category": "app", "license_type": ""}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response page contains To pole jest obowiązkowe!

  Scenario: Showcase creation requires at least one url for mobile app
    When admin's request method is POST
    And admin's request posted showcase data is {"is_mobile_app": true, "mobile_apple_url": "", "mobile_google_url": ""}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response page contains Co najmniej jeden link do aplikacji mobilnej (iOS, Android) jest wymagany!

  Scenario: Showcase creation requires at least one url for desktop app
    When admin's request method is POST
    And admin's request posted showcase data is {"is_desktop_app": true, "desktop_windows_url": "", "desktop_linux_url": "", "desktop_macos_url": ""}
    And admin's page /showcases/showcase/add/ is requested
    Then admin's response page contains Co najmniej jeden link do aplikacji desktopowej (Windows, Linux, MacOS) jest wymagany!

  Scenario: Showcase details
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Test showcase details", "datasets": [999], "category": "app"}
    When admin's page /showcases/showcase/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Test showcase details

 Scenario: Showcase trash details
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Test showcase trash", "datasets": [999], "category": "app", "is_removed": true, "is_mobile_app": true, "mobile_apple_url": "https://google.pl"}
    When admin's page /showcases/showcasetrash/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Test showcase trash

  Scenario: Showcase is not visible in API after adding to trash
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Test showcase", "datasets": [999], "main_page_position": 1}
    When admin's request method is POST
    And admin's request posted showcase data is {"post": "yes"}
    And admin's page /showcases/showcase/999/delete/ is requested
    Then admin's response status code is 200
    And admin's response page contains Ponowne wykorzystanie &quot;Test showcase&quot; usunięte pomyślnie.
    And api request path is /showcases/?id=999
    And send api request and fetch the response
    And api's response body field meta/count is 0
    And api request path is /showcases/999/datasets
    And send api request and fetch the response
    And api's response body field meta/count is 0

  Scenario: Showcase is visible in API after removing from trash
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Test showcase in trash", "is_removed": true, "datasets": [999]}
    When admin's request method is POST
    And admin's request posted showcase data is {"is_removed": false}
    And admin's page /showcases/showcasetrash/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test showcase in trash</a>" został pomyślnie zmieniony.
    And api request path is /showcases/?id=999
    And send api request and fetch the response
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/relationships/datasets/meta/count is 1
    And api request path is /showcases/999/datasets
    And send api request and fetch the response
    And api's response body field data/[0]/id is 999
    And api's response body field meta/count is 1
