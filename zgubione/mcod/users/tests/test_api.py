from pytest_bdd import scenarios

scenarios(
    "features/account.feature",
    "features/change_password.feature",
    "features/login.feature",
    "features/logout.feature",
    "features/registration.feature",
    "features/resend_activation_email.feature",
    "features/reset_password.feature",
    "features/reset_password_confirm.feature",
    "features/dashboard.feature",
    "features/meetings_api.feature",
    "features/dashboard_schedules.feature",
)
