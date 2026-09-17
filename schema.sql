CREATE TABLE usuario (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'usuario',
    CHECK (role in ('usuario', 'admin'))
);

CREATE TABLE categoria (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL UNIQUE
);

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
    valor_alvo INTEGER NOT NULL,
    data_inicio TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativo' CHECK ( status in ('ativo', 'concluido')),
    tipo TEXT NOT NULL CHECK ( tipo in ('economizar', 'investir')),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id)
);