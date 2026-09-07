from urllib.parse import urlsplit, urlunsplit


def normalize_monitor_url(url: str) -> str:
    raw_url = str(url).strip()
    parsed = urlsplit(raw_url)

    if not parsed.scheme or not parsed.netloc:
        return raw_url

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo = f"{userinfo}:{parsed.password}"
        userinfo = f"{userinfo}@"

    include_port = port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    )
    netloc = f"{userinfo}{hostname}"
    if include_port:
        netloc = f"{netloc}:{port}"

    path = parsed.path or "/"

    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def get_monitor_name(url: str) -> str:
    parsed = urlsplit(normalize_monitor_url(url))
    return parsed.netloc or parsed.path or str(url)
