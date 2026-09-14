from config import settings

# Contoh akses URL PostgreSQL utama
main_postgres_url = settings.db_postgres_1

# Contoh akses URL MongoDB
mongo_url = settings.db_mongo_1

print(f"Connecting to Postgres 1: {main_postgres_url}")