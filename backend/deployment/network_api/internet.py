"""Bounded internet checks for online dependency preparation."""

import requests


def has_internet_access() -> bool:
    """Check public HTTPS services; LAN reachability alone is insufficient.

    One reachable service permits a dependency-install attempt. It does not
    guarantee that every package registry needed by the build is available.
    """
    probes = (
        ("https://pypi.org/", 200),
        ("https://registry-1.docker.io/v2/", 401),
    )
    for url, expected_status in probes:
        try:
            with requests.head(url, timeout=(2, 3), allow_redirects=False) as response:
                if response.status_code == expected_status:
                    return True
        except requests.RequestException:
            continue
    return False
