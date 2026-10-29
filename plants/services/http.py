import requests

# Some APIs block requests that don't say who they are. Wikipedia also wants a way to contact us (the repo link).
USER_AGENT = "GrowYourGarden/1.0 (PBP student project, Universitas Indonesia; https://github.com/WilliamJesUI/Group-1-KKI)"
# requests waits forever by default. A slow API would freeze the page, so we give up after 8 seconds.
TIMEOUT_SECONDS = 8


class ApiError(Exception):
    """Any problem talking to an outside API: no key, timeout, bad status, or broken JSON."""


def get_json(url, params=None):
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        # Only the error type: the full message contains our URL, and the URL contains the token
        raise ApiError(type(error).__name__) from error