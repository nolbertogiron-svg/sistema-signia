from pathlib import Path
from datetime import datetime, date
from collections import Counter
import csv
import re
import openpyxl


BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
SALIDA = BASE / "resultados"


def texto(valor):
    if valor is None:
        return ""

    if isinstance(valor, (float, int)) and not isinstance(valor, bool):
        if float(valor).is_integer():
            return str(int(valor))

    return str(valor).strip()


def fecha_iso(valor):
    if isinstance(valor, datetime):
        return valor.date().isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    return ""


def buscar_archivo(fragmento):
    encontrados = [
        archivo
        for archivo in DATOS.glob("*.xlsx")
        if fragmento in archivo.name.upper()
        and not archivo.name.startswith("~$")
    ]

    if len(encontrados) != 1:
        raise ValueError(
            f"Debe haber un solo Excel con {fragmento} en {DATOS}"
        )

    return encontrados[0]


def guardar(nombre, filas, columnas):
    ruta = SALIDA / nombre

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas
        )
        escritor.writeheader()
        escritor.writerows(filas)


def preparar():
    preventivo = buscar_archivo("PREVENTIVO")
    historico = buscar_archivo("CORRECTIVO")

    # Leer inventario y programación.
    inventario = []

    libro = openpyxl.load_workbook(
        preventivo,
        read_only=True,
        data_only=True
    )

    hoja = libro.worksheets[0]

    columnas_inventario = [
        "codigo",
        "seccion",
        "sede_inventario",
        "proveedor",
        "ubicacion",
        "tipo_activo",
        "marca",
        "serie",
        "modelo",
        "febrero_programado",
        "mayo_programado",
        "agosto_programado",
        "noviembre_programado"
    ]

    for fila in hoja.iter_rows(min_row=4, values_only=True):
        if fila[0] is None:
            continue

        registro = dict(zip(
            columnas_inventario,
            [texto(valor) for valor in fila[:13]]
        ))

        inventario.append(registro)

    libro.close()

    codigos = {
        equipo["codigo"]
        for equipo in inventario
    }

    # Leer el historial de cotizaciones.
    registros = []
    alertas = []
    vistos = {}

    libro = openpyxl.load_workbook(
        historico,
        read_only=True,
        data_only=True
    )

    for hoja in libro:
        if not hoja.title.startswith("REGISTRO"):
            continue

        for numero, fila in enumerate(
            hoja.iter_rows(min_row=3, values_only=True),
            start=3
        ):
            if not texto(fila[7]):
                continue

            if not texto(fila[11]):
                if texto(fila[9]):
                    alertas.append({
                        "hoja": hoja.title,
                        "fila": numero,
                        "codigo": "",
                        "motivo": (
                            "Trabajo sin codigo de activo; no incluido"
                        )
                    })
                continue

            codigo = texto(fila[11])
            cuenta = texto(fila[9]).upper()

            if "CORRECT" in cuenta:
                tipo = "correctivo"
            elif "PREVENT" in cuenta:
                tipo = "preventivo"
            else:
                tipo = "sin_clasificar"

            fecha = fecha_iso(fila[2])

            registro = {
                "hoja": hoja.title,
                "fila": numero,
                "codigo": codigo,
                "fecha_cotizacion": fecha,
                "fecha_cotizacion_original": texto(fila[2]),
                "fecha_rev_sin_confirmar": texto(fila[3]),
                "tipo": tipo,
                "numero_cotizacion": texto(fila[8]),
                "cuenta_original": texto(fila[9]),
                "detalle": texto(fila[7]),
                "centro_costo": texto(fila[10]),
                "modelo_original": texto(fila[13]),
                "serie_original": texto(fila[14]),
                "costo_usd_original": texto(fila[15]),
                "costo_pen_original": texto(fila[16])
            }

            motivos = []

            if (
                not re.fullmatch(r"\d+(?:-\d+)?", codigo)
                or codigo == "0"
            ):
                motivos.append("Revisar codigo")

            if codigo not in codigos:
                motivos.append(
                    "Sin coincidencia exacta en inventario 2026"
                )

            if not fecha:
                motivos.append(
                    "Fecha de cotizacion vacia o no reconocida"
                )
            elif fecha[:4] not in hoja.title:
                motivos.append(
                    "Anio de cotizacion distinto al de la hoja"
                )

            if tipo == "sin_clasificar":
                motivos.append(
                    "Tipo de mantenimiento no reconocido"
                )

            # Señalar posibles duplicados, sin eliminarlos.
            clave = tuple(
                texto(valor)
                for valor in fila[2:18]
            )

            if clave in vistos:
                motivos.append(
                    "Posible duplicado de " + vistos[clave]
                )
            else:
                vistos[clave] = (
                    f"{hoja.title}, fila {numero}"
                )

            if motivos:
                alertas.append({
                    "hoja": hoja.title,
                    "fila": numero,
                    "codigo": codigo,
                    "motivo": "; ".join(motivos)
                })

            registros.append(registro)

    libro.close()

    if not registros or not inventario:
        raise ValueError(
            "No se encontraron datos. "
            "Revisa la estructura de los Excel."
        )

    SALIDA.mkdir(exist_ok=True)

    guardar(
        "inventario_2026.csv",
        inventario,
        columnas_inventario
    )

    guardar(
        "historial_cotizaciones.csv",
        registros,
        list(registros[0])
    )

    guardar(
        "alertas_revision.csv",
        alertas,
        ["hoja", "fila", "codigo", "motivo"]
    )

    print("Preparacion terminada; originales sin modificar.")
    print("Equipos del inventario:", len(inventario))
    print("Filas del historial:", len(registros))

    print(
        "Tipos:",
        dict(Counter(
            registro["tipo"]
            for registro in registros
        ))
    )

    print("Alertas para revisar:", len(alertas))
    print("Archivos guardados en:", SALIDA)
    print("Todavia no se entrenaron modelos.")


if __name__ == "__main__":
    preparar()