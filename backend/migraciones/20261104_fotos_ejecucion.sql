BEGIN;
ALTER TABLE public.maquinas ADD COLUMN IF NOT EXISTS ruta_foto_activo TEXT;
ALTER TABLE public.registros_mantenimiento
    ADD COLUMN IF NOT EXISTS fecha_ejecucion DATE,
    ADD COLUMN IF NOT EXISTS ejecutado_por VARCHAR(150);
COMMIT;
