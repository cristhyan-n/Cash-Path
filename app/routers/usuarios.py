import sqlite3
import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from ..config import GOOGLE_CLIENT_ID, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
from ..google_auth import GoogleTokenError, get_google_user_info

from ..security import (
    generate_jwt_token,
    decode_jwt_token,
    hash_password,
    oauth2_scheme,
    verify_jwt_token,
    verify_password,
)
from ..database import get_db_connection
from ..schemas import CadastroUsuario, ConfirmarEmail, TokenResponse, UsuarioLogin, UsuarioResponse, GoogleLogin, UsuarioUpdate, SolicitarRecuperacao, RedefinirSenha  # type: ignore[import-not-found]

router = APIRouter()


def _smtp_pronto() -> bool:
    return bool(SMTP_HOST and SMTP_FROM and (not SMTP_USER or SMTP_PASSWORD))


def _enviar_confirmacao_email(conexao, usuario_id: int, email: str) -> None:
    if not _smtp_pronto():
        raise HTTPException(status_code=503, detail="SMTP incompleto: configure remetente, servidor e senha de app para enviar confirmações.")
    # Código curto e numérico para facilitar a digitação no app.
    # O hash é único na tabela; em uma colisão rara, geramos outro código.
    cursor = conexao.cursor()
    while True:
        token = f"{secrets.randbelow(1_000_000):06d}"
        digest = hashlib.sha256(token.encode()).hexdigest()
        cursor.execute("SELECT 1 FROM confirmacao_email WHERE token_hash = ?", (digest,))
        if cursor.fetchone() is None:
            break
    expira = datetime.now(timezone.utc) + timedelta(minutes=30)
    cursor.execute(
        "UPDATE confirmacao_email SET usado = 1 WHERE usuario_id = ? AND usado = 0",
        (usuario_id,),
    )
    cursor.execute(
        "INSERT INTO confirmacao_email (token_hash, usuario_id, expira_em) VALUES (?, ?, ?)",
        (digest, usuario_id, expira.isoformat()),
    )
    conexao.commit()
    mensagem = EmailMessage()
    mensagem["Subject"] = "Confirme seu e-mail no CashPath"
    mensagem["From"] = SMTP_FROM
    mensagem["To"] = email
    mensagem.set_content(
        f"Este código foi enviado para o endereço informado no cadastro: {email}.\n"
        "Para confirmar que este e-mail é seu, informe o código abaixo no aplicativo. "
        f"Ele expira em 30 minutos:\n\n{token}"
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            if SMTP_USER:
                servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.send_message(mensagem)
    except Exception:
        cursor.execute("UPDATE confirmacao_email SET usado = 1 WHERE token_hash = ?", (digest,))
        conexao.commit()
        raise HTTPException(status_code=503, detail="Não foi possível enviar o e-mail de confirmação. Tente novamente.")


@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(dados_usuario: CadastroUsuario, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    email = dados_usuario.email.strip().lower()
    cursor.execute(
        "SELECT provider, email_verificado FROM usuario WHERE lower(email) = lower(?)",
        (email,),
    )
    existente = cursor.fetchone()
    if existente:
        if existente[0] == "google":
            raise HTTPException(
                status_code=409,
                detail="Este e-mail já tem uma conta vinculada ao Google. Use 'Entrar com Google'.",
            )
        if not existente[1]:
            raise HTTPException(
                status_code=409,
                detail="Este cadastro já está aguardando confirmação. Entre com esse e-mail e senha para receber um código.",
            )
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    try:
        cursor.execute(
            "INSERT INTO usuario (nome, email, senha, email_verificado) VALUES (?, ?, ?, 0)",
            (
                dados_usuario.nome.strip(),
                email,
                hash_password(dados_usuario.senha),
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    return {"id": novo_id, "nome": dados_usuario.nome.strip(), "email": email}


@router.post("/usuarios/confirmar-email")
def confirmar_email(dados: ConfirmarEmail, conexao=Depends(get_db_connection)):
    digest = hashlib.sha256(dados.token.encode()).hexdigest()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT usuario_id, expira_em FROM confirmacao_email WHERE token_hash = ? AND usado = 0",
        (digest,),
    )
    registro = cursor.fetchone()
    if not registro or datetime.fromisoformat(registro[1]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Código inválido ou expirado. Solicite um novo e-mail.")
    cursor.execute("UPDATE usuario SET email_verificado = 1 WHERE id = ?", (registro[0],))
    cursor.execute("UPDATE confirmacao_email SET usado = 1 WHERE token_hash = ?", (digest,))
    conexao.commit()
    return {"message": "E-mail confirmado. Agora você pode entrar no CashPath."}


@router.post("/usuarios/reenviar-confirmacao")
def reenviar_confirmacao(dados: SolicitarRecuperacao, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    email = dados.email.strip().lower()
    cursor.execute("SELECT id, email_verificado FROM usuario WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    if usuario and not usuario[1]:
        _enviar_confirmacao_email(conexao, usuario[0], email)
    return {"message": "Se a conta existir e ainda não estiver confirmada, enviaremos um código."}


@router.post("/usuarios/login", response_model=TokenResponse)
def login_usuario(dados_login: UsuarioLogin, conexao=Depends(get_db_connection)):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, senha, email_verificado FROM usuario WHERE email = ?", (dados_login.email.strip().lower(),)
    )
    resultado = cursor.fetchone()

    if not resultado:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    usuario_id, hash_senha, email_verificado = resultado

    if hash_senha is None or not verify_password(dados_login.senha, hash_senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    if not email_verificado:
        raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de entrar. Você pode solicitar um novo código na tela de login.")

    token = generate_jwt_token(usuario_id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/usuarios/logout")
def logout_usuario(
    token: str = Depends(oauth2_scheme),
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    payload = decode_jwt_token(token)
    expira = int(payload["exp"])
    conexao.execute(
        "INSERT OR IGNORE INTO token_revogado (jti, expira_em) VALUES (?, ?)",
        (payload["jti"], expira),
    )
    conexao.execute("DELETE FROM token_revogado WHERE expira_em <= ?", (int(datetime.now(timezone.utc).timestamp()),))
    conexao.commit()
    return {"message": "Sessão encerrada."}


@router.get("/usuarios/me", response_model=UsuarioResponse)
def obter_usuario_atual(
    usuario_id: int = Depends(verify_jwt_token), conexao=Depends(get_db_connection)
):
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, email, role, provider FROM usuario WHERE id = ?", (usuario_id,))
    resultado = cursor.fetchone()

    if not resultado:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    return {
        "id": resultado[0],
        "nome": resultado[1],
        "email": resultado[2],
        "role": resultado[3],
        "provider": resultado[4],
    }


@router.put("/usuarios/me", response_model=UsuarioResponse)
def atualizar_usuario_atual(
    dados: UsuarioUpdate,
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    cursor.execute("SELECT senha, role, email, email_verificado, provider FROM usuario WHERE id = ?", (usuario_id,))
    atual = cursor.fetchone()
    if not atual:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    senha_hash = atual[0]
    email_normalizado = dados.email.strip().lower()
    email_alterado = email_normalizado != atual[2]
    if email_alterado and atual[4] == "google":
        raise HTTPException(
            status_code=400,
            detail="Contas conectadas ao Google não podem alterar o e-mail pelo CashPath. Altere-o na sua Conta Google.",
        )
    if dados.nova_senha and atual[4] == "google":
        raise HTTPException(
            status_code=400,
            detail="A senha desta conta é gerenciada pelo Google. Altere-a nas configurações da sua Conta Google.",
        )
    if email_alterado:
        cursor.execute(
            "SELECT 1 FROM usuario WHERE lower(email) = lower(?) AND id <> ?",
            (email_normalizado, usuario_id),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if dados.nova_senha:
        if not senha_hash or not dados.senha_atual or not verify_password(dados.senha_atual, senha_hash):
            raise HTTPException(status_code=400, detail="Informe a senha atual correta para alterá-la.")
        senha_hash = hash_password(dados.nova_senha)
    try:
        if email_alterado:
            # O código só será enviado quando o usuário tentar entrar com o
            # novo endereço. Invalida códigos anteriores ligados a outro e-mail.
            cursor.execute(
                "UPDATE confirmacao_email SET usado = 1 WHERE usuario_id = ? AND usado = 0",
                (usuario_id,),
            )
        cursor.execute(
            "UPDATE usuario SET nome = ?, email = ?, senha = ?, email_verificado = ? WHERE id = ?",
            (dados.nome.strip(), email_normalizado, senha_hash, 0 if email_alterado else atual[3], usuario_id),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        if email_alterado:
            cursor.execute(
                "UPDATE confirmacao_email SET usado = 1 WHERE usuario_id = ? AND usado = 0",
                (usuario_id,),
            )
            conexao.commit()
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    return {
        "id": usuario_id,
        "nome": dados.nome.strip(),
        "email": email_normalizado,
        "role": atual[1],
        "provider": atual[4],
    }


@router.delete("/usuarios/me")
def excluir_usuario_atual(
    usuario_id: int = Depends(verify_jwt_token),
    conexao=Depends(get_db_connection),
):
    cursor = conexao.cursor()
    # Algumas relações antigas não usam ON DELETE CASCADE. Remova somente os
    # registros desta conta, na ordem das chaves estrangeiras, em uma transação.
    # Se qualquer relação inesperada impedir a exclusão, o bloco reverte tudo.
    try:
        with conexao:
            # Serializa exclusões concorrentes para que duas últimas contas
            # administradoras não consigam passar pela verificação ao mesmo tempo.
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("SELECT role FROM usuario WHERE id = ?", (usuario_id,))
            usuario = cursor.fetchone()
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")

            if usuario[0] == "admin":
                cursor.execute("SELECT COUNT(*) FROM usuario WHERE role = 'admin'")
                if cursor.fetchone()[0] <= 1:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Esta é a última conta administradora. Promova outro usuário "
                            "a administrador antes de excluir esta conta."
                        ),
                    )

            cursor.execute("DELETE FROM transacao WHERE usuario_id = ?", (usuario_id,))
            cursor.execute("DELETE FROM meta WHERE usuario_id = ?", (usuario_id,))
            cursor.execute("DELETE FROM orcamento WHERE usuario_id = ?", (usuario_id,))
            cursor.execute(
                "DELETE FROM perfil_financeiro WHERE usuario_id = ?", (usuario_id,)
            )
            cursor.execute(
                "DELETE FROM orcamento_grupo WHERE usuario_id = ?", (usuario_id,)
            )
            cursor.execute("DELETE FROM categoria WHERE usuario_id = ?", (usuario_id,))
            cursor.execute("DELETE FROM usuario WHERE id = ?", (usuario_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Há dados vinculados que impediram a exclusão completa. "
                "Nenhuma alteração foi aplicada. Entre em contato com o suporte."
            ),
        )

    return {"message": "A conta e os dados associados foram excluídos."}


@router.post("/usuarios/recuperar-senha")
def solicitar_recuperacao(dados: SolicitarRecuperacao, conexao=Depends(get_db_connection)):
    if not _smtp_pronto():
        raise HTTPException(status_code=503, detail="SMTP incompleto: configure as credenciais de envio no servidor.")
    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM usuario WHERE email = ?", (dados.email.strip().lower(),))
    usuario = cursor.fetchone()
    # Resposta genérica impede enumeração de contas.
    if not usuario:
        return {"message": "Se a conta existir, enviaremos instruções para redefinir a senha."}
    # Código numérico de seis dígitos, fácil de digitar no aplicativo.
    # Evita reutilizar um hash já gravado, inclusive em registros usados.
    while True:
        token = f"{secrets.randbelow(1_000_000):06d}"
        digest = hashlib.sha256(token.encode()).hexdigest()
        cursor.execute("SELECT 1 FROM recuperacao_senha WHERE token_hash = ?", (digest,))
        if cursor.fetchone() is None:
            break
    expira = datetime.now(timezone.utc) + timedelta(minutes=30)
    cursor.execute("UPDATE recuperacao_senha SET usado = 1 WHERE usuario_id = ? AND usado = 0", (usuario[0],))
    cursor.execute("INSERT INTO recuperacao_senha (token_hash, usuario_id, expira_em) VALUES (?, ?, ?)", (digest, usuario[0], expira.isoformat()))
    conexao.commit()
    mensagem = EmailMessage()
    mensagem["Subject"] = "Redefinição de senha CashPath"
    mensagem["From"] = SMTP_FROM
    mensagem["To"] = dados.email
    mensagem.set_content(f"Use este código no aplicativo para redefinir sua senha. Ele expira em 30 minutos:\n\n{token}")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            if SMTP_USER:
                servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.send_message(mensagem)
    except Exception:
        cursor.execute("UPDATE recuperacao_senha SET usado = 1 WHERE token_hash = ?", (digest,))
        conexao.commit()
        raise HTTPException(status_code=503, detail="Não foi possível enviar o e-mail de recuperação.")
    return {"message": "Se a conta existir, enviaremos instruções para redefinir a senha."}


@router.post("/usuarios/redefinir-senha")
def redefinir_senha(dados: RedefinirSenha, conexao=Depends(get_db_connection)):
    if dados.nova_senha != dados.confirmar_senha:
        raise HTTPException(status_code=400, detail="As senhas não coincidem.")
    digest = hashlib.sha256(dados.token.encode()).hexdigest()
    cursor = conexao.cursor()
    cursor.execute("SELECT usuario_id, expira_em FROM recuperacao_senha WHERE token_hash = ? AND usado = 0", (digest,))
    registro = cursor.fetchone()
    if not registro or datetime.fromisoformat(registro[1]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")
    cursor.execute("UPDATE usuario SET senha = ? WHERE id = ?", (hash_password(dados.nova_senha), registro[0]))
    cursor.execute("UPDATE recuperacao_senha SET usado = 1 WHERE token_hash = ?", (digest,))
    conexao.commit()
    return {"message": "Senha redefinida. Faça login com sua nova senha."}


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
    email_google = info["email"].strip().lower()
    cursor.execute("SELECT id, provider, email_verificado FROM usuario WHERE email = ?", (email_google,))
    existente = cursor.fetchone()

    if existente is None:
        cursor.execute(
            "INSERT INTO usuario (nome, email, provider, email_verificado) VALUES (?, ?, 'google', 1)",
            (info["nome"], email_google),
        )
        conexao.commit()
        usuario_id = cursor.lastrowid
    else:
        usuario_id, provider, email_verificado = existente
        if provider != "google":
            if email_verificado:
                raise HTTPException(
                    status_code=409,
                    detail="Este e-mail já está cadastrado com senha. Entre com e-mail e senha.",
                )
            # A identidade Google já foi validada e o endereço local ainda não
            # foi confirmado; permite que o titular confirme e recupere a conta.
            cursor.execute(
                "UPDATE usuario SET provider = 'google', email_verificado = 1 WHERE id = ?",
                (usuario_id,),
            )
            conexao.commit()

    return {"access_token": generate_jwt_token(usuario_id), "token_type": "bearer"}
