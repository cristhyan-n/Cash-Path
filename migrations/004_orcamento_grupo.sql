CREATE TABLE IF NOT EXISTS orcamento_grupo (
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    grupo TEXT NOT NULL CHECK (grupo IN ('necessidade', 'desejo', 'economia')),
    valor_limite INTEGER NOT NULL CHECK (valor_limite > 0),
    PRIMARY KEY (usuario_id, grupo)
);
