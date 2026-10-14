import os
from pathlib import Path


def _carregar_env_local():
    """Carrega o .env do projeto sem sobrescrever variáveis já definidas."""
    arquivo_env = Path(__file__).resolve().parents[1] / ".env"
    if not arquivo_env.is_file():
        return
    for linha in arquivo_env.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            valor = valor[1:-1]
        if chave and valor and not os.getenv(chave):
            os.environ[chave] = valor


_carregar_env_local()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "Variável de ambiente JWT_SECRET_KEY não definida. "
        "Defina-a antes de iniciar o servidor."
    )
