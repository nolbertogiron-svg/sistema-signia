(function () {
    'use strict';
    const categorias = {maquinaria: ['Maquinarias', 'maquinaria', 'una maquinaria'], infraestructura: ['Infraestructura', 'infraestructura', 'una infraestructura'], equipo: ['Equipos', 'equipo', 'un equipo']};
    const estados = {operable: '🟢 Operable', en_revision: '🟠 En revisión', presenta_fallas: '🔴 Presenta fallas', inoperativo: '⚫ Inoperativo'};
    const parametros = new URLSearchParams(location.search);
    const categoria = Object.hasOwn(categorias, parametros.get('categoria')) ? parametros.get('categoria') : 'maquinaria';
    window.SIGNIA_CATEGORIA = categoria;
    function esGestion(sesion) {return ['administracion', 'administrador'].includes(sesion?.usuario?.rol);}
    async function solicitar(ruta, opciones = {}) {
        const sesion = window.SIGNIA_SESION;
        if (!sesion?.token) throw new Error('Espera a que se valide tu sesión.');
        const respuesta = await fetch(window.SIGNIA_CONFIG.API_URL + ruta, {...opciones, headers: {...(opciones.body instanceof FormData ? {} : {'Content-Type': 'application/json'}), Authorization: 'Bearer ' + sesion.token, ...opciones.headers}});
        let datos; try {datos = await respuesta.json();} catch (_) {throw new Error('El servidor no respondió correctamente.');}
        if (!respuesta.ok) throw new Error(typeof datos.detail === 'string' ? datos.detail : 'Revisa los datos obligatorios y vuelve a intentarlo.');
        return datos;
    }
    function rutaFoto(codigo) {
        return '/activos/foto?' + new URLSearchParams({codigo});
    }

    function guardarFoto(codigo, foto) {
        if (!['image/jpeg', 'image/png'].includes(foto.type) || foto.size > 5 * 1024 * 1024) {
            throw new Error('Selecciona una imagen JPG o PNG de hasta 5 MB.');
        }
        const datos = new FormData();
        datos.append('foto', foto);
        return solicitar(rutaFoto(codigo), {method: 'PUT', body: datos});
    }

    window.SIGNIA_ACTIVOS = {solicitar, estados, categorias, guardarFoto};
    window.signiaMostrarFotoActivo = function (maquina, destino) {
        const bloque = document.createElement('div');
        bloque.className = 'activo-estado';
        const titulo = document.createElement('h3');
        titulo.textContent = 'Fotografía del activo';
        const foto = document.createElement('img');
        foto.alt = 'Fotografía del activo ' + maquina.codigo;
        foto.style.cssText = 'display:block;max-width:100%;max-height:320px;object-fit:contain';
        foto.style.display = 'none';
        const mensaje = document.createElement('p');
        mensaje.setAttribute('role', 'status');
        bloque.append(titulo, foto, mensaje);
        destino.prepend(bloque);

        async function cargar() {
            try {
                const {url} = await solicitar(rutaFoto(maquina.codigo));
                foto.style.display = url ? 'block' : 'none';
                if (url) foto.src = url;
                mensaje.textContent = url ? '' : 'Este código aún no tiene una fotografía.';
            } catch (error) {
                mensaje.textContent = error.message;
            }
        }
        foto.onerror = () => {foto.style.display = 'none'; mensaje.textContent = 'No se pudo abrir la fotografía.';};

        if (esGestion(window.SIGNIA_SESION)) {
            const selector = document.createElement('input');
            selector.type = 'file';
            selector.accept = 'image/jpeg,image/png';
            selector.setAttribute('aria-label', 'Seleccionar fotografía del activo');
            const guardar = document.createElement('button');
            guardar.type = 'button';
            guardar.textContent = 'Guardar fotografía';
            guardar.onclick = async () => {
                if (!selector.files[0]) {mensaje.textContent = 'Selecciona una fotografía.'; return;}
                guardar.disabled = true;
                mensaje.textContent = 'Guardando fotografía…';
                try {
                    await guardarFoto(maquina.codigo, selector.files[0]);
                    selector.value = '';
                    await cargar();
                } catch (error) {
                    mensaje.textContent = error.message;
                } finally {
                    guardar.disabled = false;
                }
            };
            bloque.append(selector, guardar);
        }
        cargar();
    };
    function iniciar(sesion) {
        const gestion = esGestion(sesion);
        const menu = document.querySelector('nav.menu');
        if (menu && !menu.dataset.activos) {
            menu.dataset.activos = 'si';
            const original = menu.querySelector('a[href="buscar-maquina.html"]');
            if (original) {
                const grupo = original.closest('details');
                if (grupo) grupo.querySelector('summary').textContent = 'Maquinarias';
                original.href = 'buscar-maquina.html?categoria=maquinaria';
                original.textContent = '🔎 Buscar maquinaria';
                for (const clave of ['equipo', 'infraestructura']) {
                    const bloque = document.createElement('details'); bloque.className = 'signia-grupo';
                    const titulo = document.createElement('summary'); titulo.textContent = categorias[clave][0];
                    const enlace = document.createElement('a'); enlace.href = 'buscar-maquina.html?categoria=' + clave; enlace.textContent = '🔎 Buscar ' + categorias[clave][1];
                    bloque.append(titulo, enlace); (grupo || original).after(bloque);
                    if (location.pathname.endsWith('buscar-maquina.html') && categoria === clave) {bloque.open = true; enlace.classList.add('activo'); if (grupo) grupo.open = false;}
                }
                if (gestion) {
                    const nuevo = document.createElement('a');
                    nuevo.href = 'nuevo-activo.html';
                    nuevo.textContent = '＋ Registrar nuevo activo';
                    menu.append(nuevo);
                }
            }
        }
        if (location.pathname.endsWith('buscar-maquina.html')) {
            const datos = categorias[categoria];
            document.title = 'Buscar ' + datos[1] + ' | SIGNIA';
            const ficha = [...document.querySelectorAll('h2')].find(e => e.textContent.includes('Datos del equipo')); if(ficha) ficha.textContent = 'Datos de ' + datos[2];
            const titulo = document.querySelector('h1'); if (titulo) {titulo.textContent = 'Buscar ' + datos[1] + ' por código'; const descripcion = titulo.nextElementSibling; if (descripcion?.tagName === 'P') descripcion.textContent = 'Consulta los datos, el estado actual y el historial de ' + datos[2] + '.';}
            const consulta = [...document.querySelectorAll('h2')].find(e => e.textContent.includes('Consultar')); if (consulta) {consulta.textContent = 'Consultar ' + datos[1]; const desc = consulta.nextElementSibling; if (desc?.tagName === 'P') desc.textContent = 'Escribe el código exacto de ' + datos[2] + '.';}
            const codigoInicial = parametros.get('codigo');
            if (codigoInicial) {const input = document.querySelector('form input'); if(input) input.value = codigoInicial;}
            const form = document.querySelector('form');
            if (form && !document.getElementById('bloquesCategoria')) {
                const bloques = document.createElement('div'); bloques.id = 'bloquesCategoria'; bloques.className = 'activos-bloques';
                Object.entries(categorias).forEach(([clave, valor]) => {const a = document.createElement('a'); a.href = 'buscar-maquina.html?categoria=' + clave; a.textContent = valor[0]; if (clave === categoria) a.setAttribute('aria-current','page'); bloques.append(a);});
                form.before(bloques);
            }
        }
        if (location.pathname.endsWith('panel.html') && !document.getElementById('categoriasPanel')) {
            const bloque = document.createElement('section'); bloque.id = 'categoriasPanel'; bloque.className = 'activos-bloques';
            Object.entries(categorias).forEach(([clave, valor]) => {const a = document.createElement('a'); a.href = 'buscar-maquina.html?categoria=' + clave; a.textContent = valor[0]; a.dataset.categoriaResumen = clave; bloque.append(a);});
            const main = document.querySelector('main'); if (main) main.prepend(bloque);
        }
        document.dispatchEvent(new CustomEvent('signiaActivosLista', {detail: sesion}));
    }
    const estilo = document.createElement('style'); estilo.textContent = '#codigoHistorial{padding:14px;border:1px solid #adc9df;border-radius:10px;font:inherit;min-width:0;flex:1;background:#f7fbff;color:#163a59}#botonBuscarHistorial{padding:14px 24px;border:0;border-radius:10px;background:#5299cd;color:white;font-weight:700;cursor:pointer}.activos-bloques{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}.activos-bloques a{padding:18px 25px;background:var(--fondo-tarjeta,#e6f1fb);color:#155584;border:1px solid #99bad5;border-radius:12px;text-decoration:none;font-weight:700}.activos-bloques a[aria-current]{background:#1769aa;color:white}.estado-inoperativo{background:#dbe1e8;color:#24354b}.activo-estado{padding:16px;border:1px solid #9ab5cd;border-radius:12px;margin-top:14px}.activo-estado select,.activo-estado button{padding:10px;margin:5px}.activo-estado p{margin-top:8px}[data-tema="oscuro"] .activos-bloques a{background:#20374b;color:#e9f4ff}'; document.head.append(estilo);
    document.addEventListener('signiaResumenActualizado', e => {
        Object.entries(e.detail.resumen_categorias || {}).forEach(([clave, valores]) => {
            const a = document.querySelector('[data-categoria-resumen="' + clave + '"]');
            if(a) a.textContent = categorias[clave][0] + ': ' + Object.values(valores).reduce((total, n) => total + Number(n), 0);
        });
    });
    document.addEventListener('signiaSesionLista', e => iniciar(e.detail));
    if (window.SIGNIA_SESION) iniciar(window.SIGNIA_SESION);
    window.signiaMostrarEstadoActivo = function (maquina) {
        document.getElementById('editarEstadoActivo')?.remove();
        if (!esGestion(window.SIGNIA_SESION)) return;
        const destino = document.getElementById('datosEquipo'); if (!destino) return;
        const bloque = document.createElement('div'); bloque.id = 'editarEstadoActivo'; bloque.className = 'activo-estado';
        const label = document.createElement('label'); label.textContent = 'Estado operativo del activo '; const selector = document.createElement('select');
        Object.entries(estados).forEach(([valor, nombre]) => {const option = document.createElement('option'); option.value = valor; option.textContent = nombre; selector.append(option);}); selector.value = maquina.estado_equipo;
        label.append(selector); const guardar = document.createElement('button'); guardar.type = 'button'; guardar.textContent = 'Guardar estado'; const mensaje = document.createElement('p'); mensaje.setAttribute('role','status');
        guardar.onclick = async () => {guardar.disabled = true; mensaje.textContent = 'Guardando…'; try {await solicitar('/maquinas/' + encodeURIComponent(maquina.codigo) + '/estado', {method:'PATCH',body:JSON.stringify({estado_equipo:selector.value})}); mensaje.textContent = 'Estado guardado. Actualizando la consulta…'; document.querySelector('form')?.requestSubmit();} catch (error) {mensaje.textContent = error.message;} finally {guardar.disabled = false;}};
        bloque.append(label,guardar,mensaje); destino.after(bloque);
    };
})();
