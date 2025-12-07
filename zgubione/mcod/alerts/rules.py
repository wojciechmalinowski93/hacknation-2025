import rules

rules.add_perm("alerts.add_alert", rules.is_superuser)
rules.add_perm("alerts.view_alert", rules.is_superuser)
rules.add_perm("alerts.change_alert", rules.is_superuser)
rules.add_perm("alerts.delete_alert", rules.is_superuser)
