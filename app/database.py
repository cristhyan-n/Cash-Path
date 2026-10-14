import sqlite3
import unicodedata
import os
from pathlib import Path


GRUPOS_CATEGORIA = ("necessidade", "desejo", "economia", "receita")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _caminho_banco():
    configurado = os.getenv("CASH_PATH_DATABASE_PATH")
    caminho = Path(configurado) if configurado else PROJECT_ROOT / "financas.db"
    if not caminho.is_absolute():
        caminho = PROJECT_ROOT / caminho
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho
GRUPOS_FIXOS = (
    ("Alimentação", "necessidade"),
    ("Transporte", "necessidade"),
    ("Moradia", "necessidade"),
    ("Contas básicas", "necessidade"),
    ("Mercado", "necessidade"),
    ("Saúde", "necessidade"),
    ("Educação", "necessidade"),
    ("Farmácia", "necessidade"),
    ("Lazer", "desejo"),
    ("Restaurantes", "desejo"),
    ("Compras", "desejo"),
    ("Viagens", "desejo"),
    ("Assinaturas", "desejo"),
    ("Beleza", "desejo"),
    ("Hobbies", "desejo"),
    ("Presentes", "desejo"),
    ("Reserva de emergência", "economia"),
    ("Investimentos", "economia"),
    ("Aposentadoria", "economia"),
    ("Objetivos financeiros", "economia"),
    ("Salário", "receita"),
    ("Renda extra", "receita"),
    ("Rendimentos de investimentos", "receita"),
)


def _normalizar(texto):
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caractere)
    )


def _grupo_legado(nome, grupo):
    normalizado = _normalizar(nome)
    fixas = {(_normalizar(n)): g for n, g in GRUPOS_FIXOS}
    if normalizado in fixas:
        return fixas[normalizado]
    if grupo in GRUPOS_CATEGORIA:
        return grupo
    if any(palavra in normalizado for palavra in ("invest", "poupanc", "reserva", "aposent", "econom")):
        return "economia"
    if any(palavra in normalizado for palavra in ("salario", "renda", "receita")):
        return "receita"
    return "desejo"


def _migrar_categorias(conexao):
    info = conexao.execute("PRAGMA table_info(categoria)").fetchall()
    colunas = {linha[1] for linha in info}
    definicao_tabela = conexao.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'categoria'"
    ).fetchone()[0]
    sql_normalizado = definicao_tabela.casefold()
    grupos_necessarios = ("necessidade", "desejo", "economia", "receita")
    if "usuario_id" not in colunas or any(
        grupo not in sql_normalizado for grupo in grupos_necessarios
    ):
        tem_grupo = "grupo" in colunas
        tem_ativa = "ativa" in colunas
        tem_usuario = "usuario_id" in colunas
        selecao = ["id", "nome"]
        if tem_grupo:
            selecao.append("grupo")
        if tem_ativa:
            selecao.append("ativa")
        if tem_usuario:
            selecao.append("usuario_id")
        linhas = conexao.execute(f"SELECT {', '.join(selecao)} FROM categoria").fetchall()
        # PRAGMA foreign_keys can only change outside a transaction. Some callers
        # may already have pending migration writes on this connection.
        if conexao.in_transaction:
            conexao.commit()
        conexao.execute("PRAGMA foreign_keys = OFF")
        conexao.execute("BEGIN")
        conexao.execute("""
            CREATE TABLE categoria_nova (
                id INTEGER PRIMARY KEY NOT NULL,
                nome TEXT NOT NULL,
                grupo TEXT NOT NULL CHECK (grupo IN ('necessidade', 'desejo', 'economia', 'receita')),
                ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
                usuario_id INTEGER REFERENCES usuario(id) ON DELETE CASCADE
            )
        """)
        for linha in linhas:
            pos = 2
            grupo = linha[pos] if tem_grupo else None
            pos += int(tem_grupo)
            ativa = linha[pos] if tem_ativa else 1
            pos += int(tem_ativa)
            usuario_id = linha[pos] if tem_usuario else None
            conexao.execute(
                """INSERT INTO categoria_nova
                (id, nome, grupo, ativa, usuario_id) VALUES (?, ?, ?, ?, ?)""",
                (linha[0], linha[1], _grupo_legado(linha[1], grupo), ativa, usuario_id),
            )
        conexao.execute("DROP TABLE categoria")
        conexao.execute("ALTER TABLE categoria_nova RENAME TO categoria")
        conexao.commit()
        conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_sistema_nome "
        "ON categoria(lower(nome)) WHERE usuario_id IS NULL"
    )
    conexao.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_usuario_nome "
        "ON categoria(usuario_id, lower(nome)) WHERE usuario_id IS NOT NULL"
    )
    for nome, grupo in GRUPOS_FIXOS:
        conexao.execute(
            "INSERT OR IGNORE INTO categoria (nome, grupo, ativa) VALUES (?, ?, 1)",
            (nome, grupo),
        )


def _migrar_orcamentos_por_grupo(conexao):
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS orcamento_grupo (
            usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            grupo TEXT NOT NULL CHECK (grupo IN ('necessidade', 'desejo', 'economia')),
            valor_limite INTEGER NOT NULL CHECK (valor_limite > 0),
            PRIMARY KEY (usuario_id, grupo)
        )
    """)


def _migrar_metas(conexao):
    colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(meta)")}
    if "nome" not in colunas:
        conexao.execute(
            "ALTER TABLE meta ADD COLUMN nome TEXT NOT NULL DEFAULT 'Minha meta'"
        )
    if "data_alvo" not in colunas:
        conexao.execute("ALTER TABLE meta ADD COLUMN data_alvo TEXT")
    if "categoria_id" not in colunas:
        conexao.execute(
            "ALTER TABLE meta ADD COLUMN categoria_id INTEGER REFERENCES categoria(id)"
        )
    conexao.execute(
        """UPDATE meta
        SET categoria_id = (
            SELECT c.id FROM categoria c
            WHERE c.usuario_id IS NULL AND c.grupo = 'economia'
                AND lower(c.nome) = lower(
                    CASE WHEN meta.tipo = 'investir'
                        THEN 'Investimentos'
                        ELSE 'Objetivos financeiros'
                    END
                )
            LIMIT 1
        )
        WHERE categoria_id IS NULL"""
    )
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS meta_movimento (
            id INTEGER PRIMARY KEY NOT NULL,
            meta_id INTEGER NOT NULL REFERENCES meta(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL CHECK (tipo IN ('aporte', 'retirada')),
            valor INTEGER NOT NULL CHECK (valor > 0),
            data TEXT NOT NULL
        )
    """)
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS ix_meta_movimento_meta_data "
        "ON meta_movimento(meta_id, data, id)"
    )
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS ix_meta_categoria_usuario "
        "ON meta(categoria_id, usuario_id)"
    )


def _aplicar_migracoes(conexao):
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("""CREATE TABLE IF NOT EXISTS token_revogado (
        jti TEXT PRIMARY KEY NOT NULL, expira_em INTEGER NOT NULL)""")
    conexao.execute("""CREATE TABLE IF NOT EXISTS recuperacao_senha (
        token_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
        expira_em TEXT NOT NULL, usado INTEGER NOT NULL DEFAULT 0)""")
    conexao.execute("""CREATE TABLE IF NOT EXISTS confirmacao_email (
        token_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
        expira_em TEXT NOT NULL, usado INTEGER NOT NULL DEFAULT 0)""")
    # Migrações leves para bancos já existentes, sem apagar dados do usuário.
    for tabela, coluna, definicao in (
        ("perfil_financeiro", "objetivo", "TEXT NOT NULL DEFAULT 'economizar'"),
        # Accounts already in the database were previously allowed to log in.
        # Only new registrations are required to confirm their address.
        ("usuario", "email_verificado", "INTEGER NOT NULL DEFAULT 1"),
    ):
        colunas = {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        if coluna not in colunas:
            conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
    _migrar_categorias(conexao)
    _migrar_orcamentos_por_grupo(conexao)
    _migrar_metas(conexao)
    conexao.commit()


def initialize_database():
    """Apply schema upgrades once when the API starts."""
    caminho = _caminho_banco()
    conexao = sqlite3.connect(caminho, timeout=15)
    try:
        tabelas = conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'usuario'"
        ).fetchone()
        if not tabelas:
            schema = PROJECT_ROOT / "schema.sql"
            conexao.executescript(schema.read_text(encoding="utf-8"))
        _aplicar_migracoes(conexao)
    finally:
        conexao.close()


def get_connection():
    # FastAPI may resume a synchronous yield dependency or its cleanup on a
    # different worker thread than the one that created the connection.
    # Connections are request-scoped, so allowing that handoff is safe here.
    conexao = sqlite3.connect(
        _caminho_banco(), timeout=15, check_same_thread=False
    )
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def get_db_connection():
    recurso = get_connection()
    try:
        yield recurso
    finally:
        recurso.close()
