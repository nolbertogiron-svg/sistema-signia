
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    OAuth2PasswordRequestForm,
    OAuth2PasswordBearer
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import Usuario, Trabajador

from schemas import TrabajadorIdentificar

from seguridad import (
    obtener_base_datos,
    verificar_contrasena,
    crear_token,
    obtener_usuario_actual,
    decodificar_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def normalizar(texto: str) -> str:
    """
    Elimina espacios innecesarios y permite
    comparar textos sin distinguir mayúsculas.
    """
    return " ".join(
        texto.strip().casefold().split()
    )


def respuesta_autenticacion(
    usuario: Usuario,
    token: str,
    trabajador: Trabajador = None
):
    """
    Construye la respuesta para el frontend.
    """

    resultado = {
        "access_token": token,
        "token_type": "bearer",
        "requiere_identificacion": (
            trabajador is None
        ),
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": usuario.rol,
            "activo": usuario.activo
        }
    }

    if trabajador is not None:
        resultado["trabajador"] = {
            "id": trabajador.id,
            "nombres": trabajador.nombres,
            "apellidos": trabajador.apellidos,
            "codigo_empleado": trabajador.codigo_empleado,
            "area": trabajador.area
        }

    return resultado


# =========================================================
# 1. INICIAR SESIÓN CON LA CUENTA DEL ÁREA
# =========================================================

@router.post("/login")
def iniciar_sesion(
    formulario: OAuth2PasswordRequestForm = Depends(),
    base_datos: Session = Depends(obtener_base_datos)
):
    """
    Primera etapa:

    El usuario inicia sesión con el correo
    y contraseña compartidos de su área.
    """

    correo = formulario.username.strip().lower()

    usuario = (
        base_datos.query(Usuario)
        .filter(
            Usuario.correo == correo
        )
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not verificar_contrasena(
        formulario.password,
        usuario.contrasena_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta se encuentra desactivada"
        )

    # Token inicial: identifica únicamente
    # a la cuenta compartida.
    token = crear_token(
        usuario_id=usuario.id,
        rol=usuario.rol
    )

    return respuesta_autenticacion(
        usuario=usuario,
        token=token
    )


# =========================================================
# 2. IDENTIFICAR O REGISTRAR AUTOMÁTICAMENTE
#    AL TRABAJADOR
# =========================================================

@router.post("/identificar-trabajador")
def identificar_trabajador(
    datos: TrabajadorIdentificar,
    token: str = Depends(oauth2_scheme),
    base_datos: Session = Depends(obtener_base_datos)
):
    """
    Segunda etapa:

    El trabajador ingresa:
    - Nombres
    - Apellidos
    - Código de empleado (máximo 5 dígitos)

    Si el trabajador no existe, se registra
    automáticamente.

    Si existe y sus datos coinciden,
    se permite el acceso.

    Si el código pertenece a otra persona
    o área, se rechaza el ingreso.
    """

    # -----------------------------------------------------
    # PASO 1. VALIDAR EL TOKEN DE LA CUENTA
    # -----------------------------------------------------

    datos_token = decodificar_token(token)

    if datos_token.get("etapa") != "cuenta":
        raise HTTPException(
            status_code=403,
            detail=(
                "Para cambiar de trabajador, "
                "inicia sesión nuevamente con la cuenta del área"
            )
        )

    try:
        usuario_id = int(
            datos_token["sub"]
        )
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token de cuenta inválido"
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
            detail="La cuenta no es válida o está desactivada"
        )

    # -----------------------------------------------------
    # PASO 2. OBTENER LOS DATOS DEL TRABAJADOR
    # -----------------------------------------------------

    nombres = " ".join(
        datos.nombres.strip().split()
    )

    apellidos = " ".join(
        datos.apellidos.strip().split()
    )

    codigo_empleado = datos.codigo_empleado

    # Por ahora se utiliza Usuario.nombre
    # como nombre del área.
    #
    # Más adelante podremos crear un campo
    # area independiente en usuarios.

    area_cuenta = " ".join(
        usuario.nombre.strip().split()
    )

    # -----------------------------------------------------
    # PASO 3. BUSCAR AL TRABAJADOR POR SU CÓDIGO
    # -----------------------------------------------------

    trabajador = (
        base_datos.query(Trabajador)
        .filter(
            Trabajador.codigo_empleado == codigo_empleado
        )
        .first()
    )

    # -----------------------------------------------------
    # PASO 4. SI NO EXISTE, REGISTRAR AUTOMÁTICAMENTE
    # -----------------------------------------------------

    if trabajador is None:

        trabajador = Trabajador(
            nombres=nombres,
            apellidos=apellidos,
            codigo_empleado=codigo_empleado,
            area=area_cuenta,
            activo=True
        )

        base_datos.add(trabajador)

        try:
            base_datos.commit()
            base_datos.refresh(trabajador)

        except IntegrityError:
            # Otro ingreso pudo registrar el mismo
            # código simultáneamente.
            base_datos.rollback()

            trabajador = (
                base_datos.query(Trabajador)
                .filter(
                    Trabajador.codigo_empleado ==
                    codigo_empleado
                )
                .first()
            )

            if trabajador is None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No se pudo registrar al trabajador. "
                        "Inténtalo nuevamente."
                    )
                )

    # -----------------------------------------------------
    # PASO 5. VALIDAR AL TRABAJADOR EXISTENTE
    # -----------------------------------------------------

    if not trabajador.activo:
        raise HTTPException(
            status_code=403,
            detail=(
                "Este trabajador se encuentra desactivado. "
                "Contacta al administrador."
            )
        )

    if (
        normalizar(trabajador.nombres)
        != normalizar(nombres)
        or
        normalizar(trabajador.apellidos)
        != normalizar(apellidos)
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "El código de empleado ya está registrado "
                "con otros nombres o apellidos. "
                "Solicita una revisión al administrador."
            )
        )

    # La cuenta debe corresponder al área
    # donde está registrado el trabajador.
    if usuario.rol != "administrador":

        if (
            normalizar(trabajador.area)
            != normalizar(area_cuenta)
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Este código de empleado está asociado "
                    "a otra área. Contacta al administrador."
                )
            )

    # -----------------------------------------------------
    # PASO 6. EMITIR TOKEN DEL TRABAJADOR
    # -----------------------------------------------------

    nuevo_token = crear_token(
        usuario_id=usuario.id,
        rol=usuario.rol,
        trabajador_id=trabajador.id
    )

    return respuesta_autenticacion(
        usuario=usuario,
        token=nuevo_token,
        trabajador=trabajador
    )


# =========================================================
# 3. CONSULTAR LA CUENTA ACTUAL
# =========================================================

@router.get("/me")
def consultar_mi_usuario(
    usuario: Usuario = Depends(
        obtener_usuario_actual
    )
):
    """
    Mantiene la compatibilidad con el
    frontend actual de SIGNIA.
    """

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "fecha_creacion": usuario.fecha_creacion
    }
