
import os

from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import jwt

from dotenv import load_dotenv

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import OAuth2PasswordBearer

from jwt.exceptions import InvalidTokenError

from pwdlib import PasswordHash

from sqlalchemy.orm import Session

from database import SessionLocal

from models import Usuario, Trabajador


# =========================================================
# CONFIGURACIÓN
# =========================================================

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "JWT_EXPIRE_MINUTES",
        "480"
    )
)

if not JWT_SECRET:
    raise ValueError(
        "Falta JWT_SECRET en el archivo .env"
    )


password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


# =========================================================
# BASE DE DATOS
# =========================================================

def obtener_base_datos():

    base_datos = SessionLocal()

    try:
        yield base_datos
    finally:
        base_datos.close()


# =========================================================
# CONTRASEÑAS
# =========================================================

def proteger_contrasena(
    contrasena: str
) -> str:

    return password_hash.hash(
        contrasena
    )


def verificar_contrasena(
    contrasena: str,
    contrasena_protegida: str
) -> bool:

    try:
        return password_hash.verify(
            contrasena,
            contrasena_protegida
        )

    except Exception:
        return False


# =========================================================
# CREACIÓN DE TOKEN
# =========================================================

def crear_token(
    usuario_id: int,
    rol: str,
    trabajador_id: Optional[int] = None
) -> str:
    """
    Crea un token JWT.

    Si no existe trabajador_id:
        Sesión de cuenta.

    Si existe trabajador_id:
        Sesión de trabajador identificado.
    """

    fecha_expiracion = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=JWT_EXPIRE_MINUTES
        )
    )

    datos_token = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": fecha_expiracion,
        "etapa": (
            "trabajador"
            if trabajador_id is not None
            else "cuenta"
        )
    }

    if trabajador_id is not None:
        datos_token["trabajador_id"] = str(
            trabajador_id
        )

    return jwt.encode(
        datos_token,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


# =========================================================
# DECODIFICAR TOKEN
# =========================================================

def decodificar_token(
    token: str
) -> dict:

    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "La sesión no es válida "
            "o ha expirado"
        ),
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:
        datos = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        usuario_id = datos.get("sub")

        if usuario_id is None:
            raise error_credenciales

        int(usuario_id)

        return datos

    except (
        InvalidTokenError,
        ValueError,
        TypeError
    ):
        raise error_credenciales


# =========================================================
# OBTENER USUARIO ACTUAL
# =========================================================

def obtener_usuario_actual(
    token: str = Depends(
        oauth2_scheme
    ),
    base_datos: Session = Depends(
        obtener_base_datos
    )
) -> Usuario:

    datos = decodificar_token(token)

    usuario_id = int(
        datos["sub"]
    )

    usuario = (
        base_datos.query(Usuario)
        .filter(
            Usuario.id == usuario_id
        )
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=403,
            detail=(
                "Este usuario se encuentra "
                "desactivado"
            )
        )

    return usuario


# =========================================================
# OBTENER TRABAJADOR IDENTIFICADO
# =========================================================

def obtener_trabajador_actual(
    token: str = Depends(
        oauth2_scheme
    ),
    base_datos: Session = Depends(
        obtener_base_datos
    )
) -> Trabajador:
    """
    Solo acepta tokens que incluyan una
    identificación de trabajador válida.

    Debe verificarse también que el trabajador
    corresponda a la cuenta/área autorizada.
    """

    datos = decodificar_token(token)

    if datos.get("etapa") != "trabajador":
        raise HTTPException(
            status_code=403,
            detail=(
                "Debes identificarte como "
                "trabajador antes de continuar"
            )
        )

    trabajador_id = datos.get(
        "trabajador_id"
    )

    if trabajador_id is None:
        raise HTTPException(
            status_code=403,
            detail="Falta la identificación"
        )

    try:
        trabajador_id = int(
            trabajador_id
        )

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Identificación no válida"
        )

    usuario_id = int(
        datos["sub"]
    )

    usuario = (
        base_datos.query(Usuario)
        .filter(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True)
        )
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Cuenta no válida"
        )

    trabajador = (
        base_datos.query(Trabajador)
        .filter(
            Trabajador.id == trabajador_id,
            Trabajador.activo.is_(True)
        )
        .first()
    )

    if trabajador is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "El trabajador no existe "
                "o está desactivado"
            )
        )

    # El administrador conserva una cuenta propia.
    # Para los demás roles, el nombre de la cuenta
    # debe corresponder al área del trabajador.
    if usuario.rol != "administrador":

        area_cuenta = " ".join(
            usuario.nombre.strip().casefold().split()
        )

        area_trabajador = " ".join(
            trabajador.area.strip().casefold().split()
        )

        if area_cuenta != area_trabajador:
            raise HTTPException(
                status_code=403,
                detail=(
                    "El trabajador no pertenece "
                    "al área de esta cuenta"
                )
            )

    return trabajador


# =========================================================
# PERMISOS POR ROL
# =========================================================

def permitir_roles(
    *roles_permitidos: str
) -> Callable:

    def comprobar_rol(
        usuario: Usuario = Depends(
            obtener_usuario_actual
        )
    ) -> Usuario:

        rol_actual = str(
            usuario.rol or ""
        ).strip().casefold()

        roles_validos = {
            str(rol).strip().casefold()
            for rol in roles_permitidos
        }
        print(
    "DEBUG PERMISOS:",
    "rol_actual =", repr(rol_actual),
    "roles_permitidos =", roles_validos
        )

        if rol_actual not in roles_validos:
            raise HTTPException(
                status_code=403,
                detail=(
                    "No tienes permiso "
                    "para realizar esta acción"
                )
            )

        return usuario

    return comprobar_rol
