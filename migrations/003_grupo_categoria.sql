-- Grupo do 50/30/20 para cada categoria de despesa.
-- NULL = categoria sem grupo (ex: Salário, que é receita).
ALTER TABLE categoria
    ADD COLUMN grupo TEXT CHECK (grupo IN ('necessidade', 'desejo'));

UPDATE categoria
SET grupo = 'necessidade'
WHERE nome IN ('Alimentação', 'Transporte', 'Moradia', 'Saúde', 'Educação');

UPDATE categoria
SET grupo = 'desejo'
WHERE nome IN ('Lazer', 'Outros');