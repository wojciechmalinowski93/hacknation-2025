from uuid import uuid4


def make_activation_code():
    """Generate a unique activation code."""
    return str(uuid4())
