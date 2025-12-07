Feature: Task results
  Scenario: Test data task result is displayed properly
    Given task result created with params {"id": 999, "status": "FAILURE", "result": {"exc_type": "WorkerLostError", "exc_message": ["Worker exited prematurely: signal 9 (SIGKILL) Job: 34478."], "exc_module": "billiard.exceptions"}}
    Then resources.TaskResult with id 999 contains data {"message": ["Nierozpoznany błąd walidacji"], "recommendation": ["Skontaktuj się z administratorem systemu."]}
