import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


# =========================================================
# CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY"
)

SUPABASE_BUCKET = os.getenv(
    "SUPABASE_BUCKET",
    "mantenimientos"
)


# =========================================================
# VALIDACIÓN DE VARIABLES
# =========================================================

if not SUPABASE_URL:
    raise ValueError(
        "Falta SUPABASE_URL en el archivo .env"
    )


if not SUPABASE_SECRET_KEY:
    raise ValueError(
        "Falta SUPABASE_SECRET_KEY en el archivo .env"
    )


# =========================================================
# CLIENTE DE SUPABASE
# =========================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# =========================================================
# FUNCIÓN GENERAL PARA SUBIR ARCHIVOS
# =========================================================

def subir_archivo(
    contenido: bytes,
    ruta: str,
    tipo_contenido: str
) -> str:
    """
    Sube un archivo al bucket de mantenimientos.

    Esta función permite almacenar:
    - fotografías
    - videos
    - documentos PDF

    Retorna la ruta interna del archivo
    dentro de Supabase Storage.
    """

    if not contenido:
        raise ValueError(
            "El archivo está vacío"
        )

    if not ruta:
        raise ValueError(
            "La ruta del archivo está vacía"
        )

    if not tipo_contenido:
        tipo_contenido = (
            "application/octet-stream"
        )

    supabase.storage.from_(
        SUPABASE_BUCKET
    ).upload(
        path=ruta,
        file=contenido,
        file_options={
            "content-type": tipo_contenido,
            "upsert": "false"
        }
    )

    return ruta


# =========================================================
# FOTOGRAFÍAS
# =========================================================

def subir_fotografia(
    contenido: bytes,
    ruta: str,
    tipo_contenido: str
) -> str:
    """
    Función conservada para mantener compatibilidad
    con el sistema anterior de SIGNIA.

    Internamente utiliza la nueva función
    subir_archivo().
    """

    return subir_archivo(
        contenido=contenido,
        ruta=ruta,
        tipo_contenido=tipo_contenido
    )


# =========================================================
# URL TEMPORAL
# =========================================================

def obtener_url_temporal(
    ruta: str,
    segundos: int = 3600
) -> str:
    """
    Genera una URL firmada temporal para acceder
    de manera segura a un archivo privado.

    Por defecto dura 1 hora.
    """

    if not ruta:
        raise ValueError(
            "La ruta del archivo está vacía"
        )

    respuesta = (
        supabase.storage
        .from_(SUPABASE_BUCKET)
        .create_signed_url(
            ruta,
            segundos
        )
    )

    if isinstance(respuesta, dict):
        url = (
            respuesta.get("signedURL")
            or respuesta.get("signedUrl")
            or respuesta.get("signed_url")
        )

        if url:
            return url

    # Compatibilidad con posibles respuestas
    # tipo objeto de la librería de Supabase.

    url = getattr(
        respuesta,
        "signed_url",
        None
    )

    if url:
        return url

    raise ValueError(
        "No se pudo generar la dirección temporal"
    )


# =========================================================
# COMPROBAR STORAGE
# =========================================================

def comprobar_storage():
    """
    Comprueba que exista conexión con Supabase
    Storage y que el bucket configurado exista.
    """

    try:
        buckets = (
            supabase.storage.list_buckets()
        )

        nombres = []

        for bucket in buckets:
            nombre = getattr(
                bucket,
                "name",
                None
            )

            if nombre:
                nombres.append(nombre)

        if SUPABASE_BUCKET in nombres:

            print(
                "Storage conectado correctamente"
            )

            print(
                "Bucket encontrado:",
                SUPABASE_BUCKET
            )

        else:

            print(
                "Se conectó a Storage, "
                "pero no se encontró el bucket "
                f"{SUPABASE_BUCKET}"
            )

            print(
                "Buckets disponibles:",
                nombres
            )

    except Exception as error:

        print(
            "No se pudo comprobar "
            "Supabase Storage"
        )

        print(
            type(error).__name__,
            str(error)
        )


# =========================================================
# PRUEBA
# =========================================================

if __name__ == "__main__":
    comprobar_storage()