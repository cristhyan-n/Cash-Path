import os

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "Variável de ambiente JWT_SECRET_KEY não definida. "
        "Defina-a antes de iniciar o servidor."
    )
