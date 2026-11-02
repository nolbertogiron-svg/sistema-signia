(function () {
    "use strict";

    function organizarRegistro() {
        const formulario =
            document.getElementById("formularioMaquina");

        if (!formulario) return;

        // Evita organizar el formulario dos veces.
        if (formulario.dataset.secciones === "listas") return;

        const tarjetas = Array.from(formulario.children)
            .filter(function (elemento) {
                return elemento.matches("section.tarjeta");
            });

        // Esta estructura corresponde al formulario actual.
        // Si cambió, se conserva el formulario original.
        if (tarjetas.length !== 4) return;

        formulario.dataset.secciones = "listas";

        const configuracion = [
            {
                titulo: "Equipo",
                descripcion: "Busca la máquina y verifica sus datos.",
                tarjetas: [tarjetas[0], tarjetas[1]]
            },
            {
                titulo: "Mantenimiento y fallas",
                descripcion: "Registra el trabajo y los hallazgos.",
                tarjetas: [tarjetas[2]]
            },
            {
                titulo: "Evidencias",
                descripcion: "Adjunta fotografías o videos.",
                tarjetas: [tarjetas[3]]
            }
        ];

        const secciones = [];

        configuracion.forEach(function (datos, indice) {
            const seccion = document.createElement("details");
            seccion.className = "registro-seccion";
            seccion.open = indice === 0;

            const encabezado = document.createElement("summary");

            const numero = document.createElement("span");
            numero.className = "registro-numero";
            numero.textContent = indice + 1;

            const textos = document.createElement("span");
            textos.className = "registro-textos";

            const titulo = document.createElement("strong");
            titulo.textContent = datos.titulo;

            const descripcion = document.createElement("small");
            descripcion.textContent = datos.descripcion;

            textos.append(titulo, descripcion);
            encabezado.append(numero, textos);

            const contenido = document.createElement("div");
            contenido.className = "registro-contenido";

            formulario.insertBefore(
                seccion,
                datos.tarjetas[0]
            );

            datos.tarjetas.forEach(function (tarjeta) {
                contenido.appendChild(tarjeta);
            });

            seccion.append(encabezado, contenido);
            secciones.push(seccion);

            if (indice < configuracion.length - 1) {
                const siguiente = document.createElement("button");

                siguiente.type = "button";
                siguiente.className = "registro-continuar";
                siguiente.textContent = "Continuar →";

                siguiente.addEventListener("click", function () {
                    // Comprueba los campos de esta sección.
                    const campos = contenido.querySelectorAll(
                        "input, select, textarea"
                    );

                    for (const campo of campos) {
                        if (
                            campo.willValidate &&
                            !campo.checkValidity()
                        ) {
                            campo.reportValidity();
                            return;
                        }
                    }

                    const proxima = secciones[indice + 1];

                    if (!proxima) return;

                    proxima.open = true;

                    const resumen =
                        proxima.querySelector("summary");

                    resumen.focus();

                    proxima.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                });

                contenido.appendChild(siguiente);
            }
        });

        // Si se intenta guardar con un campo obligatorio
        // incompleto, abre su sección para poder corregirlo.
        formulario.addEventListener(
            "invalid",
            function (evento) {
                const seccion = evento.target.closest(
                    ".registro-seccion"
                );

                if (seccion) {
                    seccion.open = true;
                }
            },
            true
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            organizarRegistro,
            { once: true }
        );
    } else {
        organizarRegistro();
    }
})();