from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
PUBLICOS = BASE / "datos_publicos"
RESULTADOS = BASE / "resultados_demo"


def contar_eventos(fechas_eventos, fechas_corte, dias):
    eventos = np.sort(
        fechas_eventos.to_numpy(dtype="datetime64[ns]")
    )

    cortes = fechas_corte.to_numpy(dtype="datetime64[ns]")
    inicio = cortes - np.timedelta64(dias, "D")

    # Solo cuenta eventos anteriores al momento de predicción.
    # Incluye el inicio del periodo y excluye la fecha de corte.
    derecha = np.searchsorted(eventos, cortes, side="left")
    izquierda = np.searchsorted(eventos, inicio, side="left")

    return derecha - izquierda


def ampliar():
    archivo_base = RESULTADOS / "dataset_demo_24h.csv"

    rutas = [
        archivo_base,
        PUBLICOS / "PdM_errors.csv",
        PUBLICOS / "PdM_maint.csv",
    ]

    for ruta in rutas:
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo: {ruta}"
            )

    datos = pd.read_csv(
        archivo_base,
        parse_dates=["fecha_corte"],
    )

    errores = pd.read_csv(
        PUBLICOS / "PdM_errors.csv",
        parse_dates=["datetime"],
    )

    mantenimientos = pd.read_csv(
        PUBLICOS / "PdM_maint.csv",
        parse_dates=["datetime"],
    )

    for nombre, tabla, columnas in [
        (
            "dataset",
            datos,
            ["machineID", "fecha_corte", "falla_proximas_24h"],
        ),
        (
            "errores",
            errores,
            ["machineID", "datetime", "errorID"],
        ),
        (
            "mantenimientos",
            mantenimientos,
            ["machineID", "datetime", "comp"],
        ),
    ]:
        faltantes = set(columnas) - set(tabla.columns)

        if faltantes:
            raise ValueError(
                f"Faltan columnas en {nombre}: {faltantes}"
            )

        if tabla[columnas].isna().any().any():
            raise ValueError(
                f"Hay valores vacíos en {nombre}."
            )

    if datos.duplicated(["machineID", "fecha_corte"]).any():
        raise ValueError(
            "Hay ejemplos duplicados por máquina y fecha."
        )

    tipos_error = [
        "error1", "error2", "error3", "error4", "error5"
    ]

    componentes = [
        "comp1", "comp2", "comp3", "comp4"
    ]

    if not set(errores["errorID"]).issubset(tipos_error):
        raise ValueError("Hay tipos de error no esperados.")

    if not set(mantenimientos["comp"]).issubset(componentes):
        raise ValueError("Hay componentes no esperados.")

    nuevas = []

    for tipo in tipos_error:
        columna = f"{tipo}_ultimos_7d"
        datos[columna] = 0
        nuevas.append(columna)

    for componente in componentes:
        columna = f"mantenimiento_{componente}_ultimos_30d"
        datos[columna] = 0
        nuevas.append(columna)

    for maquina, grupo in datos.groupby("machineID"):
        indices = grupo.index
        cortes = grupo["fecha_corte"]

        errores_maquina = errores[
            errores["machineID"] == maquina
        ]

        mantenimientos_maquina = mantenimientos[
            mantenimientos["machineID"] == maquina
        ]

        for tipo in tipos_error:
            fechas = errores_maquina.loc[
                errores_maquina["errorID"] == tipo,
                "datetime",
            ]

            datos.loc[indices, f"{tipo}_ultimos_7d"] = (
                contar_eventos(fechas, cortes, dias=7)
            )

        for componente in componentes:
            fechas = mantenimientos_maquina.loc[
                mantenimientos_maquina["comp"] == componente,
                "datetime",
            ]

            columna = (
                f"mantenimiento_{componente}_ultimos_30d"
            )

            datos.loc[indices, columna] = contar_eventos(
                fechas,
                cortes,
                dias=30,
            )

    datos[nuevas] = datos[nuevas].astype("int64")

    # Exigir al menos 30 días desde el inicio observado
    # de la telemetría evita periodos iniciales incompletos.
    telemetria = pd.read_csv(
        PUBLICOS / "PdM_telemetry.csv",
        usecols=["machineID", "datetime"],
        parse_dates=["datetime"],
    )

    inicios = telemetria.groupby("machineID")["datetime"].min()
    inicio_por_fila = datos["machineID"].map(inicios)

    if inicio_por_fila.isna().any():
        raise ValueError(
            "Hay máquinas sin telemetría de referencia."
        )

    suficientes = (
        datos["fecha_corte"] - inicio_por_fila
        >= pd.Timedelta(days=30)
    )

    datos = datos.loc[suficientes].copy()

    if datos.empty:
        raise ValueError(
            "No quedaron ejemplos con historial suficiente."
        )

    destino = RESULTADOS / "dataset_demo_ampliado_24h.csv"

    datos.to_csv(
        destino,
        index=False,
        encoding="utf-8-sig",
    )

    print("Dataset ampliado creado.")
    print("Ejemplos:", len(datos))
    print("Máquinas:", datos["machineID"].nunique())
    print("Variables nuevas:", len(nuevas))
    print(
        "Ejemplos con falla futura:",
        int(datos["falla_proximas_24h"].sum()),
    )
    print("Desde:", datos["fecha_corte"].min())
    print("Hasta:", datos["fecha_corte"].max())
    print("Archivo:", destino)
    print("El dataset anterior se conserva.")
    print("Todavía no se reentrenaron los modelos.")
    print("Datos públicos de demostración, no de SIGNIA.")


if __name__ == "__main__":
    ampliar()