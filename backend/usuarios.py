from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from database import obtener_base_datos
from models import Usuario
from seguridad import permitir_roles


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)

password_hash = PasswordHash.recommended()


ROLES_VALIDOS = {
    "proveedor",
    "tecnico",
    "operativo",
    "administracion",
    "administrador",
}


class UsuarioCrear(BaseModel):
    nombre: str = Field(
        min_length=3,
        max_length=150,
    )

    correo: EmailStr

    contrasena: str = Field(
        min_length=8,
        max_length=100,
    )

    rol: str


class UsuarioActualizarEstado(BaseModel):
    activo: bool


def convertir_usuario(usuario: Usuario):
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "fecha_creacion": usuario.fecha_creacion,
    }


@router.get("")
@router.get("/")
def listar_usuarios(
    base_datos: Session = Depends(
        obtener_base_datos
    ),
    usuario_actual: Usuario = Depends(
        permitir_roles("administrador")
    ),
):
    usuarios = (
        base_datos.query(Usuario)
        .order_by(Usuario.nombre)
        .all()
    )

    return [
        convertir_usuario(usuario)
        for usuario in usuarios
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    datos: UsuarioCrear,
    base_datos: Session = Depends(
        obtener_base_datos
    ),
    usuario_actual: Usuario = Depends(
        permitir_roles("administrador")
    ),
):
    nombre_limpio = datos.nombre.strip()

    correo_limpio = (
        str(datos.correo)
        .strip()
        .lower()
    )

    rol_limpio = (
        datos.rol
        .strip()
        .lower()
    )

    if not nombre_limpio:
        raise HTTPException(
            status_code=400,
            detail="Debes ingresar el nombre",
        )

    if rol_limpio not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=(
                "El rol debe ser proveedor, tecnico, "
                "operativo, administracion "
                "o administrador"
            ),
        )

    usuario_existente = (
        base_datos.query(Usuario)
        .filter(Usuario.correo == correo_limpio)
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe un usuario con ese correo"
            ),
        )

    nuevo_usuario = Usuario(
        nombre=nombre_limpio,
        correo=correo_limpio,
        contrasena_hash=password_hash.hash(
            datos.contrasena
        ),
        rol=rol_limpio,
        activo=True,
    )

    try:
        base_datos.add(nuevo_usuario)
        base_datos.commit()
        base_datos.refresh(nuevo_usuario)

        return convertir_usuario(nuevo_usuario)

    except Exception as error:
        base_datos.rollback()

        raise HTTPException(
            status_code=500,
            detail="No se pudo crear el usuario",
        ) from error


@router.patch("/{usuario_id}/estado")
def cambiar_estado_usuario(
    usuario_id: int,
    datos: UsuarioActualizarEstado,
    base_datos: Session = Depends(
        obtener_base_datos
    ),
    usuario_actual: Usuario = Depends(
        permitir_roles("administrador")
    ),
):
    usuario = (
        base_datos.query(Usuario)
        .filter(Usuario.id == usuario_id)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado",
        )

    if (
        usuario.id == usuario_actual.id
        and datos.activo is False
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "No puedes desactivar tu propia cuenta"
            ),
        )

    usuario.activo = datos.activo

    try:
        base_datos.commit()
        base_datos.refresh(usuario)

        return convertir_usuario(usuario)

    except Exception as error:
        base_datos.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo actualizar el usuario"
            ),
        ) from error