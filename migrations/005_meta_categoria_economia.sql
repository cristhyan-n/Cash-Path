-- Relaciona cada meta com uma categoria do grupo Economia/Investimentos.
-- Metas existentes são preservadas e recebem uma categoria padrão conforme o tipo.
ALTER TABLE meta ADD COLUMN categoria_id INTEGER REFERENCES categoria(id);

UPDATE meta
SET categoria_id = (
    SELECT c.id
    FROM categoria c
    WHERE c.usuario_id IS NULL
      AND c.grupo = 'economia'
      AND lower(c.nome) = lower(
          CASE WHEN meta.tipo = 'investir'
              THEN 'Investimentos'
              ELSE 'Objetivos financeiros'
          END
      )
    LIMIT 1
)
WHERE categoria_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_meta_categoria_usuario
ON meta(categoria_id, usuario_id);
