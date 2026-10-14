# API de la aplicación

Todas las rutas `/api/` requieren sesión. Las escrituras requieren token CSRF. Los datos de un operador requieren `?operator=<UUID>` y una asignación al usuario. Administrador accede a todos los operadores activos. La comprobación se realiza en servidor; alterar la URL no concede permisos.

| Ruta | Métodos | Uso |
|---|---|---|
| `/api/context` | GET | Operadores autorizados, cuentas y preferencias |
| `/api/operators` | GET, POST, PUT | Crear, editar y desactivar operadores; POST y PUT solo Administrador |
| `/api/users` | POST | Crear usuarios y asignar operadores; solo Administrador |
| `/api/accounts` | GET, POST, PUT | Configurar y desactivar cuentas; escrituras solo Administrador |
| `/api/orders` | GET, POST | Historial y registro de órdenes |
| `/api/orders/<UUID>` | PUT, DELETE | Corregir o eliminar una orden |
| `/api/orders/<UUID>/receipt` | GET | Descargar comprobante con autorización |
| `/api/orders/backup` | GET | Exportar órdenes, cuentas, inventario, movimientos y adjuntos |
| `/api/inventory` | GET, PUT | Consultar o conciliar saldos; PUT requiere expectedRevision |
| `/api/withdrawals` | GET, POST | Depósitos y retiros |
| `/api/withdrawals/<UUID>` | PUT, DELETE | Corregir o eliminar movimiento |
| `/api/report` | GET | FIFO, agrupaciones e informes independientes UYU/USD; parámetros from y to |
| `/api/profits` | GET | Totales de operadores autorizados y comparación diaria |
| `/api/calculate` | GET | Ciclo compra/venta con comisión en USDT; buy, sell, amount |
| `/api/import` | POST | Revisión y confirmación de importación |
| `/api/audit` | GET | Últimas 200 acciones del operador |
| `/api/market` | GET | Primeros 10 anuncios por lado; fiat, method |
| `/api/methods` | GET | Catálogo de métodos Binance |
| `/api/recommendations` | GET | Comparación progresiva de medios |
| `/health/` | GET | Estado del proceso, sin datos personales |

Las respuestas monetarias utilizan números JSON para visualización. La base y el cálculo usan Decimal, con 2 decimales para fiat, 6 para precios y 8 para saldos USDT. No deben reconstruirse balances a partir de números de coma flotante del navegador.

## Importación

1. POST `{payload:<respaldo>, mapping:<cuentas>}`: no guarda; devuelve nuevas, duplicadas, errores, destino y comprobantes faltantes.
2. POST con los mismos datos, `confirm:true`, `expectedRevision` y `preserveInventory:true`: valida de nuevo y guarda en una transacción.

No sobrescribe números existentes. Un archivo con errores se rechaza por completo. El UUID del operador del archivo es informativo: el destino se elige explícitamente en la interfaz, porque los JSON antiguos usaban claves victor/rosiriam. Comprueba el nombre de destino antes de confirmar.


## Cambios de la fase 1

Órdenes: `status` (`pending`, `completed`, `cancelled`); `expenseRate` (fracción: 0.01 = 1%); `expenseFixed` (moneda fiat); `expenseNote`. La respuesta agrega `expenses` y `cashTotal`. Los clientes anteriores que omiten estado conservan completed para órdenes nuevas y el estado existente para ediciones. Gastos omitidos en ediciones conservan los existentes.

Inventario: `reservedAccounts`, `availableAccounts`, `reservedBinance`, `availableBinance`, `pendingCount`. PUT acepta `reason`, obligatorio si cambian los saldos. Requiere revisión coincidente y saldos suficientes para las reservas.

Informe: estadísticas solo de completed; `selected` incluye todos los estados para mostrar historial y CSV; `statusCounts` detalla cantidades del período. `totals.expenses` muestra cargos de completadas del período. `buyTotal` incluye gastos; `sellTotal` los descuenta.

Calculadora: `buyExpenseRate`, `sellExpenseRate`, `buyFixed`, `sellFixed`; costos redondeados a centésimos en la moneda del escenario.

Auditoría: create/update/delete de órdenes conservan valores financieros y estado; conciliaciones contienen reason/before/after/differences/binanceDifference.


## Mercado 1.3

GET `/api/market?fiat=UYU&method=Prex&amount=1000&amountUnit=fiat`; amountUnit admite fiat/USDT, amount vacío desactiva el filtro. Límite dos páginas por lado. Los anuncios incluyen userNo y effectiveMaxFiat.

GET `/api/advertiser?userNo=IDENTIFICADOR_PUBLICO`; requiere sesión de la aplicación, devuelve nickname/ads/updatedAt/demo/limited, sin datos privados del perfil. Caché de 30 s; validación del identificador; errores de consulta 502, entradas inválidas 400.
