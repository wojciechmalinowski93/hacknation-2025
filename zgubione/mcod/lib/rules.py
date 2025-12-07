import rules


@rules.predicate
def assigned_to_organization(current_user):
    if not current_user or current_user.is_anonymous:
        return False
    return bool(current_user.organizations.all())


@rules.predicate
def is_logged_academy_or_labs_admin(current_user):
    if not current_user or current_user.is_anonymous:
        return False
    return bool(current_user.is_academy_admin or current_user.is_labs_admin)


@rules.predicate
def users_is_editor(current_user):
    return current_user.is_staff
