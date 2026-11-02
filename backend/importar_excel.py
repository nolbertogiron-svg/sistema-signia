from pathlib import Path

from openpyxl import load_workbook

from database import SessionLocal
from models import Maquina


BASE_DIR = Path(__file__).resolve().parent

ARCHIVO_EXCEL = (
    BASE_DIR /
    "MANTENIMIENTO PREVENTIVO SIGNIA 2026.xlsx"
)


def limpiar(valor, valor_vacio=None):
    if valor is None:
        return valor_vacio

    texto = str(valor).strip()

    if not texto:
        return valor_vacio

    return texto


def importar_maquinas():
    if not ARCHIVO_EXCEL.exists():
        print("No se encontró el archivo Excel:")
        print(ARCHIVO_EXCEL)
        return

    libro = load_workbook(
        ARCHIVO_EXCEL,
        data_only=True
    )

    hoja = libro[
        "MANTENIMIENTO PREVENTIVO 2026"
    ]

    base_datos = SessionLocal()

    importadas = 0
    existentes = 0

    try:
        for fila in hoja.iter_rows(
            min_row=4,
            values_only=True
        ):
            codigo = limpiar(fila[0])

            if not codigo:
                continue

            maquina_existente = (
                base_datos
                .query(Maquina)
                .filter(Maquina.codigo == codigo)
                .first()
            )

            if maquina_existente:
                existentes += 1
                continue

            maquina = Maquina(
                codigo=codigo,
                seccion=limpiar(
                    fila[1],
                    "No registrado"
                ),
                local=limpiar(
                    fila[2],
                    "No registrado"
                ),
                proveedor=limpiar(fila[3]),
                ubicacion_referencia=limpiar(
                    fila[4],
                    "No registrado"
                ),
                tipo_activo=limpiar(
                    fila[5],
                    "No registrado"
                ),
                marca=limpiar(
                    fila[6],
                    "No registrado"
                ),
                serie=limpiar(
                    fila[7],
                    "No registrado"
                ),
                modelo=limpiar(
                    fila[8],
                    "No registrado"
                ),
                mantenimiento_febrero=limpiar(
                    fila[9]
                ),
                mantenimiento_mayo=limpiar(
                    fila[10]
                ),
                mantenimiento_agosto=limpiar(
                    fila[11]
                ),
                mantenimiento_noviembre=limpiar(
                    fila[12]
                )
            )

            base_datos.add(maquina)
            importadas += 1

        base_datos.commit()

        print(
            f"Máquinas importadas: {importadas}"
        )

        print(
            f"Máquinas que ya existían: {existentes}"
        )

    except Exception as error:
        base_datos.rollback()

        print("Ocurrió un error durante la importación:")
        print(type(error).__name__, str(error))

    finally:
        base_datos.close()
        libro.close()


if __name__ == "__main__":
    importar_maquinas()