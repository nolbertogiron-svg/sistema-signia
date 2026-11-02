(function () {
    "use strict";

    function iniciarResumen() {
        const panel =
            document.getElementById("resumenAdministrativo");

        if (!panel || document.getElementById("resumenAtencion")) {
            return;
        }

        const indicadores = [
            {
                id: "equiposFallas",
                titulo: "Máquinas con fallas",
                descripcion: "Equipos registrados con estado de falla.",
                clase: "atencion-roja"
            },
            {
                id: "equiposRevision",
                titulo: "Máquinas en revisión",
                descripcion: "Equipos pendientes de revisión operativa.",
                clase: "atencion-amarilla"
            },
            {
                id: "fallasPendientes",
                titulo: "Fallas pendientes",
                descripcion: "Incidencias que todavía no se han solucionado.",
                clase: "atencion-azul"
            }
        ];

        const bloque = document.createElement("section");
        bloque.id = "resumenAtencion";
        bloque.className = "resumen-atencion";

        const encabezado = document.createElement("div");
        encabezado.className = "atencion-encabezado";

        const textos = document.createElement("div");

        const titulo = document.createElement("h2");
        titulo.textContent = "Atención de mantenimiento";

        const descripcion = document.createElement("p");
        descripcion.textContent =
            "Consulta los equipos e incidencias que requieren seguimiento.";

        textos.append(titulo, descripcion);

        const acceso = document.createElement("a");
        acceso.href = "mantenimientos.html";
        acceso.className = "atencion-acceso";
        acceso.textContent = "Ver mantenimientos →";

        encabezado.append(textos, acceso);

        const lista = document.createElement("div");
        lista.className = "atencion-indicadores";

        indicadores.forEach(function (dato) {
            const origen = document.getElementById(dato.id);

            const tarjeta = document.createElement("article");
            tarjeta.className = "atencion-item " + dato.clase;

            const etiqueta = document.createElement("h3");
            etiqueta.textContent = dato.titulo;

            const numero = document.createElement("strong");
            numero.textContent = "—";

            const detalle = document.createElement("p");
            detalle.textContent = dato.descripcion;

            const estado = document.createElement("small");

            function actualizar() {
                const texto = origen
                    ? origen.textContent.trim()
                    : "";

                // Solo mostrar cifras cuando el panel las haya cargado.
                const valido = /^\d+$/.test(texto);

                numero.textContent = valido ? texto : "—";

                estado.textContent = valido
                    ? "Según los registros del sistema"
                    : "Dato no disponible";
            }

            actualizar();

            if (origen) {
                const observador =
                    new MutationObserver(actualizar);

                observador.observe(origen, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
            }

            tarjeta.append(etiqueta, numero, detalle, estado);
            lista.appendChild(tarjeta);
        });

        const nota = document.createElement("p");
        nota.className = "atencion-nota";
        nota.textContent =
            "Una máquina puede tener varias fallas pendientes. " +
            "Las cantidades representan conceptos distintos y no deben sumarse.";

        bloque.append(encabezado, lista, nota);

        // Se coloca dentro del bloque administrativo para
        // conservar su visibilidad según el rol del usuario.
        panel.prepend(bloque);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarResumen,
            { once: true }
        );
    } else {
        iniciarResumen();
    }
})();