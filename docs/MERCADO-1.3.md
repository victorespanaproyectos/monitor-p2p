# Anunciantes y monto (Python 1.3)

## Consultar anuncios de un anunciante

Haz clic en el nombre de cualquier anunciante de las tablas de mercado. Se abre un modal con sus anuncios públicos devueltos por Binance, de compra y venta, incluyendo monedas y activos diferentes a la página actual.

Se muestran precio, disponibilidad, límites efectivos, medios de pago, condiciones públicas y enlace al anuncio. **Compra (tú vendes)** significa que el anunciante compra el activo; **Vende (tú compras)** significa que el anunciante lo vende. El modal indica fecha y hora de consulta, y distingue una lista vacía de un error de conexión. Puedes reintentar y cerrarlo con el botón o Escape. En móvil, desliza la tabla para ver sus columnas.

Se utilizan identificadores públicos de anunciante obtenidos de los anuncios, no coincidencias aproximadas de nombres. Si Binance no devuelve ese identificador, el nombre no se ofrece como botón de consulta.

Los perfiles se guardan temporalmente durante 30 segundos para reducir consultas repetidas. No se presentan como un registro de todos los anuncios de la cuenta: no incluye privados, pausados o restringidos que Binance no exponga. El límite de seguridad es 200 anuncios por lado; si la respuesta lo supera, se informa muestra limitada. No se muestran datos privados de contacto ni cuentas de pago.

## Filtrar por el monto de tu operación

1. En Mercado, completa **Anuncios para tu monto**.
2. Elige la moneda de la página (UYU o USD) o USDT.
3. Pulsa **Aplicar monto**.
4. Para volver al mercado general, pulsa **Sin filtro**.

Se verifica el mínimo, el máximo configurado, los máximos dinámicos cuando estén disponibles y la cantidad de activo disponible. Para USDT, el equivalente fiat se calcula con el precio de cada anuncio. Los anuncios cuya disponibilidad o límites no se pueden comprobar se excluyen del filtro.

El monto es el importe nominal de la operación, antes de comisiones: no sustituye el cálculo del costo total. Tampoco verifica las condiciones particulares de tu cuenta Binance, como antigüedad, nivel de verificación o requisitos del anunciante.

En UYU/USD se pasa el monto a la búsqueda de Binance y se comprueba de nuevo la disponibilidad. En USDT se consulta la muestra de mercado y se verifica cada anuncio por su precio. Se consultan como máximo dos páginas de diez anuncios por lado y medio, conservando hasta diez coincidencias. Puede haber más anuncios compatibles fuera de esa muestra. El orden y las posiciones corresponden a la muestra consultada, no a todo el mercado.

El filtro afecta los listados y sus referencias de precio. La comparación global de medios, el Top 5 y el modal del anunciante siguen separados y no usan el monto de este filtro. Puedes usar la calculadora para evaluar las comisiones y cargos adicionales.

Las respuestas atrasadas de una consulta anterior no reemplazan resultados de un filtro nuevo. Ante un error de Binance, se informa el problema: no se presenta como falta de anuncios.

## Actualización

Detén el servidor y respalda la carpeta anterior. Extrae esta entrega en una carpeta nueva. Copia `db.sqlite3`, `.local-secret` y `.env` si existen, o conserva la configuración y el respaldo de PostgreSQL. Ejecuta `iniciar-windows.bat`. No copies `.venv` ni importes otra vez el historial si ya copiaste la base. La contraseña, las cuentas y el historial se conservan. Recarga con Ctrl+F5 si ves la interfaz anterior.

Las consultas públicas de Binance pueden cambiar o ser limitadas por el servicio. La aplicación solo consulta y muestra información; no ejecuta operaciones.
