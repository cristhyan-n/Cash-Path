import sqlite3

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from ..config import GOOGLE_CLIENT_ID
from ..google_auth import GoogleTokenError, get_google_user_info

from ..security import (
    generate_jwt_token,
    hash_password,
    verify_jwt_token,
    verify_password,
)
from ..database import get_db_connection
from ..schemas import CadastroUsuario, TokenResponse, UsuarioLogin, UsuarioResponse, GoogleLogin  # type: ignore[import-not-found]

router = APIRouter()


@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(dados_usuario: CadastroUsuario, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "INSERT INTO usuario (nome, email, senha) VALUES (?, ?, ?)",
            (
                dados_usuario.nome,
                dados_usuario.email,
                hash_password(dados_usuario.senha),
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    return {"id": novo_id, "nome": dados_usuario.nome, "email": dados_usuario.email}


@router.post("/usuarios/login", response_model=TokenResponse)
def login_usuario(dados_login: UsuarioLogin, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, senha FROM usuario WHERE email = ?", (dados_login.email,)
    )
    resultado = cursor.fetchone()

    if not resultado:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    usuario_id, hash_senha = resultado

    if hash_senha is None or not verify_password(dados_login.senha, hash_senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    token = generate_jwt_token(usuario_id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/usuarios/me", response_model=UsuarioResponse)
def obter_usuario_atual(
    usuario_id: int = Depends(verify_jwt_token), conexao=Depends(get_db_connection)
):
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, email FROM usuario WHERE id = ?", (usuario_id,))
    resultado = cursor.fetchone()

    if not resultado:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    return {"id": resultado[0], "nome": resultado[1], "email": resultado[2]}


@router.post("/usuarios/login/google", response_model=TokenResponse)
def login_google(dados: GoogleLogin, conexao=Depends(get_db_connection)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503, detail="Login com Google não configurado no servidor."
        )

    try:
        info = get_google_user_info(dados.id_token)
    except GoogleTokenError:
        raise HTTPException(status_code=401, detail="Token do Google inválido.")

    cursor = conexao.cursor()
    cursor.execute("SELECT id, provider FROM usuario WHERE email = ?", (info["email"],))
    existente = cursor.fetchone()

    if existente is None:
        cursor.execute(
            "INSERT INTO usuario (nome, email, provider) VALUES (?, ?, 'google')",
            (info["nome"], info["email"]),
        )
        conexao.commit()
        usuario_id = cursor.lastrowid
    else:
        usuario_id, provider = existente
        if provider != "google":
            raise HTTPException(
                status_code=409,
                detail="Este e-mail já está cadastrado com senha. Entre com e-mail e senha.",
            )

    return {"access_token": generate_jwt_token(usuario_id), "token_type": "bearer"}
