from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .config import GOOGLE_CLIENT_ID


class GoogleTokenError(Exception):
    pass


def get_google_user_info(token: str) -> dict:
    try:
        info = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as erro:
        raise GoogleTokenError("Token do Google inválido.") from erro

    if not info.get("email_verified"):
        raise GoogleTokenError("E-mail do Google não verificado.")

    return {"email": info["email"], "nome": info.get("name", info["email"])}
