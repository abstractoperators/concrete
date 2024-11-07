try:
    import requests
    from requests.adapters import HTTPAdapter, Retry
except ImportError as e:
    raise ImportError("Install requests to use HTTPClient.") from e

from concrete.clients import Client


class HTTPClient(Client, requests.Session):
    """
    Set up requests.session to access
    """

    def __new__(*args, **kwargs):

        return super().__new__(*args, **kwargs)

    def __init__(self):
        # Setup retry logic for restful web http requests
        super().__init__()
        jitter_retry = Retry(
            total=5,
            backoff_factor=0.1,
            backoff_jitter=1.25,
            status_forcelist=[400, 403, 404, 500, 502, 503, 504],
            raise_on_status=False,
        )
        self.mount("http://", HTTPAdapter(max_retries=jitter_retry))
        self.mount("https://", HTTPAdapter(max_retries=jitter_retry))
