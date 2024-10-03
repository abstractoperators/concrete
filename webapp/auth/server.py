"""
We use the OAuth2 standard protocol enabled through google's SDKs to identify and authenticate users.

1. The user initiates login with AO
2. The user is redirected to google to complete authentication
  a. If it is the user's first time, they will have to authorize Google
  to provide their user data (name, email, profile) to AO
  b. Only URLs designated in the OAuth client on GCloud will be allowed to make this redirect with some client ID
    - This is how Google knows that they aren't fielding a random request
3. Google returns the user to a callback url on AO with a special authorization code
  a. This redirect url is also hardcoded in GCloud
4. AO uses the authorization code in the auth_callback with the Google auth sdk to receive a refresh token for the user
5. The user has now been authenticated
  a. AO stores the refresh token and creates an account if needed
6. The user is redirected away again from the auth_callback endpoint to the landing page
or the page they were originally trying to access
"""


def login():
    """
    Starting point for the user to authenticate themselves with Google
    """
    pass


def auth_callback():
    """
    Receives a request from Google once the user has completed their auth flow on Google's side.
    The user's authorization code is verified with Google's servers and swapped for a refresh token.
    """
    pass
