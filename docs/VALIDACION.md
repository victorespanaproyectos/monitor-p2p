# Corrección Crear Orden (1.3.1)

- 73 pruebas automáticas aprobadas con SQLite.
- Sintaxis JavaScript comprobada.
- Chromium: abrir el formulario sin cuentas, explicación y enlace a Inventario, crear una cuenta en otra pestaña, actualizar opciones al volver sin perder el borrador, guardar la orden, crear la siguiente y recuperar el botón ante una consulta fallida. Sin errores JavaScript.
- Datos y credenciales de pruebas excluidos de la entrega. No se probó PostgreSQL ni un despliegue público en esta corrección.

# Validación de anunciantes y monto (Python 1.3)

- 73 pruebas automáticas aprobadas con SQLite. Se añaden validación de identificadores públicos, perfil mixto, listas vacías frente a errores, caché, rechazo de datos incompletos, mínimo/máximo/disponibilidad, límites dinámicos, monto nominal en USDT, búsqueda por monto fiat, segunda página acotada y deduplicación.
- Se conserva la suite de cuentas, permisos, conciliación, reservas, gastos, FIFO, importación y migración de versiones anteriores.
- Comprobación Django sin incidencias ni migraciones pendientes. Sintaxis JavaScript comprobada.
- Chromium: filtro fiat válido, monto incompatible, conversión USDT, limpieza del filtro, USD/Airtm, modal del anunciante con monedas distintas, hora de consulta, cierre con Escape, vista móvil a 390 px y tema oscuro. Sin errores JavaScript en esos recorridos.
- Consulta real de Binance: perfil público de DiosLeBendiga recuperado y búsqueda de 1.000 UYU con Prex devolvió diez anuncios; todos pasaron la comprobación de límites y disponibilidad. Estos resultados son temporales, no se guardan como datos de demostración ni se garantiza su disponibilidad futura.
- No se probó PostgreSQL ni un despliegue público en esta actualización. Los datos y credenciales de prueba se excluyen del ZIP.
