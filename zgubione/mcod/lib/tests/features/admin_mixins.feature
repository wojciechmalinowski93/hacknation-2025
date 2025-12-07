
  Feature: Admin TrashMixin
    Scenario Outline: Objects can be restored from trash
      Given removed <object_type> objects with ids "<object_ids>"
      And logged admin user
      When admin user runs restore action for selected <object_type> objects with ids <requested_object_ids>
      Then admin's response status code is 200
      And <object_type> objects with ids <restored_object_ids> are restored from trash
      And <object_type> objects with ids <unrestored_object_ids> are still in trash

      Examples:
      | object_type      | object_ids  | requested_object_ids | restored_object_ids | unrestored_object_ids |
      | course           | 999,998,997 | 999,998              | 999,998             | 997                   |
      | institution      | 999,998,997 | 999,998              | 999,998             | 997                   |
      | category         | 999,998,997 | 999,998              | 999,998             | 997                   |
      | lab_event        | 999,998,997 | 999,998              | 999,998             | 997                   |
      | guide            | 999,998,997 | 999,998              | 999,998             | 997                   |
      | resource         | 999,998,997 | 999,998              | 999,998             | 997                   |
      | dataset          | 999,998,997 | 999,998              | 999,998             | 997                   |
      | datasource       | 999,998,997 | 999,998              | 999,998             | 997                   |
      | showcase         | 999,998,997 | 999,998              | 999,998             | 997                   |

    Scenario Outline: Objects cant be restored if their related objects are still removed
      Given removed <object_type> objects with ids "<object_ids>"
      And removed <object_type> objects with ids <object_with_related_removed_ids> and removed related <related_object_type> through <relation_name>
      And logged admin user
      When admin user runs restore action for selected <object_type> objects with ids <requested_object_ids>
      Then admin's response status code is 200
      And <object_type> objects with ids <restored_object_ids> are restored from trash
      And <object_type> objects with ids <unrestored_object_ids> are still in trash

      Examples:
      | object_type | object_ids  | object_with_related_removed_ids | related_object_type | relation_name | requested_object_ids | restored_object_ids | unrestored_object_ids |
      | resource    | 999,998,997 | 996                             | dataset             | dataset       | 999,998,996          | 999,998             | 997,996               |
      | dataset     | 999,998,997 | 996                             | institution         | organization  | 999,998,996          | 999,998             | 997,996               |
