(function () {
    "use strict";

    function iniciarGraficos() {
        const panel = document.getElementById(
            "resumenAdministrativo"
        );

        if (!panel || document.getElementById("graficosCirculares")) {
            return;
        }

        const contenedor = document.createElement("section");
        contenedor.id = "graficosCirculares";
        contenedor.className = "graficos-circulares";

        const configuraciones = [
            {
                titulo: "Estado operativo",
                descripcion: "Condición registrada de las máquinas.",
                categorias: [
                    {
                        nombre: "Operables",
                        id: "equiposOperables",
                        color: "#22c55e"
                    },
                    {
                        nombre: "En revisión",
                        id: "equiposRevision",
                        color: "#f59e0b"
                    },
                    {
                        nombre: "Presentan fallas",
                        id: "equiposFallas",
                        color: "#ef4444"
                    }
                ]
            },
            {
                titulo: "Nivel de criticidad",
                descripcion: "Clasificación actual por fallas pendientes.",
                categorias: [
                    {
                        nombre: "Crítica",
                        id: "maquinasCriticas",
                        color: "#ef4444"
                    },
                    {
                        nombre: "Alta",
                        id: "maquinasAltaPrioridad",
                        color: "#f97316"
                    },
                    {
                        nombre: "Media",
                        id: "maquinasPrioridadMedia",
                        color: "#eab308"
                    },
                    {
                        nombre: "Sin fallas pendientes",
                        restante: true,
                        color: "#22c55e"
                    }
                ]
            }
        ];

        function leerNumero(id) {
            const elemento = document.getElementById(id);

            if (!elemento) return null;

            const texto = elemento.textContent.trim();

            return /^\d+$/.test(texto)
                ? Number(texto)
                : null;
        }

        const actualizarGraficos = [];

        configuraciones.forEach(function (configuracion) {
            const tarjeta = document.createElement("article");
            tarjeta.className = "grafico-tarjeta";

            const titulo = document.createElement("h2");
            titulo.textContent = configuracion.titulo;

            const descripcion = document.createElement("p");
            descripcion.className = "grafico-descripcion";
            descripcion.textContent = configuracion.descripcion;

            const cuerpo = document.createElement("div");
            cuerpo.className = "grafico-cuerpo";

            const dona = document.createElement("div");
            dona.className = "grafico-dona";

            // La leyenda presenta los mismos datos al lector de pantalla.
            dona.setAttribute("aria-hidden", "true");

            const centro = document.createElement("div");
            centro.className = "grafico-centro";

            const totalVisible = document.createElement("strong");
            totalVisible.textContent = "—";

            const etiqueta = document.createElement("span");
            etiqueta.textContent = "máquinas";

            centro.append(totalVisible, etiqueta);
            dona.appendChild(centro);

            const leyenda = document.createElement("ul");
            leyenda.className = "grafico-leyenda";

            const mensaje = document.createElement("p");
            mensaje.className = "grafico-mensaje";
            mensaje.setAttribute("role", "status");

            cuerpo.append(dona, leyenda);
            tarjeta.append(titulo, descripcion, cuerpo, mensaje);
            contenedor.appendChild(tarjeta);

            function actualizar() {
                const total = leerNumero("totalMaquinas");

                const valores = configuracion.categorias.map(
                    function (categoria) {
                        return categoria.restante
                            ? null
                            : leerNumero(categoria.id);
                    }
                );

                const datosIncompletos =
                    total === null ||
                    valores.some(function (valor, indice) {
                        return (
                            !configuracion.categorias[indice].restante &&
                            valor === null
                        );
                    });

                leyenda.replaceChildren();
                dona.style.background = "var(--signia-borde)";
                totalVisible.textContent = "—";

                if (datosIncompletos) {
                    mensaje.textContent =
                        "Esperando los indicadores del panel.";
                    return;
                }

                const indiceRestante =
                    configuracion.categorias.findIndex(
                        categoria => categoria.restante
                    );

                if (indiceRestante !== -1) {
                    const suma = valores.reduce(
                        (acumulado, valor) =>
                            acumulado + (valor === null ? 0 : valor),
                        0
                    );

                    valores[indiceRestante] = total - suma;
                }

                const sumaTotal = valores.reduce(
                    (acumulado, valor) => acumulado + valor,
                    0
                );

                if (
                    valores.some(valor => valor < 0) ||
                    sumaTotal !== total
                ) {
                    mensaje.textContent =
                        "Las categorías no coinciden con el total. " +
                        "Revisa los indicadores antes de interpretarlos.";
                    return;
                }

                totalVisible.textContent = total;

                let acumulado = 0;
                const segmentos = [];

                configuracion.categorias.forEach(
                    function (categoria, indice) {
                        const cantidad = valores[indice];
                        const porcentaje = total > 0
                            ? cantidad / total * 100
                            : 0;

                        if (cantidad > 0) {
                            segmentos.push(
                                categoria.color + " " +
                                acumulado + "% " +
                                (acumulado + porcentaje) + "%"
                            );
                        }

                        acumulado += porcentaje;

                        const fila = document.createElement("li");

                        const punto = document.createElement("span");
                        punto.className = "grafico-punto";
                        punto.style.background = categoria.color;
                        punto.setAttribute("aria-hidden", "true");

                        const nombre = document.createElement("span");
                        nombre.className = "grafico-nombre";
                        nombre.textContent = categoria.nombre;

                        const cifra = document.createElement("strong");
                        cifra.textContent =
                            cantidad + " · " +
                            porcentaje.toLocaleString("es-PE", {
                                minimumFractionDigits: 1,
                                maximumFractionDigits: 1
                            }) + "%";

                        fila.title =
                            categoria.nombre + ": " +
                            cantidad + " máquinas";

                        fila.append(punto, nombre, cifra);
                        leyenda.appendChild(fila);
                    }
                );

                if (total > 0) {
                    dona.style.background =
                        "conic-gradient(" + segmentos.join(", ") + ")";

                    mensaje.textContent =
                        "Porcentajes sobre " + total + " máquinas.";
                } else {
                    mensaje.textContent =
                        "No hay máquinas registradas para graficar.";
                }
            }

            actualizarGraficos.push(actualizar);
        });

        // Conserva los permisos del panel administrativo.
        panel.prepend(contenedor);

        let pendiente = false;

        function actualizarTodo() {
            if (pendiente) return;

            pendiente = true;

            requestAnimationFrame(function () {
                pendiente = false;
                actualizarGraficos.forEach(
                    actualizar => actualizar()
                );
            });
        }

        const ids = [
            "totalMaquinas",
            "equiposOperables",
            "equiposRevision",
            "equiposFallas",
            "maquinasCriticas",
            "maquinasAltaPrioridad",
            "maquinasPrioridadMedia"
        ];

        const observador = new MutationObserver(actualizarTodo);

        ids.forEach(function (id) {
            const elemento = document.getElementById(id);

            if (elemento) {
                observador.observe(elemento, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
            }
        });

        actualizarTodo();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarGraficos,
            { once: true }
        );
    } else {
        iniciarGraficos();
    }
})();