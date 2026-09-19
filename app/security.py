import bcrypt
from jose import jwt


def hash_password(senha: str) -> str:
    hash_gerado = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    return hash_gerado


def verify_password(senha: str, hash_armazenado: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())


def generate_jwt_token(usuario_id: int) -> str:
    token = jwt.encode({"sub": str(usuario_id)}, "chave_secreta", algorithm="HS256")
    return token
