import json
import logging
import os
from urllib.request import Request, urlopen
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from database import engine
from models import Usuario

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USUARIO = os.getenv('SMTP_USUARIO', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
CORREO_REMITENTE = os.getenv('CORREO_REMITENTE', SMTP_USUARIO)


def obtener_correos_administradores():
    """Obtiene los correos de todos los administradores activos."""
    with Session(engine) as base_datos:
        resultados = (
            base_datos.query(Usuario.correo)
            .filter(Usuario.rol == 'administrador', Usuario.activo.is_(True))
            .all()
        )
    correos = set()
    for registro in resultados:
        correo = (registro.correo or '').strip().lower()
        if correo and '@' in correo:
            correos.add(correo)
    return sorted(correos)


def formatear_fecha(fecha_hora):
    if not fecha_hora:
        return 'No disponible'
    try:
        fecha = (fecha_hora if isinstance(fecha_hora, datetime)
                 else datetime.fromisoformat(str(fecha_hora).replace('Z', '+00:00')))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(ZoneInfo('America/Lima')).strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError, OverflowError):
        return str(fecha_hora)


def obtener_texto_tipo_mantenimiento(tipo_mantenimiento):
    tipos = {
        'preventivo': 'Preventivo',
        'correctivo': 'Correctivo',
        'solo_revision': 'Solo revisión',
    }
    return tipos.get(str(tipo_mantenimiento or '').strip().lower(), 'No especificado')


def obtener_texto_estado(estado):
    estados = {
        'operable': 'Operable',
        'en_revision': 'En revisión',
        'inoperativo': 'Inoperativo',
        'presenta_fallas': 'Presenta fallas',
        'en_reparacion': 'En reparación',
        'en_observacion': 'En observación',
    }
    return estados.get(str(estado or '').strip().lower(), 'No especificado')


def notificar_nuevo_registro(
    codigo_maquina: str,
    usuario_nombre: str,
    usuario_rol: str,
    ubicacion_actual: str,
    comentario: str,
    fecha_hora,
    tipo_mantenimiento: str = '',
    estado_maquina: str = '',
    trabajador_nombres: str = '',
    trabajador_apellidos: str = '',
    trabajador_codigo: str = '',
    trabajador_area: str = '',
):
    """Notifica a los administradores con los datos individuales del trabajador."""
    nombre_completo = ' '.join(
        dato.strip() for dato in [trabajador_nombres, trabajador_apellidos] if dato and dato.strip()
    ) or 'No identificado'

    contenido = f"""Hola,

Se registró un nuevo mantenimiento en SIGNIA.

Datos del mantenimiento:

Máquina: {codigo_maquina}
Tipo de mantenimiento: {obtener_texto_tipo_mantenimiento(tipo_mantenimiento)}
Estado de la máquina: {obtener_texto_estado(estado_maquina)}
Ubicación actual: {ubicacion_actual}
Comentario: {comentario}
Fecha y hora (Perú): {formatear_fecha(fecha_hora)}

Responsable del registro:
Trabajador: {nombre_completo}
Código de empleado: {trabajador_codigo or 'No disponible'}
Área: {trabajador_area or 'No disponible'}
Cuenta utilizada: {usuario_nombre}
Rol de la cuenta: {usuario_rol}

Este mensaje fue generado automáticamente por SIGNIA.
"""

    enviar_notificacion("SIGNIA - Nuevo mantenimiento registrado", contenido)


def notificar_nuevo_activo(codigo, categoria, descripcion, ubicacion, trabajador):
    contenido = (
        "Se registró un nuevo activo en SIGNIA.\n\n"
        f"Código: {codigo}\nCategoría: {categoria}\nDescripción: {descripcion}\n"
        f"Ubicación: {ubicacion}\nRegistrado por: {trabajador}"
    )
    enviar_notificacion("SIGNIA - Nuevo activo registrado", contenido)


def enviar_notificacion(asunto, contenido):
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    remitente_api = os.getenv("RESEND_FROM", "").strip()
    try:
        destinatarios = obtener_correos_administradores()
        if not destinatarios:
            logging.warning("SIGNIA: no hay administradores activos con correo.")
            return

        if api_key and remitente_api:
            # Enviar por separado para no exponer las direcciones entre destinatarios.
            for correo in destinatarios:
                solicitud = Request(
                    "https://api.resend.com/emails",
                    data=json.dumps({
                        "from": remitente_api, "to": [correo],
                        "subject": asunto, "text": contenido,
                    }).encode("utf-8"),
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                             "User-Agent": "SIGNIA/1.0"},
                    method="POST",
                )
                try:
                    with urlopen(solicitud, timeout=15):
                        logging.info("SIGNIA: aviso aceptado por el proveedor de correo.")
                except Exception:
                    logging.exception("SIGNIA: no se pudo enviar un aviso por HTTPS.")
            return

        if not all([SMTP_HOST, SMTP_USUARIO, SMTP_PASSWORD, CORREO_REMITENTE]):
            logging.warning("SIGNIA: faltan datos de configuración de correo.")
            return

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = CORREO_REMITENTE
        mensaje["To"] = "undisclosed-recipients:;"
        mensaje.set_content(contenido)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
            servidor.send_message(mensaje, to_addrs=destinatarios)
    except Exception:
        logging.exception("SIGNIA: no se pudo enviar la notificación.")
