## EduPack_Builder

**Ruta:** D:\Proyectos\EduPack_Builder
**Estado:** 🟡 Funcional y probado (201+ tests, cobertura ≥75%) — pendiente commit/push y decisiones abiertas
**Evidencia:** Aplicación Flask con flujo completo: usuario ingresa datos en /generar → progreso → vista previa → descargar ZIP. Tiene Procfile (web: gunicorn app:app) para deploy en Railway. README con instrucciones de uso. El último commit 7390aa1 pusheado al remote. Modo debug depende de variable de entorno FLASK_DEBUG (por defecto "0"). `.env.example` creado con las 4 variables reales (SECRET_KEY, EDUPACK_DEV, FLASK_DEBUG, PORT).
**Stack:**
- Backend: Python/Flask, gunicorn, Pillow, requests (acceso HTTP centralizado en edupack/net.py)
- Frontend: HTML/CSS/JS (plantillas Jinja2: index.html, progreso.html, vista_previa.html, historial.html)
- Persistencia: JSON en disco (data/jobs/<id>/estado.json + data/jobs/historial.json) — sin ORM, sin SQLite y sin TTL ni límite de jobs
- Infraestructura: Procfile para deploy en Railway (auto-deploy desde main)
**Git:** ⚠️ On branch main, up to date with 'origin/main', working tree CON cambios sin commitear (fase de auditoría/implementación en curso)
**GitHub:** ✅ origin https://github.com/alvaroberrio23242-eng/EduPack-Builder.git
**Último commit:** 7390aa1 Fase 3: rediseño visual completo (tipografía, tarjetas de resultado, progreso con íconos)
**¿Pusheado?** ✅ Sí — commit 7390aa1 está en origin/main (0 commits por delante de origin/main)
**Deploy:** Parcial — Procfile y Railway auto-deploy desde main; `.env.example` documenta las variables (SECRET_KEY obligatoria)
**Production readiness:** CASI LISTO
- Puntos fuertes: Procfile existente, requirements.txt completa, flujo completo de API, estructura de job IDs, resultados ZIP descargables
- Problemas: debug modo no está bloqueado para producción (depende de FLASK_DEBUG); SECRET_KEY ya no está hardcodeada — si falta, la app falla al arrancar con un error claro (opt-in local EDUPACK_DEV=1 o modo testing); sin política de retención de data/jobs/

### Próximo paso único
**Revisión del diff y decisión de commit/push** — no hay DATABASE_URL porque no existe base de datos