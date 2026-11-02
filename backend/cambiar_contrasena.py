from getpass import getpass

from pwdlib import PasswordHash

from database import SessionLocal
from models import Usuario


def cambiar_contrasena():
    base_datos = SessionLocal()
    password_hash = PasswordHash.recommended()

    try:
        correo = input(
            "Correo del usuario: "
        ).strip().lower()

        usuario = (
            base_datos.query(Usuario)
            .filter(Usuario.correo == correo)
            .first()
        )

        if not usuario:
            print("No existe un usuario con ese correo.")
            return

        nueva_contrasena = getpass(
            "Nueva contraseña: "
        )

        confirmacion = getpass(
            "Repite la nueva contraseña: "
        )

        if len(nueva_contrasena) < 8:
            print(
                "La contraseña debe tener al menos 8 caracteres."
            )
            return

        if nueva_contrasena != confirmacion:
            print("Las contraseñas no coinciden.")
            return

        usuario.contrasena_hash = (
            password_hash.hash(nueva_contrasena)
        )

        base_datos.commit()

        print(
            f"Contraseña actualizada correctamente para {usuario.correo}."
        )

    except Exception as error:
        base_datos.rollback()
        print("No se pudo cambiar la contraseña:")
        print(type(error).__name__, str(error))

    finally:
        base_datos.close()


if __name__ == "__main__":
    cambiar_contrasena()