from getpass import getpass

from database import SessionLocal
from models import Usuario
from seguridad import proteger_contrasena


def crear_administrador():
    base_datos = SessionLocal()

    try:
        print("\n=== CREAR PRIMER ADMINISTRADOR ===\n")

        nombre = input(
            "Nombre completo: "
        ).strip()

        correo = input(
            "Correo electrónico: "
        ).strip().lower()

        contrasena = getpass(
            "Contraseña: "
        )

        confirmar_contrasena = getpass(
            "Confirma la contraseña: "
        )

        if not nombre:
            print("ERROR: Debes ingresar un nombre.")
            return

        if not correo or "@" not in correo:
            print("ERROR: El correo electrónico no es válido.")
            return

        if len(contrasena) < 8:
            print(
                "ERROR: La contraseña debe tener "
                "como mínimo 8 caracteres."
            )
            return

        if contrasena != confirmar_contrasena:
            print("ERROR: Las contraseñas no coinciden.")
            return

        usuario_existente = (
            base_datos.query(Usuario)
            .filter(Usuario.correo == correo)
            .first()
        )

        if usuario_existente:
            print(
                "ERROR: Ya existe un usuario con ese correo."
            )
            return

        administrador = Usuario(
            nombre=nombre,
            correo=correo,
            contrasena_hash=proteger_contrasena(
                contrasena
            ),
            rol="administrador",
            activo=True
        )

        base_datos.add(administrador)
        base_datos.commit()
        base_datos.refresh(administrador)

        print("\nAdministrador creado correctamente.")
        print(f"ID: {administrador.id}")
        print(f"Nombre: {administrador.nombre}")
        print(f"Correo: {administrador.correo}")
        print(f"Rol: {administrador.rol}")

    except Exception as error:
        base_datos.rollback()

        print("\nNo se pudo crear el administrador.")
        print(type(error).__name__, str(error))

    finally:
        base_datos.close()


if __name__ == "__main__":
    crear_administrador()