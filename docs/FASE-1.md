# Primera fase: órdenes, conciliación y costos

## Estados y reservas

- **Pendiente:** una compra reserva monto bruto más cargos adicionales en su cuenta. Una venta reserva USDT nominales más comisión Binance. Aún no cambia el saldo total ni genera ganancia.
- **Completada:** aplica los movimientos al saldo y entra en promedios, gráficos e informes FIFO.
- **Cancelada:** no aplica movimientos, libera reservas y permanece en el historial.
- Las órdenes anteriores se migran como completadas y con gastos adicionales cero. Es la conducta anterior; revisa y cambia el estado si una orden histórica no terminó realmente.
- El formulario inicia en pendiente. Para registrar una operación histórica terminada, elige completada. La fecha de la orden determina su posición en FIFO y el período del informe: al completar, comprueba que refleje la fecha real de ejecución.
- Saldo **total** = inventario registrado; **reservado** = compromiso de pendientes; **disponible** = total menos reservado. No se cuentan como disponibles las entradas esperadas de órdenes pendientes.
- No se permite reservar más saldo ni hacer cambios que consuman una reserva existente. Las operaciones históricas completadas pueden dejar saldo negativo para revisión, como en la versión anterior, si no comprometen reservas existentes.
- Cambiar una completada a pendiente o cancelada revierte sus efectos y recalcula los informes. Es una corrección del registro interno, no una reversión en Binance. El historial de acciones conserva valores anteriores y nuevos.

## Costos adicionales

En cada orden puedes indicar un porcentaje, un importe fijo y una descripción. El porcentaje se aplica al importe bruto de esa orden; el fijo está en la misma moneda de la cuenta. Ambos se suman y se redondean a centésimos (mitad hacia arriba).

Ejemplo: compra por 100 USD, cargo de 1% y gasto fijo de 0,50 USD. Desembolso total: 101,50 USD. No se modifica la cantidad nominal de USDT comprada: la comisión de Binance se aplica aparte en USDT.

- Compra: los cargos aumentan el dinero pagado y el costo FIFO de las unidades recibidas.
- Venta: los cargos reducen el dinero recibido.
- Ganancia: venta neta menos costo de las unidades consumidas. No se vuelven a restar los gastos ya incorporados en ese cálculo.
- El resumen de gastos del período refleja cargos de órdenes completadas de esas fechas. Puede diferir de los costos realizados: una compra conserva su costo hasta que sus unidades se venden.
- UYU y USD se calculan separados. Si faltan compras anteriores en la misma moneda, la ganancia permanece parcial; no se asigna costo cero.
- Los cargos se pagan en la cuenta de la orden; esta fase no incluye cargos pagados desde otra cuenta o en otra moneda, ni un libro de gastos independientes de una orden.
- Introduce la tarifa real que te cobraron. No se presume una tarifa de Airtm ni se verifica automáticamente. Evita duplicar un cargo ya incluido en el importe ingresado.
- La calculadora de mercado admite cargos y gastos fijos de compra y venta. Las tarjetas de spread y el Top 5 siguen siendo referencias con comisión Binance, sin cargos adicionales del medio.

## Conciliación

1. Abre Inventario del operador adecuado.
2. Compara total, reservado y disponible con tus cuentas reales.
3. Introduce los **saldos totales reales**, no los disponibles tras reservar.
4. Revisa las diferencias que se muestran al editar.
5. Escribe el motivo y confirma **Conciliar saldos**.

Si el saldo cambió en otra sesión, la revisión del servidor rechaza una conciliación desactualizada. Si el saldo real no cubre reservas, primero revisa o cancela las órdenes pendientes correspondientes. Los ajustes no entran como ganancia. Se registran usuario, fecha, motivo, valores anteriores y nuevos, y diferencias por cuenta. La interfaz muestra las conciliaciones contenidas entre las últimas 200 acciones del operador.

## Actualizar sin perder datos (Windows)

Esta entrega es para el monitor **Python/Django**, no se copia sobre la versión Node.js.

1. Detén el servidor anterior con Ctrl+C y guarda una copia de su carpeta completa.
2. Descomprime el ZIP en una carpeta nueva, distinta de la anterior.
3. Copia desde la instalación anterior `db.sqlite3`, `.local-secret` y `.env` si existen. No reemplaces archivos nuevos de código por los anteriores. No copies `.venv`.
4. Si usas PostgreSQL, conserva su configuración `.env` y realiza un respaldo de la base con `pg_dump`; no necesitas `db.sqlite3`.
5. Ejecuta `iniciar-windows.bat` en la carpeta nueva. El script instala las dependencias y ejecuta las migraciones automáticamente. Los usuarios y las contraseñas existentes se conservan.
6. Abre la aplicación y verifica órdenes, inventario y cuentas antes de registrar movimientos nuevos. Si ves archivos antiguos del navegador, recarga con Ctrl+F5.

**No importes de nuevo tu historial si copiaste la base existente:** ya está dentro de la base. Conserva la copia anterior como respaldo. Volver al código anterior después de registrar nuevos datos no es un método de restauración; para deshacer la actualización, restaura la carpeta y base guardadas antes de comenzar.

### Actualización manual

Dentro del entorno virtual:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py runserver 127.0.0.1:8000
```

En una instalación nueva, utiliza el script de inicio para crear el administrador. La entrega no contiene base de datos, usuarios, comprobantes ni contraseñas de demostración.

## Verificación

```powershell
python manage.py test p2p
python manage.py check
python manage.py makemigrations --check --dry-run
```

Las pruebas cubren estados, reservas, insuficiencia de saldo, cambios y cancelaciones, costos y redondeo, FIFO, monedas independientes, importación de datos anteriores, auditoría y migración de una base conciliada. También se comprobaron en navegador la creación y finalización de órdenes, filtros, conciliación con historial y la calculadora con gastos.

## Alcance

Esta fase no ejecuta órdenes ni transferencias externas. Tampoco incluye los cambios propuestos para fases posteriores: calidad y vigencia de cotizaciones, respaldos automáticos programados, panel diario completo o publicación de una demo.
