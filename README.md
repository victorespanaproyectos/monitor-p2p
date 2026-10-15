# Monitor P2P

Aplicación web para consultar anuncios de Binance P2P y llevar el control de operaciones, cuentas y saldos desde un mismo lugar.

El proyecto reúne la comparación de precios con el seguimiento de la operativa: permite calcular costos antes de registrar una orden, reservar fondos mientras está pendiente y revisar los resultados cuando se completa. Cada operador mantiene sus propias cuentas, movimientos e historial.

Está desarrollado con **Python, Django y JavaScript**, con **SQLite** para el uso local y configuración disponible para **PostgreSQL**.

## Funcionalidades

### Mercado P2P

- Consulta de anuncios de compra y venta de USDT en UYU y USD/Airtm.
- Selección de varios medios de pago, identificados con sus iconos.
- Filtro por monto en moneda local o USDT, considerando límites y disponibilidad.
- Consulta de los anuncios públicos de un anunciante desde su nombre.
- Referencias de spread, recomendaciones y ranking de medios de pago.
- Identificación de anuncios propios y de anuncios con el mismo mínimo.
- Actualización automática con intervalos configurables.

### Calculadora de operaciones

Estimación de compras y ventas a partir del precio y el monto. Contempla la comisión de Binance configurada para el operador, cobrada en USDT, y cargos adicionales porcentuales o fijos en la moneda de la operación.

Los cargos adicionales se registran por separado para evitar confundirlos con la comisión de Binance.

### Órdenes

- Registro de compras y ventas con fecha, número de orden, cuenta y medio de pago.
- Estados pendiente, completada y cancelada.
- Reserva de fondos para órdenes pendientes y liberación al cancelarlas.
- Edición de registros y adjuntos de comprobantes privados.
- Filtros por fecha, moneda, tipo y estado.
- Exportación CSV e importación JSON con revisión previa y control de duplicados.

### Cuentas e inventario

Cada operador crea las cuentas que utiliza, en UYU o USD, y registra su saldo de Binance en USDT. La instalación comienza sin cuentas bancarias precargadas.

El inventario distingue saldo total, reservado y disponible. Incluye depósitos, retiros, conciliación de saldos con motivo e historial de ajustes. Las cuentas vacías y sin órdenes pendientes pueden archivarse y reactivarse conservando sus registros.

### Reportes

- Totales de compras, ventas, comisiones y gastos.
- Resultados por período y ranking de medios de pago.
- Cálculo de ganancias mediante FIFO: las ventas se vinculan primero con las compras más antiguas.
- Informes separados en UYU y USD.
- Valoración estimada del inventario y comparación con el día anterior.
- Indicador del 10 % de la ganancia positiva, como referencia de reserva.

Los gastos de compra se incorporan al costo y los de venta reducen el ingreso. Cuando falta información del costo de compra, el resultado se identifica como parcial. Los depósitos, retiros y conciliaciones no se consideran ganancias.

### Notificaciones

La campana junto al selector de tema muestra los avisos del operador seleccionado:

- Cambios de precio, disponibilidad o límites en anuncios propios.
- Órdenes registradas que superan el tiempo configurado como pendientes.
- Saldo disponible que cae por debajo del mínimo definido para una cuenta.
- Fallos de actualización del mercado.

Cada tipo puede activarse por separado. El sonido y las notificaciones del navegador son opcionales. Los avisos leídos desaparecen del panel y del contador.

Las consultas de avisos se realizan cada 30 segundos con la página abierta y visible. La primera lectura de un anuncio establece la referencia de comparación. Un cambio de anuncio no confirma la creación de una orden ni genera registros automáticamente.

### Acceso y personalización

- Administración de operadores y asignación de usuarios.
- Acceso a la información de los operadores autorizados.
- Usuario Binance y comisión configurables por operador.
- Interfaz adaptable y temas claro y oscuro.

## Alcance

Monitor P2P consulta información pública y registra la actividad que se carga en la aplicación. Las compras, ventas y transferencias se realizan fuera del monitor.

Los saldos bancarios se ingresan y concilian manualmente. Las cotizaciones, los spreads y la valoración del inventario son referencias para analizar operaciones; no garantizan disponibilidad ni ganancias.

La consulta del mercado es una muestra acotada, no un listado completo de Binance. La información pública puede variar por región, condiciones del anuncio o disponibilidad del servicio. El perfil de un anunciante utiliza una caché de hasta 30 segundos.

La aplicación se encuentra en fase de pruebas de uso local. La configuración de PostgreSQL y Docker está incluida; no implica que exista una instancia pública desplegada.

## Tecnologías

| Componente | Tecnología |
| --- | --- |
| Backend | Python y Django |
| Frontend | HTML, CSS y JavaScript |
| Base de datos local | SQLite |
| Base de datos configurable | PostgreSQL |
| Pruebas | Suite de Django y workflow de GitHub Actions |
| Configuración de servidor | Gunicorn, Nginx y Docker Compose |

## Instalación local

### Requisitos

- Python 3.12 o superior y pip.
- Git para clonar el repositorio.
- Conexión a Internet para instalar dependencias y consultar Binance.

El frontend no requiere Node.js ni un proceso de compilación.

### Linux / WSL

```bash
git clone https://github.com/victorespanaproyectos/monitor-p2p.git
cd monitor-p2p
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_admin
python manage.py runserver 127.0.0.1:8000
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000). El comando `setup_admin` solicita los datos de acceso; no hay una contraseña predefinida.

En Ubuntu puede ser necesario instalar `python3-venv` para crear el entorno virtual. Después de clonar el repositorio también se puede iniciar mediante `bash iniciar-linux.sh`.

### Windows

1. Clona el repositorio o descarga y extrae su ZIP.
2. Instala Python y comprueba que esté disponible con `py -3 --version`.
3. Ejecuta `iniciar-windows.bat`.
4. Completa la creación del administrador y abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

El iniciador prepara el entorno, instala las dependencias y aplica las migraciones.

## Primeros pasos

1. Inicia sesión y entra en **Operadores y cuentas**.
2. Configura el nombre del operador, su usuario de Binance y la comisión que corresponda.
3. Desde **Inventario**, crea las cuentas que utilizas y carga sus saldos.
4. Selecciona los medios de pago y el monto para consultar el mercado.
5. Registra una orden pendiente cuando necesites reservar fondos. Complétala o cancélala según el resultado real.
6. Configura los avisos desde la campana y revisa la evolución en los reportes.

El administrador puede crear otros operadores y asignarles usuarios. Las credenciales de usuarios existentes se administran desde `/admin/`.

## Datos de demostración

Para cargar ejemplos ficticios en el operador **Administrador**, que debe estar vacío:

```bash
python manage.py load_demo
```

Para consultar anuncios simulados, configura esta variable en `.env` y reinicia el servidor:

```env
P2P_MARKET_DEMO=1
```

El modo de demostración se identifica en la interfaz. Conviene utilizar una instalación separada para las pruebas y mantener los datos personales fuera del repositorio.

## Pruebas

Con el entorno virtual activado:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test p2p
```

La suite incluye permisos por operador, comisiones y cálculos FIFO, reservas, conciliaciones, importación, comprobantes y validaciones de datos. El repositorio incluye un workflow de GitHub Actions para ejecutar las pruebas con PostgreSQL.

## Configuración de servidor

Las variables disponibles están en [`.env.example`](.env.example). La configuración local utiliza SQLite; para PostgreSQL se deben completar las variables `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`.

Para probar Docker Compose localmente:

```bash
cp .env.example .env
# Completar DB_PASSWORD y DJANGO_SECRET_KEY en .env antes de continuar.
docker compose up --build -d
docker compose exec web python manage.py setup_admin
```

El ejemplo de Compose escucha en localhost y utiliza HTTP. Un despliegue público requiere configurar dominio, HTTPS, hosts, orígenes CSRF y cookies seguras, además de desactivar `DJANGO_DEBUG`.

Los archivos estáticos se preparan con `collectstatic` y se sirven desde el proxy. La arquitectura actual mantiene la caché en memoria y está planteada para Gunicorn con un worker y cuatro threads. `runserver` se reserva para desarrollo.

Antes de un despliegue:

```bash
python manage.py check --deploy
```

## Respaldos y actualizaciones

La aplicación permite descargar un respaldo JSON de los registros del operador, con los comprobantes disponibles.

Para conservar una instalación local completa con SQLite, detén el servidor y guarda `db.sqlite3`, `.local-secret` y `.env`, si existe. Los comprobantes se almacenan en la base de datos. Para PostgreSQL, utiliza un respaldo con `pg_dump`.

Antes de actualizar, conserva una copia de la instalación y aplica las migraciones pendientes. Las bases de datos, credenciales y archivos de configuración privados están excluidos mediante `.gitignore`.

## Estructura del proyecto

```text
config/             Configuración de Django y rutas
p2p/models.py       Modelos y restricciones
p2p/services.py     Cálculos, inventario y reglas de negocio
p2p/views.py        Endpoints, validaciones y permisos
p2p/market.py       Consultas públicas de Binance y caché
p2p/importing.py    Revisión e importación de registros
p2p/tests.py        Pruebas automatizadas
static/             Interfaz y recursos del frontend
templates/          Plantillas de acceso y páginas
.github/workflows/  Automatización de pruebas
deploy/             Configuración de Nginx
docs/               Documentación técnica y funcional
```

## Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [API](docs/API.md)
- [Cuentas e inventario](docs/CUENTAS-1.2.md)
- [Anunciantes y filtro por monto](docs/MERCADO-1.3.md)
- [Notificaciones](docs/NOTIFICACIONES-1.4.md)
- [Estados de órdenes, gastos y conciliación](docs/FASE-1.md)
- [Iconos y fuentes](docs/ICONOS.md)
- [Validación técnica](docs/VALIDACION.md)

## Autor

**Víctor España** · [GitHub](https://github.com/victorespanaproyectos)
