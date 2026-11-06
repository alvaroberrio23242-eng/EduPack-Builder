# EduPack Builder

## STATUS
Desplegado | Actualizado: 2026-11-03

## LINKS
Repo: https://github.com/alvaroberrio23242-eng/EduPack-Builder
Deploy: https://edupack-builder.onrender.com
Notion: ficha interna (enlace no publicado en repo publico)

## OBJECTIVE
App web para armar paquetes educativos completos sobre **cualquier tema** — guía docente, trivia, imágenes, videos, repositorios de código y artículos, todo filtrado por licencia libre y empaquetado e [fuente: README]

## STACK
Flask, Gunicorn

## ARCHITECTURE
Por completar (carpetas y componentes principales).

## CURRENT_STATE
[CONFIRMADO por git 2026-11-03] rama main; ultimo commit: 2026-10-01 fix: harden EduPack jobs and finalize validation; 1 cambios sin commitear; ramas sin mergear a main (refs locales): ninguna.

## PENDING
- Por completar

## DECISIONS
- 2026-11-03: se adopta MIP (MIP.md).

## RISKS
Por completar.

## NEXT
Por completar.

## HANDOFF 2026-11-05 (Claude)

- ESTADO: main = ed681c8 (Fase 3 mezclada y subida a GitHub, LOCAL == origin). 244 tests pasan. Deploy en Render sin verificar (https://edupack-builder.onrender.com; plan gratis: el servicio duerme y los jobs en disco son efimeros).
- HECHO: seleccion de recursos para el ZIP (edupack/seleccion.py, rutas /api/seleccion y /api/reempaquetar); panel y script duplicados de vista_previa.html corregidos; rediseno visual partes 1 y 2 en static/css/rediseno.css (Fraunces, paleta clara, bordes de 1px, tarjetas e insignias de licencia), cargado desde base.html.
- PENDIENTE (en orden): 1) probar en Render con "Historia del Jazz" (diseno, .zip con imagenes, guardar seleccion y actualizar ZIP); 2) mostrar las imagenes en la vista previa (la seccion Imagenes de vista_previa.html no tiene etiqueta img); 3) parte 3 del rediseno (pantalla de progreso: barra mas clara, iconos por tipo de recurso).
- DECISIONES: trabajo solo desde PowerShell con bloques completos (sin OpenCode); nada se marca completado sin evidencia; los cambios visuales no tocan el backend; nunca force push.
- RIESGOS: revision visual en el navegador sin confirmar; imagenes no visibles en la vista previa; deploy sin verificar.
- HISTORIAL: Registro de cambios en Notion (fila de EduPack Builder, 2026-11-05).
