import base64
import hashlib
from collections import OrderedDict

from django.contrib.auth.hashers import PBKDF2PasswordHasher, mask_hash
from django.utils.crypto import get_random_string, pbkdf2
from django.utils.translation import gettext_noop as _
from passlib.hash import pbkdf2_sha512


class PBKDF2SHA512PasswordHasher(PBKDF2PasswordHasher):
    """
    Alternate PBKDF2 hasher which uses SHA512 instead of SHA256.
    Note: As of Django 1.4.3, django.contrib.auth.models.User defines password
    with max_length=128
    Our superclass (PBKDF2PasswordHasher) generates the entry for that field
    using the following format (see
    https://github.com/django/django/blob/1.4.3/django/contrib/auth/hashers.py#L187):
        "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)
    The lengths of the various bits in that format are:
     13  self.algorithm ("pbkdf2_sha512")
      5  iterations ("10000" - inherited from superclass)
     12  salt (generated using django.utils.crypto.get_random_string())
     89  hash (see below)
      3  length of the three '$' separators
    ---
    122  TOTAL
    122 <= 128, so we're all good.
    NOTES
    hash is the base-64 encoded output of django.utils.crypto.pbkdf2(password, salt,
    iterations, digest=hashlib.sha512), which is 89 characters according to my tests.
        >>> import hashlib
        >>> from django.utils.crypto import pbkdf2
        >>> len(pbkdf2('t0ps3kr1t', 'saltsaltsalt', 10000, 0, hashlib.sha512).encode('base64').strip())
        89
    It's feasible that future versions of Django will increase the number of iterations
    (but we only lose one character per power-of-ten increase), or the salt length. That
    will cause problems if it leads to a password string longer than 128 characters, but
    let's worry about that when it happens.
    """

    iterations = 19000
    algorithm = "pbkdf2-sha512"
    digest = hashlib.sha512

    def salt(self):
        return get_random_string(22)

    def encode(self, password, salt, iterations=None):
        assert password is not None
        assert salt and "$" not in salt
        if not iterations:
            iterations = self.iterations
        hash = pbkdf2(password, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode("ascii").strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)

    def verify(self, password, encoded):
        x = encoded.replace("pbkdf2-sha512", "$pbkdf2-sha512")
        return pbkdf2_sha512.verify(password, x)

    def safe_summary(self, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        assert algorithm == self.algorithm
        return OrderedDict(
            [
                (_("algorithm"), algorithm),
                (_("iterations"), iterations),
                (_("salt"), mask_hash(salt)),
                (_("hash"), mask_hash(hash)),
            ]
        )

    def must_update(self, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        return int(iterations) != self.iterations

    def harden_runtime(self, password, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        extra_iterations = self.iterations - int(iterations)
        if extra_iterations > 0:
            self.encode(password, salt, extra_iterations)
