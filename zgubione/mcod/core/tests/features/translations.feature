@elasticsearch
Feature: Translations in API

  Scenario Outline: Test translations on list and detail endpoints in API 1.4
    Given translated objects
    When api request path is <request_path>
    And api request language is <lang_code>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field <field> has items <items_str>

    Examples:
    |request_path               | lang_code | field                | items_str                                                           |
    | /1.4/showcases/999        | en        | /data/attributes     | {"title": "title_en", "notes": "notes_en", "slug": "slug_en"}       |
    | /1.4/showcases/999        | pl        | /data/attributes     | {"title": "title_pl", "notes": "notes_pl", "slug": "slug_pl"}       |
    | /1.4/datasets/999         | en        | /data/attributes     | {"title": "title_en", "notes": "notes_en", "slug": "slug_en"}       |
    | /1.4/datasets/999         | pl        | /data/attributes     | {"title": "title_pl", "notes": "notes_pl", "slug": "slug_pl"}       |
    | /1.4/institutions/999     | en        | /data/attributes     | {"title": "title_en", "notes": "description_en", "slug": "slug_en"} |
    | /1.4/institutions/999     | pl        | /data/attributes     | {"title": "title_pl", "notes": "description_pl", "slug": "slug_pl"} |
    | /1.4/resources/999        | en        | /data/attributes     | {"title": "title_en", "description": "description_en"}              |
    | /1.4/resources/999        | pl        | /data/attributes     | {"title": "title_pl", "description": "description_pl"}              |
    | /1.4/showcases/?id=999    | en        | /data/[0]/attributes | {"title": "title_en", "notes": "notes_en", "slug": "slug_en"}       |
    | /1.4/showcases/?id=999    | pl        | /data/[0]/attributes | {"title": "title_pl", "notes": "notes_pl", "slug": "slug_pl"}       |
    | /1.4/datasets/?id=999     | en        | /data/[0]/attributes | {"title": "title_en", "notes": "notes_en", "slug": "slug_en"}       |
    | /1.4/datasets/?id=999     | pl        | /data/[0]/attributes | {"title": "title_pl", "notes": "notes_pl", "slug": "slug_pl"}       |
    | /1.4/institutions/?id=999 | en        | /data/[0]/attributes | {"title": "title_en", "notes": "description_en", "slug": "slug_en"} |
    | /1.4/institutions/?id=999 | pl        | /data/[0]/attributes | {"title": "title_pl", "notes": "description_pl", "slug": "slug_pl"} |
    | /1.4/resources/?id=999    | en        | /data/[0]/attributes | {"title": "title_en", "description": "description_en"}              |
    | /1.4/resources/?id=999    | pl        | /data/[0]/attributes | {"title": "title_pl", "description": "description_pl"}              |
