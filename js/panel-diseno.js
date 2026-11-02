(function () {
    "use strict";

    function iniciarDiseno() {
        const panel = document.getElementById(
            "resumenAdministrativo"
        );

        if (!panel) return;

        function organizarPanel() {
            const graficos = document.getElementById(
                "graficosCirculares"
            );

            const tabla = document.getElementById(
                "tablaTopFallas"
            );

            if (!graficos || !tabla) return false;

            if (panel.dataset.ordenado === "si") return true;

            const ranking = tabla.closest(".panel-grafico");

            if (!ranking) return false;

            const bloqueAnterior = ranking.closest(
                ".dashboard-analitico"
            );

            // Crear el encabezado una sola vez.
            if (!graficos.querySelector(".panel-analisis-encabezado")) {
                const encabezado = document.createElement("header");

                encabezado.className = "panel-analisis-encabezado";

                const titulo = document.createElement("h2");
                titulo.textContent =
                    "Estado y prioridad de los equipos";

                const descripcion = document.createElement("p");

                descripcion.textContent =
                    "Revisa el estado de las máquinas y los " +
                    "equipos que requieren mayor atención.";

                encabezado.append(titulo, descripcion);
                graficos.prepend(encabezado);
            }

            ranking.classList.add("ranking-integrado");

            const tituloRanking = ranking.querySelector("h3");

            if (tituloRanking) {
                tituloRanking.textContent =
                    "Máquinas que requieren atención prioritaria";
            }

            // Conservar la tabla original y su actualización.
            graficos.appendChild(ranking);

            // Evitar la distribución duplicada con barras.
            if (bloqueAnterior) {
                bloqueAnterior.hidden = true;
            }

            const atencion = document.getElementById(
                "resumenAtencion"
            );

            // Anillos primero; resumen de atención después.
            panel.prepend(graficos);

            if (atencion) {
                graficos.after(atencion);
            }

            panel.dataset.ordenado = "si";

            return true;
        }

        // Evitar repetir el total solo cuando el panel
        // administrativo realmente esté visible.
        const resumenGeneral = document.getElementById(
            "resumenGeneral"
        );

        function actualizarTotalVisible() {
            if (!resumenGeneral) return;

            const panelVisible =
                !panel.hidden &&
                getComputedStyle(panel).display !== "none";

            resumenGeneral.classList.toggle(
                "total-repetido",
                panelVisible
            );
        }

        const observadorVisibilidad = new MutationObserver(
            actualizarTotalVisible
        );

        observadorVisibilidad.observe(panel, {
            attributes: true,
            attributeFilter: ["class", "style", "hidden"]
        });

        actualizarTotalVisible();

        if (!organizarPanel()) {
            const observador = new MutationObserver(function () {
                if (organizarPanel()) {
                    observador.disconnect();
                }
            });

            observador.observe(panel, {
                childList: true,
                subtree: true
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarDiseno,
            { once: true }
        );
    } else {
        iniciarDiseno();
    }
})();