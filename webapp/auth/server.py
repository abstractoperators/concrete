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

import os

import dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

# from fastapi.security import OAuth2AuthorizationCodeBearer
from google_auth_oauthlib.flow import Flow

# from sqlmodel import Session
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# from typing import Annotated


dotenv.load_dotenv(override=True)

# Setup App with Middleware
middleware = [Middleware(HTTPSRedirectMiddleware)] if os.environ.get('ENV') != 'DEV' else []
middleware += [
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=[_ for _ in os.environ['HTTP_ALLOWED_HOSTS'].split(',')],
        www_redirect=False,
    ),
    Middleware(
        CORSMiddleware,
        allow_origins=[_ for _ in os.environ['HTTP_CORS_ORIGINS'].split(',')],
        allow_credentials=True,
    ),
    Middleware(
        SessionMiddleware,
        secret_key=os.environ['HTTP_SESSION_SECRET'],
        domain=os.environ['HTTP_SESSION_DOMAIN'],
        https_only=True,
    ),
]

app = FastAPI(title="Concrete API", middleware=middleware)


@app.get("/")
def ping():
    return {"message": "pong"}


@app.get("/login")
def login():
    """
    Starting point for the user to authenticate themselves with Google
    """
    flow = Flow.from_client_config(
        client_config={
            "web": {
                'client_id': os.environ['GOOGLE_OAUTH_CLIENT_ID'],
                'client_secret': os.environ['GOOGLE_OAUTH_CLIENT_SECRET'],
                'redirect_uris': [_ for _ in os.environ['GOOGLE_OAUTH_REDIRECT_URIS'].split(',')],
                'auth_uri': "https://accounts.google.com/o/oauth2/auth",
                'token_uri': "https://oauth2.googleapis.com/token",
            }
        },
        scopes=['openid', 'email', 'profile'],
    )
    flow.redirect_uri = os.environ['GOOGLE_OAUTH_REDIRECT']
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt="select_account",
    )
    return RedirectResponse(authorization_url)


@app.get("/auth")
def auth_callback(request: Request):
    """
    Receives a request from Google once the user has completed their auth flow on Google's side.
    The user's authorization code is verified with Google's servers and swapped for a refresh token.
    """
    return {"welcome back ya": "lad"}


# oauth2_scheme = OAuth2AuthorizationCodeBearer()


# def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#     user = fake_decode_token(token)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return user
