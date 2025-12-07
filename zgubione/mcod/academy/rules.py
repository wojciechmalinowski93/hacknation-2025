import rules

from mcod.lib.rules import is_logged_academy_or_labs_admin

rules.add_perm("is_logged_academy_or_labs_admin", is_logged_academy_or_labs_admin)
