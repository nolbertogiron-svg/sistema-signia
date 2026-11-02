
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    func,
)

from sqlalchemy.orm import relationship

from database import Base


# =========================================================
# 1. USUARIOS - CUENTAS DEL SISTEMA Y DE LAS ÁREAS
# =========================================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    nombre = Column(
        String(150),
        nullable=False
    )

    correo = Column(
        String(200),
        unique=True,
        nullable=False,
        index=True
    )

    contrasena_hash = Column(
        String(255),
        nullable=False
    )

    rol = Column(
        String(50),
        nullable=False
    )

    activo = Column(
        Boolean,
        nullable=False,
        default=True
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    registros = relationship(
        "RegistroMantenimiento",
        back_populates="usuario"
    )

    fallas = relationship(
        "FallaMaquina",
        back_populates="usuario",
        foreign_keys="FallaMaquina.usuario_id"
    )


# =========================================================
# 2. TRABAJADORES - IDENTIFICACIÓN INDIVIDUAL
# =========================================================

class Trabajador(Base):
    __tablename__ = "trabajadores"

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    nombres = Column(
        String(100),
        nullable=False
    )

    apellidos = Column(
        String(150),
        nullable=False
    )

    # Se almacena como texto para conservar códigos
    # con ceros iniciales. Ejemplo: 00125.
    codigo_empleado = Column(
        String(5),
        unique=True,
        nullable=False,
        index=True
    )

    area = Column(
        String(100),
        nullable=False
    )

    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Mantenimientos realizados por este trabajador
    registros = relationship(
        "RegistroMantenimiento",
        back_populates="trabajador",
        foreign_keys="RegistroMantenimiento.trabajador_id"
    )

    # Fallas registradas por el trabajador
    fallas_registradas = relationship(
        "FallaMaquina",
        back_populates="trabajador",
        foreign_keys="FallaMaquina.trabajador_id"
    )

    # Fallas solucionadas por el trabajador
    fallas_solucionadas = relationship(
        "FallaMaquina",
        back_populates="trabajador_solucion",
        foreign_keys="FallaMaquina.trabajador_solucion_id"
    )


# =========================================================
# 3. MÁQUINAS
# =========================================================

class Maquina(Base):
    __tablename__ = "maquinas"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    codigo = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    seccion = Column(
        String(100),
        nullable=False
    )

    local = Column(
        String(50),
        nullable=False
    )

    proveedor = Column(
        String(200),
        nullable=True
    )

    ubicacion_referencia = Column(
        Text,
        nullable=False
    )

    tipo_activo = Column(
        String(150),
        nullable=False
    )

    marca = Column(
        String(100),
        nullable=False
    )

    serie = Column(
        String(150),
        nullable=False
    )

    modelo = Column(
        String(150),
        nullable=False
    )

    mantenimiento_febrero = Column(
        String(20),
        nullable=True
    )

    mantenimiento_mayo = Column(
        String(20),
        nullable=True
    )

    mantenimiento_agosto = Column(
        String(20),
        nullable=True
    )

    mantenimiento_noviembre = Column(
        String(20),
        nullable=True
    )

    # Estados:
    # operable
    # en_revision
    # presenta_fallas
    estado_equipo = Column(
        String(50),
        nullable=False,
        default="operable",
        server_default="operable"
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    registros = relationship(
        "RegistroMantenimiento",
        back_populates="maquina",
        cascade="all, delete-orphan"
    )

    fallas = relationship(
        "FallaMaquina",
        back_populates="maquina",
        cascade="all, delete-orphan"
    )


# =========================================================
# 4. REGISTROS DE MANTENIMIENTO
# =========================================================

class RegistroMantenimiento(Base):
    __tablename__ = "registros_mantenimiento"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    maquina_id = Column(
        Integer,
        ForeignKey(
            "maquinas.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Cuenta del sistema o cuenta compartida del área
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )

    # Trabajador individual que realizó el registro
    # Nullable para conservar registros históricos.
    trabajador_id = Column(
        BigInteger,
        ForeignKey("trabajadores.id"),
        nullable=True,
        index=True
    )

    ubicacion_actual = Column(
        Text,
        nullable=False
    )

    comentario = Column(
        Text,
        nullable=False
    )

    # preventivo | correctivo | solo_revision
    tipo_mantenimiento = Column(
        String(30),
        nullable=True
    )

    # Campo antiguo que se conserva para
    # mantener fotografías de registros anteriores.
    foto_url = Column(
        Text,
        nullable=True
    )

    fecha_hora = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    maquina = relationship(
        "Maquina",
        back_populates="registros"
    )

    usuario = relationship(
        "Usuario",
        back_populates="registros"
    )

    trabajador = relationship(
        "Trabajador",
        back_populates="registros",
        foreign_keys=[trabajador_id]
    )

    archivos = relationship(
        "ArchivoMantenimiento",
        back_populates="registro",
        cascade="all, delete-orphan"
    )

    fallas = relationship(
        "FallaMaquina",
        back_populates="registro"
    )


# =========================================================
# 5. ARCHIVOS Y EVIDENCIAS DE MANTENIMIENTO
# =========================================================

class ArchivoMantenimiento(Base):
    __tablename__ = "archivos_mantenimiento"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    registro_id = Column(
        Integer,
        ForeignKey(
            "registros_mantenimiento.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # foto | video | pdf
    tipo = Column(
        String(20),
        nullable=False
    )

    nombre_original = Column(
        String(255),
        nullable=True
    )

    # Ruta dentro de Supabase Storage
    ruta_storage = Column(
        Text,
        nullable=False
    )

    tipo_contenido = Column(
        String(150),
        nullable=True
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    registro = relationship(
        "RegistroMantenimiento",
        back_populates="archivos"
    )


# =========================================================
# 6. FALLAS DE MÁQUINAS
# =========================================================

class FallaMaquina(Base):
    __tablename__ = "fallas_maquina"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    maquina_id = Column(
        Integer,
        ForeignKey(
            "maquinas.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    registro_id = Column(
        Integer,
        ForeignKey(
            "registros_mantenimiento.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    # Cuenta que registró la falla
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )

    # Trabajador que registró la falla
    trabajador_id = Column(
        BigInteger,
        ForeignKey("trabajadores.id"),
        nullable=True,
        index=True
    )

    descripcion = Column(
        Text,
        nullable=False
    )

    # pendiente | solucionada
    estado = Column(
        String(30),
        nullable=False,
        default="pendiente",
        server_default="pendiente"
    )

    fecha_creacion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    fecha_solucion = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Cuenta que solucionó la falla
    usuario_solucion_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True
    )

    # Trabajador que solucionó la falla
    trabajador_solucion_id = Column(
        BigInteger,
        ForeignKey("trabajadores.id"),
        nullable=True,
        index=True
    )

    maquina = relationship(
        "Maquina",
        back_populates="fallas"
    )

    registro = relationship(
        "RegistroMantenimiento",
        back_populates="fallas"
    )

    usuario = relationship(
        "Usuario",
        back_populates="fallas",
        foreign_keys=[usuario_id]
    )

    trabajador = relationship(
        "Trabajador",
        back_populates="fallas_registradas",
        foreign_keys=[trabajador_id]
    )

    trabajador_solucion = relationship(
        "Trabajador",
        back_populates="fallas_solucionadas",
        foreign_keys=[trabajador_solucion_id]
    )
