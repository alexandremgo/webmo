from urllib.parse import urlparse

CORRECT_SCHEMES = ["http", "https"]


# get a correct url for the requests library
def clean_url(url):
    # parse the url
    parsed_url = urlparse(url)

    # if an http or https is given it will keep it. Otherwise
    scheme = parsed_url.scheme if parsed_url.scheme in CORRECT_SCHEMES else "http"

    # netloc: the domain name of the url
    # path: the path just after the domain name
    return scheme + "://" + parsed_url.netloc + parsed_url.path