(function () {
    "use strict";

    let iniciado = false;

    async function iniciar(sesion) {
        if (iniciado || !sesion) return;

        const rol = String(sesion.usuario?.rol || "")
            .trim()
            .toLowerCase();

        if (!["administracion", "administrador"].includes(rol)) {
            return;
        }

        const seccion = document.getElementById("prediccionDemo");
        if (!seccion) return;

        iniciado = true;
        seccion.hidden = false;

        const formulario = document.getElementById("formPrediccionDemo");
        const equipos = document.getElementById("equipoPrediccion");
        const fechas = document.getElementById("fechaPrediccion");
        const boton = document.getElementById("consultarPrediccion");
        const mensaje = document.getElementById("mensajePrediccion");
        const resultado = document.getElementById("resultadoPrediccion");

        const api = SIGNIA_API_URL.replace(/\/+$/, "");
        let catalogo = [];
        let consultando = false;

        function opcion(valor, texto) {
            const elemento = document.createElement("option");
            elemento.value = String(valor);
            elemento.textContent = texto;
            return elemento;
        }

        function fechaVisible(fecha) {
            const [anio, mes, dia] = fecha.split("-");
            return `${dia}/${mes}/${anio}`;
        }

        async function consultar(ruta) {
            const controlador = new AbortController();
            const temporizador = setTimeout(
                () => controlador.abort(),
                60000
            );

            try {
                const respuesta = await fetch(api + ruta, {
                    headers: {
                        Authorization: `Bearer ${sesion.token}`
                    },
                    signal: controlador.signal
                });

                let datos = null;

                try {
                    datos = await respuesta.json();
                } catch {
                    // El servidor puede devolver un error sin JSON.
                }

                if (!respuesta.ok) {
                    if (respuesta.status === 401) {
                        throw new Error(
                            "Tu sesión venció. Vuelve a iniciar sesión."
                        );
                    }

                    if (respuesta.status === 403) {
                        throw new Error(
                            "Tu cuenta no tiene permiso para esta consulta."
                        );
                    }

                    throw new Error(
                        typeof datos?.detail === "string"
                            ? datos.detail
                            : "No se pudo completar la consulta."
                    );
                }

                return datos;
            } catch (error) {
                if (error.name === "AbortError") {
                    throw new Error(
                        "El servidor tardó demasiado. Recarga para intentar otra vez."
                    );
                }

                if (error instanceof TypeError) {
                    throw new Error(
                        "No se pudo conectar. Comprueba que el backend esté encendido."
                    );
                }

                throw error;
            } finally {
                clearTimeout(temporizador);
            }
        }

        function actualizarFechas() {
            resultado.hidden = true;

            const equipo = catalogo.find(
                elemento => String(elemento.id) === equipos.value
            );

            fechas.replaceChildren();

            if (!equipo) {
                fechas.disabled = true;
                boton.disabled = true;
                return;
            }

            equipo.fechas.forEach(fecha => {
                fechas.appendChild(
                    opcion(fecha, fechaVisible(fecha))
                );
            });

            fechas.disabled = equipo.fechas.length === 0;
            boton.disabled = fechas.disabled || consultando;
            mensaje.textContent = "Selecciona una fecha y consulta el modelo.";
        }

        equipos.addEventListener("change", actualizarFechas);

        fechas.addEventListener("change", function () {
            resultado.hidden = true;
            mensaje.textContent = "Pulsa Consultar predicción.";
        });

        formulario.addEventListener("submit", async function (evento) {
            evento.preventDefault();

            if (consultando || !equipos.value || !fechas.value) return;

            consultando = true;
            boton.disabled = true;
            equipos.disabled = true;
            fechas.disabled = true;
            resultado.hidden = true;
            mensaje.textContent = "Analizando el historial del equipo…";
            seccion.setAttribute("aria-busy", "true");

            try {
                const parametros = new URLSearchParams({
                    equipo: equipos.value,
                    fecha: fechas.value
                });

                const datos = await consultar(
                    "/prediccion-demo/predecir?" + parametros
                );

                resultado.dataset.alerta = datos.alerta ? "si" : "no";

                document.getElementById("estadoPrediccion").textContent =
                    datos.alerta
                        ? "ALERTA EXPERIMENTAL"
                        : "SIN ALERTA EXPERIMENTAL";

                document.getElementById("tituloPrediccion").textContent =
                    datos.resultado;

                document.getElementById("detallePrediccion").textContent =
                    `${datos.equipo} · Fecha de corte: ` +
                    fechaVisible(datos.fecha_corte) +
                    ` · Horizonte: ${datos.horizonte_dias} días.`;

                document.getElementById(
                "interpretacionPrediccion"
                ).textContent = datos.recomendacion;

                document.getElementById("puntuacionPrediccion").textContent =
                    `Puntuación: ${datos.puntuacion}. ` +
                    `Umbral de alerta: ${datos.umbral}.`;

                resultado.hidden = false;
                mensaje.textContent = "Consulta completada.";
            } catch (error) {
                mensaje.textContent = error.message;
            } finally {
                consultando = false;
                boton.disabled = false;
                equipos.disabled = false;
                fechas.disabled = false;
                seccion.removeAttribute("aria-busy");
            }
        });

        try {
            const datos = await consultar("/prediccion-demo/catalogo");

            if (!Array.isArray(datos.equipos) || !datos.equipos.length) {
                throw new Error("No hay equipos demo disponibles.");
            }

            catalogo = datos.equipos;
            equipos.replaceChildren();

            catalogo.forEach(equipo => {
                equipos.appendChild(opcion(equipo.id, equipo.nombre));
            });

            seccion.querySelector(".pred-demo-modelo").textContent =
                datos.modelo === "random_forest"
                ? "Random Forest"
                : datos.modelo === "regresion_logistica"
                ? "Regresión logística"
                : datos.modelo;

            equipos.disabled = false;
            actualizarFechas();
        } catch (error) {
            equipos.replaceChildren(opcion("", "No disponible"));
            mensaje.textContent = error.message + " Recarga para reintentar.";
        }
    }

    document.addEventListener("signiaSesionLista", function (evento) {
        iniciar(evento.detail);
    });

    function comprobarInicio() {
        if (window.SIGNIA_SESION) {
            iniciar(window.SIGNIA_SESION);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", comprobarInicio);
    } else {
        comprobarInicio();
    }
})();