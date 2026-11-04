const SIGNIA_API_URL = window.SIGNIA_CONFIG.API_URL;

function obtenerToken() {
    return (
        sessionStorage.getItem("signia_token") ||
        localStorage.getItem("signia_token")
    );
}

function obtenerDatoGuardado(clave) {
    const texto =
        sessionStorage.getItem(clave) ||
        localStorage.getItem(clave);

    if (!texto) return null;

    try {
        return JSON.parse(texto);
    } catch {
        return null;
    }
}

function obtenerUsuarioGuardado() {
    return obtenerDatoGuardado("signia_usuario");
}

function obtenerTrabajadorGuardado() {
    return obtenerDatoGuardado("signia_trabajador");
}

function limpiarSesion() {
    const claves = [
        "signia_token",
        "signia_usuario",
        "signia_trabajador"
    ];

    for (const almacenamiento of [
        sessionStorage,
        localStorage
    ]) {
        for (const clave of claves) {
            almacenamiento.removeItem(clave);
        }
    }
}

function cerrarSesion(evento) {
    if (evento) {
        evento.preventDefault();
    }

    limpiarSesion();
    window.location.replace("index.html");
}

function formatearRol(rol) {
    const nombres = {
        proveedor: "Proveedor",
        tecnico: "Técnico",
        operativo: "Personal operativo",
        administracion: "Administración",
        administrador: "Administrador"
    };

    return nombres[rol] || rol || "Sin rol";
}

function paginaActual() {
    const partes = window.location.pathname.split("/");

    return partes[partes.length - 1] || "panel.html";
}

function paginaInicioPorRol() {
    return "panel.html";
}

function rolPuedeEntrarPagina(rol, pagina) {
    const permisos = {
        "nuevo-activo.html": ["administracion", "administrador"],
        "panel.html": [
            "proveedor",
            "tecnico",
            "operativo",
            "administracion",
            "administrador"
        ],
        "registrar-maquina.html": [
            "proveedor",
            "tecnico",
            "operativo",
            "administracion",
            "administrador"
        ],
        "buscar-maquina.html": [
            "proveedor",
            "tecnico",
            "operativo",
            "administracion",
            "administrador"
        ],
        "mantenimientos.html": [
            "tecnico",
            "administracion",
            "administrador"
        ],
        "reportes.html": [
            "administracion",
            "administrador"
        ],
        "usuarios.html": [
            "administrador"
        ]
    };

    if (!permisos[pagina]) {
        return true;
    }

    return permisos[pagina].includes(rol);
}

function protegerPaginaPorRol(usuario) {
    const rol = String(usuario.rol || "")
        .trim()
        .toLowerCase();

    if (!rolPuedeEntrarPagina(rol, paginaActual())) {
        window.location.replace(paginaInicioPorRol(rol));
        return false;
    }

    return true;
}

function ocultarOpcionPorHref(href) {
    document.querySelectorAll(
        `a[href="${href}"]`
    ).forEach(function (enlace) {
        enlace.style.display = "none";
    });
}

function mostrarOpcionPorHref(href) {
    document.querySelectorAll(
        `a[href="${href}"]`
    ).forEach(function (enlace) {
        enlace.style.display = "";
    });
}

function aplicarMenuPorRol(usuario) {
    const rol = String(usuario.rol || "")
        .trim()
        .toLowerCase();

    const paginas = [
        "panel.html",
        "registrar-maquina.html",
        "buscar-maquina.html",
        "mantenimientos.html",
        "reportes.html",
        "usuarios.html"
    ];

    paginas.forEach(ocultarOpcionPorHref);

    paginas.forEach(function (pagina) {
        if (rolPuedeEntrarPagina(rol, pagina)) {
            mostrarOpcionPorHref(pagina);
        }
    });
}

function mostrarDatosUsuario(usuario, trabajador) {
    const elementoNombre =
        document.getElementById("nombreUsuario");

    const elementoRol =
        document.getElementById("rolUsuario");

    const avatar =
        document.getElementById("avatarUsuario");

    const nombreCompleto = trabajador
        ? `${trabajador.nombres} ${trabajador.apellidos}`
        : usuario.nombre;

    if (elementoNombre) {
        elementoNombre.textContent = nombreCompleto;
    }

    if (elementoRol) {
        elementoRol.textContent = formatearRol(usuario.rol);
    }

    if (avatar) {
        const iniciales = nombreCompleto
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map(parte => parte.charAt(0).toUpperCase())
            .join("");

        avatar.textContent = iniciales || "--";
    }
}

/*
 * Lee el contenido del token para comprobar
 * el estado de la navegación en el frontend.
 *
 * IMPORTANTE:
 * Esto NO verifica la firma del JWT.
 * La seguridad real debe comprobarla FastAPI.
 */
function leerDatosToken(token) {
    try {
        const partes = token.split(".");

        if (partes.length !== 3) return null;

        const base64 = partes[1]
            .replace(/-/g, "+")
            .replace(/_/g, "/");

        const json = atob(base64);

        return JSON.parse(json);
    } catch {
        return null;
    }
}

function tieneIdentificacionLocalValida(token, trabajador) {
    if (!trabajador || !trabajador.id) {
        return false;
    }

    const datos = leerDatosToken(token);

    if (!datos) return false;

    return (
        datos.etapa === "trabajador" &&
        String(datos.trabajador_id) ===
        String(trabajador.id)
    );
}

async function comprobarSesion() {
    const token = obtenerToken();

    if (!token) {
        window.location.replace("index.html");
        return;
    }

    const trabajador = obtenerTrabajadorGuardado();

    /*
     * Si todavía tiene el token inicial de cuenta,
     * debe pasar por la identificación individual.
     */
    if (!tieneIdentificacionLocalValida(token, trabajador)) {
        window.location.replace(
            "identificar-trabajador.html"
        );
        return;
    }

    try {
        const respuesta = await fetch(
            `${SIGNIA_API_URL}/auth/me`,
            {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );

        if (!respuesta.ok) {
            throw new Error("Sesión no válida");
        }

        const usuario = await respuesta.json();

        if (!protegerPaginaPorRol(usuario)) {
            return;
        }

        window.SIGNIA_SESION = {
            token: token,
            usuario: usuario,
            trabajador: trabajador
        };

        mostrarDatosUsuario(usuario, trabajador);

        aplicarMenuPorRol(usuario);

        document.dispatchEvent(
            new CustomEvent(
                "signiaSesionLista",
                {
                    detail: window.SIGNIA_SESION
                }
            )
        );

    } catch (error) {
        limpiarSesion();

        window.location.replace("index.html");
    }
}

document.addEventListener(
    "DOMContentLoaded",
    function () {
        comprobarSesion();

        const botonCerrar =
            document.getElementById("cerrarSesion");

        if (botonCerrar) {
            botonCerrar.addEventListener(
                "click",
                cerrarSesion
            );
        }
    }
);
