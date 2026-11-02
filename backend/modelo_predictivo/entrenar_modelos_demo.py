from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
    brier_score_loss
)


BASE = Path(__file__).resolve().parent
CARPETA = BASE / "resultados_demo"
OBJETIVO = "falla_proximas_24h"

NUMERICAS = [
    sensor + sufijo
    for sensor in ["volt", "rotate", "pressure", "vibration"]
    for sufijo in ["_media24h", "_desv24h", "_ultimo"]
] + ["age"]

VARIABLES = NUMERICAS + ["model"]


def medir(y, probabilidades, umbral):
    predicciones = (probabilidades >= umbral).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y,
        predicciones,
        labels=[0, 1]
    ).ravel()

    return {
        "precision": float(precision_score(
            y, predicciones, zero_division=0
        )),
        "sensibilidad": float(recall_score(
            y, predicciones, zero_division=0
        )),
        "f1": float(f1_score(
            y, predicciones, zero_division=0
        )),
        "exactitud": float(accuracy_score(y, predicciones)),
        "AP": float(average_precision_score(y, probabilidades)),
        "brier": float(brier_score_loss(y, probabilidades)),
        "verdaderos_negativos": int(tn),
        "falsas_alertas": int(fp),
        "fallas_no_detectadas": int(fn),
        "fallas_detectadas": int(tp)
    }


def entrenar():
    datos = pd.read_csv(
        CARPETA / "dataset_demo_24h.csv",
        parse_dates=["fecha_corte"]
    )

    if datos.duplicated(["machineID", "fecha_corte"]).any():
        raise ValueError("Hay ejemplos duplicados por maquina y fecha.")

    if datos[VARIABLES + [OBJETIVO]].isna().any().any():
        raise ValueError("Hay valores vacios en las variables.")

    if not set(datos[OBJETIVO].unique()).issubset({0, 1}):
        raise ValueError("El objetivo debe contener solamente 0 y 1.")

    corte_validacion = pd.Timestamp("2015-08-01")
    corte_prueba = pd.Timestamp("2015-10-01")

    fin_etiqueta = (
        datos["fecha_corte"] + pd.Timedelta(hours=24)
    )

    # Evitar que los resultados futuros del entrenamiento
    # invadan el periodo de validacion.
    entrenamiento = datos.loc[
        fin_etiqueta < corte_validacion
    ].copy()

    validacion = datos.loc[
        (datos["fecha_corte"] >= corte_validacion)
        & (fin_etiqueta < corte_prueba)
    ].copy()

    prueba = datos.loc[
        datos["fecha_corte"] >= corte_prueba
    ].copy()

    partes = [
        ("Entrenamiento", entrenamiento),
        ("Validacion", validacion),
        ("Prueba", prueba)
    ]

    for nombre, parte in partes:
        if parte.empty or parte[OBJETIVO].nunique() != 2:
            raise ValueError(
                f"{nombre} necesita ejemplos de ambas clases."
            )

        print(
            nombre,
            ":",
            len(parte),
            "ejemplos;",
            int(parte[OBJETIVO].sum()),
            "positivos",
            flush=True
        )

    candidatos = {
        "regresion_logistica": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1
        )
    }

    entrenados = {}
    filas_validacion = []

    for nombre, clasificador in candidatos.items():
        print("Entrenando:", nombre, flush=True)

        transformacion = ColumnTransformer([
            (
                "numericas",
                StandardScaler(),
                NUMERICAS
            ),
            (
                "categoricas",
                OneHotEncoder(handle_unknown="ignore"),
                ["model"]
            )
        ])

        modelo = Pipeline([
            ("preparacion", transformacion),
            ("clasificador", clasificador)
        ])

        # La preparacion se aprende solo con entrenamiento.
        modelo.fit(
            entrenamiento[VARIABLES],
            entrenamiento[OBJETIVO]
        )

        probabilidades = modelo.predict_proba(
            validacion[VARIABLES]
        )[:, 1]

        precision, sensibilidad, umbrales = (
            precision_recall_curve(
                validacion[OBJETIVO],
                probabilidades
            )
        )

        valores_f1 = (
            2 * precision[:-1] * sensibilidad[:-1]
            / np.maximum(
                precision[:-1] + sensibilidad[:-1],
                1e-12
            )
        )

        # Elegir el umbral usando solo validacion.
        umbral = float(
            umbrales[int(np.argmax(valores_f1))]
        )

        resultado = medir(
            validacion[OBJETIVO],
            probabilidades,
            umbral
        )

        filas_validacion.append({
            "modelo": nombre,
            "umbral": umbral,
            **resultado
        })

        entrenados[nombre] = (modelo, umbral)

    # Elegir el modelo antes de consultar los resultados de prueba.
    mejor = sorted(
        filas_validacion,
        key=lambda resultado: (
            resultado["AP"],
            resultado["f1"]
        ),
        reverse=True
    )[0]["modelo"]

    filas_prueba = []

    for nombre, (modelo, umbral) in entrenados.items():
        probabilidades = modelo.predict_proba(
            prueba[VARIABLES]
        )[:, 1]

        filas_prueba.append({
            "modelo": nombre,
            "umbral": umbral,
            **medir(
                prueba[OBJETIVO],
                probabilidades,
                umbral
            )
        })

    # Referencia sencilla: misma puntuacion para todos,
    # basada en la frecuencia de fallas del entrenamiento.
    prevalencia = float(entrenamiento[OBJETIVO].mean())
    referencia = np.full(len(prueba), prevalencia)

    filas_prueba.append({
        "modelo": "referencia_sin_alertas",
        "umbral": 0.5,
        **medir(prueba[OBJETIVO], referencia, 0.5)
    })

    pd.DataFrame(filas_validacion).to_csv(
        CARPETA / "comparacion_validacion.csv",
        index=False,
        encoding="utf-8-sig"
    )

    tabla = pd.DataFrame(filas_prueba)

    tabla.to_csv(
        CARPETA / "comparacion_prueba.csv",
        index=False,
        encoding="utf-8-sig"
    )

    modelo, umbral = entrenados[mejor]

    paquete = {
        "modelo": modelo,
        "nombre": mejor,
        "umbral": umbral,
        "variables": VARIABLES,
        "horizonte_horas": 24,
        "origen": "Microsoft PdM, datos publicos de demostracion",
        "uso": "experimental; no validado para SIGNIA",
        "version_sklearn": sklearn.__version__,
        "probabilidades_calibradas": False
    }

    joblib.dump(
        paquete,
        CARPETA / "modelo_demo.joblib"
    )

    metadata = {
        clave: valor
        for clave, valor in paquete.items()
        if clave != "modelo"
    }

    metadata["seleccion"] = (
        "Mayor AP de validacion; desempate por F1"
    )
    metadata["umbral_seleccion"] = (
        "Mayor F1 en validacion"
    )
    metadata["validacion"] = filas_validacion
    metadata["prueba"] = filas_prueba

    metadata["periodos"] = {
        nombre: {
            "desde": str(parte["fecha_corte"].min()),
            "hasta": str(parte["fecha_corte"].max()),
            "filas": len(parte),
            "positivos": int(parte[OBJETIVO].sum())
        }
        for nombre, parte in partes
    }

    (CARPETA / "evaluacion_demo.json").write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\nResultados de prueba:")

    print(
        tabla[[
            "modelo",
            "precision",
            "sensibilidad",
            "f1",
            "AP",
            "exactitud"
        ]].round(4).to_string(index=False)
    )

    print("\nModelo elegido por validacion:", mejor)
    print("Archivo guardado: modelo_demo.joblib")
    print(
        "Scores sin calibrar: no interpretar como "
        "porcentajes de riesgo real de SIGNIA."
    )


if __name__ == "__main__":
    entrenar()