from pathlib import Path
from datetime import date
import json
import unicodedata

import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


BASE = Path(__file__).resolve().parent
SALIDA = BASE / "resultados_manual_simulado"
INVENTARIO = BASE / "resultados" / "inventario_2026.csv"

VARIABLES = [
    "fallas_ultimos_7d",
    "fallas_ultimos_30d",
    "dias_desde_mantenimiento",
]

OBJETIVO = "falla_proximos_7d"
SEMILLA = 42


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    ).lower().strip()


def obtener_codigos():
    if not INVENTARIO.exists():
        raise FileNotFoundError(
            "Falta resultados/inventario_2026.csv. "
            "Es el archivo generado por preparar_datos.py."
        )

    tabla = pd.read_csv(
        INVENTARIO,
        dtype=str,
        encoding="utf-8-sig",
    )

    candidatos = [
        columna
        for columna in tabla.columns
        if "codigo" in normalizar(columna)
    ]

    if len(candidatos) != 1:
        raise ValueError(
            "No se pudo identificar una única columna de código. "
            f"Columnas disponibles: {list(tabla.columns)}"
        )

    codigos = (
        tabla[candidatos[0]]
        .dropna()
        .str.strip()
    )

    codigos = codigos[codigos != ""].unique()

    if len(codigos) < 2:
        raise ValueError("Se necesitan al menos dos máquinas.")

    return codigos


def generar_historial(codigos):
    rng = np.random.default_rng(SEMILLA)

    # Un año simulado hasta la fecha de ejecución.
    fechas = pd.date_range(
        end=pd.Timestamp(date.today()),
        periods=365,
        freq="D",
    )

    filas = []

    for codigo in codigos:
        fallas = []
        dias_mantenimiento = int(rng.integers(0, 30))

        # Diferencias artificiales entre equipos.
        propension = rng.uniform(0.003, 0.015)

        for indice, fecha in enumerate(fechas):
            previas7 = sum(fallas[max(0, indice - 7):indice])
            previas30 = sum(fallas[max(0, indice - 30):indice])

            # Reglas hipotéticas de simulación.
            # No proceden de un estudio de las máquinas reales.
            probabilidad = min(
                0.35,
                propension
                + 0.0015 * dias_mantenimiento
                + 0.035 * previas7,
            )

            falla_hoy = int(rng.random() < probabilidad)

            mantenimiento_hoy = int(
                rng.random() < (
                    0.65 if falla_hoy else 0.025
                )
            )

            filas.append({
                "codigo": str(codigo),
                "fecha": fecha,
                "falla_registrada": falla_hoy,
                "mantenimiento_realizado": mantenimiento_hoy,
                "origen": "simulado",
            })

            fallas.append(falla_hoy)

            dias_mantenimiento = (
                0
                if mantenimiento_hoy
                else dias_mantenimiento + 1
            )

    return pd.DataFrame(filas)


def preparar_dataset(historial):
    filas = []

    for codigo, grupo in historial.groupby("codigo"):
        grupo = grupo.sort_values("fecha").reset_index(drop=True)

        fallas = grupo["falla_registrada"].to_numpy()
        mantenimientos = grupo["mantenimiento_realizado"].to_numpy()

        ultimo_mantenimiento = None

        for indice, fila in grupo.iterrows():
            if mantenimientos[indice]:
                ultimo_mantenimiento = indice

            # Consulta al cierre del día.
            # Usamos solo observaciones disponibles hasta ese día.
            if indice < 30 or ultimo_mantenimiento is None:
                continue

            registro = {
                "codigo": str(codigo),
                "fecha_corte": fila["fecha"],
                "fallas_ultimos_7d": int(
                    fallas[indice - 6:indice + 1].sum()
                ),
                "fallas_ultimos_30d": int(
                    fallas[indice - 29:indice + 1].sum()
                ),
                "dias_desde_mantenimiento": (
                    indice - ultimo_mantenimiento
                ),
                "origen": "simulado",
            }

            # Si no conocemos los siete días posteriores,
            # dejamos la etiqueta vacía; nunca asumimos "sin falla".
            registro[OBJETIVO] = (
                int(fallas[indice + 1:indice + 8].sum() > 0)
                if indice + 7 < len(grupo)
                else np.nan
            )

            filas.append(registro)

    return pd.DataFrame(filas)


def elegir_umbral(y, puntuaciones):
    precision, sensibilidad, umbrales = precision_recall_curve(
        y, puntuaciones
    )

    denominador = precision[:-1] + sensibilidad[:-1]

    f1 = np.divide(
        2 * precision[:-1] * sensibilidad[:-1],
        denominador,
        out=np.zeros_like(denominador),
        where=denominador > 0,
    )

    return float(umbrales[int(np.argmax(f1))])


def evaluar(y, puntuaciones, umbral):
    predicciones = (puntuaciones >= umbral).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y, predicciones, labels=[0, 1]
    ).ravel()

    return {
        "precision": float(
            precision_score(y, predicciones, zero_division=0)
        ),
        "sensibilidad": float(
            recall_score(y, predicciones, zero_division=0)
        ),
        "f1": float(
            f1_score(y, predicciones, zero_division=0)
        ),
        "AP": float(average_precision_score(y, puntuaciones)),
        "fallas_detectadas": int(tp),
        "fallas_no_detectadas": int(fn),
        "falsas_alertas": int(fp),
        "verdaderos_negativos": int(tn),
    }


def ejecutar():
    SALIDA.mkdir(parents=True, exist_ok=True)

    codigos = obtener_codigos()
    historial = generar_historial(codigos)
    dataset = preparar_dataset(historial)

    historial.to_csv(
        SALIDA / "historial_manual_simulado.csv",
        index=False,
        encoding="utf-8-sig",
    )

    dataset.to_csv(
        SALIDA / "dataset_manual_simulado.csv",
        index=False,
        encoding="utf-8-sig",
    )

    etiquetados = dataset.dropna(subset=[OBJETIVO]).copy()
    etiquetados[OBJETIVO] = etiquetados[OBJETIVO].astype(int)

    fechas = sorted(etiquetados["fecha_corte"].unique())
    corte_validacion = pd.Timestamp(fechas[int(len(fechas) * 0.65)])
    corte_prueba = pd.Timestamp(fechas[int(len(fechas) * 0.82)])

    fin_objetivo = (
        etiquetados["fecha_corte"] + pd.Timedelta(days=7)
    )

    # Separación temporal con siete días de separación
    # para que las etiquetas no crucen entre periodos.
    entrenamiento = etiquetados[
        fin_objetivo < corte_validacion
    ]

    validacion = etiquetados[
        (etiquetados["fecha_corte"] >= corte_validacion)
        & (fin_objetivo < corte_prueba)
    ]

    prueba = etiquetados[
        etiquetados["fecha_corte"] >= corte_prueba
    ]

    for nombre, parte in [
        ("Entrenamiento", entrenamiento),
        ("Validación", validacion),
        ("Prueba", prueba),
    ]:
        if parte.empty or parte[OBJETIVO].nunique() != 2:
            raise ValueError(
                f"{nombre} necesita ejemplos con y sin falla futura."
            )

        print(
            nombre,
            len(parte),
            "ejemplos;",
            int(parte[OBJETIVO].sum()),
            "positivos",
        )

    modelos = {
        "regresion_logistica": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=SEMILLA,
            ),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=15,
            class_weight="balanced_subsample",
            random_state=SEMILLA,
            n_jobs=-1,
        ),
    }

    resultados_validacion = []
    umbrales = {}

    for nombre, modelo in modelos.items():
        print("Entrenando:", nombre, flush=True)

        modelo.fit(
            entrenamiento[VARIABLES],
            entrenamiento[OBJETIVO],
        )

        puntuaciones = modelo.predict_proba(
            validacion[VARIABLES]
        )[:, 1]

        umbral = elegir_umbral(
            validacion[OBJETIVO],
            puntuaciones,
        )

        umbrales[nombre] = umbral

        resultados_validacion.append({
            "modelo": nombre,
            "umbral": umbral,
            **evaluar(
                validacion[OBJETIVO],
                puntuaciones,
                umbral,
            ),
        })

    tabla_validacion = pd.DataFrame(resultados_validacion)

    # Criterio fijado antes de consultar la prueba:
    # mayor F1 de validación; desempate por AP.
    elegido = tabla_validacion.sort_values(
        ["f1", "AP"],
        ascending=False,
    ).iloc[0]["modelo"]

    resultados_prueba = []

    for nombre, modelo in modelos.items():
        puntuaciones = modelo.predict_proba(
            prueba[VARIABLES]
        )[:, 1]

        resultados_prueba.append({
            "modelo": nombre,
            **evaluar(
                prueba[OBJETIVO],
                puntuaciones,
                umbrales[nombre],
            ),
        })

    # Referencia: siempre responder "sin alerta".
    resultados_prueba.append({
        "modelo": "referencia_sin_alertas",
        **evaluar(
            prueba[OBJETIVO],
            np.zeros(len(prueba)),
            0.5,
        ),
    })

    tabla_prueba = pd.DataFrame(resultados_prueba)

    tabla_validacion.to_csv(
        SALIDA / "comparacion_validacion.csv",
        index=False,
        encoding="utf-8-sig",
    )

    tabla_prueba.to_csv(
        SALIDA / "comparacion_prueba.csv",
        index=False,
        encoding="utf-8-sig",
    )

    paquete = {
        "modelo": modelos[elegido],
        "nombre": elegido,
        "variables": VARIABLES,
        "umbral": umbrales[elegido],
        "horizonte_dias": 7,
        "origen": "registros manuales artificialmente simulados",
        "semilla": SEMILLA,
        "probabilidades_calibradas": False,
        "uso": "demostracion; no validado con fallas reales",
        "momento_consulta": "cierre del dia",
    }

    joblib.dump(
        paquete,
        SALIDA / "modelo_manual_simulado.joblib",
    )

    metadata = {
        clave: valor
        for clave, valor in paquete.items()
        if clave != "modelo"
    }

    metadata["seleccion"] = "Mayor F1 en validacion"
    metadata["corte_validacion"] = corte_validacion.isoformat()
    metadata["corte_prueba"] = corte_prueba.isoformat()

    with open(
        SALIDA / "informacion_modelo.json",
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(metadata, archivo, indent=2, ensure_ascii=False)

    # Último estado simulado disponible de cada máquina.
    ultimos = (
        dataset.sort_values("fecha_corte")
        .groupby("codigo")
        .tail(1)
        .drop(columns=[OBJETIVO])
    )

    ultimos.to_csv(
        SALIDA / "estados_actuales_simulados.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\nRESULTADOS DE PRUEBA SIMULADA")
    print(tabla_prueba.round(4).to_string(index=False))
    print("\nModelo elegido por validación:", elegido)
    print("Carpeta:", SALIDA)
    print(
        "\nLos códigos proceden del inventario; "
        "los eventos fueron generados artificialmente."
    )
    print(
        "No se utilizaron ni modificaron los registros de Supabase."
    )
    print(
        "Estos resultados no demuestran rendimiento en fallas reales."
    )


if __name__ == "__main__":
    ejecutar()