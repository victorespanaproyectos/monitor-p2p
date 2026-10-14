# Arquitectura y decisiones

- Django sirve el acceso y la interfaz; no hay servidor Node.js.
- HTML, CSS y JavaScript mantienen la experiencia web, modales y gráficos.
- PostgreSQL es la base para despliegue; SQLite facilita el arranque individual local.
- `services.py` contiene contabilidad e inventario con Decimal. Los informes, ganancias e inventario se obtienen del backend. Los spreads visuales se estiman también en el navegador para responder al escribir; el cálculo de la calculadora se confirma con Python.
- Usuario y Operador son entidades distintas. Una relación muchos-a-muchos asigna usuarios a operadores. Administrador es un superusuario de Django y el primer operador se llama Administrador.
- Las cuentas tienen moneda, saldo base y estado. No hay nombres de operadores obligatorios. Binance es un saldo USDT único por operador.
- Órdenes guardan la comisión vigente cuando se crean. Cambiar comisión del operador no altera las órdenes antiguas. Cada corrección conserva su tasa histórica.
- Inventario efectivo = saldo base - efectos guardados al conciliar + efectos actuales. Así editar y eliminar cambia la diferencia, y guardar saldos reales establece una nueva base.
- Modificaciones de un operador bloquean su fila en PostgreSQL y se ejecutan en una transacción. SQLite adquiere bloqueo de escritura. expectedRevision evita sobrescribir una conciliación con saldos ya desactualizados.
- Comprobantes se almacenan como bytes en la base de datos para incluirlos en la transacción y en el respaldo. Solo pueden descargarse por la ruta autorizada; no hay carpeta pública de comprobantes. Esta decisión es sencilla para el portfolio; a mayor escala se migraría a almacenamiento privado de objetos.
- FIFO se calcula por moneda. Si una venta está financiada con compras en otra moneda, su costo no se adivina: puede aparecer ganancia parcial. No se suman UYU y USD como si fueran una moneda.
- Valor USD -> USDT -> UYU usa promedios independientes y descuenta comisión USDT. Sin referencias suficientes, se muestra pendiente.
- El historial diario guarda la última observación de cada operador en horario de Montevideo. Días sin uso no se rellenan con valores inventados. Las variaciones pueden deberse a depósitos, retiros, operaciones o cambios en precios de valoración; no equivalen por sí solas a ganancia.
- Binance usa endpoints de su web pública, que pueden cambiar o restringirse. Caché y concurrencia máxima de dos solicitudes por proceso. No se ejecutan operaciones ni se reciben claves API.
- Las consultas completas de métodos se realizan progresivamente en segundo plano. Un único worker con varios threads mantiene coherentes los caches en esta entrega. Para escalar a varios procesos se sustituirían por Redis y un trabajador dedicado.
- Registro Audit guarda actor, acción, operador, identificador y fecha. Las acciones de importación y conciliación quedan registradas. No es un historial completo de valores antes/después.

## Modelo de datos

Usuario <-> Operador -> Cuenta. Operador -> Orden -> Cuenta. Operador -> Movimiento -> Cuenta. Operador -> Audit y DailySnapshot. Orden puede tener comprobante privado.

## Decisiones de seguridad

Sesiones Django, hashes de contraseña del framework, validadores de contraseña, CSRF, permisos en todas las rutas de datos, consultas ORM, adjuntos limitados a 10 MB, respuestas de descarga con sandbox y registros separados. El login limita intentos por usuario/IP dentro del proceso. Para despliegue multiproceso debe utilizarse un cache compartido o limitación en el proxy. Los endpoints de API no exponen datos de operadores no asignados.

Documentación oficial de referencia: https://docs.djangoproject.com/en/5.2/ y https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
