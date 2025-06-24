import base64


def prepare_tokens(tokens):
    """Return a dict mapping base64-encoded tokens to mountpoints."""
    result = {}
    for key, mount in tokens.items():
        enc = base64.b64encode(key.encode()).decode()
        result[enc] = mount
    return result


def match_token(tokens, token, mount):
    """Return True if token is valid for mount."""
    mnt = tokens.get(token)
    if mnt is None:
        return False
    return mnt == '*' or mnt.lower() == mount.lower()
