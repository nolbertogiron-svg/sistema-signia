from pathlib import Path
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos_publicos"
SALIDA = BASE / "resultados_demo"

SENSORES = ["volt", "rotate", "pressure", "vibration"]


def crear_dataset():
    telemetria = pd.read_csv(DATOS / "PdM_telemetry.csv")
    fallas = pd.read_csv(DATOS / "PdM_failures.csv")
    maquinas = pd.read_csv(DATOS / "PdM_machines.csv")

    for tabla in [telemetria, fallas]:
        tabla["datetime"] = pd.to_datetime(
            tabla["datetime"],
            errors="raise"
        )

    if telemetria.duplicated(["machineID", "datetime"]).any():
        raise ValueError(
            "Hay mediciones duplicadas para una maquina y hora."
        )

    if maquinas["machineID"].duplicated().any():
        raise ValueError(
            "Hay identificadores duplicados en maquinas."
        )

    if not set(fallas["machineID"]).issubset(
        set(telemetria["machineID"])
    ):
        raise ValueError("Hay fallas de maquinas sin telemetria.")

    if telemetria[SENSORES].isna().any().any():
        raise ValueError("Hay sensores sin valor.")

    for sensor in SENSORES:
        telemetria[sensor] = pd.to_numeric(
            telemetria[sensor],
            errors="raise"
        )

    if not np.isfinite(telemetria[SENSORES].to_numpy()).all():
        raise ValueError("Hay valores de sensores no finitos.")

    partes = []
    variables = []

    for sensor in SENSORES:
        variables.extend([
            sensor + "_media24h",
            sensor + "_desv24h",
            sensor + "_ultimo"
        ])

    for identificador, grupo in telemetria.groupby("machineID"):
        grupo = grupo.sort_values("datetime").set_index("datetime")

        diferencias = grupo.index.to_series().diff().dropna()

        if not diferencias.eq(pd.Timedelta(hours=1)).all():
            raise ValueError(
                f"La maquina {identificador} tiene huecos horarios."
            )

        entradas = pd.DataFrame(index=grupo.index)

        # Solo mediciones anteriores a la fecha de corte.
        for sensor in SENSORES:
            pasado = grupo[sensor].shift(1)

            entradas[sensor + "_media24h"] = (
                pasado.rolling(24, min_periods=24).mean()
            )

            entradas[sensor + "_desv24h"] = (
                pasado.rolling(24, min_periods=24).std()
            )

            entradas[sensor + "_ultimo"] = pasado

        fechas_fallas = pd.DatetimeIndex(
            fallas.loc[
                fallas["machineID"] == identificador,
                "datetime"
            ]
        ).unique().sort_values()

        tiempos = entradas.index
        fin_observado = grupo.index.max()

        # Un ejemplo diario por maquina.
        # Excluir cortes sin 24 horas posteriores observadas
        # y cortes donde la falla ya esta ocurriendo.
        seleccion = (
            (tiempos.hour == 0)
            & (
                tiempos + pd.Timedelta(hours=24)
                <= fin_observado
            )
            & ~tiempos.isin(fechas_fallas)
        )

        entradas = (
            entradas.loc[seleccion]
            .dropna(subset=variables)
            .copy()
        )

        etiquetas = []

        for momento in entradas.index:
            posicion = fechas_fallas.searchsorted(
                momento,
                side="right"
            )

            ocurrira = (
                posicion < len(fechas_fallas)
                and fechas_fallas[posicion]
                <= momento + pd.Timedelta(hours=24)
            )

            etiquetas.append(int(ocurrira))

        entradas["falla_proximas_24h"] = etiquetas
        entradas["machineID"] = identificador
        entradas.index.name = "fecha_corte"

        partes.append(entradas.reset_index())

    dataset = pd.concat(partes, ignore_index=True)

    dataset = dataset.merge(
        maquinas[["machineID", "model", "age"]],
        on="machineID",
        how="left",
        validate="many_to_one"
    )

    if dataset[["model", "age"]].isna().any().any():
        raise ValueError(
            "Faltan datos de modelo o antiguedad."
        )

    dataset = dataset.sort_values(["fecha_corte", "machineID"])

    SALIDA.mkdir(exist_ok=True)

    ruta = SALIDA / "dataset_demo_24h.csv"

    dataset.to_csv(
        ruta,
        index=False,
        encoding="utf-8-sig"
    )

    print("Dataset experimental creado.")
    print("Filas:", len(dataset))
    print("Maquinas:", dataset["machineID"].nunique())

    print(
        "Ejemplos con falla futura:",
        int(dataset["falla_proximas_24h"].sum())
    )

    print(
        "Ejemplos sin falla futura:",
        int((dataset["falla_proximas_24h"] == 0).sum())
    )

    print("Desde:", dataset["fecha_corte"].min())
    print("Hasta:", dataset["fecha_corte"].max())
    print("Archivo:", ruta)
    print("Datos publicos de demostracion, no de SIGNIA.")


if __name__ == "__main__":
    crear_dataset()