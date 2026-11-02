from pathlib import Path
import shutil

import entrenar_modelos_demo as entrenamiento


BASE = Path(__file__).resolve().parent

ORIGEN = (
    BASE
    / "resultados_demo"
    / "dataset_demo_ampliado_24h.csv"
)

DESTINO = BASE / "resultados_ampliados"


def ejecutar():
    if not ORIGEN.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset ampliado: {ORIGEN}"
        )

    DESTINO.mkdir(parents=True, exist_ok=True)

    # El entrenamiento anterior espera este nombre de archivo.
    # La copia queda en una carpeta independiente.
    shutil.copyfile(
        ORIGEN,
        DESTINO / "dataset_demo_24h.csv",
    )

    nuevas_variables = [
        "error1_ultimos_7d",
        "error2_ultimos_7d",
        "error3_ultimos_7d",
        "error4_ultimos_7d",
        "error5_ultimos_7d",
        "mantenimiento_comp1_ultimos_30d",
        "mantenimiento_comp2_ultimos_30d",
        "mantenimiento_comp3_ultimos_30d",
        "mantenimiento_comp4_ultimos_30d",
    ]

    entrenamiento.CARPETA = DESTINO

    entrenamiento.NUMERICAS = (
        entrenamiento.NUMERICAS + nuevas_variables
    )

    entrenamiento.VARIABLES = (
        entrenamiento.NUMERICAS + ["model"]
    )

    print("Entrenamiento con historial ampliado.")
    print("Resultados guardados en:", DESTINO)
    print("Se conserva la selección por AP de validación.")
    print()

    entrenamiento.entrenar()

    print()
    print("Comparación experimental con datos públicos.")
    print(
        "La prueba reutilizada no constituye "
        "una evaluación independiente de la mejora."
    )


if __name__ == "__main__":
    ejecutar()