import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from .config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/login")


def hash_password(senha: str) -> str:
    hash_gerado = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    return hash_gerado


def verify_password(senha: str, hash_armazenado: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())


def generate_jwt_token(usuario_id: int) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(usuario_id), "exp": expira_em}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True},
        )
        usuario_id = int(payload.get("sub"))
        return usuario_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
