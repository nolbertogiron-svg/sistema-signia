from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import logging

import joblib
import numpy as np
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import obtener_base_datos
from models import Maquina, RegistroMantenimiento, FallaMaquina


router = APIRouter(
    prefix="/prediccion-demo",
    tags=["Predicción experimental"],
)

BASE = Path(__file__).resolve().parent

RUTA_MODELO = (
    BASE
    / "modelo_predictivo"
    / "resultados_manual_simulado"
    / "modelo_manual_simulado.joblib"
)

# Zona horaria de Perú.
PERU = timezone(timedelta(hours=-5))

VARIABLES = [
    "fallas_ultimos_7d",
    "fallas_ultimos_30d",
    "dias_desde_mantenimiento",
]

logger = logging.getLogger(__name__)


def fecha_peru(valor):
    if valor is None:
        return None

    # Los timestamps de Supabase se interpretan en UTC.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)

    return valor.astimezone(PERU).date()


@lru_cache(maxsize=1)
def cargar_modelo():
    try:
        paquete = joblib.load(RUTA_MODELO)

        if paquete["variables"] != VARIABLES:
            raise ValueError("Las variables no coinciden.")

        if int(paquete["horizonte_dias"]) != 7:
            raise ValueError("Horizonte incompatible.")

        umbral = float(paquete["umbral"])

        if not np.isfinite(umbral) or not 0 <= umbral <= 1:
            raise ValueError("Umbral inválido.")

        return paquete

    except Exception:
        logger.exception("No se pudo cargar el modelo.")

        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudo cargar el modelo manual simulado. "
                "Revisa la terminal del backend."
            ),
        )


def consultar_historial(base_datos, maquina_id):
    ahora = datetime.now(timezone.utc)

    registros = (
        base_datos.query(RegistroMantenimiento)
        .filter(
            RegistroMantenimiento.maquina_id == maquina_id,
            RegistroMantenimiento.fecha_hora <= ahora,
        )
        .all()
    )

    fallas = (
        base_datos.query(FallaMaquina)
        .filter(
            FallaMaquina.maquina_id == maquina_id,
            FallaMaquina.fecha_creacion <= ahora,
        )
        .all()
    )

    return registros, fallas


def ultima_fecha(registros, fallas):
    fechas = [
        fecha_peru(registro.fecha_hora)
        for registro in registros
    ]

    fechas.extend(
        fecha_peru(falla.fecha_creacion)
        for falla in fallas
    )

    return max(
        (fecha for fecha in fechas if fecha is not None),
        default=None,
    )


@router.get("/catalogo")
def obtener_catalogo(
    base_datos: Session = Depends(obtener_base_datos),
):
    paquete = cargar_modelo()
    equipos = []

    maquinas = (
        base_datos.query(Maquina)
        .order_by(Maquina.codigo)
        .all()
    )

    for maquina in maquinas:
        registros, fallas = consultar_historial(
            base_datos,
            maquina.id,
        )

        fecha = ultima_fecha(registros, fallas)

        # No inventar una fecha para máquinas sin registros.
        if fecha is None:
            continue

        equipos.append({
            "id": maquina.codigo,
            "nombre": f"Máquina {maquina.codigo}",
            "fechas": [fecha.isoformat()],
        })

    return {
        "modelo": paquete["nombre"],
        "horizonte_dias": 7,
        "horizonte_horas": 168,
        "equipos": equipos,
    }


@router.get("/predecir")
def predecir(
    fecha: date,
    equipo: str = Query(..., min_length=1, max_length=100),
    base_datos: Session = Depends(obtener_base_datos),
):
    paquete = cargar_modelo()

    maquina = (
        base_datos.query(Maquina)
        .filter(Maquina.codigo == equipo)
        .first()
    )

    if maquina is None:
        raise HTTPException(
            status_code=404,
            detail="No existe esa máquina.",
        )

    registros, fallas = consultar_historial(
        base_datos,
        maquina.id,
    )

    fecha_actual = ultima_fecha(registros, fallas)

    if fecha_actual is None:
        raise HTTPException(
            status_code=409,
            detail="La máquina no tiene historial registrado.",
        )

    if fecha != fecha_actual:
        raise HTTPException(
            status_code=409,
            detail=(
                "El historial cambió. Recarga el panel "
                "para consultar la nueva fecha."
            ),
        )

    mantenimientos = [
        fecha_peru(registro.fecha_hora)
        for registro in registros
        if str(registro.tipo_mantenimiento or "")
        .strip()
        .lower() in {"preventivo", "correctivo"}
    ]

    if not mantenimientos:
        raise HTTPException(
            status_code=409,
            detail=(
                "Información insuficiente: no hay un mantenimiento "
                "preventivo o correctivo registrado. Una revisión "
                "normal no cuenta como mantenimiento. Registra solo "
                "eventos realmente realizados o pruebas identificadas."
            ),
        )

    fechas_historial = [
        fecha_peru(registro.fecha_hora)
        for registro in registros
    ] + [
        fecha_peru(falla.fecha_creacion)
        for falla in fallas
    ]

    if (fecha - min(fechas_historial)).days < 30:
        raise HTTPException(
            status_code=409,
            detail=(
                "Información insuficiente: el historial disponible "
                "abarca menos de 30 días. No se completarán "
                "los días faltantes con datos inventados."
            ),
        )

    fechas_fallas = [
        fecha_peru(falla.fecha_creacion)
        for falla in fallas
    ]

    # Contar fallas registradas, tanto pendientes como solucionadas.
    # Solucionarlas no elimina el evento de su historial.
    entradas = pd.DataFrame([{
        "fallas_ultimos_7d": sum(
            fecha - timedelta(days=6) <= dia <= fecha
            for dia in fechas_fallas
        ),
        "fallas_ultimos_30d": sum(
            fecha - timedelta(days=29) <= dia <= fecha
            for dia in fechas_fallas
        ),
        "dias_desde_mantenimiento": (
            fecha - max(mantenimientos)
        ).days,
    }], columns=VARIABLES)

    try:
        modelo = paquete["modelo"]
        posicion = list(modelo.classes_).index(1)

        puntuacion = float(
            modelo.predict_proba(entradas)[0, posicion]
        )

        if not np.isfinite(puntuacion):
            raise ValueError("Puntuación inválida.")

    except Exception:
        logger.exception("Error ejecutando el modelo.")

        raise HTTPException(
            status_code=503,
            detail="No se pudo ejecutar la predicción.",
        )

    umbral = float(paquete["umbral"])
    alerta = puntuacion >= umbral

    desde = fecha + timedelta(days=1)
    hasta = fecha + timedelta(days=7)

    periodo = (
        f"{desde.strftime('%d/%m/%Y')} "
        f"al {hasta.strftime('%d/%m/%Y')}"
    )

    recomendacion = (
        "El modelo experimental sugiere solicitar revisión técnica."
        if alerta
        else "No se emitió alerta experimental; conserva las revisiones "
        "y mantenimientos programados."
    )

    recomendacion += (
        " Se utilizaron los eventos registrados en Supabase. "
        "No se ha verificado que el historial esté completo. "
        "El modelo fue entrenado con datos artificiales y "
        "no está validado para uso real."
    )

    hoy = datetime.now(PERU).date()

    if fecha < hoy:
        recomendacion += (
            " El historial no está actualizado a hoy: "
            "el periodo mostrado parte del último evento registrado."
        )
    else:
        recomendacion += (
            " Los datos de hoy son parciales hasta este momento; "
            "el entrenamiento utilizó días completos."
        )

    return {
        "equipo": f"Máquina {maquina.codigo}",
        "fecha_corte": fecha.isoformat(),
        "modelo": paquete["nombre"],
        "horizonte_dias": 7,
        "horizonte_horas": 168,
        "alerta": bool(alerta),
        "resultado": (
            f"Alerta experimental: {periodo}"
            if alerta
            else f"Sin alerta experimental: {periodo}"
        ),
        "recomendacion": recomendacion,
        "puntuacion": round(puntuacion, 4),
        "umbral": round(umbral, 4),
    }