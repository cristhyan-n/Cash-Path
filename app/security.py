import bcrypt

hash_gerado = bcrypt.hashpw("senha123".encode(), bcrypt.gensalt())
