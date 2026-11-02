from sqlalchemy import inspect, text

from database import Base, engine

# Importamos los modelos para que SQLAlchemy
# conozca todas las tablas, incluida la nueva
# tabla archivos_mantenimiento.
import models  # noqa: F401


def columna_existe(
    inspector,
    tabla: str,
    columna: str
) -> bool:
    """
    Comprueba si una columna ya existe
    dentro de una tabla.
    """

    columnas = inspector.get_columns(tabla)

    return any(
        item["name"] == columna
        for item in columnas
    )


def actualizar_base_datos():
    print("=" * 60)
    print("ACTUALIZACIÓN DE BASE DE DATOS - SIGNIA")
    print("=" * 60)

    try:
        # -------------------------------------------------
        # 1. COMPROBAR CONEXIÓN
        # -------------------------------------------------

        print("\n[1/5] Comprobando conexión...")

        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))

        print("OK - Conexión correcta.")


        # -------------------------------------------------
        # 2. REVISAR TABLAS ACTUALES
        # -------------------------------------------------

        print("\n[2/5] Revisando estructura actual...")

        inspector = inspect(engine)

        tablas = inspector.get_table_names()

        if "maquinas" not in tablas:
            raise Exception(
                "No existe la tabla 'maquinas'."
            )

        if "registros_mantenimiento" not in tablas:
            raise Exception(
                "No existe la tabla "
                "'registros_mantenimiento'."
            )

        print("OK - Tablas principales encontradas.")


        # -------------------------------------------------
        # 3. AGREGAR COLUMNAS NUEVAS
        # -------------------------------------------------

        print("\n[3/5] Actualizando columnas...")

        with engine.begin() as conexion:

            # ESTADO DEL EQUIPO

            inspector = inspect(engine)

            if not columna_existe(
                inspector,
                "maquinas",
                "estado_equipo"
            ):
                conexion.execute(
                    text(
                        """
                        ALTER TABLE maquinas
                        ADD COLUMN estado_equipo
                        VARCHAR(50)
                        DEFAULT 'operable'
                        """
                    )
                )

                print(
                    "OK - Se agregó "
                    "'estado_equipo'."
                )

            else:
                print(
                    "INFO - 'estado_equipo' "
                    "ya existe."
                )


            # TIPO DE MANTENIMIENTO

            inspector = inspect(engine)

            if not columna_existe(
                inspector,
                "registros_mantenimiento",
                "tipo_mantenimiento"
            ):
                conexion.execute(
                    text(
                        """
                        ALTER TABLE registros_mantenimiento
                        ADD COLUMN tipo_mantenimiento
                        VARCHAR(30)
                        """
                    )
                )

                print(
                    "OK - Se agregó "
                    "'tipo_mantenimiento'."
                )

            else:
                print(
                    "INFO - 'tipo_mantenimiento' "
                    "ya existe."
                )


        # -------------------------------------------------
        # 4. CREAR NUEVA TABLA DE ARCHIVOS
        # -------------------------------------------------

        print(
            "\n[4/5] Creando tabla de evidencias..."
        )

        # create_all NO elimina tablas ni registros.
        # Solo crea las tablas definidas en los modelos
        # que todavía no existan.

        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)

        tablas = inspector.get_table_names()

        if "archivos_mantenimiento" in tablas:
            print(
                "OK - Tabla "
                "'archivos_mantenimiento' disponible."
            )

        else:
            raise Exception(
                "No se pudo crear la tabla "
                "'archivos_mantenimiento'."
            )


        # -------------------------------------------------
        # 5. VERIFICACIÓN FINAL
        # -------------------------------------------------

        print("\n[5/5] Verificando cambios...")

        inspector = inspect(engine)

        columnas_maquinas = [
            columna["name"]
            for columna
            in inspector.get_columns("maquinas")
        ]

        columnas_registros = [
            columna["name"]
            for columna
            in inspector.get_columns(
                "registros_mantenimiento"
            )
        ]

        if "estado_equipo" not in columnas_maquinas:
            raise Exception(
                "No se encontró "
                "'estado_equipo'."
            )

        if (
            "tipo_mantenimiento"
            not in columnas_registros
        ):
            raise Exception(
                "No se encontró "
                "'tipo_mantenimiento'."
            )

        print(
            "OK - estado_equipo"
        )

        print(
            "OK - tipo_mantenimiento"
        )

        print(
            "OK - archivos_mantenimiento"
        )

        print("\n" + "=" * 60)
        print(
            "BASE DE DATOS ACTUALIZADA CORRECTAMENTE"
        )
        print("=" * 60)

        print(
            "\nTus registros anteriores "
            "se conservaron."
        )

        print(
            "SIGNIA ya tiene la estructura "
            "necesaria para continuar."
        )


    except Exception as error:

        print("\n" + "=" * 60)

        print(
            "ERROR AL ACTUALIZAR "
            "LA BASE DE DATOS"
        )

        print("=" * 60)

        print(
            f"\nDetalle: {error}"
        )

        print(
            "\nNo continúes con los siguientes "
            "archivos hasta solucionar este error."
        )


if __name__ == "__main__":
    actualizar_base_datos()