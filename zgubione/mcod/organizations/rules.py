import rules

from mcod.lib.rules import assigned_to_organization

rules.add_perm("organizations", rules.always_allow)
rules.add_perm("organizations.add_organization", rules.is_superuser)
rules.add_perm("organizations.view_organization", assigned_to_organization)
rules.add_perm("organizations.change_organization", assigned_to_organization)
# #rules.add_perm('organizations.delete_organization', is_in_organization)
