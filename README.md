# 🍩 SHAR MP Admin Panel

Panel administrativo en **Python GUI** para gestionar servidores de **The Simpsons: Hit & Run Multiplayer Server** usando una interfaz compacta, profesional y simple.

Proyecto creado por **Azzlaer + ChatGPT (OpenAI)** para la comunidad **LatinBattle.com**.

---

## 📌 Descripción

**SHAR MP Admin Panel** es una herramienta gráfica para Windows diseñada para administrar un servidor de **The Simpsons: Hit & Run Multiplayer Server** desde una sola ventana.

Permite iniciar y detener el servidor, leer la consola en tiempo real, enviar comandos, editar `Server.yaml`, administrar usuarios desde SQLite `.db.ocala` y enviar anuncios automáticos a Discord mediante webhooks.

El panel fue creado pensando en administradores de servidores que desean una solución visual, ordenada y fácil de configurar sin depender de herramientas externas.

---

## ✨ Características principales

- Interfaz GUI compacta y profesional.
- Consola del servidor en tiempo real.
- Inicio, detención y reinicio del servidor.
- Envío de comandos al servidor desde el panel.
- Lectura de logs línea por línea.
- Editor visual para `Server.yaml`.
- Administración de usuarios desde SQLite `.db.ocala`.
- Soporte para tabla oficial `users`.
- Crear usuarios desde el panel.
- Resetear contraseña generando hash SHA256 compatible con `/login`.
- Cambiar flags de usuario:
  - `operator`
  - `remember_me`
- Visualizar:
  - username
  - password_hash
  - operator
  - remember_me
  - última IP
  - fecha de creación
  - último login
- Exportar usuarios a CSV.
- Ver esquema SQLite de la base.
- Ejecutar `integrity_check`.
- Bot Discord integrado por webhooks.
- Webhooks separados para:
  - servidor online
  - conexión de jugador
  - desconexión de jugador
  - chat del juego
- Mensajes de Discord personalizables desde el GUI.
- Compatible con múltiples webhooks por evento.
- No requiere librerías externas.

---

## 🧩 Estructura del proyecto

```text
SHAR_MP_Admin_Panel/
├── main.py
├── config.ini
├── run_panel.bat
├── run_panel_admin.bat
└── README.md
```

---

## 🖥️ Requisitos

- Windows 10/11 x64.
- Python 3.10 o superior.
- Servidor de **The Simpsons: Hit & Run Multiplayer Server** instalado.
- Mod `Simpsons Hit & Run Multiplayer` instalado en `ServerMods`.
- Archivo `Server.yaml` existente.
- Base SQLite `.db.ocala` generada por el servidor.

No requiere instalar dependencias externas. El panel usa módulos estándar de Python:

```text
tkinter
sqlite3
subprocess
threading
configparser
urllib
hashlib
csv
json
re
queue
```

---

## 📁 Rutas recomendadas

Ejemplo de estructura usada durante el desarrollo:

```text
D:\Juegos\Vivendi Universal Games\
├── main.py
├── config.ini
├── run_panel.bat
└── Server\
    ├── SHARMPServer.exe
    ├── Server.yaml
    └── ServerMods\
        └── Simpsons Hit & Run Multiplayer\
            └── .db.ocala
```

Ruta del servidor:

```text
D:\Juegos\Vivendi Universal Games\Server
```

Ruta del archivo `Server.yaml`:

```text
D:\Juegos\Vivendi Universal Games\Server\Server.yaml
```

Ruta de la base de datos:

```text
D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer\.db.ocala
```

---

## ⚙️ Configuración inicial

El archivo principal de configuración es:

```text
config.ini
```

Ejemplo recomendado:

```ini
[SERVER]
exe_path = D:\Juegos\Vivendi Universal Games\Server\SHARMPServer.exe
working_dir = D:\Juegos\Vivendi Universal Games\Server
startup_args =
auto_scroll = true
send_exit_on_stop = true
kill_after_seconds = 5
server_yaml_path = D:\Juegos\Vivendi Universal Games\Server\Server.yaml

[DATABASE]
sqlite_path = D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer\.db.ocala
mod_folder = D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer
users_table = users
auto_connect = true

[DISCORD]
enabled = false
username = SHAR MP Bot
avatar_url =
status_webhooks =
connect_webhooks =
disconnect_webhooks =
chat_webhooks =
send_online = true
send_connect = true
send_disconnect = true
send_chat = true
message_online = 🟢 Servidor online en el puerto {port}.
message_connect = ✅ **{player}** ha entrado al servidor. Nivel: {level} | Personaje: {character}
message_disconnect = ❌ **{player}** ha salido del servidor. Razón: {reason}
message_chat = **{player}:** {message}
log_discord_to_console = true

[UI]
console_max_lines = 2500
```

---

## ▶️ Ejecución

Desde PowerShell o CMD:

```bat
python main.py
```

También puedes usar:

```bat
run_panel.bat
```

Para ejecutar como administrador:

```bat
run_panel_admin.bat
```

---

## 🖥️ Pestañas del panel

### Consola

Permite ver el log completo del servidor en tiempo real.

Funciones:

- leer salida del servidor
- enviar comandos
- limpiar consola
- activar/desactivar auto-scroll

Ejemplo de logs detectados:

```text
[RakNet] Server started on port 7777
[RakNet::GameStart] 193655237974965221 (azzlaer#5261) is starting the game on level 0 with character 1
[Received Chat Message] azzlaer#2707: muy bueno
[Client] [Client Disconnected] 193655237974965221 (No message given)
```

---

### Discord

El panel incluye un sistema de bot por **Discord Webhook**.

Eventos soportados:

- servidor online
- jugador conectado
- jugador desconectado
- mensajes del chat del juego

Cada evento puede tener su propio webhook.

También se pueden configurar varios webhooks por evento, escribiendo uno por línea.

#### Variables disponibles

Online:

```text
{port}
{time}
{raw}
```

Connect:

```text
{player}
{guid}
{level}
{character}
{time}
{raw}
```

Disconnect:

```text
{player}
{guid}
{reason}
{time}
{raw}
```

Chat:

```text
{player}
{message}
{time}
{raw}
```

#### Ejemplos de mensajes

Servidor online:

```text
🟢 Servidor online en el puerto {port}.
```

Jugador conectado:

```text
✅ **{player}** ha entrado al servidor. Nivel: {level} | Personaje: {character}
```

Jugador desconectado:

```text
❌ **{player}** ha salido del servidor. Razón: {reason}
```

Chat del juego:

```text
**{player}:** {message}
```

---

### Usuarios

Permite administrar los usuarios guardados en la base SQLite `.db.ocala`.

La tabla oficial usada por el servidor es:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    operator BOOLEAN DEFAULT 0,
    remember_me BOOLEAN DEFAULT 0,
    last_ip_address TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL
);
```

Funciones disponibles:

- conectar base de datos
- refrescar usuarios
- crear usuario
- resetear contraseña
- cambiar `operator`
- cambiar `remember_me`
- eliminar usuario
- exportar usuarios a CSV

> Nota: el servidor oficial guarda `password_hash`, no contraseña en texto plano. El panel genera SHA256 compatible con el comando `/login`.

---

### SQLite

Permite revisar la base de datos y su estructura.

Funciones:

- cargar esquema SQLite
- ver tablas existentes
- revisar columnas
- ejecutar `integrity_check`
- crear/verificar tabla oficial `users`

---

### Server.yaml

Editor visual para el archivo de configuración del servidor.

Permite modificar:

- `serverName`
- `hostname`
- `password`
- `port`
- `maxPlayers`
- `masterServer`
- `masterServerAuthorisation`
- `broadcastServer`
- `gameMode`
- `allowInGameTextChat`
- `useChatFilter`
- `updateInterval`
- `updateIntervalLowBandwidth`
- `enableMods`
- `serverModificationPaths`
- `clientModificationPaths`
- `requiredModNames`
- `bannedModNames`
- `requiredModsSHA256`
- `bannedModsSHA256`
- `modPermissions.webRequests`
- `nonSyncedGameBehaviours`

Al guardar, el panel puede crear una copia de seguridad:

```text
Server.yaml.bak
```

---

### Config

Permite configurar rutas importantes del proyecto:

- ejecutable del servidor
- carpeta de trabajo
- argumentos de inicio
- ruta de `Server.yaml`
- carpeta del mod
- ruta de `.db.ocala`
- tabla de usuarios

---

### Comandos

Pestaña de comandos rápidos para enviar órdenes al servidor.

Ejemplos:

```text
exit
help
status
players
countdown
```

También incluye campo para escribir comandos personalizados.

---

## 🤖 Integración Discord por Webhook

El panel analiza los logs del servidor y detecta patrones como:

### Servidor online

```text
[RakNet] Server started on port 7777
```

Mensaje enviado:

```text
🟢 Servidor online en el puerto 7777.
```

### Jugador conectado

```text
[RakNet::GameStart] 193655237974965221 (azzlaer#5261) is starting the game on level 0 with character 1
```

Mensaje enviado:

```text
✅ azzlaer#5261 ha entrado al servidor.
```

### Jugador desconectado

```text
[RakNet] Client azzlaer#5261 removed with GUID 193655237974965221.
```

Mensaje enviado:

```text
❌ azzlaer#5261 ha salido del servidor.
```

### Chat del juego

```text
[Received Chat Message] azzlaer#2707: muy bueno
```

Mensaje enviado:

```text
azzlaer#2707: muy bueno
```

---

## 🔐 Seguridad

Recomendaciones:

- No publiques tu `config.ini` si contiene webhooks privados.
- No subas tus URLs de Discord Webhook a GitHub.
- No edites `.db.ocala` mientras el servidor está escribiendo intensamente.
- Haz backup antes de modificar usuarios.
- Usa `run_panel_admin.bat` si Windows bloquea permisos de archivos.

---

## 🧪 Compilar a EXE

Opcionalmente puedes compilar el panel con PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name SHAR_MP_Admin_Panel main.py
```

El ejecutable quedará en:

```text
dist\SHAR_MP_Admin_Panel.exe
```

Copia `config.ini` junto al `.exe`.

---

## 🛠️ Posibles mejoras futuras

- Sistema de economía virtual con monedas.
- Pestaña de `LatinCoins`.
- Ranking de usuarios.
- Web panel PHP remoto.
- Backups automáticos de `.db.ocala`.
- Programador de reinicios.
- Alertas programadas por Discord.
- Sistema de whitelist.
- Sistema de sanciones.
- Bridge Discord ↔ chat del juego.
- Estadísticas de jugadores.
- Logs filtrados por evento.

---

## 📜 Créditos

Proyecto desarrollado por:

```text
Azzlaer + ChatGPT (OpenAI)
```

Para:

```text
LatinBattle.com
```

Servidor objetivo:

```text
The Simpsons: Hit & Run Multiplayer Server
```

Comunidad y modding:

```text
Donut Team / SHAR MP
```

---

## ⚠️ Aviso

Este proyecto es una herramienta comunitaria de administración y personalización.  
No forma parte oficial de Donut Team ni de los desarrolladores originales del juego.

Úsalo bajo tu propia responsabilidad y siempre conserva copias de seguridad de tus archivos importantes.
