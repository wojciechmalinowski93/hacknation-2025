import rules

rules.add_perm("tags", rules.always_allow)
rules.add_perm("tags.add_tag", rules.is_staff)
rules.add_perm("tags.view_tag", rules.always_allow)
rules.add_perm("tags.change_tag", rules.is_staff)
