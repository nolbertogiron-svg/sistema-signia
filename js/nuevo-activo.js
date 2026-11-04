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
 try {const activo=await window.SIGNIA_ACTIVOS.solicitar('/activos',{method:'POST',body:JSON.stringify(datos)});mensaje.textContent='Activo '+activo.codigo+' creado correctamente.';const a=document.getElementById('consultarActivo');a.href='buscar-maquina.html?categoria='+encodeURIComponent(activo.categoria)+'&codigo='+encodeURIComponent(activo.codigo);a.hidden=false;form.reset();}
 catch(error){mensaje.dataset.error='si';mensaje.textContent=error.message;}
 finally {boton.disabled=false;}
});
})();
