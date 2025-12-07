@elasticsearch
Feature: Course details page in admin panel

  Scenario: Course change page is not visible for NOT academy admin
    Given course created with params {"id": 999, "title": "Course with id: 999"}
    And admin's request logged user is active user
    When admin's page /academy/course/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zaloguj się

  Scenario: Course change page is visible for academy admin
    Given admin's request logged user is academy admin
    And course created with params {"id": 999, "title": "Testowy kurs 999"}
    When admin's page /academy/course/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Testowy kurs 999

  Scenario: Course creation is ok
    When admin's request method is POST
    And admin's request posted course data is {"title": "test", "notes": "Opis...", "participants_number": 10, "venue": "Królewska 27", "status": "published", "modules-0-start": "2020-07-01", "modules-0-number_of_days": "2", "modules-0-type": "general"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test</a>" został pomyślnie dodany.
    And academy.Course with title test contains data {"notes": "Opis...", "venue": "Królewska 27", "participants_number": 10, "start": "2020-07-01", "end": "2020-07-02"}

  Scenario: Course related session type is required
    When admin's request method is POST
    And admin's request posted course data is {"title": "kurs z sesją bez typu", "notes": "Opis...", "participants_number": 10, "venue": "Królewska 27", "status": "published", "modules-0-start": "2020-07-01", "modules-0-number_of_days": "2", "modules-0-type": ""}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains <ul class="errorlist"><li>To pole jest obowiązkowe.</li>

  Scenario: Course creation fails without at least 1 session added
    When admin's request method is POST
    And admin's request posted course data is {"title": "test", "notes": "Opis...", "participants_number": "10", "venue": "Królewska 27", "status": "published"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Proszę, popraw poniższy błąd.
    And admin's response page contains <ul class="errorlist"><li>Kurs musi zawierać przynajmniej 1 sesję.</li></ul>

  Scenario: Course creation fails without title in form
    When admin's request method is POST
    And admin's request posted course data is {"title": "", "notes": "Opis...", "participants_number": "10", "status": "published"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Proszę, popraw poniższe błędy.
    And admin's response page contains <input type="text" name="title" class="span12" maxlength="300" required id="id_title"><span class="help-inline"><ul class="errorlist"><li>To pole jest obowiązkowe.

  Scenario: Course creation fails without number of participants in form
    Given admin's request logged user is academy admin
    When admin's request method is POST
    And admin's request posted course data is {"title": "Kurs testowy", "notes": "Opis...", "participants_number": "", "venue": "Królewska 27", "status": "published"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Proszę, popraw poniższe błędy.
    And admin's response page contains required id="id_participants_number"><span class="help-inline"><ul class="errorlist"><li>To pole jest obowiązkowe.</li></ul>

  Scenario: Course creation fails without venue in form
    Given admin's request logged user is academy admin
    When admin's request method is POST
    And admin's request posted course data is {"title": "Kurs testowy", "notes": "Opis...", "participants_number": "10", "venue": "", "status": "published"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Proszę, popraw poniższe błędy.
    And admin's response page contains required id="id_venue"><span class="help-inline"><ul class="errorlist"><li>To pole jest obowiązkowe.</li></ul>

  Scenario: Course creation fails without description in form
    Given admin's request logged user is academy admin
    When admin's request method is POST
    And admin's request posted course data is {"title": "Kurs testowy", "notes": "", "participants_number": "10", "venue": "Królewska 27", "status": "published"}
    And admin's page /academy/course/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Proszę, popraw poniższe błędy.
    And admin's response page contains <div class="inline error errors"><textarea name="notes" cols="40" rows="2" class="span12" required id="id_notes"></textarea><script type="text/javascript">Suit.$('#id_notes').autosize();</script><span class="help-inline"><ul class="errorlist"><li>To pole jest obowiązkowe.</li></ul></span></div>
