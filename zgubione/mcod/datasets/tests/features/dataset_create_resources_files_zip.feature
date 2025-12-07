Feature: Create archive containing resources files

  Scenario: Archive contains files of published resources
    Given dataset with id 1999 and 2 resources
    Then Dataset with id 1999 has archive containing 2 files


  Scenario: Setting status to draft removes resource's file from dataset's archive
    Given dataset with id 1998
    And resource with id 998 and dataset_id is 1998
    Then set status to draft on resource with id 998
    And Dataset with id 1998 has no archive assigned

  Scenario: Deleting resource removes resource's file from dataset's archive
    Given dataset with id 1997
    And resource with id 991 and dataset_id is 1997
    Then remove resource with id 991
    And Dataset with id 1997 has no archive assigned

  Scenario: Restoring resource adds file to dataset's archive
    Given dataset with id 1001
    And resource with id 1000 and dataset_id is 1001
    Then remove resource with id 1000
    And restore resource with id 1000
    And Dataset with id 1001 has archive containing 1 files

  Scenario: Republishing resource adds file to dataset's archive
    Given dataset with id 1002
    And resource with id 1001 and dataset_id is 1002
    Then set status to draft on resource with id 1001
    And set status to published on resource with id 1001
    And Dataset with id 1002 has archive containing 1 files

  Scenario: Archive of dataset and resource with very long title and special chars is created
    Given dataset with id 2000 and title is  vvvvvvvvvvvvvvvvvvvvvvveeeeeeeeeeerrrrrrrrrrrrrrrrrrryyyyyyyyyyyyyyyyyyyyyzażółć gęślą jaźń\\_/loooooonnnnnnnnnngggggggggggggg \ĘÓĄŚŁŻŹĆŃdddddddaaatttaaassseeeettt_ttttttttttttttiiiiiiiiiiittttttttttttttttttttttttttttttttttlllllllllllllllllleeeeeeeeeeeeeeeeeeee <>?:;'!@#$%^&*()-+
    And resource with id 1002 and dataset_id is 2000 and title is vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvveeeeeeeeeeerrrrrrrrrrrrrrrryyyyyyyyyyyyyyyyyyzażółć gęślą jaźń\_/loooooonnnnnnnnngggggggggggggŚĆŹŻŁÓ_<>?:;'!@#$%^&*()-+reeeesssssoooouuuurrrcccccceeeeeee_ttttttttttttttiiiiiiiiiiiiiiiiiiitttttttttttttttttttttttttllllllllllllleeeeeeeeeeeeeeeeee_.csv
    Then Dataset with id 2000 has archive containing 1 files
    And Dataset with id 2000 has zip with trimmed file names and no special characters

  Scenario: Switching resource datasets updates dataset's archive
    Given dataset with id 1998
    And dataset with id 2001
    And resource with id 998 and dataset_id is 1998
    Then set dataset_id to 2001 on resource with id 998
    And Dataset with id 1998 has no archive assigned
    And Dataset with id 2001 has archive containing 1 files
