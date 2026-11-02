(function () {
    "use strict";

    function iniciarTendencia() {
        const panel = document.getElementById(
            "resumenAdministrativo"
        );

        if (!panel) return;

        function instalar() {
            const contenedor = document.getElementById(
                "graficosCirculares"
            );

            if (!contenedor) return false;

            if (document.getElementById("tarjetaTendencia")) {
                return true;
            }

            const tarjeta = document.createElement("article");
            tarjeta.id = "tarjetaTendencia";
            tarjeta.className = "grafico-tarjeta tendencia-tarjeta";

            tarjeta.innerHTML = `
                <h2>Fallas registradas por día</h2>

                <p class="grafico-descripcion">
                    Consulta las nuevas fallas registradas en el sistema.
                </p>

                <div class="tendencia-filtros">
                    <label>
                        Periodo
                        <select id="periodoTendencia">
                            <option value="7">Últimos 7 días</option>
                            <option value="30" selected>
                                Últimos 30 días
                            </option>
                            <option value="90">Últimos 90 días</option>
                        </select>
                    </label>

                    <label>
                        Sede del inventario
                        <select id="sedeTendencia">
                            <option value="">Todas las sedes</option>
                        </select>
                    </label>
                </div>

                <p class="tendencia-estado" role="status"></p>

                <div class="tendencia-lienzo"></div>

                <p class="tendencia-nota">
                    Los filtros corresponden únicamente a este gráfico.
                    Los anillos muestran el estado general actual.
                </p>
            `;

            contenedor.appendChild(tarjeta);

            const periodo = tarjeta.querySelector(
                "#periodoTendencia"
            );

            const sede = tarjeta.querySelector(
                "#sedeTendencia"
            );

            const estado = tarjeta.querySelector(
                ".tendencia-estado"
            );

            const lienzo = tarjeta.querySelector(
                ".tendencia-lienzo"
            );

            let solicitud = 0;
            let controlador;

            function dibujar(serie) {
                const ancho = 620;
                const alto = 260;

                const izquierda = 42;
                const derecha = 18;
                const arriba = 20;
                const abajo = 40;

                const utilX = ancho - izquierda - derecha;
                const utilY = alto - arriba - abajo;

                const maximo = Math.max(
                    4,
                    ...serie.map(punto => punto.cantidad)
                );

                // Eje vertical con intervalos enteros.
                const paso = Math.ceil(maximo / 4);
                const limite = paso * 4;

                function x(indice) {
                    return izquierda +
                        indice / Math.max(1, serie.length - 1) * utilX;
                }

                function y(cantidad) {
                    return arriba + utilY -
                        cantidad / limite * utilY;
                }

                let contenido = "";

                for (let i = 0; i <= 4; i++) {
                    const valor = i * paso;
                    const posicion = y(valor);

                    contenido += `
                        <line
                            class="tendencia-rejilla"
                            x1="${izquierda}"
                            y1="${posicion}"
                            x2="${ancho - derecha}"
                            y2="${posicion}"
                        />
                        <text
                            x="${izquierda - 10}"
                            y="${posicion + 4}"
                            text-anchor="end"
                        >${valor}</text>
                    `;
                }

                const puntos = serie.map(function (punto, indice) {
                    return x(indice) + "," + y(punto.cantidad);
                }).join(" ");

                const fechaCorta = function (fecha) {
                    const partes = fecha.split("-");
                    return partes[2] + "/" + partes[1];
                };

                const salto = Math.max(
                    1,
                    Math.ceil((serie.length - 1) / 5)
                );

                serie.forEach(function (punto, indice) {
                    const posicionX = x(indice);
                    const posicionY = y(punto.cantidad);

                    contenido += `
                        <circle
                            class="tendencia-punto"
                            cx="${posicionX}"
                            cy="${posicionY}"
                            r="4"
                        >
                            <title>${punto.fecha}: ${
                                punto.cantidad
                            } fallas registradas</title>
                        </circle>
                    `;

                    if (
                        indice % salto === 0 ||
                        indice === serie.length - 1
                    ) {
                        contenido += `
                            <text
                                x="${posicionX}"
                                y="${alto - 12}"
                                text-anchor="middle"
                            >${fechaCorta(punto.fecha)}</text>
                        `;
                    }
                });

                lienzo.innerHTML = `
                    <svg
                        viewBox="0 0 ${ancho} ${alto}"
                        role="img"
                        aria-label="Cantidad de fallas registradas por día"
                    >
                        <title>Fallas registradas por día</title>
                        <polyline
                            class="tendencia-linea"
                            points="${puntos}"
                        />
                        ${contenido}
                    </svg>
                `;

                // Datos accesibles también como tabla desplegable.
                const detalle = document.createElement("details");
                detalle.className = "tendencia-datos";

                const resumen = document.createElement("summary");
                resumen.textContent = "Ver datos por día";

                const tabla = document.createElement("table");
                const cabecera = document.createElement("thead");
                cabecera.innerHTML =
                    "<tr><th>Fecha</th><th>Fallas registradas</th></tr>";

                const cuerpo = document.createElement("tbody");

                serie.forEach(function (punto) {
                    const fila = document.createElement("tr");

                    const fecha = document.createElement("td");
                    fecha.textContent = punto.fecha;

                    const cantidad = document.createElement("td");
                    cantidad.textContent = punto.cantidad;

                    fila.append(fecha, cantidad);
                    cuerpo.appendChild(fila);
                });

                tabla.append(cabecera, cuerpo);
                detalle.append(resumen, tabla);
                lienzo.appendChild(detalle);
            }

            async function cargar() {
                const numero = ++solicitud;

                if (controlador) controlador.abort();

                controlador = new AbortController();

                estado.textContent = "Cargando datos...";
                lienzo.replaceChildren();
                tarjeta.setAttribute("aria-busy", "true");

                try {
                    const api = window.SIGNIA_CONFIG?.API_URL;

                    if (!api) {
                        throw new Error(
                            "No se cargó la configuración del servidor."
                        );
                    }

                    const token =
                        sessionStorage.getItem("signia_token") ||
                        localStorage.getItem("signia_token");

                    if (!token) {
                        throw new Error(
                            "Inicia sesión para consultar las fallas."
                        );
                    }

                    const parametros = new URLSearchParams({
                        dias: periodo.value
                    });

                    if (sede.value) {
                        parametros.set("sede", sede.value);
                    }

                    const respuesta = await fetch(
                        api + "/panel/tendencia-fallas?" + parametros,
                        {
                            headers: {
                                Authorization: "Bearer " + token
                            },
                            signal: controlador.signal
                        }
                    );

                    if (!respuesta.ok) {
                        throw new Error(
                            respuesta.status === 401 ||
                            respuesta.status === 403
                                ? "Tu sesión no tiene acceso a esta consulta."
                                : "No se pudo consultar el gráfico. " +
                                  "Comprueba que actualizaste main.py."
                        );
                    }

                    const datos = await respuesta.json();

                    if (numero !== solicitud) return;

                    if (
                        !Array.isArray(datos.serie) ||
                        !datos.serie.length ||
                        !datos.serie.every(punto =>
                            /^\d{4}-\d{2}-\d{2}$/.test(punto.fecha) &&
                            Number.isInteger(punto.cantidad) &&
                            punto.cantidad >= 0
                        )
                    ) {
                        throw new Error(
                            "El servidor no devolvió una serie válida."
                        );
                    }

                    const seleccion = sede.value;

                    sede.replaceChildren(
                        new Option("Todas las sedes", "")
                    );

                    datos.sedes.forEach(function (nombre) {
                        sede.add(new Option(nombre, nombre));
                    });

                    sede.value = seleccion;

                    dibujar(datos.serie);

                    estado.textContent =
                        datos.total + " fallas registradas · " +
                        datos.desde + " al " + datos.hasta;
                } catch (error) {
                    if (
                        error.name === "AbortError" ||
                        numero !== solicitud
                    ) return;

                    estado.textContent = error.message;
                } finally {
                    if (numero === solicitud) {
                        tarjeta.setAttribute("aria-busy", "false");
                    }
                }
            }

            periodo.addEventListener("change", cargar);
            sede.addEventListener("change", cargar);

            // Consultar solo cuando la sección administrativa sea visible.
            let cargado = false;

            function cargarSiVisible() {
                if (
                    !cargado &&
                    !panel.hidden &&
                    getComputedStyle(panel).display !== "none"
                ) {
                    cargado = true;
                    cargar();
                    visibilidad.disconnect();
                }
            }

            const visibilidad = new MutationObserver(cargarSiVisible);

            visibilidad.observe(panel, {
                attributes: true,
                attributeFilter: ["class", "style", "hidden"]
            });

            cargarSiVisible();

            return true;
        }

        if (instalar()) return;

        const observador = new MutationObserver(function () {
            if (instalar()) observador.disconnect();
        });

        observador.observe(panel, {
            childList: true,
            subtree: true
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarTendencia,
            { once: true }
        );
    } else {
        iniciarTendencia();
    }
})();