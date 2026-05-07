# ============================================================
# SHAR MP Admin Panel v4.1 - Compact Professional UI
# The Simpsons: Hit & Run Multiplayer Server
#
# Autor: Azzlaer + ChatGPT
# Comunidad: LatinBattle.com
#
# Características:
# - GUI más compacta y profesional
# - Scrollbars en pestañas largas
# - Bot Discord por webhooks
# - Consola en tiempo real
# - Usuarios SQLite .db.ocala
# - Editor Server.yaml
# - Sin librerías externas
# ============================================================

import os
import re
import sys
import csv
import time
import json
import queue
import sqlite3
import hashlib
import threading
import subprocess
import configparser
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "SHAR MP Admin Panel"
CONFIG_FILE = "config.ini"


# ============================================================
# Helpers
# ============================================================

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def bool_to_int(value):
    return 1 if bool(value) else 0


def int_to_bool(value):
    try:
        return int(value) == 1
    except Exception:
        return False


def split_webhooks(value):
    if not value:
        return []

    raw = str(value).replace(",", "\n").replace(";", "\n").replace("|", "\n")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def safe_template(template, values):
    try:
        return template.format(**values)
    except Exception:
        return template


def now_local_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def bool_to_yaml(value):
    return "true" if bool(value) else "false"


def yaml_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "si", "on")


def parse_scalar(value):
    value = value.strip()

    if value == "''" or value == '""':
        return ""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    try:
        return int(value)
    except Exception:
        return value


def simple_yaml_load(path):
    data = {}
    current_parent = None

    if not os.path.exists(path):
        return data

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for raw in lines:
        line = raw.rstrip("\n\r")

        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith("  ") and current_parent:
            child_line = line.strip()

            if child_line.startswith("- "):
                item = child_line[2:].strip()
                if not isinstance(data.get(current_parent), list):
                    data[current_parent] = []
                data[current_parent].append(parse_scalar(item))
                continue

            if ":" not in child_line:
                continue

            k, v = child_line.split(":", 1)
            if not isinstance(data.get(current_parent), dict):
                data[current_parent] = {}

            data[current_parent][k.strip()] = parse_scalar(v.strip())
            continue

        current_parent = None

        if ":" not in line:
            continue

        k, v = line.split(":", 1)
        key = k.strip()
        value = v.strip()

        if value == "":
            data[key] = {}
            current_parent = key
        else:
            data[key] = parse_scalar(value)

    return data


def yaml_quote(value):
    value = "" if value is None else str(value)

    if value == "":
        return "''"

    if any(ch in value for ch in [":", "#", "{", "}", "[", "]", "'", '"']) or value.strip() != value:
        value = value.replace("'", "''")
        return "'" + value + "'"

    return value


def simple_yaml_save(path, data):
    ordered_keys = [
        "serverName",
        "hostname",
        "password",
        "port",
        "maxPlayers",
        "masterServer",
        "masterServerAuthorisation",
        "broadcastServer",
        "gameMode",
        "rules",
        "allowInGameTextChat",
        "useChatFilter",
        "updateInterval",
        "updateIntervalLowBandwidth",
        "enableMods",
        "serverModificationPaths",
        "clientModificationPaths",
        "requiredModNames",
        "bannedModNames",
        "requiredModsSHA256",
        "bannedModsSHA256",
        "modPermissions",
        "nonSyncedGameBehaviours",
    ]

    lines = []

    for key in ordered_keys:
        value = data.get(key)

        if isinstance(value, bool):
            lines.append(f"{key}: {bool_to_yaml(value)}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            if len(value) == 0:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {yaml_quote(item)}")
        elif isinstance(value, dict):
            if len(value) == 0:
                lines.append(f"{key}: {{}}")
            else:
                lines.append(f"{key}:")
                for child_key, child_value in value.items():
                    if isinstance(child_value, bool):
                        lines.append(f"  {child_key}: {bool_to_yaml(child_value)}")
                    elif isinstance(child_value, int):
                        lines.append(f"  {child_key}: {child_value}")
                    else:
                        lines.append(f"  {child_key}: {yaml_quote(child_value)}")
        else:
            lines.append(f"{key}: {yaml_quote(value)}")

    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# ============================================================
# Config
# ============================================================

class PanelConfig:
    def __init__(self):
        self.path = os.path.join(app_dir(), CONFIG_FILE)
        self.config = configparser.ConfigParser()
        self.load()

    def create_default(self):
        self.config["SERVER"] = {
            "exe_path": r"D:\Juegos\Vivendi Universal Games\Server\SHARMPServer.exe",
            "working_dir": r"D:\Juegos\Vivendi Universal Games\Server",
            "startup_args": "",
            "auto_scroll": "true",
            "send_exit_on_stop": "true",
            "kill_after_seconds": "5",
            "server_yaml_path": r"D:\Juegos\Vivendi Universal Games\Server\Server.yaml",
        }

        self.config["DATABASE"] = {
            "sqlite_path": r"D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer\.db.ocala",
            "mod_folder": r"D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer",
            "users_table": "users",
            "auto_connect": "true",
        }

        self.config["DISCORD"] = {
            "enabled": "false",
            "username": "SHAR MP Bot",
            "avatar_url": "",
            "status_webhooks": "",
            "connect_webhooks": "",
            "disconnect_webhooks": "",
            "chat_webhooks": "",
            "send_online": "true",
            "send_connect": "true",
            "send_disconnect": "true",
            "send_chat": "true",
            "message_online": "🟢 Servidor online en el puerto {port}.",
            "message_connect": "✅ **{player}** ha entrado al servidor. Nivel: {level} | Personaje: {character}",
            "message_disconnect": "❌ **{player}** ha salido del servidor. Razón: {reason}",
            "message_chat": "**{player}:** {message}",
            "log_discord_to_console": "true",
        }

        self.config["UI"] = {
            "console_max_lines": "2500",
        }

        self.save()

    def load(self):
        if not os.path.exists(self.path):
            self.create_default()

        self.config.read(self.path, encoding="utf-8")

        defaults = {
            "SERVER": {
                "exe_path": r"D:\Juegos\Vivendi Universal Games\Server\SHARMPServer.exe",
                "working_dir": r"D:\Juegos\Vivendi Universal Games\Server",
                "startup_args": "",
                "auto_scroll": "true",
                "send_exit_on_stop": "true",
                "kill_after_seconds": "5",
                "server_yaml_path": r"D:\Juegos\Vivendi Universal Games\Server\Server.yaml",
            },
            "DATABASE": {
                "sqlite_path": r"D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer\.db.ocala",
                "mod_folder": r"D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer",
                "users_table": "users",
                "auto_connect": "true",
            },
            "DISCORD": {
                "enabled": "false",
                "username": "SHAR MP Bot",
                "avatar_url": "",
                "status_webhooks": "",
                "connect_webhooks": "",
                "disconnect_webhooks": "",
                "chat_webhooks": "",
                "send_online": "true",
                "send_connect": "true",
                "send_disconnect": "true",
                "send_chat": "true",
                "message_online": "🟢 Servidor online en el puerto {port}.",
                "message_connect": "✅ **{player}** ha entrado al servidor. Nivel: {level} | Personaje: {character}",
                "message_disconnect": "❌ **{player}** ha salido del servidor. Razón: {reason}",
                "message_chat": "**{player}:** {message}",
                "log_discord_to_console": "true",
            },
            "UI": {
                "console_max_lines": "2500",
            },
        }

        changed = False

        for section, pairs in defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
                changed = True

            for key, value in pairs.items():
                if not self.config.has_option(section, key):
                    self.config.set(section, key, value)
                    changed = True

        if changed:
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            self.config.write(f)

    def get(self, section, key, fallback=""):
        return self.config.get(section, key, fallback=fallback)

    def get_bool(self, section, key, fallback=False):
        return self.config.getboolean(section, key, fallback=fallback)

    def get_int(self, section, key, fallback=0):
        return self.config.getint(section, key, fallback=fallback)

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, str(value))


# ============================================================
# Scrollable Frame
# ============================================================

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, bg="#0F172A"):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas)

        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_content_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)

    def _on_mousewheel(self, event):
        try:
            focused = self.focus_get()
            if focused and str(focused).startswith(str(self)):
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass


# ============================================================
# Discord Bot
# ============================================================

class DiscordWebhookBot:
    def __init__(self, log_callback=None):
        self.enabled = False
        self.username = "SHAR MP Bot"
        self.avatar_url = ""

        self.status_webhooks = []
        self.connect_webhooks = []
        self.disconnect_webhooks = []
        self.chat_webhooks = []

        self.send_online = True
        self.send_connect = True
        self.send_disconnect = True
        self.send_chat = True
        self.log_discord_to_console = True

        self.message_online = "🟢 Servidor online en el puerto {port}."
        self.message_connect = "✅ **{player}** ha entrado al servidor. Nivel: {level} | Personaje: {character}"
        self.message_disconnect = "❌ **{player}** ha salido del servidor. Razón: {reason}"
        self.message_chat = "**{player}:** {message}"

        self.log_callback = log_callback

        self.guid_to_player = {}
        self.player_to_guid = {}
        self.sent_connect_guids = set()
        self.sent_disconnect_guids = set()

        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

        self.re_online = re.compile(r"\[RakNet\]\s+Server started on port\s+(\d+)", re.IGNORECASE)
        self.re_join_name = re.compile(r"\[RakNet::Join\]\s+Name=([^,\s]+),", re.IGNORECASE)
        self.re_gamestart = re.compile(
            r"\[RakNet::GameStart\]\s+(\d+)\s+\(([^)]+)\)\s+is starting the game on level\s+(\d+)\s+with character\s+(\d+)",
            re.IGNORECASE,
        )
        self.re_session_join = re.compile(r"\[Session\]\s+\[Client Joined\]\s+(\d+)\s+to session on level\s+(\d+)", re.IGNORECASE)
        self.re_removed = re.compile(r"\[RakNet\]\s+Client\s+(.+?)\s+removed with GUID\s+(\d+)\.", re.IGNORECASE)
        self.re_disconnected = re.compile(r"\[Client\]\s+\[Client Disconnected\]\s+(\d+)\s+\((.*?)\)", re.IGNORECASE)
        self.re_chat = re.compile(r"\[Received Chat Message\]\s+([^:]+):\s*(.*)$", re.IGNORECASE)

    def log(self, text):
        if self.log_discord_to_console and self.log_callback:
            self.log_callback(text)

    def configure(
        self,
        enabled=False,
        username="SHAR MP Bot",
        avatar_url="",
        status_webhooks=None,
        connect_webhooks=None,
        disconnect_webhooks=None,
        chat_webhooks=None,
        send_online=True,
        send_connect=True,
        send_disconnect=True,
        send_chat=True,
        message_online="",
        message_connect="",
        message_disconnect="",
        message_chat="",
        log_discord_to_console=True,
    ):
        self.enabled = bool(enabled)
        self.username = username or "SHAR MP Bot"
        self.avatar_url = avatar_url or ""

        self.status_webhooks = status_webhooks or []
        self.connect_webhooks = connect_webhooks or []
        self.disconnect_webhooks = disconnect_webhooks or []
        self.chat_webhooks = chat_webhooks or []

        self.send_online = bool(send_online)
        self.send_connect = bool(send_connect)
        self.send_disconnect = bool(send_disconnect)
        self.send_chat = bool(send_chat)
        self.log_discord_to_console = bool(log_discord_to_console)

        if message_online:
            self.message_online = message_online
        if message_connect:
            self.message_connect = message_connect
        if message_disconnect:
            self.message_disconnect = message_disconnect
        if message_chat:
            self.message_chat = message_chat

    def reset_runtime_state(self):
        self.guid_to_player.clear()
        self.player_to_guid.clear()
        self.sent_connect_guids.clear()
        self.sent_disconnect_guids.clear()

    def process_log_line(self, line):
        if not line:
            return

        clean = line.strip()
        if not clean:
            return

        m = self.re_online.search(clean)
        if m:
            self.emit_online(port=m.group(1), raw=clean)
            return

        m = self.re_join_name.search(clean)
        if m:
            player = m.group(1)
            self.player_to_guid.setdefault(player, "")
            return

        m = self.re_gamestart.search(clean)
        if m:
            guid = m.group(1)
            player = m.group(2)
            level = m.group(3)
            character = m.group(4)

            self.guid_to_player[guid] = player
            self.player_to_guid[player] = guid

            if guid not in self.sent_connect_guids:
                self.sent_connect_guids.add(guid)
                self.emit_connect(player=player, guid=guid, level=level, character=character, raw=clean)
            return

        m = self.re_session_join.search(clean)
        if m:
            guid = m.group(1)
            level = m.group(2)
            player = self.guid_to_player.get(guid, f"GUID {guid}")

            if guid not in self.sent_connect_guids and not player.startswith("GUID "):
                self.sent_connect_guids.add(guid)
                self.emit_connect(player=player, guid=guid, level=level, character="?", raw=clean)
            return

        m = self.re_removed.search(clean)
        if m:
            player = m.group(1).strip()
            guid = m.group(2).strip()
            self.guid_to_player[guid] = player

            if guid not in self.sent_disconnect_guids:
                self.sent_disconnect_guids.add(guid)
                self.emit_disconnect(player=player, guid=guid, reason="Client removed", raw=clean)
            return

        m = self.re_disconnected.search(clean)
        if m:
            guid = m.group(1).strip()
            reason = m.group(2).strip() or "No message given"
            player = self.guid_to_player.get(guid, f"GUID {guid}")

            if guid not in self.sent_disconnect_guids:
                self.sent_disconnect_guids.add(guid)
                self.emit_disconnect(player=player, guid=guid, reason=reason, raw=clean)
            return

        m = self.re_chat.search(clean)
        if m:
            player = m.group(1).strip()
            message = m.group(2).strip()
            self.emit_chat(player=player, message=message, raw=clean)
            return

    def emit_online(self, port, raw=""):
        if not self.enabled or not self.send_online:
            return

        values = {"port": port, "time": now_local_text(), "raw": raw}
        content = safe_template(self.message_online, values)
        self.enqueue(self.status_webhooks, content, event="online")

    def emit_connect(self, player, guid, level="?", character="?", raw=""):
        if not self.enabled or not self.send_connect:
            return

        values = {
            "player": player,
            "guid": guid,
            "level": level,
            "character": character,
            "time": now_local_text(),
            "raw": raw,
        }
        content = safe_template(self.message_connect, values)
        self.enqueue(self.connect_webhooks, content, event="connect")

    def emit_disconnect(self, player, guid, reason="No message given", raw=""):
        if not self.enabled or not self.send_disconnect:
            return

        values = {
            "player": player,
            "guid": guid,
            "reason": reason,
            "time": now_local_text(),
            "raw": raw,
        }
        content = safe_template(self.message_disconnect, values)
        self.enqueue(self.disconnect_webhooks, content, event="disconnect")

    def emit_chat(self, player, message, raw=""):
        if not self.enabled or not self.send_chat:
            return

        values = {"player": player, "message": message, "time": now_local_text(), "raw": raw}
        content = safe_template(self.message_chat, values)
        self.enqueue(self.chat_webhooks, content, event="chat")

    def enqueue(self, webhooks, content, event="generic"):
        urls = [u for u in webhooks if u.strip()]

        if not urls:
            self.log(f"[DISCORD] Sin webhook configurado para evento: {event}\n")
            return

        for url in urls:
            self.queue.put((url, content, event))

    def _worker_loop(self):
        while True:
            try:
                url, content, event = self.queue.get()
                self._send_webhook(url, content, event)
            except Exception as e:
                self.log(f"[DISCORD ERROR] Worker: {e}\n")
            finally:
                try:
                    self.queue.task_done()
                except Exception:
                    pass

    def _send_webhook(self, url, content, event):
        payload = {"content": content, "username": self.username}

        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "SHAR-MP-Admin-Panel-v4.1"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status

            if 200 <= status < 300:
                self.log(f"[DISCORD] Enviado evento '{event}'.\n")
            else:
                self.log(f"[DISCORD ERROR] HTTP {status} en evento '{event}'.\n")

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            self.log(f"[DISCORD ERROR] HTTP {e.code} evento '{event}': {body}\n")

        except Exception as e:
            self.log(f"[DISCORD ERROR] No se pudo enviar evento '{event}': {e}\n")


# ============================================================
# Server Process
# ============================================================

class ServerProcess:
    def __init__(self, log_callback, stopped_callback):
        self.proc = None
        self.thread = None
        self.log_callback = log_callback
        self.stopped_callback = stopped_callback

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, exe_path, working_dir, args=""):
        if self.is_running():
            raise RuntimeError("El servidor ya está iniciado.")

        if not exe_path or not os.path.exists(exe_path):
            raise FileNotFoundError(f"No existe el ejecutable: {exe_path}")

        if not working_dir or not os.path.isdir(working_dir):
            working_dir = os.path.dirname(exe_path)

        cmd = [exe_path]

        if args.strip():
            cmd.extend(args.strip().split())

        creation_flags = 0

        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )

        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        self.log_callback("[PANEL] Servidor iniciado.\n")

    def _reader_loop(self):
        try:
            while self.proc and self.proc.poll() is None:
                line = self.proc.stdout.readline()

                if line:
                    self.log_callback(line)
                else:
                    time.sleep(0.05)

            if self.proc:
                remaining = self.proc.stdout.read()
                if remaining:
                    self.log_callback(remaining)

            code = self.proc.poll() if self.proc else None
            self.log_callback(f"\n[PANEL] Servidor finalizado. Código: {code}\n")
            self.stopped_callback()

        except Exception as e:
            self.log_callback(f"\n[PANEL ERROR] Error leyendo consola: {e}\n")
            self.stopped_callback()

    def send_command(self, command):
        if not self.is_running():
            raise RuntimeError("El servidor no está iniciado.")

        if not command.endswith("\n"):
            command += "\n"

        self.proc.stdin.write(command)
        self.proc.stdin.flush()

    def stop(self, send_exit=True, kill_after_seconds=5):
        if not self.is_running():
            return

        if send_exit:
            try:
                self.send_command("exit")
            except Exception:
                pass

            start = time.time()

            while time.time() - start < kill_after_seconds:
                if not self.is_running():
                    return
                time.sleep(0.2)

        try:
            self.proc.terminate()
        except Exception:
            pass

        start = time.time()

        while time.time() - start < 3:
            if not self.is_running():
                return
            time.sleep(0.2)

        try:
            self.proc.kill()
        except Exception:
            pass


# ============================================================
# Database
# ============================================================

class DatabaseManager:
    def __init__(self):
        self.path = ""

    def set_path(self, path):
        self.path = path

    def exists(self):
        return bool(self.path) and os.path.exists(self.path)

    def connect(self):
        if not self.exists():
            raise FileNotFoundError(f"No existe la base SQLite: {self.path}")

        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def test(self):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            return cur.fetchone()[0]
        finally:
            conn.close()

    def ensure_users_table(self):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
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
            """)
            conn.commit()
        finally:
            conn.close()

    def get_users(self):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password_hash, operator, remember_me,
                       last_ip_address, created_at, last_login
                FROM users
                ORDER BY id DESC;
            """)
            return cur.fetchall()
        finally:
            conn.close()

    def create_user(self, username, password, operator=False, remember_me=False, last_ip_address=None):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (username, password_hash, operator, remember_me, last_ip_address)
                VALUES (?, ?, ?, ?, ?);
            """, (
                username,
                sha256_text(password),
                bool_to_int(operator),
                bool_to_int(remember_me),
                last_ip_address,
            ))
            conn.commit()
        finally:
            conn.close()

    def update_flags(self, user_id, operator, remember_me):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users
                SET operator = ?, remember_me = ?
                WHERE id = ?;
            """, (
                bool_to_int(operator),
                bool_to_int(remember_me),
                user_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def reset_password(self, user_id, new_password):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users
                SET password_hash = ?
                WHERE id = ?;
            """, (
                sha256_text(new_password),
                user_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def delete_user(self, user_id):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = ?;", (user_id,))
            conn.commit()
        finally:
            conn.close()

    def get_tables(self):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            return [r["name"] for r in cur.fetchall()]
        finally:
            conn.close()


# ============================================================
# Dialogs
# ============================================================

class UserEditor(tk.Toplevel):
    def __init__(self, master, title, mode="create", user=None, on_save=None):
        super().__init__(master)
        self.title(title)
        self.geometry("420x330")
        self.resizable(False, False)
        self.configure(bg="#0F172A")

        self.mode = mode
        self.user = user or {}
        self.on_save = on_save

        self.username_var = tk.StringVar(value=str(self.user.get("username", "")))
        self.password_var = tk.StringVar()
        self.ip_var = tk.StringVar(value=str(self.user.get("last_ip_address", "") or ""))
        self.operator_var = tk.BooleanVar(value=int_to_bool(self.user.get("operator", 0)))
        self.remember_var = tk.BooleanVar(value=int_to_bool(self.user.get("remember_me", 0)))

        self.build()

    def build(self):
        frame = ttk.Frame(self, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(frame, text="Usuario").pack(anchor="w")
        username_entry = ttk.Entry(frame, textvariable=self.username_var)
        username_entry.pack(fill="x", pady=(3, 10))

        if self.mode == "reset":
            username_entry.configure(state="disabled")
            ttk.Label(frame, text="Nueva contraseña").pack(anchor="w")
        else:
            ttk.Label(frame, text="Contraseña").pack(anchor="w")

        ttk.Entry(frame, textvariable=self.password_var, show="*").pack(fill="x", pady=(3, 10))

        if self.mode == "create":
            ttk.Label(frame, text="IP inicial opcional").pack(anchor="w")
            ttk.Entry(frame, textvariable=self.ip_var).pack(fill="x", pady=(3, 10))

        ttk.Checkbutton(frame, text="Operator / OP", variable=self.operator_var).pack(anchor="w", pady=3)
        ttk.Checkbutton(frame, text="Remember Me", variable=self.remember_var).pack(anchor="w", pady=3)

        ttk.Label(
            frame,
            text="Se guardará como SHA256 compatible con /login.",
            style="Muted.TLabel",
            wraplength=380,
        ).pack(anchor="w", pady=(10, 8))

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.pack(fill="x", side="bottom", pady=(10, 0))

        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Guardar", command=self.save).pack(side="right")

    def save(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        ip = self.ip_var.get().strip()
        operator = self.operator_var.get()
        remember = self.remember_var.get()

        if self.mode == "create" and not username:
            messagebox.showwarning("Usuario", "Debes ingresar un username.")
            return

        if not password:
            messagebox.showwarning("Contraseña", "Debes ingresar una contraseña.")
            return

        if self.on_save:
            self.on_save(username, password, ip, operator, remember)

        self.destroy()


# ============================================================
# Main App
# ============================================================

class SHARPanel(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1080, 680)

        self.cfg = PanelConfig()
        self.log_queue = queue.Queue()
        self.server = ServerProcess(self.enqueue_log, self.on_server_stopped)
        self.db = DatabaseManager()
        self.discord_bot = DiscordWebhookBot(log_callback=self.enqueue_log)

        self.console_line_count = 0
        self.users_all = []

        self.status_var = tk.StringVar(value="OFFLINE")
        self.db_status_var = tk.StringVar(value="DB: sin conectar")
        self.discord_status_var = tk.StringVar(value="Discord: desactivado")
        self.schema_status_var = tk.StringVar(value="Schema: sin cargar")
        self.yaml_status_var = tk.StringVar(value="Server.yaml: sin cargar")
        self.command_var = tk.StringVar()
        self.search_user_var = tk.StringVar()

        self.exe_var = tk.StringVar(value=self.cfg.get("SERVER", "exe_path"))
        self.workdir_var = tk.StringVar(value=self.cfg.get("SERVER", "working_dir"))
        self.args_var = tk.StringVar(value=self.cfg.get("SERVER", "startup_args"))
        self.yaml_path_var = tk.StringVar(value=self.cfg.get("SERVER", "server_yaml_path"))
        self.sqlite_var = tk.StringVar(value=self.cfg.get("DATABASE", "sqlite_path"))
        self.mod_folder_var = tk.StringVar(value=self.cfg.get("DATABASE", "mod_folder"))
        self.table_var = tk.StringVar(value=self.cfg.get("DATABASE", "users_table", "users"))
        self.autoscroll_var = tk.BooleanVar(value=self.cfg.get_bool("SERVER", "auto_scroll", True))

        self.user_count_var = tk.StringVar(value="0")
        self.op_count_var = tk.StringVar(value="0")
        self.login_count_var = tk.StringVar(value="0")
        self.db_file_var = tk.StringVar(value="-")

        self.discord_enabled_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "enabled", False))
        self.discord_username_var = tk.StringVar(value=self.cfg.get("DISCORD", "username", "SHAR MP Bot"))
        self.discord_avatar_var = tk.StringVar(value=self.cfg.get("DISCORD", "avatar_url", ""))

        self.send_online_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "send_online", True))
        self.send_connect_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "send_connect", True))
        self.send_disconnect_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "send_disconnect", True))
        self.send_chat_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "send_chat", True))
        self.discord_log_console_var = tk.BooleanVar(value=self.cfg.get_bool("DISCORD", "log_discord_to_console", True))

        self.message_online_var = tk.StringVar(value=self.cfg.get("DISCORD", "message_online"))
        self.message_connect_var = tk.StringVar(value=self.cfg.get("DISCORD", "message_connect"))
        self.message_disconnect_var = tk.StringVar(value=self.cfg.get("DISCORD", "message_disconnect"))
        self.message_chat_var = tk.StringVar(value=self.cfg.get("DISCORD", "message_chat"))

        self.yaml_vars = {
            "serverName": tk.StringVar(value="LatinBattle.com"),
            "hostname": tk.StringVar(value="LatinBattle.com"),
            "password": tk.StringVar(value=""),
            "port": tk.StringVar(value="7777"),
            "maxPlayers": tk.StringVar(value="32"),
            "masterServer": tk.StringVar(value="https://launcher.donutteam.com"),
            "masterServerAuthorisation": tk.StringVar(value=""),
            "gameMode": tk.StringVar(value="Free roam"),
            "updateInterval": tk.StringVar(value="60"),
            "updateIntervalLowBandwidth": tk.StringVar(value="400"),
        }

        self.yaml_bools = {
            "broadcastServer": tk.BooleanVar(value=True),
            "allowInGameTextChat": tk.BooleanVar(value=True),
            "useChatFilter": tk.BooleanVar(value=True),
            "enableMods": tk.BooleanVar(value=True),
            "webRequests": tk.BooleanVar(value=False),
            "pedestrians": tk.BooleanVar(value=True),
            "traffic": tk.BooleanVar(value=True),
            "missions": tk.BooleanVar(value=True),
            "police": tk.BooleanVar(value=True),
        }

        self.configure_style()
        self.build_ui()

        self.db.set_path(self.sqlite_var.get().strip())
        self.apply_discord_config(save=False)

        self.after(100, self.process_log_queue)
        self.after(1000, self.refresh_status_loop)

        if self.cfg.get_bool("DATABASE", "auto_connect", True):
            self.after(500, self.auto_db_bootstrap)

    # ========================================================
    # Style
    # ========================================================

    def configure_style(self):
        self.configure(bg="#0F172A")

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", font=("Segoe UI", 9))
        style.configure("TFrame", background="#0F172A")
        style.configure("Panel.TFrame", background="#111827")
        style.configure("Card.TFrame", background="#111827", relief="flat")
        style.configure("TLabel", background="#0F172A", foreground="#E5E7EB")
        style.configure("Panel.TLabel", background="#111827", foreground="#E5E7EB")
        style.configure("Muted.TLabel", background="#0F172A", foreground="#94A3B8")
        style.configure("PanelMuted.TLabel", background="#111827", foreground="#94A3B8")
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), foreground="#F8FAFC", background="#0F172A")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#94A3B8", background="#0F172A")
        style.configure("CardNumber.TLabel", font=("Segoe UI", 16, "bold"), foreground="#F8FAFC", background="#111827")
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"), foreground="#F8FAFC", background="#0F172A")
        style.configure("PanelSection.TLabel", font=("Segoe UI", 10, "bold"), foreground="#F8FAFC", background="#111827")
        style.configure("TButton", padding=(8, 5))
        style.configure("TCheckbutton", background="#0F172A", foreground="#E5E7EB")
        style.configure("Panel.TCheckbutton", background="#111827", foreground="#E5E7EB")
        style.configure("TNotebook", background="#0F172A", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(11, 6), font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", background="#111827", foreground="#E5E7EB", fieldbackground="#111827", rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#1E293B", foreground="#F8FAFC")

    # ========================================================
    # Layout
    # ========================================================

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=14, pady=(10, 6))

        left = ttk.Frame(header)
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(left, text="SHAR MP Admin Panel", style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, text="Consola, SQLite .db.ocala, Server.yaml y webhooks Discord.", style="Sub.TLabel").pack(anchor="w")

        right = ttk.Frame(header)
        right.pack(side="right")

        self.status_badge = tk.Label(
            right,
            textvariable=self.status_var,
            bg="#7F1D1D",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=5,
        )
        self.status_badge.pack(side="right")

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=14, pady=(0, 8))

        ttk.Button(controls, text="▶ Iniciar", command=self.start_server).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="■ Detener", command=self.stop_server).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="↻ Reiniciar", command=self.restart_server).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Detectar DB", command=self.detect_ocala_db).pack(side="left", padx=(6, 6))
        ttk.Button(controls, text="Guardar config", command=self.save_config).pack(side="right")

        cards = ttk.Frame(self)
        cards.pack(fill="x", padx=14, pady=(0, 8))

        self.card(cards, "Usuarios", self.user_count_var, 0)
        self.card(cards, "OP", self.op_count_var, 1)
        self.card(cards, "Logins", self.login_count_var, 2)
        self.card(cards, "DB", self.db_file_var, 3, wide=True)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.tab_console = ttk.Frame(self.notebook)
        self.tab_discord = ttk.Frame(self.notebook)
        self.tab_users = ttk.Frame(self.notebook)
        self.tab_schema = ttk.Frame(self.notebook)
        self.tab_yaml = ttk.Frame(self.notebook)
        self.tab_config = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_console, text="Consola")
        self.notebook.add(self.tab_discord, text="Discord")
        self.notebook.add(self.tab_users, text="Usuarios")
        self.notebook.add(self.tab_schema, text="SQLite")
        self.notebook.add(self.tab_yaml, text="Server.yaml")
        self.notebook.add(self.tab_config, text="Config")
        self.notebook.add(self.tab_tools, text="Comandos")

        self.build_console_tab()
        self.build_discord_tab()
        self.build_users_tab()
        self.build_schema_tab()
        self.build_yaml_tab()
        self.build_config_tab()
        self.build_tools_tab()

    def card(self, parent, title, var, col, wide=False):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=col, sticky="ew", padx=(0, 8), ipadx=8, ipady=5)
        parent.columnconfigure(col, weight=2 if wide else 1)

        ttk.Label(frame, text=title, style="PanelMuted.TLabel").pack(anchor="w", padx=10, pady=(7, 0))
        ttk.Label(frame, textvariable=var, style="CardNumber.TLabel").pack(anchor="w", padx=10, pady=(0, 7))

    def make_panel(self, parent, title=None):
        box = ttk.Frame(parent, style="Panel.TFrame")
        box.pack(fill="x", padx=0, pady=(0, 8))

        if title:
            title_frame = ttk.Frame(box, style="Panel.TFrame")
            title_frame.pack(fill="x", padx=12, pady=(10, 0))
            ttk.Label(title_frame, text=title, style="PanelSection.TLabel").pack(anchor="w")

        inner = ttk.Frame(box, style="Panel.TFrame")
        inner.pack(fill="x", padx=12, pady=(8 if title else 10, 10))

        return inner

    # ========================================================
    # Console tab
    # ========================================================

    def build_console_tab(self):
        frame = ttk.Frame(self.tab_console)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.console = tk.Text(
            frame,
            bg="#020617",
            fg="#D1D5DB",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
            wrap="word",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.console.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(frame, command=self.console.yview)
        scroll.pack(fill="y", side="right")
        self.console.configure(yscrollcommand=scroll.set)

        bottom = ttk.Frame(self.tab_console)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Comando").pack(side="left", padx=(0, 6))
        entry = ttk.Entry(bottom, textvariable=self.command_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.send_console_command())

        ttk.Button(bottom, text="Enviar", command=self.send_console_command).pack(side="left", padx=(6, 0))
        ttk.Button(bottom, text="Limpiar", command=self.clear_console).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(bottom, text="Auto-scroll", variable=self.autoscroll_var).pack(side="left", padx=(8, 0))

    # ========================================================
    # Discord tab
    # ========================================================

    def build_discord_tab(self):
        sf = ScrollableFrame(self.tab_discord)
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        root = sf.content

        top = self.make_panel(root, "Estado del bot")

        ttk.Checkbutton(top, text="Activar bot Discord por Webhook", variable=self.discord_enabled_var, style="Panel.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=3)
        ttk.Checkbutton(top, text="Log en consola", variable=self.discord_log_console_var, style="Panel.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 12), pady=3)
        ttk.Label(top, textvariable=self.discord_status_var, style="PanelMuted.TLabel").grid(row=0, column=2, sticky="e", pady=3)
        top.columnconfigure(2, weight=1)

        btns = ttk.Frame(top, style="Panel.TFrame")
        btns.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="Aplicar", command=lambda: self.apply_discord_config(save=True)).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Enviar prueba", command=self.send_discord_test).pack(side="left", padx=(0, 6))

        identity = self.make_panel(root, "Identidad")
        self.form_row(identity, 0, "Nombre Bot", self.discord_username_var)
        self.form_row(identity, 1, "Avatar URL", self.discord_avatar_var)

        events = self.make_panel(root, "Eventos")
        ttk.Checkbutton(events, text="Servidor Online", variable=self.send_online_var, style="Panel.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=3)
        ttk.Checkbutton(events, text="Connect", variable=self.send_connect_var, style="Panel.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 12), pady=3)
        ttk.Checkbutton(events, text="Disconnect", variable=self.send_disconnect_var, style="Panel.TCheckbutton").grid(row=0, column=2, sticky="w", padx=(0, 12), pady=3)
        ttk.Checkbutton(events, text="Chat", variable=self.send_chat_var, style="Panel.TCheckbutton").grid(row=0, column=3, sticky="w", padx=(0, 12), pady=3)

        webhooks = self.make_panel(root, "Webhooks por evento")
        grid = ttk.Frame(webhooks, style="Panel.TFrame")
        grid.pack(fill="x")

        self.webhook_status_text = self.discord_text_block(grid, 0, 0, "Server Online", self.cfg.get("DISCORD", "status_webhooks"))
        self.webhook_connect_text = self.discord_text_block(grid, 0, 1, "Connect", self.cfg.get("DISCORD", "connect_webhooks"))
        self.webhook_disconnect_text = self.discord_text_block(grid, 1, 0, "Disconnect", self.cfg.get("DISCORD", "disconnect_webhooks"))
        self.webhook_chat_text = self.discord_text_block(grid, 1, 1, "Chat", self.cfg.get("DISCORD", "chat_webhooks"))

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        messages = self.make_panel(root, "Mensajes personalizados")
        self.form_row(messages, 0, "Online", self.message_online_var)
        self.form_row(messages, 1, "Connect", self.message_connect_var)
        self.form_row(messages, 2, "Disconnect", self.message_disconnect_var)
        self.form_row(messages, 3, "Chat", self.message_chat_var)

        helpbox = self.make_panel(root, "Variables disponibles")
        help_text = (
            "Online: {port}, {time}, {raw}\n"
            "Connect: {player}, {guid}, {level}, {character}, {time}, {raw}\n"
            "Disconnect: {player}, {guid}, {reason}, {time}, {raw}\n"
            "Chat: {player}, {message}, {time}, {raw}\n\n"
            "Puedes poner varios webhooks, uno por línea. Ejemplo chat: **{player}:** {message}"
        )
        ttk.Label(helpbox, text=help_text, style="PanelMuted.TLabel", justify="left").pack(anchor="w")

    def discord_text_block(self, parent, row, col, title, default_text):
        box = ttk.Frame(parent, style="Panel.TFrame")
        box.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=(0, 8))

        ttk.Label(box, text=title, style="PanelMuted.TLabel").pack(anchor="w")
        txt = tk.Text(
            box,
            height=3,
            bg="#020617",
            fg="#D1D5DB",
            insertbackground="#FFFFFF",
            font=("Consolas", 8),
            relief="flat",
            padx=6,
            pady=5,
        )
        txt.pack(fill="x", pady=(3, 0))
        txt.insert("1.0", str(default_text or ""))
        return txt

    def form_row(self, parent, row, label, var, show=None):
        ttk.Label(parent, text=label, style="Panel.TLabel", width=18).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(parent, textvariable=var, show=show).grid(row=row, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)

    def get_textarea_value(self, text_widget):
        return text_widget.get("1.0", "end").strip()

    def apply_discord_config(self, save=True):
        status_hooks = split_webhooks(self.get_textarea_value(self.webhook_status_text)) if hasattr(self, "webhook_status_text") else split_webhooks(self.cfg.get("DISCORD", "status_webhooks"))
        connect_hooks = split_webhooks(self.get_textarea_value(self.webhook_connect_text)) if hasattr(self, "webhook_connect_text") else split_webhooks(self.cfg.get("DISCORD", "connect_webhooks"))
        disconnect_hooks = split_webhooks(self.get_textarea_value(self.webhook_disconnect_text)) if hasattr(self, "webhook_disconnect_text") else split_webhooks(self.cfg.get("DISCORD", "disconnect_webhooks"))
        chat_hooks = split_webhooks(self.get_textarea_value(self.webhook_chat_text)) if hasattr(self, "webhook_chat_text") else split_webhooks(self.cfg.get("DISCORD", "chat_webhooks"))

        self.discord_bot.configure(
            enabled=self.discord_enabled_var.get(),
            username=self.discord_username_var.get().strip() or "SHAR MP Bot",
            avatar_url=self.discord_avatar_var.get().strip(),
            status_webhooks=status_hooks,
            connect_webhooks=connect_hooks,
            disconnect_webhooks=disconnect_hooks,
            chat_webhooks=chat_hooks,
            send_online=self.send_online_var.get(),
            send_connect=self.send_connect_var.get(),
            send_disconnect=self.send_disconnect_var.get(),
            send_chat=self.send_chat_var.get(),
            message_online=self.message_online_var.get(),
            message_connect=self.message_connect_var.get(),
            message_disconnect=self.message_disconnect_var.get(),
            message_chat=self.message_chat_var.get(),
            log_discord_to_console=self.discord_log_console_var.get(),
        )

        self.discord_status_var.set("Discord: activado" if self.discord_enabled_var.get() else "Discord: desactivado")

        if save:
            self.save_config(silent=True)
            messagebox.showinfo("Discord", "Configuración aplicada y guardada.")

    def send_discord_test(self):
        self.apply_discord_config(save=True)

        if not self.discord_enabled_var.get():
            messagebox.showwarning("Discord", "Activa el bot Discord primero.")
            return

        content = "🧪 Prueba desde SHAR MP Admin Panel. Webhook funcionando correctamente."

        all_hooks = []
        all_hooks.extend(self.discord_bot.status_webhooks)
        all_hooks.extend(self.discord_bot.connect_webhooks)
        all_hooks.extend(self.discord_bot.disconnect_webhooks)
        all_hooks.extend(self.discord_bot.chat_webhooks)

        unique_hooks = []

        for h in all_hooks:
            if h not in unique_hooks:
                unique_hooks.append(h)

        if not unique_hooks:
            messagebox.showwarning("Discord", "No hay webhooks configurados.")
            return

        self.discord_bot.enqueue(unique_hooks, content, event="test")
        messagebox.showinfo("Discord", "Prueba enviada.")

    # ========================================================
    # Users tab
    # ========================================================

    def build_users_tab(self):
        top = ttk.Frame(self.tab_users)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Conectar", command=self.connect_db).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Refrescar", command=self.load_users).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Crear", command=self.open_create_user).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Reset Pass", command=self.open_reset_password).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Guardar flags", command=self.save_selected_flags).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Eliminar", command=self.delete_selected_user).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="CSV", command=self.export_users_csv).pack(side="left", padx=(0, 6))

        ttk.Label(top, text="Buscar").pack(side="left", padx=(10, 5))
        search = ttk.Entry(top, textvariable=self.search_user_var, width=20)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda e: self.filter_users())

        ttk.Label(top, textvariable=self.db_status_var, style="Sub.TLabel").pack(side="right")

        columns = ("id", "username", "operator", "remember_me", "last_ip_address", "created_at", "last_login", "password_hash")
        self.users_tree = ttk.Treeview(self.tab_users, columns=columns, show="headings", selectmode="browse")
        self.users_tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.users_tree.bind("<<TreeviewSelect>>", lambda e: self.populate_user_side_panel())

        headings = {
            "id": "ID",
            "username": "Username",
            "operator": "OP",
            "remember_me": "Remember",
            "last_ip_address": "Última IP",
            "created_at": "Creado",
            "last_login": "Último login",
            "password_hash": "Password SHA256",
        }

        widths = {
            "id": 50,
            "username": 150,
            "operator": 55,
            "remember_me": 75,
            "last_ip_address": 130,
            "created_at": 145,
            "last_login": 145,
            "password_hash": 360,
        }

        for col in columns:
            self.users_tree.heading(col, text=headings[col])
            self.users_tree.column(col, width=widths[col], anchor="w")

        side = ttk.Frame(self.tab_users)
        side.pack(fill="x", padx=10, pady=(0, 10))

        self.selected_user_var = tk.StringVar(value="Seleccionado: -")
        self.selected_op_var = tk.BooleanVar(value=False)
        self.selected_remember_var = tk.BooleanVar(value=False)

        ttk.Label(side, textvariable=self.selected_user_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(side, text="Operator / OP", variable=self.selected_op_var).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(side, text="Remember Me", variable=self.selected_remember_var).pack(side="left", padx=(0, 10))

    # ========================================================
    # Schema tab
    # ========================================================

    def build_schema_tab(self):
        top = ttk.Frame(self.tab_schema)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Cargar esquema", command=self.load_schema).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Integrity check", command=self.integrity_check).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Crear users", command=self.ensure_users_table).pack(side="left", padx=(0, 6))
        ttk.Label(top, textvariable=self.schema_status_var, style="Sub.TLabel").pack(side="right")

        self.schema_text = tk.Text(
            self.tab_schema,
            bg="#020617",
            fg="#D1D5DB",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
            wrap="none",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.schema_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ========================================================
    # YAML tab
    # ========================================================

    def build_yaml_tab(self):
        sf = ScrollableFrame(self.tab_yaml)
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        wrapper = sf.content

        top = self.make_panel(wrapper, "Archivo Server.yaml")

        ttk.Label(top, text="Ruta", style="Panel.TLabel", width=10).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(top, textvariable=self.yaml_path_var).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(top, text="Buscar", command=self.browse_yaml).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(top, text="Cargar", command=self.load_server_yaml).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(top, text="Guardar", command=self.save_server_yaml).grid(row=0, column=4)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, textvariable=self.yaml_status_var, style="PanelMuted.TLabel").grid(row=1, column=0, columnspan=5, sticky="w", pady=(6, 0))

        basic = self.make_panel(wrapper, "Servidor")
        self.form_row(basic, 0, "Nombre", self.yaml_vars["serverName"])
        self.form_row(basic, 1, "Hostname", self.yaml_vars["hostname"])
        self.form_row(basic, 2, "Password", self.yaml_vars["password"], show="*")
        self.form_row(basic, 3, "Puerto", self.yaml_vars["port"])
        self.form_row(basic, 4, "Max players", self.yaml_vars["maxPlayers"])
        self.form_row(basic, 5, "Game mode", self.yaml_vars["gameMode"])

        master = self.make_panel(wrapper, "Master Server")
        self.form_row(master, 0, "Master", self.yaml_vars["masterServer"])
        self.form_row(master, 1, "Token", self.yaml_vars["masterServerAuthorisation"])
        ttk.Checkbutton(master, text="broadcastServer", variable=self.yaml_bools["broadcastServer"], style="Panel.TCheckbutton").grid(row=2, column=1, sticky="w", pady=4)

        opts = self.make_panel(wrapper, "Opciones")
        ttk.Checkbutton(opts, text="allowInGameTextChat", variable=self.yaml_bools["allowInGameTextChat"], style="Panel.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(opts, text="useChatFilter", variable=self.yaml_bools["useChatFilter"], style="Panel.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(opts, text="enableMods", variable=self.yaml_bools["enableMods"], style="Panel.TCheckbutton").grid(row=0, column=2, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(opts, text="webRequests", variable=self.yaml_bools["webRequests"], style="Panel.TCheckbutton").grid(row=0, column=3, sticky="w", padx=(0, 16), pady=3)

        intervals = self.make_panel(wrapper, "Intervalos")
        self.form_row(intervals, 0, "Update", self.yaml_vars["updateInterval"])
        self.form_row(intervals, 1, "Low bandwidth", self.yaml_vars["updateIntervalLowBandwidth"])

        behaviours = self.make_panel(wrapper, "Non-synced behaviours")
        ttk.Checkbutton(behaviours, text="pedestrians", variable=self.yaml_bools["pedestrians"], style="Panel.TCheckbutton").grid(row=0, column=0, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(behaviours, text="traffic", variable=self.yaml_bools["traffic"], style="Panel.TCheckbutton").grid(row=0, column=1, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(behaviours, text="missions", variable=self.yaml_bools["missions"], style="Panel.TCheckbutton").grid(row=0, column=2, sticky="w", padx=(0, 16), pady=3)
        ttk.Checkbutton(behaviours, text="police", variable=self.yaml_bools["police"], style="Panel.TCheckbutton").grid(row=0, column=3, sticky="w", padx=(0, 16), pady=3)

        lists = self.make_panel(wrapper, "Listas")
        self.server_mod_paths_text = self.small_text(lists, 0, 0, "serverModificationPaths")
        self.client_mod_paths_text = self.small_text(lists, 0, 1, "clientModificationPaths")
        self.required_mod_names_text = self.small_text(lists, 1, 0, "requiredModNames")
        self.banned_mod_names_text = self.small_text(lists, 1, 1, "bannedModNames")
        self.required_sha_text = self.small_text(lists, 2, 0, "requiredModsSHA256")
        self.banned_sha_text = self.small_text(lists, 2, 1, "bannedModsSHA256")

        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)

        self.load_server_yaml(silent=True)

    def small_text(self, parent, row, col, label):
        box = ttk.Frame(parent, style="Panel.TFrame")
        box.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=(0, 8))

        ttk.Label(box, text=label, style="PanelMuted.TLabel").pack(anchor="w")
        txt = tk.Text(box, height=3, bg="#020617", fg="#D1D5DB", insertbackground="#FFFFFF", font=("Consolas", 8), relief="flat", padx=6, pady=5)
        txt.pack(fill="x", pady=(3, 0))
        return txt

    # ========================================================
    # Config tab
    # ========================================================

    def build_config_tab(self):
        sf = ScrollableFrame(self.tab_config)
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        wrapper = sf.content

        server = self.make_panel(wrapper, "Servidor")
        self.path_row(server, 0, "EXE", self.exe_var, self.browse_exe)
        self.path_row(server, 1, "Working dir", self.workdir_var, self.browse_workdir)
        self.form_row(server, 2, "Argumentos", self.args_var)
        self.path_row(server, 3, "Server.yaml", self.yaml_path_var, self.browse_yaml)

        db = self.make_panel(wrapper, "Base de datos")
        self.path_row(db, 0, "Mod folder", self.mod_folder_var, self.browse_mod_folder)
        self.path_row(db, 1, ".db.ocala", self.sqlite_var, self.browse_sqlite)
        self.form_row(db, 2, "Tabla users", self.table_var)

        note = self.make_panel(wrapper, "Notas")
        ttk.Label(
            note,
            text="La DB oficial normalmente está en:\nD:\\Juegos\\Vivendi Universal Games\\server\\ServerMods\\Simpsons Hit & Run Multiplayer\\.db.ocala\n\nDiscord se configura en la pestaña Discord.",
            style="PanelMuted.TLabel",
            justify="left",
        ).pack(anchor="w")

    def path_row(self, parent, row, label, var, command):
        ttk.Label(parent, text=label, style="Panel.TLabel", width=18).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4, padx=(0, 6))
        ttk.Button(parent, text="Buscar", command=command).grid(row=row, column=2, sticky="e", pady=4)
        parent.columnconfigure(1, weight=1)

    # ========================================================
    # Tools tab
    # ========================================================

    def build_tools_tab(self):
        sf = ScrollableFrame(self.tab_tools)
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        wrapper = sf.content

        quick = self.make_panel(wrapper, "Comandos rápidos")
        commands = [
            ("exit", "Cerrar servidor"),
            ("help", "Ayuda consola"),
            ("status", "Estado"),
            ("players", "Jugadores"),
            ("countdown", "Countdown"),
        ]

        for i, (cmd, label) in enumerate(commands):
            ttk.Button(quick, text=f"{label}\n{cmd}", command=lambda c=cmd: self.quick_command(c)).grid(
                row=i // 3,
                column=i % 3,
                padx=4,
                pady=4,
                sticky="ew",
            )

        for i in range(3):
            quick.columnconfigure(i, weight=1)

        custom = self.make_panel(wrapper, "Comando personalizado")
        self.quick_custom_var = tk.StringVar()
        ttk.Entry(custom, textvariable=self.quick_custom_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(custom, text="Enviar", command=lambda: self.quick_command(self.quick_custom_var.get())).pack(side="left")

    # ========================================================
    # Runtime / Console
    # ========================================================

    def enqueue_log(self, text):
        self.log_queue.put(text)

        try:
            for line in str(text).splitlines():
                self.discord_bot.process_log_line(line)
        except Exception as e:
            self.log_queue.put(f"[DISCORD PARSER ERROR] {e}\n")

    def process_log_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                self.write_console(text)
        except queue.Empty:
            pass

        self.after(100, self.process_log_queue)

    def write_console(self, text):
        self.console.insert("end", text)
        self.console_line_count += text.count("\n")

        max_lines = self.cfg.get_int("UI", "console_max_lines", 2500)

        if self.console_line_count > max_lines:
            self.console.delete("1.0", "250.0")
            self.console_line_count = max_lines - 250

        if self.autoscroll_var.get():
            self.console.see("end")

    def clear_console(self):
        self.console.delete("1.0", "end")
        self.console_line_count = 0

    def start_server(self):
        try:
            self.save_config(silent=True)
            self.apply_discord_config(save=False)
            self.discord_bot.reset_runtime_state()

            self.server.start(
                self.exe_var.get().strip(),
                self.workdir_var.get().strip(),
                self.args_var.get().strip(),
            )
            self.set_online(True)

        except Exception as e:
            messagebox.showerror("Error al iniciar", str(e))
            self.enqueue_log(f"[PANEL ERROR] {e}\n")

    def stop_server(self):
        try:
            send_exit = self.cfg.get_bool("SERVER", "send_exit_on_stop", True)
            kill_after = self.cfg.get_int("SERVER", "kill_after_seconds", 5)
            self.server.stop(send_exit=send_exit, kill_after_seconds=kill_after)

        except Exception as e:
            messagebox.showerror("Error al detener", str(e))
            self.enqueue_log(f"[PANEL ERROR] {e}\n")

    def restart_server(self):
        self.stop_server()
        self.after(1200, self.start_server)

    def on_server_stopped(self):
        self.after(0, lambda: self.set_online(False))

    def set_online(self, online):
        if online:
            self.status_var.set("ONLINE")
            self.status_badge.configure(bg="#065F46")
        else:
            self.status_var.set("OFFLINE")
            self.status_badge.configure(bg="#7F1D1D")

    def refresh_status_loop(self):
        self.set_online(self.server.is_running())
        self.after(1000, self.refresh_status_loop)

    def send_console_command(self):
        cmd = self.command_var.get().strip()

        if not cmd:
            return

        try:
            self.server.send_command(cmd)
            self.enqueue_log(f"> {cmd}\n")
            self.command_var.set("")

        except Exception as e:
            messagebox.showerror("No se pudo enviar", str(e))

    def quick_command(self, cmd):
        cmd = (cmd or "").strip()

        if not cmd:
            return

        try:
            self.server.send_command(cmd)
            self.enqueue_log(f"> {cmd}\n")

        except Exception as e:
            messagebox.showerror("No se pudo enviar", str(e))

    # ========================================================
    # Database actions
    # ========================================================

    def auto_db_bootstrap(self):
        if not os.path.exists(self.sqlite_var.get().strip()):
            self.detect_ocala_db(silent=True)

        if os.path.exists(self.sqlite_var.get().strip()):
            self.connect_db(silent=True)
            self.load_users(silent=True)
            self.load_schema(silent=True)

    def detect_ocala_db(self, silent=False):
        candidates = []
        mod_folder = self.mod_folder_var.get().strip()

        possible_roots = [
            mod_folder,
            os.path.join(self.workdir_var.get().strip(), "ServerMods", "Simpsons Hit & Run Multiplayer"),
            r"D:\Juegos\Vivendi Universal Games\server\ServerMods\Simpsons Hit & Run Multiplayer",
            r"D:\Juegos\Vivendi Universal Games\ServerMods\Simpsons Hit & Run Multiplayer",
        ]

        for root in possible_roots:
            if root and os.path.isdir(root):
                direct = os.path.join(root, ".db.ocala")

                if os.path.exists(direct):
                    candidates.append(direct)

                try:
                    for dirpath, _, filenames in os.walk(root):
                        for name in filenames:
                            if name.lower() == ".db.ocala" or name.lower().endswith((".sqlite", ".sqlite3", ".db")):
                                candidates.append(os.path.join(dirpath, name))
                except Exception:
                    pass

        seen = []

        for c in candidates:
            if c not in seen:
                seen.append(c)

        if seen:
            self.sqlite_var.set(seen[0])
            self.db.set_path(seen[0])
            self.db_file_var.set(os.path.basename(seen[0]))
            self.db_status_var.set("DB detectada")
            self.save_config(silent=True)

            if not silent:
                messagebox.showinfo("Detectar DB", "Base detectada:\n" + seen[0])

            return seen[0]

        if not silent:
            messagebox.showwarning("Detectar DB", "No se encontró .db.ocala. Inicia el servidor una vez para que cree la base.")

        return None

    def connect_db(self, silent=False):
        path = self.sqlite_var.get().strip()
        self.db.set_path(path)

        if not os.path.exists(path):
            self.db_status_var.set("DB: archivo no encontrado")

            if not silent:
                messagebox.showwarning("SQLite", f"No existe la base:\n{path}")

            return False

        try:
            result = self.db.test()
            self.db_status_var.set("DB conectada: " + str(result))
            self.db_file_var.set(os.path.basename(path))
            self.save_config(silent=True)

            if not silent:
                messagebox.showinfo("SQLite", "Conectado correctamente.\nIntegrity check: " + str(result))

            return True

        except Exception as e:
            self.db_status_var.set("DB: error")

            if not silent:
                messagebox.showerror("SQLite", str(e))

            return False

    def ensure_users_table(self):
        try:
            self.db.set_path(self.sqlite_var.get().strip())
            self.db.ensure_users_table()
            self.load_schema(silent=True)
            self.load_users(silent=True)
            messagebox.showinfo("SQLite", "Tabla users oficial creada/verificada.")

        except Exception as e:
            messagebox.showerror("SQLite", str(e))

    def load_users(self, silent=False):
        self.db.set_path(self.sqlite_var.get().strip())

        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        try:
            users = self.db.get_users()
            self.users_all = []

            total = 0
            ops = 0
            logged = 0

            for row in users:
                d = dict(row)
                self.users_all.append(d)
                total += 1

                if int_to_bool(d.get("operator")):
                    ops += 1

                if d.get("last_login"):
                    logged += 1

            self.user_count_var.set(str(total))
            self.op_count_var.set(str(ops))
            self.login_count_var.set(str(logged))
            self.db_file_var.set(os.path.basename(self.sqlite_var.get().strip()))
            self.render_users(self.users_all)
            self.db_status_var.set(f"DB: {total} usuarios")

        except Exception as e:
            self.db_status_var.set("DB: error users")

            if not silent:
                messagebox.showerror("SQLite users", str(e))

    def render_users(self, users):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        for d in users:
            values = (
                d.get("id", ""),
                d.get("username", ""),
                int(d.get("operator") or 0),
                int(d.get("remember_me") or 0),
                d.get("last_ip_address", "") or "",
                d.get("created_at", "") or "",
                d.get("last_login", "") or "",
                d.get("password_hash", "") or "",
            )
            self.users_tree.insert("", "end", values=values)

    def filter_users(self):
        term = self.search_user_var.get().strip().lower()

        if not term:
            self.render_users(self.users_all)
            return

        filtered = []

        for d in self.users_all:
            joined = " ".join(str(v) for v in d.values()).lower()

            if term in joined:
                filtered.append(d)

        self.render_users(filtered)

    def get_selected_user_values(self):
        item = self.users_tree.focus()

        if not item:
            return None

        vals = self.users_tree.item(item, "values")

        if not vals:
            return None

        return {
            "id": int(vals[0]),
            "username": vals[1],
            "operator": vals[2],
            "remember_me": vals[3],
            "last_ip_address": vals[4],
            "created_at": vals[5],
            "last_login": vals[6],
            "password_hash": vals[7],
        }

    def populate_user_side_panel(self):
        user = self.get_selected_user_values()

        if not user:
            self.selected_user_var.set("Seleccionado: -")
            return

        self.selected_user_var.set(f"Seleccionado: #{user['id']} {user['username']}")
        self.selected_op_var.set(int_to_bool(user["operator"]))
        self.selected_remember_var.set(int_to_bool(user["remember_me"]))

    def open_create_user(self):
        def on_save(username, password, ip, operator, remember):
            try:
                self.db.set_path(self.sqlite_var.get().strip())
                self.db.create_user(username, password, operator, remember, ip or None)
                self.load_users(silent=True)
                messagebox.showinfo("Usuario", "Usuario creado correctamente.")
            except Exception as e:
                messagebox.showerror("Crear usuario", str(e))

        UserEditor(self, "Crear usuario", mode="create", on_save=on_save)

    def open_reset_password(self):
        user = self.get_selected_user_values()

        if not user:
            messagebox.showwarning("Reset password", "Selecciona un usuario.")
            return

        def on_save(username, password, ip, operator, remember):
            try:
                self.db.set_path(self.sqlite_var.get().strip())
                self.db.reset_password(user["id"], password)
                self.db.update_flags(user["id"], operator, remember)
                self.load_users(silent=True)
                messagebox.showinfo("Password", "Password reseteada correctamente.")
            except Exception as e:
                messagebox.showerror("Reset password", str(e))

        UserEditor(self, "Reset password", mode="reset", user=user, on_save=on_save)

    def save_selected_flags(self):
        user = self.get_selected_user_values()

        if not user:
            messagebox.showwarning("Flags", "Selecciona un usuario.")
            return

        try:
            self.db.set_path(self.sqlite_var.get().strip())
            self.db.update_flags(user["id"], self.selected_op_var.get(), self.selected_remember_var.get())
            self.load_users(silent=True)
            messagebox.showinfo("Flags", "Flags actualizados.")

        except Exception as e:
            messagebox.showerror("Flags", str(e))

    def delete_selected_user(self):
        user = self.get_selected_user_values()

        if not user:
            messagebox.showwarning("Eliminar", "Selecciona un usuario.")
            return

        if not messagebox.askyesno("Eliminar", f"¿Eliminar usuario {user['username']}?"):
            return

        try:
            self.db.set_path(self.sqlite_var.get().strip())
            self.db.delete_user(user["id"])
            self.load_users(silent=True)
            messagebox.showinfo("Eliminar", "Usuario eliminado.")

        except Exception as e:
            messagebox.showerror("Eliminar", str(e))

    def export_users_csv(self):
        if not self.users_all:
            messagebox.showwarning("CSV", "No hay usuarios cargados.")
            return

        path = filedialog.asksaveasfilename(title="Exportar usuarios", defaultextension=".csv", filetypes=[("CSV", "*.csv")])

        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["id", "username", "password_hash", "operator", "remember_me", "last_ip_address", "created_at", "last_login"],
                )
                writer.writeheader()

                for row in self.users_all:
                    writer.writerow({k: row.get(k, "") for k in writer.fieldnames})

            messagebox.showinfo("CSV", "Exportado correctamente.")

        except Exception as e:
            messagebox.showerror("CSV", str(e))

    def load_schema(self, silent=False):
        self.db.set_path(self.sqlite_var.get().strip())
        self.schema_text.delete("1.0", "end")

        try:
            tables = self.db.get_tables()
            output = []
            output.append("SQLite database:")
            output.append(self.sqlite_var.get().strip())
            output.append("")
            output.append("Tables:")

            for table in tables:
                output.append(f" - {table}")

            output.append("")
            output.append("Schema details:")

            conn = self.db.connect()

            try:
                cur = conn.cursor()

                for table in tables:
                    output.append("")
                    output.append("=" * 72)
                    output.append(f"TABLE: {table}")
                    output.append("=" * 72)

                    cur.execute(f"PRAGMA table_info({table})")

                    for col in cur.fetchall():
                        output.append(
                            f"{col['cid']:02d} | {col['name']} | {col['type']} | notnull={col['notnull']} | default={col['dflt_value']} | pk={col['pk']}"
                        )

                    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table,))
                    row = cur.fetchone()

                    if row and row["sql"]:
                        output.append("")
                        output.append(row["sql"])

            finally:
                conn.close()

            self.schema_text.insert("1.0", "\n".join(output))
            self.schema_status_var.set(f"Schema: {len(tables)} tablas")

        except Exception as e:
            self.schema_status_var.set("Schema: error")

            if not silent:
                messagebox.showerror("Schema", str(e))

    def integrity_check(self):
        try:
            self.db.set_path(self.sqlite_var.get().strip())
            result = self.db.test()
            messagebox.showinfo("Integrity check", str(result))

        except Exception as e:
            messagebox.showerror("Integrity check", str(e))

    # ========================================================
    # YAML
    # ========================================================

    def set_text_lines(self, text_widget, values):
        text_widget.delete("1.0", "end")

        if isinstance(values, list):
            text_widget.insert("1.0", "\n".join(str(v) for v in values))
        elif values:
            text_widget.insert("1.0", str(values))

    def get_text_lines(self, text_widget):
        raw = text_widget.get("1.0", "end").strip()

        if not raw:
            return []

        return [line.strip() for line in raw.splitlines() if line.strip()]

    def load_server_yaml(self, silent=False):
        path = self.yaml_path_var.get().strip()

        if not path:
            if not silent:
                messagebox.showwarning("Server.yaml", "No hay ruta configurada para Server.yaml.")
            return

        if not os.path.exists(path):
            self.yaml_status_var.set("Server.yaml: no encontrado")

            if not silent:
                messagebox.showwarning("Server.yaml", f"No existe:\n{path}")

            return

        try:
            data = simple_yaml_load(path)

            for key, var in self.yaml_vars.items():
                if key in data:
                    var.set(str(data.get(key, "")))

            for key in ["broadcastServer", "allowInGameTextChat", "useChatFilter", "enableMods"]:
                if key in data:
                    self.yaml_bools[key].set(yaml_bool(data[key]))

            mod_perm = data.get("modPermissions", {})

            if isinstance(mod_perm, dict) and "webRequests" in mod_perm:
                self.yaml_bools["webRequests"].set(yaml_bool(mod_perm["webRequests"]))

            behaviours = data.get("nonSyncedGameBehaviours", {})

            if isinstance(behaviours, dict):
                for key in ["pedestrians", "traffic", "missions", "police"]:
                    if key in behaviours:
                        self.yaml_bools[key].set(yaml_bool(behaviours[key]))

            if hasattr(self, "server_mod_paths_text"):
                self.set_text_lines(self.server_mod_paths_text, data.get("serverModificationPaths", []))
                self.set_text_lines(self.client_mod_paths_text, data.get("clientModificationPaths", []))
                self.set_text_lines(self.required_mod_names_text, data.get("requiredModNames", []))
                self.set_text_lines(self.banned_mod_names_text, data.get("bannedModNames", []))
                self.set_text_lines(self.required_sha_text, data.get("requiredModsSHA256", []))
                self.set_text_lines(self.banned_sha_text, data.get("bannedModsSHA256", []))

            self.yaml_status_var.set("Server.yaml: cargado")

        except Exception as e:
            self.yaml_status_var.set("Server.yaml: error")

            if not silent:
                messagebox.showerror("Server.yaml", str(e))

    def save_server_yaml(self):
        path = self.yaml_path_var.get().strip()

        if not path:
            messagebox.showwarning("Server.yaml", "No hay ruta configurada.")
            return

        try:
            data = {
                "serverName": self.yaml_vars["serverName"].get(),
                "hostname": self.yaml_vars["hostname"].get(),
                "password": self.yaml_vars["password"].get(),
                "port": int(self.yaml_vars["port"].get() or 7777),
                "maxPlayers": int(self.yaml_vars["maxPlayers"].get() or 32),
                "masterServer": self.yaml_vars["masterServer"].get(),
                "masterServerAuthorisation": self.yaml_vars["masterServerAuthorisation"].get(),
                "broadcastServer": self.yaml_bools["broadcastServer"].get(),
                "gameMode": self.yaml_vars["gameMode"].get(),
                "rules": {},
                "allowInGameTextChat": self.yaml_bools["allowInGameTextChat"].get(),
                "useChatFilter": self.yaml_bools["useChatFilter"].get(),
                "updateInterval": int(self.yaml_vars["updateInterval"].get() or 60),
                "updateIntervalLowBandwidth": int(self.yaml_vars["updateIntervalLowBandwidth"].get() or 400),
                "enableMods": self.yaml_bools["enableMods"].get(),
                "serverModificationPaths": self.get_text_lines(self.server_mod_paths_text),
                "clientModificationPaths": self.get_text_lines(self.client_mod_paths_text),
                "requiredModNames": self.get_text_lines(self.required_mod_names_text),
                "bannedModNames": self.get_text_lines(self.banned_mod_names_text),
                "requiredModsSHA256": self.get_text_lines(self.required_sha_text),
                "bannedModsSHA256": self.get_text_lines(self.banned_sha_text),
                "modPermissions": {"webRequests": self.yaml_bools["webRequests"].get()},
                "nonSyncedGameBehaviours": {
                    "pedestrians": self.yaml_bools["pedestrians"].get(),
                    "traffic": self.yaml_bools["traffic"].get(),
                    "missions": self.yaml_bools["missions"].get(),
                    "police": self.yaml_bools["police"].get(),
                },
            }

            backup_path = path + ".bak"

            if os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="replace") as src:
                    old = src.read()

                with open(backup_path, "w", encoding="utf-8") as bak:
                    bak.write(old)

            simple_yaml_save(path, data)
            self.yaml_status_var.set("Server.yaml: guardado")
            self.save_config(silent=True)
            messagebox.showinfo("Server.yaml", f"Guardado correctamente.\nBackup:\n{backup_path}")

        except ValueError:
            messagebox.showerror("Server.yaml", "Puerto, maxPlayers e intervalos deben ser números.")

        except Exception as e:
            self.yaml_status_var.set("Server.yaml: error")
            messagebox.showerror("Server.yaml", str(e))

    # ========================================================
    # Browse / Config save
    # ========================================================

    def browse_exe(self):
        path = filedialog.askopenfilename(title="Seleccionar servidor EXE", filetypes=[("Ejecutables", "*.exe"), ("Todos", "*.*")])

        if path:
            self.exe_var.set(path)

            if not self.workdir_var.get().strip():
                self.workdir_var.set(os.path.dirname(path))

    def browse_workdir(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de trabajo")

        if path:
            self.workdir_var.set(path)

    def browse_mod_folder(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta del mod SHAR MP")

        if path:
            self.mod_folder_var.set(path)
            db_path = os.path.join(path, ".db.ocala")

            if os.path.exists(db_path):
                self.sqlite_var.set(db_path)

    def browse_sqlite(self):
        path = filedialog.askopenfilename(
            title="Seleccionar base SQLite / .db.ocala",
            filetypes=[("Ocala SQLite", ".db.ocala"), ("SQLite", "*.db *.sqlite *.sqlite3"), ("Todos", "*.*")],
        )

        if path:
            self.sqlite_var.set(path)
            self.db.set_path(path)

    def browse_yaml(self):
        path = filedialog.askopenfilename(title="Seleccionar Server.yaml", filetypes=[("YAML", "*.yaml *.yml"), ("Todos", "*.*")])

        if path:
            self.yaml_path_var.set(path)

    def save_config(self, silent=False):
        self.cfg.set("SERVER", "exe_path", self.exe_var.get().strip())
        self.cfg.set("SERVER", "working_dir", self.workdir_var.get().strip())
        self.cfg.set("SERVER", "startup_args", self.args_var.get().strip())
        self.cfg.set("SERVER", "auto_scroll", str(self.autoscroll_var.get()).lower())
        self.cfg.set("SERVER", "server_yaml_path", self.yaml_path_var.get().strip())

        self.cfg.set("DATABASE", "sqlite_path", self.sqlite_var.get().strip())
        self.cfg.set("DATABASE", "mod_folder", self.mod_folder_var.get().strip())
        self.cfg.set("DATABASE", "users_table", self.table_var.get().strip())

        self.cfg.set("DISCORD", "enabled", str(self.discord_enabled_var.get()).lower())
        self.cfg.set("DISCORD", "username", self.discord_username_var.get().strip())
        self.cfg.set("DISCORD", "avatar_url", self.discord_avatar_var.get().strip())

        if hasattr(self, "webhook_status_text"):
            self.cfg.set("DISCORD", "status_webhooks", self.get_textarea_value(self.webhook_status_text))
            self.cfg.set("DISCORD", "connect_webhooks", self.get_textarea_value(self.webhook_connect_text))
            self.cfg.set("DISCORD", "disconnect_webhooks", self.get_textarea_value(self.webhook_disconnect_text))
            self.cfg.set("DISCORD", "chat_webhooks", self.get_textarea_value(self.webhook_chat_text))

        self.cfg.set("DISCORD", "send_online", str(self.send_online_var.get()).lower())
        self.cfg.set("DISCORD", "send_connect", str(self.send_connect_var.get()).lower())
        self.cfg.set("DISCORD", "send_disconnect", str(self.send_disconnect_var.get()).lower())
        self.cfg.set("DISCORD", "send_chat", str(self.send_chat_var.get()).lower())
        self.cfg.set("DISCORD", "log_discord_to_console", str(self.discord_log_console_var.get()).lower())

        self.cfg.set("DISCORD", "message_online", self.message_online_var.get())
        self.cfg.set("DISCORD", "message_connect", self.message_connect_var.get())
        self.cfg.set("DISCORD", "message_disconnect", self.message_disconnect_var.get())
        self.cfg.set("DISCORD", "message_chat", self.message_chat_var.get())

        self.cfg.save()

        if not silent:
            messagebox.showinfo("Configuración", "Config guardado correctamente.")


if __name__ == "__main__":
    app = SHARPanel()
    app.mainloop()
