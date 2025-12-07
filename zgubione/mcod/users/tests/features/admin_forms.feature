Feature: Create new user

  Scenario Outline: User creation form validates properly
    Given UserCreationForm with <posted_data>
    Then form validation equals <expected_validation>

    Examples:
    | posted_data                                                                                                                                                | expected_validation |
    |{"email":"rtest1@test.pl", "password1":"password", "password2":"password", "fullname":"R test", "is_staff":true, "is_superuser":true, "state":"active"}     | true                |
    |{"email":"rtest1@test.pl", "password1":null, "password2":null, "fullname":"R test", "is_staff":true, "is_superuser":true, "state":"active"}                 | false               |
    |{"email":null, "password1":"password", "password2":"password", "fullname":"R test", "is_staff":true, "is_superuser":true, "state":"active"}                 | false               |
    |{"email":"rtest1@test.pl", "password1":"password", "password2":"password", "fullname":"R test", "is_staff":true, "is_superuser":true, "state":null}         | false               |
