import json

from django.core import mail
from django.test import Client as DjangoClient
from pytest_bdd import given, parsers, then

from mcod.core.caches import flush_sessions
from mcod.core.registries import factories_registry
from mcod.newsletter.models import Subscription
from mcod.organizations.models import Organization
from mcod.resources.factories import ResourceFactory
from mcod.users.factories import EditorFactory, MeetingFactory, MeetingFileFactory, UserFactory
from mcod.users.models import User


@given(parsers.parse("{state} user with email {email_address} and password {password}"))
def user_with_state_email_and_password(context, state, email_address, password):
    assert state in ["active", "pending"]
    return UserFactory(
        email=email_address,
        password=password,
        state=state,
    )


@given(parsers.parse("{state} user for data{data_str}"))
def user_for_data(context, state, data_str):
    assert state in ["active", "pending"]
    data = json.loads(data_str)
    data["state"] = state
    return UserFactory(**data)


@given("session is flushed")
def session_is_flushed():
    flush_sessions()


@given(parsers.parse("logged agent user created with {params}"))
def logged_agent_user_created_with_params(context, params):
    _factory = factories_registry.get_factory("agent user")
    kwargs = {
        "email": "agent_user@dane.gov.pl",
        "password": "12345.Abcde",
    }
    kwargs.update(json.loads(params))
    context.user = _factory(**kwargs)
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged out agent user created with {params}"))
def logged_out_agent_user_created_with_params(context, params):
    _factory = factories_registry.get_factory("agent user")
    kwargs = {
        "email": "agent_user@dane.gov.pl",
        "password": "12345.Abcde",
    }
    kwargs.update(json.loads(params))
    context.user = _factory(**kwargs)
    DjangoClient().logout()


@given(parsers.parse("logged extra agent with id {extra_agent_id:d} of agent with id {agent_id:d}"))
def logged_extra_agent_with_id_of_agent_with_id(context, extra_agent_id, agent_id):
    _agent_factory = factories_registry.get_factory("agent user")
    _active_user_factory = factories_registry.get_factory("active user")
    agent = _agent_factory(
        id=agent_id,
        email="agent_user@dane.gov.pl",
        password="12345.Abcde",
    )
    user = _active_user_factory(
        id=extra_agent_id,
        email="extra_agent_user@dane.gov.pl",
        password="12345.Abcde",
    )
    user.extra_agent_of = agent
    user.save()
    context.user = user
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged {user_type}"))
def logged_user_type(context, user_type):
    _factory = factories_registry.get_factory(user_type)
    context.user = _factory(
        email="{}@dane.gov.pl".format(user_type.replace(" ", "_")),
        password="12345.Abcde",
    )
    DjangoClient().force_login(context.user)


@given(parsers.parse("logingovpl {user_type} with email {email} and pesel {pesel}"))
def logingovpl_user_type_with_email_and_pesel(context, user_type, email, pesel):
    """Returns the user with fixed user type, email and pesel, not logged in."""
    _factory = factories_registry.get_factory(user_type)
    return _factory(email=email, pesel=pesel)


@given(parsers.parse("{user_type} linked to logingovpl and logged by form with email {email} and pesel {pesel}"))
def logged_by_form_logingovpl_user_type_with_email_and_pesel(context, user_type, email, pesel):
    """Returns the user with fixed user type, email and pesel, logged in via standard form
    (the field `is_gov_auth` is `False`).
    """
    _factory = factories_registry.get_factory(user_type)
    context.user = _factory(email=email, pesel=pesel, is_gov_auth=False)
    DjangoClient().force_login(context.user)


@given(parsers.parse("{user_type} linked to logingovpl and logged by logingovpl with email {email} and pesel {pesel}"))
def logged_by_logingovpl_logingovpl_user_type_with_email_and_pesel(context, user_type, email, pesel):
    """Returns the user with fixed user type, email and pesel, logged in via the login.gov.pl service
    (the field `is_gov_auth` is `True`).
    """
    _factory = factories_registry.get_factory(user_type)
    context.user = _factory(email=email, pesel=pesel, is_gov_auth=True)
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged active user with email {email} and newsletter subscription enabled with code {activation_code}"))
def logged_active_user_with_newsletter_subscription_enabled(context, email, activation_code):
    user = UserFactory(email=email, password="12345.Abcde", state="active")
    subscription = Subscription.subscribe(email, user=user)
    subscription.activation_code = activation_code
    subscription.confirm_subscription()
    context.user = user
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged active user with email {email_address} and password {password}"))
def logged_active_user_with_email_and_password(context, email_address, password):
    context.user = UserFactory(email=email_address, password=password, state="active")
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged out {state} user with email {email} and password {password}"))
def logged_out_user_with_email_and_password(context, state, email, password):
    context.user = UserFactory(
        email=email,
        password=password,
        state=state,
    )
    DjangoClient().logout()


@given("logged admin user")
def logged_admin(context, admin):
    context.user = admin
    DjangoClient().force_login(context.user)


@given(parsers.parse("logged user is from organization of resource {res_id:d}"))
def logged_user_with_organization(context, res_id):
    resource = ResourceFactory.create(id=res_id)
    context.user.organizations.add(resource.dataset.organization)


@given(parsers.parse("editor with id {editor_id:d} from organization of resource {res_id:d}"))
def user_with_id_with_organization(context, editor_id, res_id):
    resource = ResourceFactory.create(id=res_id)
    editor = EditorFactory.create(id=editor_id)
    editor.organizations.add(resource.dataset.organization)


@then(parsers.parse("logged active user attribute {user_attribute} is {user_attribute_value}"))
def logged_user_attribute_is(context, user_attribute, user_attribute_value):
    user = User.objects.get(id=context.user.id)
    assert str(getattr(user, user_attribute)) == user_attribute_value


@then(parsers.parse("user with id {user_id:d} attribute {user_attribute} is {user_attribute_value}"))
def user_attribute_is(context, user_id, user_attribute, user_attribute_value):
    user = User.objects.get(id=user_id)
    assert str(getattr(user, user_attribute)) == user_attribute_value


@then(parsers.parse("user with email {email} is related to institution with id {organization_id:d}"))
def user_organization_is(context, email, organization_id):
    user = User.objects.get(email=email)
    organization = Organization.objects.get(id=organization_id)
    assert user in organization.users.all()


@then(parsers.parse("sent email contains {text}"))
def sent_email_contains_text(context, text):
    assert len(mail.outbox) == 1
    assert text in mail.outbox[0].body, f'Phrase: "{text}" not found in email content.'


@then(parsers.parse("sent email recipient is {recipient}"))
def sent_mail_recipient_is(context, recipient):
    assert recipient in mail.outbox[0].to


@then(parsers.parse("valid {link_type} link for {email} in mail content"))
def valid_link_for_email_in_mail_content(context, link_type, email):
    assert link_type in ["confirmation", "reset"]
    user = User.objects.get(email=email)
    links = {
        "confirmation": user.email_validation_absolute_url,
        "reset": user.password_reset_absolute_url,
    }
    assert len(mail.outbox) == 1
    assert links[link_type] in mail.outbox[0].body


@then(parsers.parse("password {password} is valid for user {email}"))
def password_is_valid_for_user_email(password, email):
    user = User.objects.get(email=email)
    assert user.check_password(password), f'password "{password}" is not valid for user: {email}'


@given(parsers.parse("logged {object_type} for data {user_data}"))
def generic_user_with_data(object_type, user_data, context, admin_context):
    assert object_type.endswith(" user"), "this keyword is only suited for creating users"
    factory_ = factories_registry.get_factory(object_type)
    if factory_ is None:
        raise ValueError("invalid object type: %s" % object_type)
    user_data = json.loads(user_data)
    user = admin_context.admin.user = context.user = factory_(**user_data)
    DjangoClient().force_login(user)


@given(parsers.parse("meeting with id {meeting_id:d} and {number:d} files"))
def meeting_with_files(meeting_id, number):
    obj = MeetingFactory(id=meeting_id)
    MeetingFileFactory.create_batch(int(number), meeting=obj)
    obj.save()
    return obj
