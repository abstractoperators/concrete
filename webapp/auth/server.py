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

import functools
import os
import urllib

import dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from concrete.db.crud import (
    create_authstate,
    create_authtoken,
    create_user,
    get_authstate,
    get_user,
)
from concrete.db.orm.models import AuthStateCreate, AuthTokenCreate, UserCreate
from concrete.db.orm.setup import Session
from concrete.utils import verify_jwt
from concrete.webutils import AuthMiddleware

dotenv.load_dotenv(override=True)

# Google Auth Details
GOOGLE_OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]
GoogleOAuthClient = functools.partial(
    Flow.from_client_config,
    **{
        'client_config': {
            "web": {
                'client_id': os.environ['GOOGLE_OAUTH_CLIENT_ID'],
                'client_secret': os.environ['GOOGLE_OAUTH_CLIENT_SECRET'],
                'redirect_uris': [_ for _ in os.environ['GOOGLE_OAUTH_REDIRECT_URIS'].split(',')],
                'auth_uri': "https://accounts.google.com/o/oauth2/auth",
                'token_uri': "https://oauth2.googleapis.com/token",
            }
        },
        'scopes': GOOGLE_OAUTH_SCOPES,
    },
)


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
    ),
]

app = FastAPI(title="Concrete API", middleware=middleware)


@app.get("/")
def ping():
    return {"message": "pong"}


@app.get("/login")
def login(request: Request, destination_url: str | None = None):
    """
    Starting point for the user to authenticate themselves with Google
    """
    user_data = AuthMiddleware.check_auth(request)
    if user_data:
        return JSONResponse({"Message": "Already logged in", "email": user_data['email']})

    flow = GoogleOAuthClient()
    flow.redirect_uri = os.environ['GOOGLE_OAUTH_REDIRECT']

    # for security, only redirect to paths on the saas after api auth
    clean_destination_url = os.environ['SAAS_AUTH_REDIRECT']
    if destination_url:
        parsed = urllib.parse.urlparse(destination_url)
        clean_destination_url += (f':{port}' if (port := parsed.port) else '') + parsed.path

    # Randomly generated state from google's sdk
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt="select_account",
    )

    auth_state = AuthStateCreate(state=state, destination_url=clean_destination_url)
    with Session() as session:
        create_authstate(session, auth_state)

    return RedirectResponse(authorization_url)


@app.get('/logout')
def logout(request: Request):
    request.session.clear()
    return JSONResponse({"Message": "Logged out"})


@app.get("/auth")
def auth_callback(request: Request):
    """
    Receives a request from Google once the user has completed their auth flow on Google's side.
    The user's authorization code is verified with Google's servers and swapped for a refresh token.
    """
    query_params = request.query_params
    if error := query_params.get('error'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
    if (code := query_params.get('code')) is None:
        # code is used later to get tokens
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization code was provided.")
    if (state := query_params.get('state')) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    with Session() as session:
        auth_state = get_authstate(session, state)
        if auth_state is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    # Complete PKCE flow with Google
    flow = GoogleOAuthClient()
    flow.redirect_uri = os.environ['GOOGLE_OAUTH_REDIRECT']
    try:
        # Hydrates credentials
        flow.fetch_token(code=code)
    except InvalidGrantError:
        # A code was re-used or otherwise failed to convert to a token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code exchanged failed. Try again.")

    id_token = flow.credentials._id_token
    access_token = flow.credentials.token
    user_info: dict[str, str]
    try:
        user_info = verify_jwt(jwt_token=id_token, access_token=access_token)
    except AssertionError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unrecognized ID token Signature")
    # Set valid id_token to session
    request.session['id_token'] = id_token
    request.session['access_token'] = access_token

    # Commented because there's no use for invoking the API directly with the access token (for now)
    # For payload info see
    # https://googleapis.github.io/google-api-python-client/docs/dyn/oauth2_v2.userinfo.html
    # user_info_service = build('oauth2', 'v2', credentials=flow.credentials)
    # user_info = user_info_service.userinfo().get().execute()

    with Session() as session:
        user = get_user(session, user_info['email'])

    if user is None:
        # Create the user if they're new
        new_user = UserCreate(
            first_name=user_info['given_name'],
            last_name=user_info['family_name'],
            email=user_info['email'],
            profile_picture=user_info['picture'],
        )
        with Session() as session:
            user = create_user(session, new_user)

        # Start saving refresh tokens for later. Only given to us for the first auth.
        auth_token = AuthTokenCreate(refresh_token=flow.credentials.refresh_token, user_id=user.id)
        with Session() as session:
            create_authtoken(session, auth_token)

    # Not strictly necessary as of now
    request.session['user'] = {'uuid': str(user.id), 'email': user.email}

    if auth_state.destination_url:
        return RedirectResponse(auth_state.destination_url)
    return {"message": "login successful"}


@app.get("/token")
def token(request: Request):
    """
    Return an auth token or start the auth flow
    """
    if 'id_token' not in request.session or (id_token := request.session['id_token']) is None:
        return RedirectResponse(request.url_for('login').include_query_params(destination_url=request.url))
    return {"access_token": f"{id_token}", "token_type": "bearer"}
