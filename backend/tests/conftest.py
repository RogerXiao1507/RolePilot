import os


os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "test")
