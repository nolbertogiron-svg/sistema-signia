import os
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
    if not all([SMTP_HOST, SMTP_USUARIO, SMTP_PASSWORD, CORREO_REMITENTE]):
        print('Notificación no enviada: faltan datos de configuración SMTP.')
        return

    try:
        destinatarios = obtener_correos_administradores()
    except Exception as error:
        print('No se pudieron consultar los administradores:', error)
        return

    if not destinatarios:
        print('Notificación no enviada: no hay administradores activos con correo.')
        return

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

    mensaje = EmailMessage()
    mensaje['Subject'] = 'SIGNIA - Nuevo mantenimiento registrado'
    mensaje['From'] = CORREO_REMITENTE
    mensaje['To'] = CORREO_REMITENTE
    mensaje['Bcc'] = ', '.join(destinatarios)
    mensaje.set_content(contenido)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
            servidor.send_message(mensaje)
        print(f'Notificación enviada a {len(destinatarios)} administrador(es).')
    except Exception as error:
        print('No se pudo enviar la notificación:', error)
