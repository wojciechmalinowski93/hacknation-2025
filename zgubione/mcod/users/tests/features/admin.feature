Feature: User Admin
  Scenario: Admin can change user to be a superuser with post method
    Given active user for data {"id": 987, "email": "ActiveTestUser2Admin@dane.gov.pl", "password": "12345.Abcde"}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser2Admin@dane.gov.pl", "is_superuser": true, "state": "active"}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.

  Scenario: Admin cannot add user for existing email address (case insensitive validation)
    Given active user for data {"id": 987, "email": "ActiveTestUser@dane.gov.pl", "password": "12345.Abcde"}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ACTIVETESTUSER@DANE.GOV.PL", "is_superuser": true, "state": "active"}
    And admin's page /users/user/add/ is requested
    Then admin's response page contains <ul class="errorlist"><li>Konto powiązane z tym adresem email już istnieje</li></ul>

  Scenario: User email is saved with small letters
    Given logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "RTEST2@WP.PL", "password1": "123", "password2": "123", "fullname": "R K", "is_staff": true, "state": "pending", "is_academy_admin": false, "is_labs_admin": false}
    And admin's page /users/user/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains >rtest2@wp.pl</a>" został pomyślnie dodany. Poniżej możesz ponownie edytować.

  Scenario: Admin can create user related to institution
    Given institution with id 999
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "rtest1@wp.pl", "password1": "123", "password2": "123", "fullname": "R K", "is_staff": true, "state": "pending", "organizations": [999], "is_academy_admin": false, "is_labs_admin": false}
    And admin's page /users/user/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie dodany.
    And user with email rtest1@wp.pl is related to institution with id 999

  Scenario: User changed to superuser is automatically set as staff
    Given active user for data {"id": 987, "email": "ActiveTestUser2Admin@dane.gov.pl", "password": "12345.Abcde", "is_superuser": false, "is_staff": false}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser2Admin@dane.gov.pl", "is_superuser": true, "state": "active"}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.
    And user with id 987 attribute is_superuser is True
    And user with id 987 attribute is_staff is True

  Scenario: User changed to academy admin is automatically set as staff
    Given active user for data {"id": 987, "email": "ActiveTestUser2Admin@dane.gov.pl", "password": "12345.Abcde", "is_staff": false}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser2Admin@dane.gov.pl", "is_academy_admin": true, "state": "active"}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.
    And user with id 987 attribute is_academy_admin is True
    And user with id 987 attribute is_staff is True

  Scenario: User changed to laboratory admin is automatically set as staff
    Given active user for data {"id": 987, "email": "ActiveTestUser2Admin@dane.gov.pl", "password": "12345.Abcde", "is_staff": false}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser2Admin@dane.gov.pl", "is_labs_admin": true, "state": "active"}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.
    And user with id 987 attribute is_labs_admin is True
    And user with id 987 attribute is_staff is True

  Scenario Outline: User with non-active state cannot login to admin panel.
    Given logged <object_type> for data <user_data>
    When admin's request method is POST
    And admin's request posted <data_type> data is <req_post_data>
    And admin's page /login/ is requested
    Then admin's response page contains <contained_value>
    Examples:
    | object_type      | req_post_data                                           | user_data                                                                  | data_type | contained_value                                                  |
    # normal users
    | blocked user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1"}                       | user      | Ten użytkownik jest zablokowany, skontaktuj się z administracją. |
    | pending user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1"}                       | user      | Musisz najpierw potwierdzić swój adres email.                    |
    | inactive user    | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1"}                       | user      | Brak uprawnień do panelu administratora.                         |
    | unconfirmed user | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1"}                       | user      | Brak uprawnień do panelu administratora.                         |

    # staff users (so called editors)
    | blocked user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_staff": true}     | user      | Ten użytkownik jest zablokowany, skontaktuj się z administracją. |
    | pending user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_staff": true}     | user      | Musisz najpierw potwierdzić swój adres email.                    |
    | inactive user    | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_staff": true}     | user      | Brak uprawnień do panelu administratora.                         |
    | unconfirmed user | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_staff": true}     | user      | Brak uprawnień do panelu administratora.                         |

    # superusers
    | blocked user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_superuser": true} | user      | Ten użytkownik jest zablokowany, skontaktuj się z administracją. |
    | pending user     | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_superuser": true} | user      | Musisz najpierw potwierdzić swój adres email.                    |
    | inactive user    | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_superuser": true} | user      | Brak uprawnień do panelu administratora.                         |
    | unconfirmed user | {"username": "x@example.com", "password": "Britenet.1"} | {"email": "x@example.com", "password": "Britenet.1", "is_superuser": true} | user      | Brak uprawnień do panelu administratora.                         |

  Scenario: User can be set as agent by setting new agent institutions
    Given active user for data {"id": 987, "email": "ActiveTestUser1Admin@dane.gov.pl", "password": "12345.Abcde", "is_staff": true, "is_agent": false}
    And institution with id 999
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser1Admin@dane.gov.pl", "is_agent": true, "is_agent_opts": "new", "agent_organization_main": 999, "agent_organizations": [999]}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.
    And user with id 987 attribute is_agent is True

    Scenario: Test that passing agent organizations for agent is obligatory
    Given active user for data {"id": 987, "email": "ActiveTestUser1Admin@dane.gov.pl", "password": "12345.Abcde", "is_staff": true, "is_agent": false}
    And institution with id 999
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser1Admin@dane.gov.pl", "is_agent": true, "is_agent_opts": "new", "agent_organization_main": 999, "agent_organizations": []}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybór organizacji dla pełnomocnika jest obligatoryjny!

  Scenario: User can be set as agent with data copied from another agent
    Given active user for data {"id": 987, "email": "ActiveTestUser1Admin@dane.gov.pl", "password": "12345.Abcde", "is_staff": true, "is_agent": false}
    And institution with id 999
    And logged out agent user created with {"id": 986}
    And logged admin user
    When admin's request method is POST
    And admin's request posted user data is {"email": "ActiveTestUser1Admin@dane.gov.pl", "is_agent": true, "is_agent_opts": "from_agent", "from_agent": 986}
    And admin's page /users/user/987/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains został pomyślnie zmieniony.
    And user with id 987 attribute is_agent is True

  Scenario: Send registration mail link is displayed in pending user form for admin
    Given pending user for data {"id": 999, "email": "SendRegistrationMailUser@dane.gov.pl", "password": "12345.Abcde"}
    When admin's page /users/user/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wyślij ponownie link do aktywacji konta

  Scenario: Send registration mail link is not displayed in active user form for admin
    Given active user for data {"id": 999, "email": "SendRegistrationMailUser@dane.gov.pl", "password": "12345.Abcde"}
    When admin's page /users/user/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page not contains Wyślij ponownie link do aktywacji konta

  Scenario: Send registration mail link works properly for admin
    Given pending user for data {"id": 999, "email": "SendRegistrationMailUser@dane.gov.pl", "password": "12345.Abcde"}
    When admin's page /users/user/999/send_registration_email/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zadanie wysyłki wiadomości email z linkiem do aktywacji konta zostało zlecone.

  Scenario: Send registration mail link is not working for non admin
    Given pending user for data {"id": 999, "email": "SendRegistrationMailUser@dane.gov.pl", "password": "12345.Abcde"}
    And admin's request logged user is editor user
    When admin's page /users/user/999/send_registration_email/ is requested
    Then admin's response status code is 403

  Scenario: Send registration mail link is not working if invalid id is used (99999)
    Given pending user for data {"id": 999, "email": "SendRegistrationMailUser@dane.gov.pl", "password": "12345.Abcde"}
    When admin's page /users/user/99999/send_registration_email/ is requested
    Then admin's response status code is 404
