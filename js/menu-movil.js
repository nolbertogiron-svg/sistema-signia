(function () {
    "use strict";

    function iniciarMenuMovil() {
        const menu = document.querySelector(".menu-lateral");

        if (!menu || document.querySelector(".barra-movil")) {
            return;
        }

        const pantallaMovil = window.matchMedia(
            "(max-width: 700px)"
        );

        if (!menu.id) {
            menu.id = "menuSignia";
        }

        const barra = document.createElement("div");
        barra.className = "barra-movil";

        const marca = document.createElement("strong");
        marca.textContent = "SIGNIA";

        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "boton-menu-movil";
        boton.setAttribute("aria-controls", menu.id);

        barra.append(marca, boton);
        document.body.prepend(barra);

        function mostrarMenu(abierto) {
            menu.classList.toggle("menu-abierto", abierto);

            boton.textContent = abierto
                ? "Cerrar menú ✕"
                : "☰ Menú";

            boton.setAttribute(
                "aria-expanded",
                String(abierto)
            );

            // Evita entrar con el teclado al menú cerrado.
            menu.inert = pantallaMovil.matches && !abierto;
        }

        boton.addEventListener("click", function () {
            mostrarMenu(
                !menu.classList.contains("menu-abierto")
            );
        });

        menu.addEventListener("click", function (evento) {
            if (
                pantallaMovil.matches &&
                evento.target.closest("a")
            ) {
                mostrarMenu(false);
            }
        });

        document.addEventListener("keydown", function (evento) {
            if (
                evento.key === "Escape" &&
                pantallaMovil.matches &&
                menu.classList.contains("menu-abierto")
            ) {
                mostrarMenu(false);
                boton.focus();
            }
        });

        pantallaMovil.addEventListener("change", function () {
            mostrarMenu(false);
        });

        mostrarMenu(false);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciarMenuMovil,
            { once: true }
        );
    } else {
        iniciarMenuMovil();
    }
})();