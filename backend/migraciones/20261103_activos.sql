-- Ejecutar en Supabase > SQL Editor ANTES de desplegar el backend actualizado.
-- Operación aditiva: conserva códigos, datos e historiales existentes.
BEGIN;
ALTER TABLE public.maquinas ADD COLUMN IF NOT EXISTS categoria VARCHAR(30) NOT NULL DEFAULT 'maquinaria';
CREATE INDEX IF NOT EXISTS ix_maquinas_categoria ON public.maquinas(categoria);
COMMIT;
-- Los activos actuales se mantienen como maquinaria. Reclasificar individualmente
-- solo cuando se confirme la categoría real de cada código.
-- Ejemplo (adaptar el código real, no ejecutar sin verificar):
-- UPDATE public.maquinas SET categoria = 'equipo' WHERE codigo = 'CODIGO_REAL';
