(function () {
    "use strict";

    let tema = "claro";

    try {
        tema = localStorage.getItem("signia_tema") || "claro";
    } catch (error) {
        tema = "claro";
    }

    document.documentElement.dataset.tema =
        tema === "oscuro" ? "oscuro" : "claro";

    function iniciarInterfaz() {
        const lateral = document.querySelector(".menu-lateral");

        // Crear el botón solo si todavía no existe.
        if (!document.querySelector(".signia-tema")) {
            const boton = document.createElement("button");

            boton.type = "button";
            boton.className = "signia-tema";

            function actualizarBoton() {
                const oscuro =
                    document.documentElement.dataset.tema === "oscuro";

                boton.textContent = oscuro
                    ? "Modo claro"
                    : "Modo oscuro";

                boton.setAttribute("aria-pressed", String(oscuro));

                boton.setAttribute(
                    "aria-label",
                    oscuro
                        ? "Cambiar a modo claro"
                        : "Cambiar a modo oscuro"
                );
            }

            boton.addEventListener("click", function () {
                const nuevoTema =
                    document.documentElement.dataset.tema === "oscuro"
                        ? "claro"
                        : "oscuro";

                document.documentElement.dataset.tema = nuevoTema;

                try {
                    localStorage.setItem("signia_tema", nuevoTema);
                } catch (error) {
                    // El cambio funciona aunque no pueda guardarse.
                }

                actualizarBoton();
            });

            actualizarBoton();

            const cerrarSesion = lateral
                ? lateral.querySelector(".cerrar-sesion")
                : null;

            if (cerrarSesion) {
                cerrarSesion.before(boton);
            } else {
                (lateral || document.body).appendChild(boton);
            }
        }

        const menu = document.querySelector("nav.menu");

        if (!menu || menu.dataset.agrupado === "si") return;

        menu.dataset.agrupado = "si";

        const grupos = [
            [
                "Mantenimientos",
                ["registrar-maquina.html", "mantenimientos.html"]
            ],
            [
                "Equipos",
                ["buscar-maquina.html"]
            ],
            [
                "Administración",
                ["reportes.html", "usuarios.html"]
            ]
        ];

        const paginaActual = location.pathname.split("/").pop();

        grupos.forEach(function ([nombre, destinos]) {
            const enlaces = destinos.map(function (destino) {
                return menu.querySelector(
                    'a[href="' + destino + '"]'
                );
            }).filter(Boolean);

            if (!enlaces.length) return;

            const grupo = document.createElement("details");
            grupo.className = "signia-grupo";

            const titulo = document.createElement("summary");
            titulo.textContent = nombre;

            grupo.appendChild(titulo);

            menu.insertBefore(grupo, enlaces[0]);

            enlaces.forEach(function (enlace) {
                grupo.appendChild(enlace);
            });

            grupo.open = enlaces.some(function (enlace) {
                return enlace.getAttribute("href") === paginaActual;
            });

            function actualizarVisibilidad() {
                grupo.hidden = enlaces.every(function (enlace) {
                    return (
                        enlace.hidden ||
                        enlace.style.display === "none"
                    );
                });
            }

            const observador =
                new MutationObserver(actualizarVisibilidad);

            enlaces.forEach(function (enlace) {
                observador.observe(enlace, {
                    attributes: true,
                    attributeFilter: ["style", "hidden"]
                });
            });

            actualizarVisibilidad();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarInterfaz,
            { once: true }
        );
    } else {
        iniciarInterfaz();
    }
})();