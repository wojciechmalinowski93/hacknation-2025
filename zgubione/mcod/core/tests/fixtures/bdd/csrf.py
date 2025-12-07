import random
from string import ascii_letters, digits

import pytest
from pytest_bdd import given, parsers, then, when

from mcod.core.csrf import salt_cipher_secret, unsalt_cipher_token

allowed_alphabet = ascii_letters + digits


@pytest.fixture
def random_string():
    return "".join([random.choice(allowed_alphabet) for _ in range(32)])


@given("a random cipher secret")
def a_random_cipher_secret(random_string):
    return random_string


@when(parsers.parse("the string has length {length:d}"))
def has_length(random_string, length):
    assert len(random_string) == length


@when("the string is alphanumeric")
def is_alphanumeric(random_string):
    assert set(random_string).issubset(set(allowed_alphabet))


@then("salting and unsalting the string is mutually opposite")
def salt_unsalt_is_opposite(random_string):
    assert random_string == unsalt_cipher_token(salt_cipher_secret(random_string))


@pytest.fixture
def salted_secret(random_string):
    return salt_cipher_secret(random_string)


@given("the salted secret")
def the_salted_secret(salted_secret):
    return salted_secret


@when(parsers.parse("the token is of length {length:d}"))
def token_is_of_length(salted_secret, length):
    assert len(salted_secret) == length


@then("unsalting the token results in the original cipher secret")
def unsalting_result_check(random_string, salted_secret):
    assert unsalt_cipher_token(salted_secret) == random_string
