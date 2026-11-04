(function () {
'use strict';
const form = document.getElementById('formActivo');
const boton = document.getElementById('guardarActivo');
const mensaje = document.getElementById('mensajeActivo');
function habilitar(sesion) {if (['administracion','administrador'].includes(sesion?.usuario?.rol)) {boton.disabled=false;mensaje.textContent='Completa los campos obligatorios (*).';}}
document.addEventListener('signiaActivosLista', e => habilitar(e.detail));
if (window.SIGNIA_SESION) habilitar(window.SIGNIA_SESION);
form.addEventListener('submit',async e => {
 e.preventDefault(); if (!form.reportValidity()) return;
 boton.disabled=true; mensaje.dataset.error='no';mensaje.textContent='Guardando…';document.getElementById('consultarActivo').hidden=true;
 const datos=Object.fromEntries(new FormData(form));Object.keys(datos).forEach(k=>datos[k]=datos[k].trim());
 for(const k of ['marca','serie','modelo']) if(!datos[k]) datos[k]='No aplica'; if(!datos.proveedor) datos.proveedor=null;
 try {
    const foto = document.getElementById('fotoNuevoActivo').files[0];
    if (foto && (!['image/jpeg', 'image/png'].includes(foto.type) || foto.size > 5 * 1024 * 1024)) {
        throw new Error('Selecciona una imagen JPG o PNG de hasta 5 MB.');
    }
    const activo = await window.SIGNIA_ACTIVOS.solicitar('/activos', {method:'POST', body:JSON.stringify(datos)});
    const enlace = document.getElementById('consultarActivo');
    enlace.href = 'buscar-maquina.html?' + new URLSearchParams({categoria: activo.categoria, codigo: activo.codigo});
    enlace.hidden = false;
    form.reset();
    mensaje.textContent = 'Activo ' + activo.codigo + ' creado correctamente.';
    if (foto) {
        try {
            await window.SIGNIA_ACTIVOS.guardarFoto(activo.codigo, foto);
        } catch (error) {
            mensaje.textContent += ' ' + error.message + ' Puedes volver a cargarla desde Consultar activo.';
        }
    }
 }
 catch(error){mensaje.dataset.error='si';mensaje.textContent=error.message;}
 finally {boton.disabled=false;}
});
})();
