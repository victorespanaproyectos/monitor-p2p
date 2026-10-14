# Cuentas a medida e iconos (Python 1.2)

## Crear tu inventario

Las instalaciones nuevas y los operadores nuevos empiezan sin bancos ni billeteras creados. Binance mantiene un campo único en USDT.

1. Abre Inventario del operador que corresponda.
2. Pulsa **Agregar cuenta**.
3. Elige un banco o billetera de referencia, o selecciona otro. Escribe el nombre de tu cuenta y selecciona UYU o USD. Puedes crear varias cuentas del mismo banco; usa nombres que permitan distinguirlas.
4. La cuenta se crea con saldo cero. Introduce su saldo real y guarda la conciliación con un motivo.

El selector de institución no crea cuentas hasta confirmar el formulario. Los usuarios autorizados pueden crear cuentas y quitarlas o reactivarlas solo en sus operadores asignados. La administración general y la modificación de datos de cuentas existentes siguen reservadas al administrador.

## Cuentas existentes

La actualización conserva todas tus cuentas, saldos, órdenes e historial. No borra automáticamente cuentas anteriores.

Para quitar un banco precargado que no utilizas, pulsa **Quitar del inventario** junto a su saldo. La cuenta debe tener saldo cero y no tener órdenes pendientes. Se oculta de los campos de saldo y de las selecciones de nuevas operaciones, pero su historial permanece.

Puedes recuperarla desde **Cuentas quitadas -> Volver a usar**. No uses una conciliación ficticia para poner a cero una cuenta que todavía tiene fondos reales; conserva el saldo y registra los movimientos reales que correspondan.

Si todavía estás editando saldos, primero guárdalos o recárgalos antes de crear o quitar cuentas. Esto evita perder cambios del formulario.

## Medios de pago del mercado

Los botones de Santander, Itaú, OCA Blue, MercadoPago, BROU, Prex y Airtm muestran iconos locales en lugar de iniciales. El nombre sigue visible para identificar cada institución. Los medios adicionales utilizan un icono de banco genérico. No se descargan imágenes externas al abrir la aplicación.

Los medios consultables del mercado y tus cuentas del inventario son independientes: puedes comparar anuncios de un medio sin crear una cuenta propia para él.

## Actualización

Detén el servidor, respalda tu carpeta y extrae este ZIP en una carpeta nueva. Copia `db.sqlite3`, `.local-secret` y `.env` si existen, o conserva la configuración y el respaldo de PostgreSQL. Ejecuta `iniciar-windows.bat`. No copies la carpeta `.venv`. No vuelvas a importar órdenes si copiaste la base existente. Se conserva la contraseña. Recarga con Ctrl+F5 si el navegador muestra la interfaz anterior.

Si vienes de Node.js, utiliza el procedimiento de importación del README; no copies su carpeta data sobre esta versión Python.
