
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


# =========================================================
# 1. USUARIOS - CUENTAS DEL SISTEMA
# =========================================================

class UsuarioCrear(BaseModel):
    nombre: str = Field(
        min_length=2,
        max_length=150
    )

    correo: EmailStr

    contrasena: str = Field(
        min_length=8,
        max_length=100
    )

    rol: str = Field(
        min_length=3,
        max_length=50
    )


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    nombre: str
    correo: EmailStr
    rol: str
    activo: bool
    fecha_creacion: datetime


# =========================================================
# 2. TRABAJADORES - IDENTIFICACIÓN INDIVIDUAL
# =========================================================

class TrabajadorIdentificar(BaseModel):
    """
    Datos que ingresa el trabajador después de
    iniciar sesión con la cuenta de su área.
    """

    nombres: str = Field(
        min_length=2,
        max_length=100
    )

    apellidos: str = Field(
        min_length=2,
        max_length=150
    )

    codigo_empleado: str = Field(
        min_length=1,
        max_length=5,
        pattern=r"^[0-9]{1,5}$"
    )

    @field_validator("nombres", "apellidos")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor = " ".join(valor.strip().split())

        if len(valor) < 2:
            raise ValueError(
                "Debes ingresar al menos dos caracteres"
            )

        return valor


class TrabajadorCrear(TrabajadorIdentificar):
    """
    Datos para registrar un trabajador autorizado.

    El administrador indica a qué área pertenece.
    """

    area: str = Field(
        min_length=2,
        max_length=100
    )

    @field_validator("area")
    @classmethod
    def validar_area(cls, valor: str) -> str:
        valor = " ".join(valor.strip().split())

        if len(valor) < 2:
            raise ValueError(
                "Debes ingresar un área válida"
            )

        return valor


class TrabajadorRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    nombres: str
    apellidos: str
    codigo_empleado: str
    area: str
    activo: bool
    fecha_creacion: datetime


class TrabajadorSesion(BaseModel):
    """
    Información del trabajador identificado
    que puede devolverse al frontend.
    """

    id: int
    nombres: str
    apellidos: str
    codigo_empleado: str
    area: str


# =========================================================
# 3. ARCHIVOS DE MANTENIMIENTO
# =========================================================

class ArchivoMantenimientoRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    registro_id: int

    # foto | video | pdf
    tipo: str

    nombre_original: Optional[str] = None

    ruta_storage: str

    tipo_contenido: Optional[str] = None

    fecha_creacion: datetime


# =========================================================
# 4. MÁQUINAS
# =========================================================

class MaquinaRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    codigo: str
    seccion: str
    local: str

    proveedor: Optional[str] = None

    ubicacion_referencia: str
    tipo_activo: str
    marca: str
    serie: str
    modelo: str

    mantenimiento_febrero: Optional[str] = None
    mantenimiento_mayo: Optional[str] = None
    mantenimiento_agosto: Optional[str] = None
    mantenimiento_noviembre: Optional[str] = None

    estado_equipo: str = "operable"

    fecha_creacion: datetime


# =========================================================
# 5. ACTUALIZACIÓN DEL ESTADO DE UNA MÁQUINA
# =========================================================

class EstadoMaquinaActualizar(BaseModel):
    estado_equipo: str = Field(
        min_length=3,
        max_length=50
    )


# =========================================================
# 6. REGISTROS DE MANTENIMIENTO
# =========================================================

class RegistroCrear(BaseModel):
    codigo_maquina: str = Field(
        min_length=1,
        max_length=50
    )

    ubicacion_actual: str = Field(
        min_length=2,
        max_length=500
    )

    comentario: str = Field(
        min_length=2,
        max_length=2000
    )

    # preventivo | correctivo | solo_revision
    tipo_mantenimiento: str = Field(
        min_length=5,
        max_length=30
    )

    # Cuenta compartida o usuario del sistema
    usuario_id: Optional[int] = None


class RegistroRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    maquina_id: int

    usuario_id: Optional[int] = None

    # Opcional para conservar registros antiguos.
    trabajador_id: Optional[int] = None

    ubicacion_actual: str
    comentario: str

    tipo_mantenimiento: Optional[str] = None

    # Compatibilidad con fotografías antiguas
    foto_url: Optional[str] = None

    fecha_hora: datetime

    archivos: list[ArchivoMantenimientoRespuesta] = Field(
        default_factory=list
    )


# =========================================================
# 7. FALLAS Y OBSERVACIONES DE MÁQUINAS
# =========================================================

class FallaCrear(BaseModel):
    descripcion: str = Field(
        min_length=2,
        max_length=2000
    )


class FallaSolucionar(BaseModel):
    estado: str = "solucionada"


class FallaRespuesta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    maquina_id: int

    registro_id: Optional[int] = None

    # Cuenta del sistema que registró la falla
    usuario_id: Optional[int] = None

    # Trabajador individual que registró la falla
    trabajador_id: Optional[int] = None

    descripcion: str
    estado: str

    fecha_creacion: datetime

    fecha_solucion: Optional[datetime] = None

    # Cuenta del sistema que solucionó la falla
    usuario_solucion_id: Optional[int] = None

    # Trabajador individual que solucionó la falla
    trabajador_solucion_id: Optional[int] = None


# =========================================================
# 8. RESPUESTA GENERAL
# =========================================================

class MensajeRespuesta(BaseModel):
    mensaje: str
