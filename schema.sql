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