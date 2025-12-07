import rules

rules.add_perm("users", rules.always_allow)
rules.add_perm("users.add_user", rules.is_superuser)
rules.add_perm("users.view_user", rules.is_superuser)
rules.add_perm("users.change_user", rules.is_staff)
