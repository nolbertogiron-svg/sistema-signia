import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


datos_requeridos = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}


faltantes = [
    nombre
    for nombre, valor in datos_requeridos.items()
    if not valor
]


if faltantes:
    raise ValueError(
        "Faltan datos en el archivo .env: "
        + ", ".join(faltantes)
    )


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
    query={
        "sslmode": "require"
    }
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def obtener_base_datos():
    base_datos = SessionLocal()

    try:
        yield base_datos
    finally:
        base_datos.close()


def comprobar_conexion():
    try:
        with engine.connect() as conexion:
            resultado = conexion.execute(
                text("SELECT 1")
            )

            resultado.scalar()

        print(
            "Conexion correcta con PostgreSQL de Supabase"
        )

    except Exception as error:
        print(
            "No se pudo conectar con PostgreSQL"
        )

        print(
            type(error).__name__,
            str(error)
        )


if __name__ == "__main__":
    comprobar_conexion()