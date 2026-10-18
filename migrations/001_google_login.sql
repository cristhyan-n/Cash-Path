PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE usuario_novo (
    id INTEGER PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT,
    role TEXT NOT NULL DEFAULT 'usuario',
    provider TEXT NOT NULL DEFAULT 'local',
    CHECK (role IN ('usuario', 'admin')),
    CHECK (provider IN ('local', 'google')),
    CHECK (provider = 'google' OR senha IS NOT NULL)
);

INSERT INTO usuario_novo (id, nome, email, senha, role)
SELECT id, nome, email, senha, role FROM usuario;

DROP TABLE usuario;
ALTER TABLE usuario_novo RENAME TO usuario;

COMMIT;
PRAGMA foreign_keys = ON;