# Notificaciones — 1.4

## Actualizar sin perder los datos

1. Detén la aplicación anterior y conserva una copia completa de su carpeta.
2. Extrae esta versión en una carpeta nueva.
3. Copia desde tu instalación anterior `db.sqlite3`, `.local-secret` y `.env` (si existe) a la raíz de esta versión. No copies sus archivos de código ni el entorno virtual.
4. Ejecuta el iniciador habitual. Esta actualización no añade tablas ni cambia tus órdenes o saldos. El iniciador aplica cualquier migración pendiente de versiones anteriores.
5. Abre la aplicación y actualiza la página si conservabas una pestaña abierta.

El ZIP contiene el proyecto sin información cargada, sin contraseñas ni base de datos de demostración.

## Abrir y configurar

La campana junto al selector de tema aparece en mercado, órdenes, inventario y administración. Muestra el número de avisos sin leer del operador seleccionado. El panel muestra únicamente avisos sin leer. «Marcar como leídas» los retira del panel y del contador. Abrir la acción de un aviso marca solo ese aviso como leído. Los avisos previamente leídos también quedan ocultos. El panel permite borrar el historial y configurar cada tipo. Borrar el historial no cambia las referencias ni vuelve a disparar avisos ya emitidos.

Los ajustes y hasta 60 avisos se conservan en este navegador por usuario y operador; no se sincronizan con otros equipos. Cambiar de operador carga su propio historial. No se modifican registros financieros al emitir un aviso.

## Cambios de anuncio

Vigila precio, cantidad disponible, mínimo, máximo configurado y máximo efectivo. Informa de los valores anteriores y nuevos, para compras y ventas públicas del perfil. Nunca confirma que se creó una orden y nunca crea una orden automáticamente.

La primera consulta válida fija la referencia. Cada anuncio nuevo establece su propia referencia. No se avisa por cambios de posición, estado conectado/desconectado, desapariciones de una muestra, campos desconocidos o respuestas antiguas. La comparación exige el mismo ID, activo, moneda y tipo de anuncio. Si cambia el usuario Binance configurado, se inicia una nueva referencia.

El perfil se identifica por el usuario Binance del operador, inicialmente en una muestra acotada UYU/USD sin filtros. Si no se encuentra, el panel lo informa: abre un mercado y medio de pago donde aparezca tu anuncio. Cuando el listado devuelve tu anuncio, se utiliza su identificador público, verificando que el nombre corresponda al operador. Una vez identificado, se consulta el perfil público completo devuelto por Binance, independientemente del monto y los bancos elegidos en el mercado.

La lista pública puede ser limitada o no incluir anuncios restringidos. El panel muestra si la respuesta es limitada y cuándo fue obtenida. Sin una consulta válida no se puede confirmar un cambio.

### Prueba manual con tu anuncio

1. Selecciona tu operador y confirma que su usuario Binance sea correcto.
2. Abre Avisos y espera «Vigilando … anuncios públicos». La primera lectura no genera avisos.
3. En Binance modifica el precio o un límite de ese anuncio y guarda el cambio.
4. Mantén el monitor abierto y visible. Espera la siguiente consulta; por la caché puede tomar una o dos revisiones.
5. Revisa el aviso «Tu anuncio … cambió» y sus valores. El enlace abre Binance en otra pestaña.
6. Déjalo sin cambios durante otras revisiones: no debe repetir el aviso.

La detección de modificaciones manuales se probó con respuestas simuladas. La reserva de USDT de una orden real depende de que Binance publique ese cambio y debe verificarse con tu operativa real.

## Órdenes pendientes

Tiempo configurable entre 1 minuto y 7 días, inicialmente 30 minutos. Solo considera órdenes pendientes registradas en este monitor, no las órdenes privadas de Binance. Después de la primera lectura, avisa de las que superen el plazo. La referencia es la fecha registrada en la orden. No repite el mismo aviso en cada revisión.

## Saldo disponible bajo

Define un mínimo para cada cuenta activa o Binance USDT; vacío significa sin alerta. Compara saldo disponible, descontando reservas. La primera lectura fija la referencia: avisa al pasar de saldo suficiente a un saldo menor que el mínimo. Se rearma cuando el saldo recupera el mínimo; volver a caer genera un nuevo aviso. Al cambiar la configuración se toma una nueva referencia.

## Fallos de actualización

Dos consultas fallidas consecutivas al mercado generan un aviso con la última actualización correcta conocida durante la sesión. No repite el mismo aviso durante la falla; se rearma después de una consulta correcta. Un error del perfil propio también puede generar un aviso; las fallas de saldos y órdenes se indican en el panel sin fingir datos nuevos.

## Frecuencia, sonido y navegador

Saldos, órdenes y perfil se revisan cada 30 segundos mientras la página esté abierta y visible. Las consultas de mercado siguen la recarga configurada en el mercado. Al volver a la pestaña se revisa nuevamente. Binance conserva hasta 30 segundos de caché de perfil y puede tardar en publicar cambios.

El sonido está desactivado inicialmente; al activarlo se reproduce un sonido de prueba. Puede quedar condicionado por las reglas del navegador. Los avisos de escritorio están desactivados inicialmente y requieren permiso del navegador. Si no están disponibles o no se concede permiso, los avisos internos siguen funcionando.

No se envían correos, mensajes de WhatsApp ni avisos con el monitor cerrado. Los cambios que ocurran y se reviertan entre dos consultas pueden pasar inadvertidos.

## Verificación

77 pruebas del backend, con permisos por operador y validación de identidad del perfil. Comparaciones de primera lectura, respuestas antiguas, campos desconocidos, cambios efectivos y diferencias numéricas mínimas. Pruebas de interfaz con respuestas ficticias para los cuatro tipos, deduplicación, configuración, lectura, tema oscuro y pantalla móvil. No se ejecutaron operaciones reales en Binance.
