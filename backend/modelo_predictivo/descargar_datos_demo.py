from pathlib import Path
from urllib.request import urlopen
import csv
import shutil


BASE = Path(__file__).resolve().parent
DESTINO = BASE / "datos_publicos"

URL_BASE = (
    "https://raw.githubusercontent.com/"
    "microsoft/sqlworkshops/master/"
    "SQLServerAndAzureMachineLearning/"
    "ML%20Services%20for%20SQL%20Server/data/"
)

ARCHIVOS = {
    "PdM_telemetry.csv": {
        "datetime", "machineID",
        "volt", "rotate", "pressure", "vibration"
    },
    "PdM_errors.csv": {
        "datetime", "machineID", "errorID"
    },
    "PdM_maint.csv": {
        "datetime", "machineID", "comp"
    },
    "PdM_failures.csv": {
        "datetime", "machineID", "failure"
    },
    "PdM_machines.csv": {
        "machineID", "model", "age"
    }
}


def comprobar_columnas(ruta, columnas):
    with ruta.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:
        lector = csv.reader(archivo)
        encabezados = next(lector, [])

    if not columnas.issubset(set(encabezados)):
        raise ValueError(
            f"Las columnas de {ruta.name} no son las esperadas."
        )


def descargar():
    DESTINO.mkdir(parents=True, exist_ok=True)

    for nombre, columnas in ARCHIVOS.items():
        ruta = DESTINO / nombre

        if ruta.exists():
            comprobar_columnas(ruta, columnas)
            print("Ya existe y tiene las columnas correctas:", nombre)
            continue

        temporal = DESTINO / (nombre + ".part")

        print("Descargando:", nombre, flush=True)

        try:
            with urlopen(
                URL_BASE + nombre,
                timeout=120
            ) as respuesta:
                with temporal.open("wb") as archivo:
                    shutil.copyfileobj(respuesta, archivo)

            comprobar_columnas(temporal, columnas)
            temporal.replace(ruta)

            megabytes = ruta.stat().st_size / (1024 * 1024)

            print(
                f"Descarga terminada: {nombre} "
                f"({megabytes:.2f} MB)"
            )

        except Exception as error:
            if temporal.exists():
                temporal.unlink()

            raise RuntimeError(
                f"No se pudo descargar {nombre}. "
                "Comprueba tu conexión y vuelve a ejecutar."
            ) from error

    print()
    print("Los cinco archivos están disponibles.")
    print("Carpeta:", DESTINO)
    print("Estos datos son del ejemplo público, no de SIGNIA.")
    print("Todavía no se entrenaron los modelos.")


if __name__ == "__main__":
    descargar()