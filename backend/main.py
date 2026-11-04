from typing import List, Optional

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import logging

from uuid import uuid4

from fastapi import (

    BackgroundTasks,

    Depends,

    FastAPI,

    File,

    Form,

    HTTPException,

    UploadFile,

    status,

)

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, text

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from auth import router as auth_router

from database import Base, engine, obtener_base_datos

from models import (

    ArchivoMantenimiento,

    FallaMaquina,

    Maquina,

    RegistroMantenimiento,

    Trabajador,

    Usuario,

)

from notificaciones import notificar_nuevo_activo, notificar_nuevo_registro

from schemas import (
    ActivoCrear,

    EstadoMaquinaActualizar,

    FallaCrear,

    FallaRespuesta,

    MaquinaRespuesta,

    RegistroRespuesta,

)

from seguridad import permitir_roles, obtener_trabajador_actual

from storage_supabase import (

    eliminar_archivos,
    obtener_url_temporal,

    subir_archivo,

)

from usuarios import router as usuarios_router

# Base.metadata.create_all(bind=engine)

ROLES_CONSULTA = (

    "proveedor",

    "tecnico",

    "operativo",

    "administracion",

    "administrador",

)

ROLES_REGISTRO = (

    "proveedor",

    "tecnico",

    "operativo",

    "administracion",

    "administrador",

)

ROLES_ADMINISTRATIVOS = (

    "administracion",

    "administrador",

)

app = FastAPI(

    title="API SIGNIA",

    description=(

        "API para la gestión de máquinas "

        "y mantenimientos de SIGNIA"

    ),

    version="2.0.0",

)

app.include_router(auth_router)

app.include_router(usuarios_router)

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"],

)

TIPOS_FOTOGRAFIA = {

    "image/jpeg": ".jpg",

    "image/png": ".png",

}

TIPOS_VIDEO = {

    "video/mp4": ".mp4",

    "video/webm": ".webm",

}

TIPO_PDF = "application/pdf"

LIMITE_FOTOGRAFIA = 5 * 1024 * 1024

LIMITE_VIDEO = 50 * 1024 * 1024

LIMITE_PDF = 10 * 1024 * 1024

def limpiar_texto(

    valor: Optional[str]

) -> str:

    if valor is None:

        return ""

    return valor.strip()

def contar_fallas_pendientes(

    base_datos: Session,

    maquina_id: int

) -> int:

    return (

        base_datos.query(

            func.count(FallaMaquina.id)

        )

        .filter(

            FallaMaquina.maquina_id == maquina_id,

            FallaMaquina.estado == "pendiente"

        )

        .scalar()

        or 0

    )

def obtener_extension_archivo(

    archivo: UploadFile,

    tipos_permitidos: dict,

) -> str:

    extension = tipos_permitidos.get(

        archivo.content_type

    )

    if not extension:

        raise HTTPException(

            status_code=400,

            detail=(

                f"Tipo de archivo no permitido: "

                f"{archivo.filename}"

            ),

        )

    return extension

async def leer_archivo_validado(

    archivo: UploadFile,

    tipos_permitidos: dict,

    limite_bytes: int,

    descripcion: str,

):

    extension = obtener_extension_archivo(

        archivo,

        tipos_permitidos,

    )

    contenido = await archivo.read(limite_bytes + 1)

    if not contenido:

        raise HTTPException(

            status_code=400,

            detail=(

                f"El archivo {archivo.filename} "

                f"está vacío"

            ),

        )

    if len(contenido) > limite_bytes:

        limite_mb = (

            limite_bytes // (1024 * 1024)

        )

        raise HTTPException(

            status_code=400,

            detail=(

                f"{descripcion} "

                f"{archivo.filename} supera "

                f"el límite de {limite_mb} MB"

            ),

        )

    return contenido, extension

def construir_archivos_registro(

    registro: RegistroMantenimiento,

):

    resultado = []

    for archivo in registro.archivos:

        resultado.append(

            {

                "id": archivo.id,

                "registro_id":

                    archivo.registro_id,

                "tipo":

                    archivo.tipo,

                "nombre_original":

                    archivo.nombre_original,

                "tipo_contenido":

                    archivo.tipo_contenido,

                "fecha_creacion":

                    archivo.fecha_creacion,

            }

        )

    return resultado

@app.get("/")

def inicio():

    return {

        "mensaje":

            "API SIGNIA funcionando correctamente",

        "version": "2.0.0",

        "base_datos":

            "Supabase PostgreSQL",

        "archivos":

            "Supabase Storage",

    }

@app.get("/salud")

def comprobar_salud(

    base_datos: Session = Depends(

        obtener_base_datos

    ),

):

    try:

        base_datos.execute(

            text("SELECT 1")

        )

        return {

            "estado": "correcto",

            "base_datos": "conectada",

            "archivos":

                "Supabase Storage",

        }

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=(

                "No se pudo conectar con "

                "la base de datos"

            ),

        ) from error

@app.get("/resumen")
def obtener_resumen(
    base_datos: Session = Depends(
        obtener_base_datos
    ),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(
        permitir_roles(*ROLES_CONSULTA)
    ),
):
    total_maquinas = (
        base_datos.query(
            func.count(Maquina.id)
        )
        .scalar()
        or 0
    )

    equipos_inoperativos = base_datos.query(func.count(Maquina.id)).filter(Maquina.estado_equipo == "inoperativo").scalar() or 0
    resumen_categorias = {}
    for categoria in ("maquinaria", "infraestructura", "equipo"):
        filas = base_datos.query(Maquina.estado_equipo, func.count(Maquina.id)).filter(Maquina.categoria == categoria).group_by(Maquina.estado_equipo).all()
        resumen_categorias[categoria] = dict(filas)

    total_registros = (
        base_datos.query(
            func.count(
                RegistroMantenimiento.id
            )
        )
        .scalar()
        or 0
    )

    maquinas_con_mantenimiento = (
        base_datos.query(
            func.count(
                func.distinct(
                    RegistroMantenimiento.maquina_id
                )
            )
        )
        .scalar()
        or 0
    )

    maquinas_sin_mantenimiento = max(
        total_maquinas
        - maquinas_con_mantenimiento,
        0,
    )

    total_preventivos = (
        base_datos.query(
            func.count(
                RegistroMantenimiento.id
            )
        )
        .filter(
            RegistroMantenimiento.tipo_mantenimiento
            == "preventivo"
        )
        .scalar()
        or 0
    )

    total_correctivos = (
        base_datos.query(
            func.count(
                RegistroMantenimiento.id
            )
        )
        .filter(
            RegistroMantenimiento.tipo_mantenimiento
            == "correctivo"
        )
        .scalar()
        or 0
    )

    total_observaciones = (
        base_datos.query(
            func.count(
                RegistroMantenimiento.id
            )
        )
        .filter(
            RegistroMantenimiento.tipo_mantenimiento
            == "solo_revision"
        )
        .scalar()
        or 0
    )

    equipos_operables = (
        base_datos.query(
            func.count(Maquina.id)
        )
        .filter(
            Maquina.estado_equipo
            == "operable"
        )
        .scalar()
        or 0
    )

    equipos_en_revision = (
        base_datos.query(
            func.count(Maquina.id)
        )
        .filter(
            Maquina.estado_equipo
            == "en_revision"
        )
        .scalar()
        or 0
    )

    equipos_presentan_fallas = (
        base_datos.query(
            func.count(Maquina.id)
        )
        .filter(
            Maquina.estado_equipo
            == "presenta_fallas"
        )
        .scalar()
        or 0
    )

    fallas_pendientes = (
        base_datos.query(
            func.count(FallaMaquina.id)
        )
        .filter(
            FallaMaquina.estado
            == "pendiente"
        )
        .scalar()
        or 0
    )

    fallas_solucionadas = (
        base_datos.query(
            func.count(FallaMaquina.id)
        )
        .filter(
            FallaMaquina.estado
            == "solucionada"
        )
        .scalar()
        or 0
    )

    total_fallas = (
        fallas_pendientes
        + fallas_solucionadas
    )

    maquinas_con_fallas = (
        base_datos.query(
            FallaMaquina.maquina_id,
            func.count(FallaMaquina.id).label(
                "cantidad_fallas"
            )
        )
        .filter(
            FallaMaquina.estado
            == "pendiente"
        )
        .group_by(
            FallaMaquina.maquina_id
        )
        .subquery()
    )

    maquinas_criticas = (
        base_datos.query(
            func.count()
        )
        .select_from(
            maquinas_con_fallas
        )
        .filter(
            maquinas_con_fallas.c.cantidad_fallas >= 5
        )
        .scalar()
        or 0
    )

    maquinas_alta_prioridad = (
        base_datos.query(
            func.count()
        )
        .select_from(
            maquinas_con_fallas
        )
        .filter(
            maquinas_con_fallas.c.cantidad_fallas == 4
        )
        .scalar()
        or 0
    )

    maquinas_prioridad_media = (
        base_datos.query(
            func.count()
        )
        .select_from(
            maquinas_con_fallas
        )
        .filter(
            maquinas_con_fallas.c.cantidad_fallas >= 1,
            maquinas_con_fallas.c.cantidad_fallas <= 3,
        )
        .scalar()
        or 0
    )

    maquinas_sin_fallas_pendientes = max(
        total_maquinas
        - maquinas_criticas
        - maquinas_alta_prioridad
        - maquinas_prioridad_media,
        0,
    )

    def calcular_porcentaje(cantidad: int) -> float:
        if total_maquinas == 0:
            return 0

        return round(
            (
                cantidad
                / total_maquinas
            )
            * 100,
            2,
        )

    porcentaje_criticas = calcular_porcentaje(
        maquinas_criticas
    )

    porcentaje_alta_prioridad = calcular_porcentaje(
        maquinas_alta_prioridad
    )

    porcentaje_media_prioridad = calcular_porcentaje(
        maquinas_prioridad_media
    )

    porcentaje_operables = calcular_porcentaje(
        maquinas_sin_fallas_pendientes
    )

    top_maquinas_fallas = (
        base_datos.query(
            Maquina.codigo,
            Maquina.seccion,
            Maquina.local,
            Maquina.tipo_activo,
            Maquina.estado_equipo,
            func.count(FallaMaquina.id).label(
                "fallas_pendientes"
            ),
        )
        .join(
            FallaMaquina,
            FallaMaquina.maquina_id == Maquina.id,
        )
        .filter(
            FallaMaquina.estado
            == "pendiente"
        )
        .group_by(
            Maquina.id,
            Maquina.codigo,
            Maquina.seccion,
            Maquina.local,
            Maquina.tipo_activo,
            Maquina.estado_equipo,
        )
        .order_by(
            func.count(FallaMaquina.id).desc()
        )
        .limit(5)
        .all()
    )

    ranking_maquinas_fallas = []

    for maquina in top_maquinas_fallas:
        cantidad = int(
            maquina.fallas_pendientes
            or 0
        )

        if cantidad >= 5:
            nivel = "Crítica"
        elif cantidad == 4:
            nivel = "Alta"
        elif cantidad >= 1:
            nivel = "Media"
        else:
            nivel = "Operable"

        ranking_maquinas_fallas.append(
            {
                "codigo":
                    maquina.codigo,

                "seccion":
                    maquina.seccion,

                "local":
                    maquina.local,

                "tipo_activo":
                    maquina.tipo_activo,

                "estado_equipo":
                    maquina.estado_equipo,

                "fallas_pendientes":
                    cantidad,

                "nivel_criticidad":
                    nivel,
            }
        )

    return {
        "total_maquinas":
            total_maquinas,

        "maquinas_con_mantenimiento":
            maquinas_con_mantenimiento,

        "maquinas_sin_mantenimiento":
            maquinas_sin_mantenimiento,

        "total_registros":
            total_registros,

        "total_preventivos":
            total_preventivos,

        "total_correctivos":
            total_correctivos,

        "total_observaciones":
            total_observaciones,

        "equipos_inoperativos": equipos_inoperativos,
        "resumen_categorias": resumen_categorias,
        "equipos_operables":
            equipos_operables,

        "equipos_en_revision":
            equipos_en_revision,

        "equipos_presentan_fallas":
            equipos_presentan_fallas,

        "fallas_pendientes":
            fallas_pendientes,

        "fallas_solucionadas":
            fallas_solucionadas,

        "total_fallas":
            total_fallas,

        "maquinas_criticas":
            maquinas_criticas,

        "maquinas_alta_prioridad":
            maquinas_alta_prioridad,

        "maquinas_prioridad_media":
            maquinas_prioridad_media,
            
        "maquinas_sin_fallas_pendientes":
            maquinas_sin_fallas_pendientes,

        "porcentaje_criticas":
            porcentaje_criticas,

        "porcentaje_alta_prioridad":
            porcentaje_alta_prioridad,

        "porcentaje_media_prioridad":
            porcentaje_media_prioridad,

        "porcentaje_operables":
            porcentaje_operables,

        "dashboard_criticidad": {
            "criticas": {
                "cantidad":
                    maquinas_criticas,
                "porcentaje":
                    porcentaje_criticas,
                "criterio":
                    "5 o más fallas pendientes",
            },

            "alta_prioridad": {
                "cantidad":
                    maquinas_alta_prioridad,
                "porcentaje":
                    porcentaje_alta_prioridad,
                "criterio":
                    "4 fallas pendientes",
            },

            "prioridad_media": {
                "cantidad":
                    maquinas_prioridad_media,
                "porcentaje":
                    porcentaje_media_prioridad,
                "criterio":
                    "1 a 3 fallas pendientes",
            },

            "operables": {
                "cantidad":
                    maquinas_sin_fallas_pendientes,
                "porcentaje":
                    porcentaje_operables,
                "criterio":
                    "0 fallas pendientes",
            },
        },

        "top_maquinas_fallas":
            ranking_maquinas_fallas,
    }

@app.get(

    "/maquinas",

    response_model=list[MaquinaRespuesta],

)

def listar_maquinas(
    categoria: Optional[str] = None,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    consulta = base_datos.query(Maquina)
    if categoria:
        if categoria not in ("maquinaria", "infraestructura", "equipo"):
            raise HTTPException(status_code=400, detail="Categoría no válida")
        consulta = consulta.filter(Maquina.categoria == categoria)
    return consulta.order_by(Maquina.codigo).all()

@app.get(

    "/maquinas/{codigo}",

    response_model=MaquinaRespuesta,

)

def buscar_maquina(

    codigo: str,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo

            == codigo.strip()

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail=(

                "Código de máquina "

                "no encontrado"

            ),

        )

    return maquina

@app.patch(

    "/maquinas/{codigo}/estado",

    response_model=MaquinaRespuesta,

)

def cambiar_estado_maquina(

    codigo: str,

    datos: EstadoMaquinaActualizar,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(

            "tecnico",

            "administracion",

            "administrador",

        )

    ),

):

    estados_permitidos = {

        "operable",

        "en_revision",

        "presenta_fallas",

        "inoperativo",

    }

    nombres_estado = {

        "operable": "Operable",

        "en_revision": "En revisión",

        "presenta_fallas": "Presenta fallas",

        "inoperativo": "Inoperativo",

        "en_reparacion": "Presenta fallas",

        "en_observacion": "En revisión",

    }

    estado = (

        datos.estado_equipo

        .strip()

        .lower()

    )

    if estado == "en_reparacion":

        estado = "presenta_fallas"

    if estado == "en_observacion":

        estado = "en_revision"

    if estado not in estados_permitidos:

        raise HTTPException(

            status_code=400,

            detail=(

                "Estado no válido. "

                "Utiliza: operable, "

                "en_revision o "

                "presenta_fallas o inoperativo"

            ),

        )

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo

            == codigo.strip()

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail=(

                "Código de máquina "

                "no encontrado"

            ),

        )

    estado_anterior = (

        maquina.estado_equipo

        or "operable"

    )

    if estado_anterior == "en_reparacion":

        estado_anterior = "presenta_fallas"

    if estado_anterior == "en_observacion":

        estado_anterior = "en_revision"

    if estado_anterior == estado:

        return maquina

    if estado == "operable":

        fallas_pendientes = contar_fallas_pendientes(

            base_datos,

            maquina.id

        )

        if fallas_pendientes > 0:

            raise HTTPException(

                status_code=400,

                detail=(

                    "No puedes marcar esta máquina como operable "

                    "porque tiene fallas pendientes por solucionar."

                ),

            )

    maquina.estado_equipo = estado

    comentario_historial = (

        "Actualización administrativa de estado: "

        + nombres_estado.get(

            estado_anterior,

            estado_anterior

        )

        + " → "

        + nombres_estado.get(

            estado,

            estado

        )

        + "."

    )

    registro_estado = RegistroMantenimiento(

        maquina_id=maquina.id,

        usuario_id=usuario_actual.id,

        trabajador_id=trabajador_actual.id,

        ubicacion_actual=(

            maquina.ubicacion_referencia

            or maquina.local

            or "Actualización administrativa"

        ),

        comentario=comentario_historial,

        tipo_mantenimiento="solo_revision",

        foto_url=None,

    )

    try:

        base_datos.add(

            registro_estado

        )

        base_datos.commit()

        base_datos.refresh(

            maquina

        )

        return maquina

    except Exception as error:

        base_datos.rollback()

        raise HTTPException(

            status_code=500,

            detail=(

                "No se pudo actualizar "

                "el estado de la máquina"

            ),

        ) from error

@app.post(

    "/registros",

    response_model=RegistroRespuesta,

    status_code=status.HTTP_201_CREATED,

)

async def crear_registro(

    background_tasks: BackgroundTasks,

    codigo_maquina: str = Form(...),

    ubicacion_actual: str = Form(...),

    comentario: str = Form(...),

    tipo_mantenimiento: str = Form(...),
    fecha_ejecucion: Optional[date] = Form(None),
    ejecutado_por: Optional[str] = Form(None, max_length=150),

    estado_equipo: str = Form(

        "operable"

    ),

    fotografias: Optional[

        List[UploadFile]

    ] = File(None),

    videos: Optional[

        List[UploadFile]

    ] = File(None),

    documentos: Optional[

        List[UploadFile]

    ] = File(None),

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_REGISTRO)

    ),

):

    codigo_limpio = limpiar_texto(

        codigo_maquina

    )

    ubicacion_limpia = limpiar_texto(

        ubicacion_actual

    )

    comentario_limpio = limpiar_texto(

        comentario

    )

    tipo_limpio = (

        limpiar_texto(

            tipo_mantenimiento

        )

        .lower()

    )

    estado_limpio = (

        limpiar_texto(

            estado_equipo

        )

        .lower()

    )

    if not codigo_limpio:

        raise HTTPException(

            status_code=400,

            detail=(

                "Debes ingresar el código "

                "de la máquina"

            ),

        )

    if not ubicacion_limpia:

        raise HTTPException(

            status_code=400,

            detail=(

                "Debes ingresar la "

                "ubicación actual"

            ),

        )

    if not comentario_limpio:

        raise HTTPException(

            status_code=400,

            detail=(

                "Debes ingresar "

                "un comentario"

            ),

        )

    if tipo_limpio not in {

        "preventivo",

        "correctivo",

        "solo_revision",

    }:

        raise HTTPException(

            status_code=400,

            detail=(

                "El tipo de mantenimiento "

                "debe ser preventivo, "

                "correctivo o solo_revision"

            ),

        )

    if estado_limpio not in {

        "operable",

        "en_revision",

        "presenta_fallas",

        "inoperativo",

    }:

        raise HTTPException(

            status_code=400,

            detail=(

                "El estado de la máquina "

                "debe ser operable, "

                "en_revision o "

                "presenta_fallas o inoperativo"

            ),

        )

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo

            == codigo_limpio

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail=(

                "Código de máquina "

                "no encontrado"

            ),

        )

    fallas_pendientes = contar_fallas_pendientes(
        base_datos,
        maquina.id
    )

    if (
        estado_limpio == "operable"
        and fallas_pendientes > 0
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "No puedes registrar la máquina como operable "
                "porque tiene fallas pendientes. "
                "Primero marca las fallas como solucionadas."
            ),
        )

    maquina.estado_equipo = estado_limpio

    fotografias = fotografias or []

    videos = videos or []

    documentos = documentos or []

    if (

        documentos

        and usuario_actual.rol

        != "proveedor"

    ):

        raise HTTPException(

            status_code=403,

            detail=(

                "Solo los usuarios con rol "

                "proveedor pueden adjuntar "

                "documentos PDF"

            ),

        )

    archivos_preparados = []

    for fotografia in fotografias:

        contenido, extension = (

            await leer_archivo_validado(

                archivo=fotografia,

                tipos_permitidos=

                    TIPOS_FOTOGRAFIA,

                limite_bytes=

                    LIMITE_FOTOGRAFIA,

                descripcion=

                    "La fotografía",

            )

        )

        archivos_preparados.append(

            {

                "tipo": "foto",

                "archivo": fotografia,

                "contenido": contenido,

                "extension": extension,

            }

        )

    for video in videos:

        contenido, extension = (

            await leer_archivo_validado(

                archivo=video,

                tipos_permitidos=

                    TIPOS_VIDEO,

                limite_bytes=

                    LIMITE_VIDEO,

                descripcion=

                    "El video",

            )

        )

        archivos_preparados.append(

            {

                "tipo": "video",

                "archivo": video,

                "contenido": contenido,

                "extension": extension,

            }

        )

    tipos_pdf = {

        TIPO_PDF: ".pdf"

    }

    for documento in documentos:

        contenido, extension = (

            await leer_archivo_validado(

                archivo=documento,

                tipos_permitidos=

                    tipos_pdf,

                limite_bytes=

                    LIMITE_PDF,

                descripcion=

                    "El documento",

            )

        )

        archivos_preparados.append(

            {

                "tipo": "pdf",

                "archivo": documento,

                "contenido": contenido,

                "extension": extension,

            }

        )

    ejecutor = (ejecutado_por or "").strip() or None
    if tipo_limpio in ("preventivo", "correctivo"):
        if not fecha_ejecucion or not ejecutor:
            raise HTTPException(status_code=422, detail="Indica la fecha de ejecución y el nombre de quien realizó el mantenimiento.")
        if fecha_ejecucion > datetime.now(ZoneInfo("America/Lima")).date():
            raise HTTPException(status_code=422, detail="La fecha de ejecución no puede ser futura.")
    else:
        fecha_ejecucion = None
        ejecutor = None

    nuevo_registro = (

        RegistroMantenimiento(

            maquina_id=maquina.id,

            usuario_id=

                usuario_actual.id,

            trabajador_id=trabajador_actual.id,

            ubicacion_actual=

                ubicacion_limpia,

            comentario=

                comentario_limpio,

            tipo_mantenimiento=

                tipo_limpio,

            foto_url=None,
            fecha_ejecucion=fecha_ejecucion,
            ejecutado_por=ejecutor,

        )

    )

    try:

        base_datos.add(

            nuevo_registro

        )

        base_datos.flush()

        for item in archivos_preparados:

            archivo = item["archivo"]

            ruta_storage = (

                f"{codigo_limpio}/"

                f"registro_{nuevo_registro.id}/"

                f"{item['tipo']}/"

                f"{uuid4().hex}"

                f"{item['extension']}"

            )

            subir_archivo(

                contenido=

                    item["contenido"],

                ruta=

                    ruta_storage,

                tipo_contenido=

                    archivo.content_type,

            )

            nuevo_archivo = (

                ArchivoMantenimiento(

                    registro_id=

                        nuevo_registro.id,

                    tipo=

                        item["tipo"],

                    nombre_original=

                        archivo.filename,

                    ruta_storage=

                        ruta_storage,

                    tipo_contenido=

                        archivo.content_type,

                )

            )

            base_datos.add(

                nuevo_archivo

            )

        base_datos.commit()

        base_datos.refresh(

            nuevo_registro

        )

        background_tasks.add_task(

            notificar_nuevo_registro,

            codigo_maquina=

                maquina.codigo,

            usuario_nombre=

                usuario_actual.nombre,

            usuario_rol=

                usuario_actual.rol,

            ubicacion_actual=

                ubicacion_limpia,

            comentario=

                comentario_limpio,

            fecha_hora=

                nuevo_registro.fecha_hora,

            tipo_mantenimiento=

                tipo_limpio,

            estado_maquina=

                estado_limpio,

            trabajador_nombres=trabajador_actual.nombres,

            trabajador_apellidos=trabajador_actual.apellidos,

            trabajador_codigo=trabajador_actual.codigo_empleado,

            trabajador_area=trabajador_actual.area,

        )

        return nuevo_registro

    except HTTPException:

        base_datos.rollback()

        raise

    except Exception as error:

        base_datos.rollback()

        raise HTTPException(

            status_code=500,

            detail=(

                "No se pudo guardar "

                "el registro de mantenimiento"

            ),

        ) from error

@app.get("/registros")

def listar_registros(

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(

            "tecnico",

            "administracion",

            "administrador",

        )

    ),

):

    registros = (

        base_datos.query(

            RegistroMantenimiento

        )

        .order_by(

            RegistroMantenimiento

            .fecha_hora

            .desc()

        )

        .all()

    )

    trabajadores_por_id = {
        trabajador.id: trabajador
        for trabajador in base_datos.query(Trabajador).filter(
            Trabajador.id.in_([
                registro.trabajador_id
                for registro in registros
                if registro.trabajador_id is not None
            ])
        ).all()
    }

    resultado = []

    for registro in registros:

        trabajador_registro = trabajadores_por_id.get(registro.trabajador_id)

        archivos = (

            construir_archivos_registro(

                registro

            )

        )

        resultado.append(

            {

                "id":

                    registro.id,

                "maquina_id":

                    registro.maquina_id,

                "categoria_activo": registro.maquina.categoria if registro.maquina else None,
                "estado_actual_activo": registro.maquina.estado_equipo if registro.maquina else None,
                "codigo_maquina": (

                    registro.maquina.codigo

                    if registro.maquina

                    else

                    "No disponible"

                ),

                "trabajador_id": registro.trabajador_id,

                "trabajador_nombres": (
                    trabajador_registro.nombres if trabajador_registro else None
                ),

                "trabajador_apellidos": (
                    trabajador_registro.apellidos if trabajador_registro else None
                ),

                "trabajador_codigo": (
                    trabajador_registro.codigo_empleado if trabajador_registro else None
                ),

                "trabajador_area": (
                    trabajador_registro.area if trabajador_registro else None
                ),

                "usuario_id":

                    registro.usuario_id,

                "usuario_nombre": (

                    registro.usuario.nombre

                    if registro.usuario

                    else

                    "Usuario no disponible"

                ),

                "usuario_rol": (

                    registro.usuario.rol

                    if registro.usuario

                    else "Sin rol"

                ),

                "ubicacion_actual":

                    registro.ubicacion_actual,

                "comentario":

                    registro.comentario,

                "tipo_mantenimiento":

                    registro.tipo_mantenimiento,

                "foto_url":

                    registro.foto_url,

                "tiene_fotografia":

                    (

                        bool(registro.foto_url)

                        or any(

                            archivo["tipo"]

                            == "foto"

                            for archivo

                            in archivos

                        )

                    ),

                "cantidad_archivos":

                    len(archivos),

                "archivos":

                    archivos,

                "fecha_ejecucion": registro.fecha_ejecucion,
                "ejecutado_por": registro.ejecutado_por,
                "fecha_hora":

                    registro.fecha_hora,

            }

        )

    return resultado

@app.get(

    "/registros/maquina/{codigo}"

)

def historial_maquina(

    codigo: str,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo

            == codigo.strip()

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail=(

                "Código de máquina "

                "no encontrado"

            ),

        )

    registros = (

        base_datos.query(

            RegistroMantenimiento

        )

        .filter(

            RegistroMantenimiento.maquina_id

            == maquina.id

        )

        .order_by(

            RegistroMantenimiento

            .fecha_hora

            .desc()

        )

        .all()

    )

    trabajadores_por_id = {
        trabajador.id: trabajador
        for trabajador in base_datos.query(Trabajador).filter(
            Trabajador.id.in_([
                registro.trabajador_id
                for registro in registros
                if registro.trabajador_id is not None
            ])
        ).all()
    }

    historial = []

    for registro in registros:

        trabajador_registro = trabajadores_por_id.get(registro.trabajador_id)

        archivos = (

            construir_archivos_registro(

                registro

            )

        )

        historial.append(

            {

                "id":

                    registro.id,

                "maquina_id":

                    registro.maquina_id,

                "codigo_maquina":

                    maquina.codigo,

                "trabajador_id": registro.trabajador_id,

                "trabajador_nombres": (
                    trabajador_registro.nombres if trabajador_registro else None
                ),

                "trabajador_apellidos": (
                    trabajador_registro.apellidos if trabajador_registro else None
                ),

                "trabajador_codigo": (
                    trabajador_registro.codigo_empleado if trabajador_registro else None
                ),

                "trabajador_area": (
                    trabajador_registro.area if trabajador_registro else None
                ),

                "usuario_id":

                    registro.usuario_id,

                "usuario_nombre": (

                    registro.usuario.nombre

                    if registro.usuario

                    else

                    "Usuario no disponible"

                ),

                "usuario_rol": (

                    registro.usuario.rol

                    if registro.usuario

                    else "Sin rol"

                ),

                "ubicacion_actual":

                    registro.ubicacion_actual,

                "comentario":

                    registro.comentario,

                "tipo_mantenimiento":

                    registro.tipo_mantenimiento,

                "foto_url":

                    registro.foto_url,

                "tiene_fotografia":

                    (

                        bool(registro.foto_url)

                        or any(

                            archivo["tipo"]

                            == "foto"

                            for archivo

                            in archivos

                        )

                    ),

                "cantidad_archivos":

                    len(archivos),

                "archivos":

                    archivos,

                "fecha_ejecucion": registro.fecha_ejecucion,
                "ejecutado_por": registro.ejecutado_por,
                "fecha_hora":

                    registro.fecha_hora,

            }

        )

    return {

        "maquina": {

            "id":

                maquina.id,

            "categoria": maquina.categoria,

            "codigo":

                maquina.codigo,

            "seccion":

                maquina.seccion,

            "local":

                maquina.local,

            "proveedor":

                maquina.proveedor,

            "ubicacion_referencia":

                maquina.ubicacion_referencia,

            "tipo_activo":

                maquina.tipo_activo,

            "marca":

                maquina.marca,

            "serie":

                maquina.serie,

            "modelo":

                maquina.modelo,

            "mantenimiento_febrero":

                maquina.mantenimiento_febrero,

            "mantenimiento_mayo":

                maquina.mantenimiento_mayo,

            "mantenimiento_agosto":

                maquina.mantenimiento_agosto,

            "mantenimiento_noviembre":

                maquina.mantenimiento_noviembre,

            "estado_equipo":

                maquina.estado_equipo,

            "fecha_creacion":

                maquina.fecha_creacion,

        },

        "cantidad_registros":

            len(historial),

        "registros":

            historial,

    }

@app.get(

    "/archivos/{archivo_id}"

)

def obtener_archivo_temporal(

    archivo_id: int,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    archivo = (

        base_datos.query(

            ArchivoMantenimiento

        )

        .filter(

            ArchivoMantenimiento.id

            == archivo_id

        )

        .first()

    )

    if not archivo:

        raise HTTPException(

            status_code=404,

            detail="Archivo no encontrado",

        )

    try:

        url = obtener_url_temporal(

            archivo.ruta_storage,

            segundos=3600,

        )

        return {

            "archivo_id":

                archivo.id,

            "registro_id":

                archivo.registro_id,

            "tipo":

                archivo.tipo,

            "nombre_original":

                archivo.nombre_original,

            "tipo_contenido":

                archivo.tipo_contenido,

            "url_temporal":

                url,

            "duracion_segundos":

                3600,

        }

    except Exception as error:

        raise HTTPException(

            status_code=502,

            detail=(

                "No se pudo generar "

                "la dirección temporal "

                "del archivo"

            ),

        ) from error

@app.get(

    "/registros/{registro_id}/foto"

)

def obtener_fotografia(

    registro_id: int,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    registro = (

        base_datos.query(

            RegistroMantenimiento

        )

        .filter(

            RegistroMantenimiento.id

            == registro_id

        )

        .first()

    )

    if not registro:

        raise HTTPException(

            status_code=404,

            detail="Registro no encontrado",

        )

    if registro.foto_url:

        if registro.foto_url.startswith(

            "/uploads/"

        ):

            raise HTTPException(

                status_code=409,

                detail=(

                    "Esta fotografía pertenece "

                    "al almacenamiento local "

                    "anterior"

                ),

            )

        try:

            url = obtener_url_temporal(

                registro.foto_url,

                segundos=3600,

            )

            return {

                "registro_id":

                    registro.id,

                "tipo":

                    "foto",

                "sistema":

                    "anterior",

                "url_temporal":

                    url,

                "duracion_segundos":

                    3600,

            }

        except Exception as error:

            raise HTTPException(

                status_code=502,

                detail=(

                    "No se pudo generar "

                    "la dirección temporal"

                ),

            ) from error

    fotografia = (

        base_datos.query(

            ArchivoMantenimiento

        )

        .filter(

            ArchivoMantenimiento.registro_id

            == registro.id,

            ArchivoMantenimiento.tipo

            == "foto",

        )

        .order_by(

            ArchivoMantenimiento.id

        )

        .first()

    )

    if not fotografia:

        raise HTTPException(

            status_code=404,

            detail=(

                "El registro no tiene "

                "fotografías"

            ),

        )

    try:

        url = obtener_url_temporal(

            fotografia.ruta_storage,

            segundos=3600,

        )

        return {

            "registro_id":

                registro.id,

            "archivo_id":

                fotografia.id,

            "tipo":

                "foto",

            "sistema":

                "nuevo",

            "url_temporal":

                url,

            "duracion_segundos":

                3600,

        }

    except Exception as error:

        raise HTTPException(

            status_code=502,

            detail=(

                "No se pudo generar "

                "la dirección temporal"

            ),

        ) from error



# =========================================================
# REPORTE GLOBAL DE FALLAS Y SOLUCIONES (SOLO ADMINISTRACIÓN)
# =========================================================
@app.get("/reportes/fallas")
def reporte_global_fallas(
    base_datos: Session = Depends(obtener_base_datos),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),
    usuario_actual: Usuario = Depends(permitir_roles(*ROLES_ADMINISTRATIVOS)),
):
    registros = (
        base_datos.query(FallaMaquina, Maquina.codigo)
        .join(Maquina, FallaMaquina.maquina_id == Maquina.id)
        .order_by(FallaMaquina.fecha_creacion.desc(), FallaMaquina.id.desc())
        .all()
    )

    trabajadores_ids = {
        trabajador_id
        for falla, _ in registros
        for trabajador_id in (falla.trabajador_id, falla.trabajador_solucion_id)
        if trabajador_id is not None
    }
    trabajadores = (
        {t.id: t for t in base_datos.query(Trabajador)
         .filter(Trabajador.id.in_(trabajadores_ids)).all()}
        if trabajadores_ids else {}
    )

    resultado = []
    for falla, codigo_maquina in registros:
        responsable = trabajadores.get(falla.trabajador_id)
        solucionador = trabajadores.get(falla.trabajador_solucion_id)
        resultado.append({
            "id": falla.id,
            "codigo_maquina": codigo_maquina,
            "descripcion": falla.descripcion,
            "estado": falla.estado,
            "fecha_creacion": falla.fecha_creacion,
            "fecha_solucion": falla.fecha_solucion,
            "trabajador_id": falla.trabajador_id,
            "trabajador_nombres": responsable.nombres if responsable else None,
            "trabajador_apellidos": responsable.apellidos if responsable else None,
            "trabajador_codigo": responsable.codigo_empleado if responsable else None,
            "trabajador_area": responsable.area if responsable else None,
            "trabajador_solucion_id": falla.trabajador_solucion_id,
            "trabajador_solucion_nombres": solucionador.nombres if solucionador else None,
            "trabajador_solucion_apellidos": solucionador.apellidos if solucionador else None,
            "trabajador_solucion_codigo": solucionador.codigo_empleado if solucionador else None,
            "trabajador_solucion_area": solucionador.area if solucionador else None,
        })
    return resultado

@app.get(

    "/maquinas/{codigo}/fallas",

)

def listar_fallas_maquina(

    codigo: str,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(*ROLES_CONSULTA)

    ),

):

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo == codigo.strip()

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail="Código de máquina no encontrado",

        )

    fallas = (
        base_datos.query(FallaMaquina)
        .filter(FallaMaquina.maquina_id == maquina.id)
        .order_by(FallaMaquina.fecha_creacion.desc())
        .all()
    )

    ids_trabajadores = {
        identificador
        for falla in fallas
        for identificador in (falla.trabajador_id, falla.trabajador_solucion_id)
        if identificador is not None
    }
    trabajadores = (
        {
            trabajador.id: trabajador
            for trabajador in base_datos.query(Trabajador)
            .filter(Trabajador.id.in_(ids_trabajadores)).all()
        }
        if ids_trabajadores else {}
    )

    resultado = []
    for falla in fallas:
        responsable = trabajadores.get(falla.trabajador_id)
        solucionador = trabajadores.get(falla.trabajador_solucion_id)
        resultado.append({
            "id": falla.id,
            "maquina_id": falla.maquina_id,
            "registro_id": falla.registro_id,
            "usuario_id": falla.usuario_id,
            "descripcion": falla.descripcion,
            "estado": falla.estado,
            "fecha_creacion": falla.fecha_creacion,
            "fecha_solucion": falla.fecha_solucion,
            "usuario_solucion_id": falla.usuario_solucion_id,
            "trabajador_id": falla.trabajador_id,
            "trabajador_nombres": responsable.nombres if responsable else None,
            "trabajador_apellidos": responsable.apellidos if responsable else None,
            "trabajador_codigo": responsable.codigo_empleado if responsable else None,
            "trabajador_area": responsable.area if responsable else None,
            "trabajador_solucion_id": falla.trabajador_solucion_id,
            "trabajador_solucion_nombres": solucionador.nombres if solucionador else None,
            "trabajador_solucion_apellidos": solucionador.apellidos if solucionador else None,
            "trabajador_solucion_codigo": solucionador.codigo_empleado if solucionador else None,
            "trabajador_solucion_area": solucionador.area if solucionador else None,
        })

    return resultado

@app.post(

    "/maquinas/{codigo}/fallas",

    response_model=FallaRespuesta,

    status_code=status.HTTP_201_CREATED,

)

def crear_falla_maquina(

    codigo: str,

    datos: FallaCrear,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(

            "proveedor",

            "tecnico",

            "operativo",

            "administracion",

            "administrador"

        )

    ),

):

    descripcion_limpia = limpiar_texto(

        datos.descripcion

    )

    if not descripcion_limpia:

        raise HTTPException(

            status_code=400,

            detail="Debes ingresar la descripción de la falla.",

        )

    maquina = (

        base_datos.query(Maquina)

        .filter(

            Maquina.codigo == codigo.strip()

        )

        .first()

    )

    if not maquina:

        raise HTTPException(

            status_code=404,

            detail="Código de máquina no encontrado",

        )

    nueva_falla = FallaMaquina(

        maquina_id=maquina.id,

        usuario_id=usuario_actual.id,

        trabajador_id=trabajador_actual.id,

        descripcion=descripcion_limpia,

        estado="pendiente",

    )

    if maquina.estado_equipo != "inoperativo":
        maquina.estado_equipo = "presenta_fallas"

    try:

        base_datos.add(nueva_falla)

        base_datos.commit()

        base_datos.refresh(nueva_falla)

        return nueva_falla

    except Exception as error:

        base_datos.rollback()

        raise HTTPException(

            status_code=500,

            detail="No se pudo registrar la falla.",

        ) from error

@app.patch(

    "/fallas/{falla_id}/solucionar",

    response_model=FallaRespuesta,

)

def solucionar_falla_maquina(

    falla_id: int,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(

            "tecnico",

            "administrador"

        )

    ),

):

    falla = (

        base_datos.query(FallaMaquina)

        .filter(

            FallaMaquina.id == falla_id

        )

        .first()

    )

    if not falla:

        raise HTTPException(

            status_code=404,

            detail="Falla no encontrada.",

        )

    falla.estado = "solucionada"

    falla.usuario_solucion_id = usuario_actual.id

    falla.trabajador_solucion_id = trabajador_actual.id

    falla.fecha_solucion = datetime.now(timezone.utc)

    try:

        base_datos.commit()

        base_datos.refresh(falla)

        pendientes = contar_fallas_pendientes(

            base_datos,

            falla.maquina_id

        )

        if falla.maquina and falla.maquina.estado_equipo != "inoperativo":

            if pendientes == 0:

                falla.maquina.estado_equipo = "operable"

            else:

                falla.maquina.estado_equipo = "en_revision"

            base_datos.commit()

            base_datos.refresh(falla)

        return falla

    except Exception as error:

        base_datos.rollback()

        raise HTTPException(

            status_code=500,

            detail="No se pudo solucionar la falla.",

        ) from error

@app.delete(

    "/registros/{registro_id}"

)

def eliminar_registro(

    registro_id: int,

    base_datos: Session = Depends(

        obtener_base_datos

    ),

    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),

    usuario_actual: Usuario = Depends(

        permitir_roles(

            "administrador"

        )

    ),

):

    registro = (

        base_datos.query(

            RegistroMantenimiento

        )

        .filter(

            RegistroMantenimiento.id == registro_id

        )

        .first()

    )

    if not registro:

        raise HTTPException(

            status_code=404,

            detail="Registro no encontrado",

        )

    try:

        archivos_del_registro = list(

            registro.archivos

        )

        for archivo in archivos_del_registro:

            base_datos.delete(

                archivo

            )

        base_datos.delete(

            registro

        )

        base_datos.commit()

        return {

            "mensaje": "Registro eliminado correctamente",

            "registro_id": registro_id,

        }

    except Exception as error:

        base_datos.rollback()

        raise HTTPException(

            status_code=500,

            detail="No se pudo eliminar el registro",

        ) from error

# TENDENCIA DIARIA DE FALLAS
from datetime import timedelta
from zoneinfo import ZoneInfo
from fastapi import Query


@app.get("/panel/tendencia-fallas")
def tendencia_diaria_fallas(
    dias: int = Query(default=30, ge=1, le=90),
    sede: Optional[str] = Query(default=None, max_length=50),
    base_datos: Session = Depends(obtener_base_datos),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),
    usuario_actual: Usuario = Depends(
        permitir_roles(*ROLES_ADMINISTRATIVOS)
    ),
):
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).date()
    inicio = hoy - timedelta(days=dias - 1)

    desde = datetime(
        inicio.year, inicio.month, inicio.day, tzinfo=zona
    )
    hasta = datetime(
        hoy.year, hoy.month, hoy.day, tzinfo=zona
    ) + timedelta(days=1)

    # Día de registro según la hora de Perú.
    dia_local = func.date(
        func.timezone("America/Lima", FallaMaquina.fecha_creacion)
    )

    consulta = (
        base_datos.query(
            dia_local.label("dia"),
            func.count(FallaMaquina.id).label("cantidad"),
        )
        .join(Maquina, FallaMaquina.maquina_id == Maquina.id)
        .filter(
            FallaMaquina.fecha_creacion >= desde,
            FallaMaquina.fecha_creacion < hasta,
        )
    )

    if sede:
        consulta = consulta.filter(Maquina.local == sede)

    resultados = (
        consulta.group_by(dia_local)
        .order_by(dia_local)
        .all()
    )

    cantidades = {
        str(fila.dia): int(fila.cantidad)
        for fila in resultados
    }

    serie = []

    for numero in range(dias):
        fecha = inicio + timedelta(days=numero)
        fecha_texto = fecha.isoformat()

        serie.append({
            "fecha": fecha_texto,
            "cantidad": cantidades.get(fecha_texto, 0),
        })

    sedes = [
        fila[0]
        for fila in (
            base_datos.query(Maquina.local)
            .filter(
                Maquina.local.isnot(None),
                Maquina.local != "",
            )
            .distinct()
            .order_by(Maquina.local)
            .all()
        )
    ]

    return {
        "serie": serie,
        "sedes": sedes,
        "total": sum(punto["cantidad"] for punto in serie),
        "desde": inicio.isoformat(),
        "hasta": hoy.isoformat(),
    }
# PREDICCIÓN EXPERIMENTAL

from prediccion_demo import router as prediccion_demo_router

app.include_router(
    prediccion_demo_router,
    dependencies=[
        Depends(obtener_trabajador_actual),
        Depends(permitir_roles(*ROLES_ADMINISTRATIVOS)),
    ],
)

@app.post("/activos", response_model=MaquinaRespuesta, status_code=201)
def crear_activo(
    datos: ActivoCrear,
    background_tasks: BackgroundTasks,
    base_datos: Session = Depends(obtener_base_datos),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),
    usuario_actual: Usuario = Depends(permitir_roles("administracion", "administrador")),
):
    if datos.categoria not in ("maquinaria", "infraestructura", "equipo"):
        raise HTTPException(status_code=400, detail="Categoría no válida")
    if datos.estado_equipo not in ("operable", "en_revision", "presenta_fallas", "inoperativo"):
        raise HTTPException(status_code=400, detail="Estado no válido")
    if base_datos.query(Maquina.id).filter(Maquina.codigo == datos.codigo).first():
        raise HTTPException(status_code=409, detail="Este código ya existe. Utiliza un código único para cada activo.")
    activo = Maquina(**datos.model_dump())
    try:
        base_datos.add(activo)
        base_datos.commit()
        base_datos.refresh(activo)
        background_tasks.add_task(
            notificar_nuevo_activo, activo.codigo, activo.categoria, activo.tipo_activo,
            activo.ubicacion_referencia,
            f"{trabajador_actual.nombres} {trabajador_actual.apellidos}".strip(),
        )
        return activo
    except IntegrityError:
        base_datos.rollback()
        raise HTTPException(status_code=409, detail="Este código ya existe")


@app.get("/activos/foto")
def consultar_foto_activo(
    codigo: str,
    base_datos: Session = Depends(obtener_base_datos),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),
    usuario_actual: Usuario = Depends(permitir_roles(*ROLES_CONSULTA)),
):
    activo = base_datos.query(Maquina).filter_by(codigo=codigo).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado.")
    return {"url": obtener_url_temporal(activo.ruta_foto_activo) if activo.ruta_foto_activo else None}


@app.put("/activos/foto")
async def guardar_foto_activo(
    codigo: str,
    foto: UploadFile = File(...),
    base_datos: Session = Depends(obtener_base_datos),
    trabajador_actual: Trabajador = Depends(obtener_trabajador_actual),
    usuario_actual: Usuario = Depends(permitir_roles(*ROLES_ADMINISTRATIVOS)),
):
    contenido, extension = await leer_archivo_validado(foto, TIPOS_FOTOGRAFIA, LIMITE_FOTOGRAFIA, "La imagen")
    firma = b"\xff\xd8\xff" if extension == ".jpg" else b"\x89PNG\r\n\x1a\n"
    if not contenido.startswith(firma):
        raise HTTPException(status_code=400, detail="Selecciona una imagen JPG o PNG válida.")

    activo = base_datos.query(Maquina).filter_by(codigo=codigo).with_for_update().first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado.")
    anterior = activo.ruta_foto_activo
    ruta = f"fotos_activos/{activo.id}/{uuid4().hex}{extension}"
    try:
        subir_archivo(contenido, ruta, foto.content_type)
        activo.ruta_foto_activo = ruta
        base_datos.commit()
    except Exception:
        base_datos.rollback()
        logging.exception("No se pudo guardar la foto del activo")
        retirar_foto_activo(ruta)
        raise HTTPException(status_code=502, detail="No se pudo guardar la foto. Vuelve a intentarlo.")
    if anterior:
        retirar_foto_activo(anterior)
    return {"guardada": True}



def retirar_foto_activo(ruta):
    try:
        eliminar_archivos([ruta])
    except Exception:
        logging.exception("No se pudo retirar una foto de activo del almacenamiento")
