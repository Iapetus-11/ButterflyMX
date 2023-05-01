from urllib.parse import parse_qs, urlparse


def get_query_params(url: str) -> dict[str, str | list[str]]:
    return {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(urlparse(url).query).items()}
