import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import secrets
from .database import get_db_connection
from .config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/login")


def hash_password(senha: str) -> str:
    hash_gerado = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    return hash_gerado


def verify_password(senha: str, hash_armazenado: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())


def generate_jwt_token(usuario_id: int) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(usuario_id), "exp": expira_em, "jti": secrets.token_urlsafe(24)}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str):
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def verify_jwt_token(
    token: str = Depends(oauth2_scheme), conexao=Depends(get_db_connection)
) -> int:
    try:
        payload = decode_jwt_token(token)
        usuario_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Sessão antiga. Entre novamente.")
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM token_revogado WHERE jti = ?", (jti,))
        if cursor.fetchone():
            raise HTTPException(status_code=401, detail="Sessão encerrada.")
        cursor.execute("SELECT email_verificado FROM usuario WHERE id = ?", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario[0]:
            raise HTTPException(status_code=401, detail="Confirme seu e-mail antes de continuar.")
        return usuario_id
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido")
