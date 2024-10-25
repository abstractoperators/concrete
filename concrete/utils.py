"""AI generated"""

import ast
import base64
import os
import re
import time
from datetime import timedelta

import astor
import dotenv
import jwt
from fastapi import HTTPException

dotenv.load_dotenv(override=True)

# These are slow-changing, so the certs are hardcoded directly here
GOOGLE_OIDC_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
# GOOGLE_OIDC_CONFIG = requests.get(GOOGLE_OIDC_DISCOVERY).json()
GOOGLE_OIDC_ALGOS = ['RS256']
# GOOGLE_JWKS_URI = GOOGLE_OIDC_CONFIG["jwks_uri"]
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
google_jwks_client = jwt.PyJWKClient(GOOGLE_JWKS_URI)


class CommentAndDocstringRemover(ast.NodeTransformer):
    def visit_Module(self, node):
        # Remove module-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Remove class-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Remove function-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_Expr(self, node):
        # Remove standalone expressions that are actually comments
        if isinstance(node.value, ast.Constant):
            return None
        return self.generic_visit(node)


def remove_comments(source_code):
    # Parse the source code into an AST
    tree = ast.parse(source_code)

    # Transform the AST to remove comments and docstrings
    remover = CommentAndDocstringRemover()
    tree = remover.visit(tree)

    # Convert the AST back to source code
    modified_code = astor.to_source(tree)

    # Remove extra whitespace
    modified_code = remove_extra_whitespace(modified_code)

    return modified_code


def remove_extra_whitespace(code: str):
    # Preserve strings while removing extra whitespace
    string_regex = r"(\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|\".*?\"|\'.*?\')"

    # Extract strings and replace them with placeholders
    strings = re.findall(string_regex, code, re.DOTALL)
    placeholders = [f"__STRING_PLACEHOLDER_{i}__" for i in range(len(strings))]
    code_without_strings = re.sub(string_regex, lambda m: placeholders.pop(0), code, flags=re.DOTALL)

    # Remove extra whitespace outside of strings
    code_without_extra_whitespace = re.sub(r"\n\s*\n", "\n", code_without_strings)  # Remove empty lines
    code_without_extra_whitespace = re.sub(
        r"^\s+$", "", code_without_extra_whitespace, flags=re.MULTILINE
    )  # Remove lines with only whitespace

    # Reinsert the strings back into their placeholders
    for i, placeholder in enumerate(strings):
        code_without_extra_whitespace = code_without_extra_whitespace.replace(f"__STRING_PLACEHOLDER_{i}__", strings[i])

    return code_without_extra_whitespace


def verify_jwt(jwt_token: str, access_token: str) -> dict[str, str]:
    """
    Raise an assertion error if the JWT cannot be verified.
    Verifies token authenticity again Google's public keys.
    """
    signing_key = google_jwks_client.get_signing_key_from_jwt(jwt_token)
    data = jwt.PyJWT().decode_complete(
        jwt=jwt_token,
        key=signing_key.key,
        algorithms=GOOGLE_OIDC_ALGOS,
        audience=os.environ['GOOGLE_OAUTH_CLIENT_ID'],
        # Allow two weeks stale tokens
        leeway=timedelta(weeks=2).total_seconds(),
    )
    # For payload details, see
    # https://developers.google.com/identity/openid-connect/openid-connect#an-id-tokens-payload
    payload, header = data["payload"], data["header"]
    alg_obj = jwt.get_algorithm_by_name(header["alg"])
    digest = alg_obj.compute_hash_digest(bytes(access_token, 'utf-8'))
    at_hash = base64.urlsafe_b64encode(digest[: (len(digest) // 2)]).rstrip(b"=")
    # Check signature
    assert at_hash == bytes(payload["at_hash"], 'utf-8')
    # Simple checks
    # See https://developers.google.com/identity/openid-connect/openid-connect#validatinganidtoken
    assert payload['iss'] in {'https://accounts.google.com', 'accounts.google.com'}
    assert payload['aud'] == os.environ['GOOGLE_OAUTH_CLIENT_ID']
    return payload


# TODO merge with verify_jwt
class JwtToken:
    """
    Represents a JWT token.
    Manages token expiry and generation.
    """

    def __init__(
        self,
        key_name: str,
        alg: str = "RS256",
        expiry_offset: int = 600,
        iss: str | None = None,
        aud: str | None = None,
        nbf: int | None = None,
        additional_headers: dict = {},
    ):
        """
        additional_headers (dict): Headers additional to {typ: 'JWT', alg: alg}
        """
        self.iat = None
        self.exp = None
        self.alg = alg
        self.expiry_offset = expiry_offset
        self.iss = iss
        self.aud = aud
        self.nbf = nbf
        self.additional_headers = additional_headers
        self.key_value = os.getenv(key_name)
        if not self.key_value:
            raise HTTPException(status_code=500, detail=f"{key_name} is not set")

        self._token: str | None = None

    @property
    def token(self):
        if not self._token or self._is_expired():
            self._generate_jwt()
        return self._token

    def _is_expired(self):
        return self.exp is None or time.time() >= self.exp

    def _generate_jwt(self):
        self.iat = time.time()
        self.exp = self.iat + self.expiry_offset
        payload = {
            'exp': self.iat + self.expiry_offset,
            'iat': self.iat,
            'iss': self.iss,
            'aud': self.aud,
            'nbf': self.nbf,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        self._token = jwt.encode(payload, self.key_value, algorithm=self.alg, headers=self.additional_headers)
