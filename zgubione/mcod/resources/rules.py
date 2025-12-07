import rules

from mcod.lib.rules import assigned_to_organization, users_is_editor

rules.add_perm("resources", rules.always_allow)
rules.add_perm("resources.add_resource", assigned_to_organization)
rules.add_perm("resources.view_resource", assigned_to_organization)
rules.add_perm("resources.change_resource", assigned_to_organization)
rules.add_perm("resources.delete_resource", users_is_editor)

rules.add_perm("resources.add_chart", assigned_to_organization)
rules.add_perm("resources.view_chart", rules.always_allow)
rules.add_perm("resources.change_chart", assigned_to_organization)
rules.add_perm("resources.delete_chart", users_is_editor)


rules.add_perm("resources.view_resourcetrash", users_is_editor)
rules.add_perm("resources.change_resourcetrash", users_is_editor)

rules.add_perm("resources.add_supplement", assigned_to_organization)
rules.add_perm("resources.view_supplement", assigned_to_organization)
rules.add_perm("resources.change_supplement", assigned_to_organization)
rules.add_perm("resources.delete_supplement", users_is_editor)
