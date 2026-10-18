CREATE TABLE usuario (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT,
    role TEXT NOT NULL DEFAULT 'usuario',
    provider TEXT NOT NULL DEFAULT 'local',
    email_verificado INTEGER NOT NULL DEFAULT 1 CHECK (email_verificado IN (0, 1)),
    CHECK (role IN ('usuario', 'admin')),
    CHECK (provider IN ('local', 'google')),
    CHECK (provider = 'google' OR senha IS NOT NULL)
);

CREATE TABLE categoria (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    grupo TEXT NOT NULL CHECK (grupo IN ('necessidade', 'desejo', 'economia', 'receita')),
    ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
    usuario_id INTEGER REFERENCES usuario(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_categoria_sistema_nome ON categoria(lower(nome)) WHERE usuario_id IS NULL;
CREATE UNIQUE INDEX uq_categoria_usuario_nome ON categoria(usuario_id, lower(nome)) WHERE usuario_id IS NOT NULL;

CREATE TABLE transacao (
    id INTEGER PRIMARY KEY NOT NULL,
    valor INTEGER NOT NULL,
    data TEXT NOT NULL ,
    tipo TEXT NOT NULL CHECK ( tipo in ('receita', 'despesa')),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id)
);

CREATE TABLE meta (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL DEFAULT 'Minha meta',
    valor_alvo INTEGER NOT NULL,
    data_inicio TEXT NOT NULL,
    data_alvo TEXT,
    status TEXT NOT NULL DEFAULT 'ativo' CHECK ( status in ('ativo', 'concluido')),
    tipo TEXT NOT NULL CHECK ( tipo in ('economizar', 'investir')),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id)
);

CREATE INDEX ix_meta_categoria_usuario ON meta(categoria_id, usuario_id);

CREATE TABLE meta_movimento (
    id INTEGER PRIMARY KEY NOT NULL,
    meta_id INTEGER NOT NULL REFERENCES meta(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('aporte', 'retirada')),
    valor INTEGER NOT NULL CHECK (valor > 0),
    data TEXT NOT NULL
);

CREATE INDEX ix_meta_movimento_meta_data ON meta_movimento(meta_id, data, id);

CREATE TABLE perfil_financeiro (
    id INTEGER PRIMARY KEY NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    valor_renda INTEGER NOT NULL,
    renda_periodo TEXT NOT NULL,
    objetivo TEXT NOT NULL DEFAULT 'economizar' CHECK (objetivo IN ('economizar', 'investir')),
    UNIQUE (usuario_id, renda_periodo)
);

CREATE TABLE orcamento (
    id INTEGER PRIMARY KEY NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    valor_limite INTEGER NOT NULL,
    UNIQUE (usuario_id, categoria_id)
);

CREATE TABLE orcamento_grupo (
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    grupo TEXT NOT NULL CHECK (grupo IN ('necessidade', 'desejo', 'economia')),
    valor_limite INTEGER NOT NULL CHECK (valor_limite > 0),
    PRIMARY KEY (usuario_id, grupo)
);

CREATE TABLE token_revogado (
    jti TEXT PRIMARY KEY NOT NULL,
    expira_em INTEGER NOT NULL
);

CREATE TABLE confirmacao_email (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    expira_em TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0
);
