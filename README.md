# Monitor P2P y gestor de operaciones — Python 1.4.2

Aplicación web de portfolio para comparar anuncios Binance P2P y gestionar órdenes, cuentas, inventario y movimientos de varios operadores. Backend Django/Python; interfaz HTML, CSS y JavaScript; PostgreSQL para despliegue y SQLite para uso local. La aplicación no realiza compras, ventas ni transferencias en Binance.

## Ajustes de cabecera y avisos (1.4.2)

Icono Binance junto a la campana, manteniendo el mercado UYU o USD del enlace original. Los avisos leídos desaparecen del desplegable; abrir su acción marca ese aviso como leído, y «Marcar como leídas» retira todos los visibles. Los avisos ya leídos de versiones anteriores tampoco se muestran. No se borran las referencias que evitan repetir alertas.

## Diseño de notificaciones

Campana SVG junto al selector de tema, sin texto, con contador flotante y panel desplegable bajo la campana. Tarjetas con iconos, colores según el aviso y acciones, adaptadas a modo claro, oscuro y móvil.

## Notificaciones (1.4)

Campana y panel de avisos por operador: cambios de anuncios propios, órdenes pendientes, saldo disponible bajo y fallos del mercado. Configuración, sonido opcional y avisos del navegador con permiso. Lee [docs/NOTIFICACIONES-1.4.md](docs/NOTIFICACIONES-1.4.md).

## Corrección de creación de órdenes (1.3.1)

Crear Orden comprueba las cuentas disponibles y abre el formulario. Si no hay cuentas, muestra un enlace a Inventario. Las cuentas creadas en otra pestaña se actualizan al volver, conservando el borrador. Un fallo de consulta vuelve a habilitar el botón; no queda bloqueado.

## Anunciantes y filtro por monto (1.3)

Haz clic en un anunciante para consultar sus anuncios públicos en un modal. Filtra las listas por monto en UYU, USD o USDT, comprobando mínimo, máximo efectivo y disponibilidad. Lee [docs/MERCADO-1.3.md](docs/MERCADO-1.3.md).

## Cuentas e iconos (1.2)

Inventario sin cuentas precargadas para instalaciones u operadores nuevos, creación de cuentas desde el inventario, opción para quitar y reactivar cuentas e iconos locales de bancos y billeteras en el mercado. Lee [docs/CUENTAS-1.2.md](docs/CUENTAS-1.2.md).

## Primera fase de mejoras

Estados pendiente/completada/cancelada, reservas de saldo, costos porcentuales y fijos, conciliación con motivo e historial. **Antes de actualizar, sigue [docs/FASE-1.md](docs/FASE-1.md)** para conservar la base de datos y el acceso.

## Funcionalidades

- Inicio de sesión y Administrador inicial. Alta, edición y desactivación de operadores; usuario Binance y comisión configurables.
- Usuarios con acceso solo a operadores asignados. Administrador puede gestionar todos.
- Cuentas configurables en UYU o USD, Binance USDT único y conciliación manual de saldos.
- Mercado UYU y USD/Airtm, varios medios seleccionados, spreads recomendados y Top 5, posición y resaltado del anuncio propio, estados de conexión y recarga automática.
- Calculadora después de los spreads y antes de los anuncios. No comprueba demanda ni disponibilidad para completar la operación.
- Crear y editar órdenes mediante modal, comprobantes privados, filtros, exportación CSV, informes FIFO separados por moneda y reserva del 10% de ganancia positiva.
- Depósitos y retiros mediante modal, historial y correcciones automáticas del saldo.
- Inventario de los operadores autorizados, observación del día anterior y variación ajustada por retiros.
- Importación JSON con revisión y confirmación, sin duplicar órdenes. Respaldo con adjuntos incrustados cuando están disponibles.
- Modo claro/oscuro, datos ficticios de ejemplo y registro de acciones.

## Requisitos

Python 3.12 o superior, pip, acceso a Internet para instalar dependencias. Para mercado real, acceso a Binance y disponibilidad de sus endpoints web. PostgreSQL 16 o Docker Compose para la opción de despliegue. La aplicación local no necesita Node.js.

## Arranque en Windows

1. Extrae el ZIP en una carpeta diferente de la aplicación anterior. No copies la carpeta data encima de esta versión.
2. Instala Python y verifica `py -3 --version` en una terminal.
3. Ejecuta `iniciar-windows.bat`.
4. En el primer arranque elige la contraseña del usuario **admin**. Debe cumplir las reglas mostradas. No hay contraseña predefinida.
5. Abre http://127.0.0.1:8000 e inicia sesión.

El script instala dependencias, crea las tablas y solicita la contraseña solo si aún no existe Administrador. Para recuperar acceso usa `python manage.py changepassword admin` dentro del entorno virtual; no borres la base.

## Arranque manual en Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_admin
python manage.py runserver 127.0.0.1:8000
```

También puedes ejecutar `bash iniciar-linux.sh`. Si Ubuntu no incluye venv, instala el paquete python3-venv de tu distribución. El servidor de desarrollo escucha solo localmente.

## Configuración inicial y operadores

La instalación empieza con un usuario administrador y un operador llamado **Administrador**, sin órdenes ni dinero de ejemplo. No se crean bancos ni billeteras por defecto. Desde **Inventario -> Agregar cuenta**, crea solo las cuentas que utilizas y después concilia sus saldos reales. Binance conserva su campo único en USDT. Configura su usuario de Binance y comisión en **Operadores y cuentas**.

Desde esa sección puedes crear operadores, asignarles usuarios y agregar/desactivar cuentas. Los nombres de operadores se muestran en el selector del mercado. Los usuarios creados desde esa pantalla son usuarios normales, sin permisos de administrador. Para cambiar o desactivar un usuario existente, el Administrador puede utilizar `/admin/`, sección Usuarios. Las tablas financieras del admin son de inspección: las modificaciones pasan por la aplicación.

Desde Inventario puedes quitar una cuenta con saldo cero y sin órdenes pendientes. Su historial se conserva y puedes reactivarla desde Cuentas quitadas. Deja de aceptar órdenes y movimientos nuevos mientras esté desactivada. Un operador desactivado conserva su historial, pero deja de aparecer entre los activos.

## Traer datos de la versión Node.js

1. Conserva tu instalación anterior y respalda toda su carpeta data.
2. Crea los operadores de destino (por ejemplo, Victor y Rosiriam) en la nueva aplicación.
3. Selecciona uno de ellos en el mercado y abre **Órdenes -> Importar JSON**.
4. Carga su orders.json o el respaldo completo descargado desde la aplicación anterior.
5. Asigna las cuentas que no coincidan y pulsa **Revisar importación**. Confirma destino, nuevas órdenes, duplicadas y errores.
6. Confirma la importación. Los saldos ya configurados se mantienen; las operaciones históricas importadas se incorporan a la base de conciliación.
7. Abre Inventario y guarda los saldos reales actuales de ese operador. Repite para el siguiente.

El JSON orders.json contiene referencias a comprobantes, pero no sus bytes. Para recuperar los adjuntos utiliza un respaldo completo con receipt.data. La revisión informa los comprobantes cuyo archivo no está incluido. Los datos nunca se importan automáticamente al instalar.

La importación toma como destino el operador que elegiste y no el nombre del archivo. Las monedas se validan contra la cuenta. Las operaciones antiguas de Airtm con moneda o importes incorrectos deben corregirse antes de importar. El inventario del respaldo no se aplica silenciosamente: guarda los saldos reales después.

## Demostración del portfolio

```bash
python manage.py load_demo
```

Solo funciona en el operador Administrador vacío y carga ejemplos ficticios. Configura `P2P_MARKET_DEMO=1` en `.env` para mostrar anuncios simulados, identificados en la interfaz. Nunca publiques tus datos de Binance, comprobantes o respaldos personales.

Para reiniciar una demo publicada utiliza una base separada y restaura una copia de sus datos ficticios; no ejecutes comandos de borrado sobre tu base real. Incluye en tu presentación un recorrido de mercado -> crear orden -> inventario -> movimientos -> estadísticas -> gestión de operadores.

## Base PostgreSQL

Copia `.env.example` a `.env` y cambia DB_ENGINE a postgresql. Completa DB_NAME, DB_USER, DB_PASSWORD, DB_HOST y DB_PORT, crea esa base y ejecuta `python manage.py migrate` y `python manage.py setup_admin`.

### Docker Compose local

1. Copia `.env.example` a `.env`. Define DB_PASSWORD y DJANGO_SECRET_KEY con valores privados.
2. `docker compose up --build -d`
3. `docker compose exec web python manage.py setup_admin`
4. Abre http://127.0.0.1:8000.

Esta configuración está limitada a localhost y usa HTTP para prueba local. Antes de publicarla configura dominio, HTTPS, cookies seguras y hosts de producción. No uses el ejemplo local de Compose como configuración pública sin adaptarlo.

## Pruebas y calidad

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test p2p
```

La suite comprueba permisos por operador, CSRF, cálculos FIFO, comisiones, corrección/eliminación de órdenes y movimientos, importación idempotente, conciliación y revisión concurrente, comprobantes y comparación diaria. El workflow de GitHub Actions incluido ejecuta la suite con PostgreSQL cuando subas el proyecto a tu repositorio. El informe de validación de esta entrega está en docs/VALIDACION.md.

## Publicación

Configura DJANGO_DEBUG=0, una DJANGO_SECRET_KEY privada, hosts y orígenes CSRF válidos, PostgreSQL y HTTPS. Sirve `/static/` desde collectstatic con el proxy; ejecuta Gunicorn con 1 worker y 4 threads para esta arquitectura de cache. Si un proxy confiable termina HTTPS, configura DJANGO_TRUST_PROXY=1 y elimina cualquier cabecera X-Forwarded-Proto que venga del cliente. Ejecuta `python manage.py check --deploy`. El servidor runserver es para desarrollo.

## Respaldos

SQLite: detén el servidor y copia db.sqlite3; conserva también .local-secret o tu configuración de secreto. PostgreSQL: utiliza pg_dump. Los comprobantes están dentro de la base, por lo que se incluyen en el respaldo de base. No incluyas .env, bases ni secretos en Git.

## Estructura

- config: configuración y rutas.
- p2p/models.py: modelo relacional y restricciones.
- p2p/services.py: cálculos Decimal e inventario.
- p2p/views.py: endpoints, validación y permisos.
- p2p/importing.py: importación revisada.
- p2p/market.py: cliente Binance, cache y demo.
- p2p/tests.py: pruebas automáticas.
- static y templates: interfaz, acceso y modales.
- docs: arquitectura, API y validación.

## Portfolio y autoría

Describe el problema, decisiones de diseño, cálculos y pruebas. Si utilizaste IA para desarrollar, puedes indicarlo: «Proyecto desarrollado con asistencia de IA, con definición de requisitos y validación funcional propia». Estudia las partes que presentes para poder explicarlas en una entrevista.
