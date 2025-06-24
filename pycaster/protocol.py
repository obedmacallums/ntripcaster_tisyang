"""Helpers to parse minimal NTRIP requests."""


def parse_request(data):
    """Parse raw bytes from a newly connected agent."""
    text = data.decode('utf-8', 'ignore') if isinstance(data, (bytes, bytearray)) else str(data)
    lines = text.splitlines()
    if not lines:
        return None

    first = lines[0]
    headers = {k.lower(): v.strip() for k, _, v in (line.partition(':') for line in lines[1:]) if k}

    if first.startswith('GET'):
        parts = first.split()
        if len(parts) < 2:
            return None
        mount = parts[1].lstrip('/')
        return {
            'type': 'client',
            'mountpoint': mount,
            'auth': headers.get('authorization', ''),
            'user_agent': headers.get('user-agent', '')
        }

    if first.startswith('SOURCE'):
        parts = first.split()
        if len(parts) < 3:
            return None
        passwd = parts[1]
        mount = parts[2].lstrip('/')
        return {
            'type': 'source',
            'mountpoint': mount,
            'passwd': passwd,
            'user_agent': headers.get('source-agent', '')
        }

    return None
