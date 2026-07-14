"""Client entrypoint and high-level runtime controller."""

import json
import os
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, SERVER_HOST, SERVER_PORT
from common.protocol import MESSAGE_TYPES
from client_file_transfer import ClientFileTransferMixin
from client_history import ClientHistoryMixin
from client_ui import ClientUiMixin


class Client(ClientUiMixin, ClientHistoryMixin, ClientFileTransferMixin):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOCAL_DATA_PATH = os.path.join(BASE_DIR, "data", "client")
    CHAT_HISTORY_FILE = os.path.join(LOCAL_DATA_PATH, "chat_history.json")
    DOWNLOAD_PATH = os.path.join(LOCAL_DATA_PATH, "downloads")

    COLORS = {
        "bg": "#f2f2f7",
        "panel": "#ffffff",
        "panel_alt": "#f8f8fb",
        "panel_soft": "#fbfbfd",
        "border": "#d9d9df",
        "primary": "#0a84ff",
        "primary_dark": "#0066cc",
        "success": "#1f9d73",
        "warning": "#d97706",
        "danger": "#c2410c",
        "notification": "#ff3b30",
        "text": "#1c1c1e",
        "muted": "#6e6e73",
        "light_text": "#a1a1a6",
    }

    FILE_STATUS_LABELS = {
        "pending": "Pending",
        "rejected": "Ignored",
        "downloading": "Downloading",
        "done": "Downloaded",
        "sending": "Uploading",
        "sent": "Sent",
        "failed": "Transfer failed",
    }

    def __init__(self):
        self.client_socket = None
        self.username = None
        self.is_connected = False
        self.is_closing = False
        self.recv_buffer = b""
        self.send_lock = threading.Lock()
        self.connection_lock = threading.Lock()
        self.connection_generation = 0
        self.is_reconnecting = False
        self.reconnect_interval = 3
        self.last_login_username = None
        self.last_login_password = None
        self.pending_login_username = None
        self.pending_login_password = None
        self.last_server_activity = 0.0
        self.connection_stall_timeout = max(HEARTBEAT_TIMEOUT + 5, HEARTBEAT_INTERVAL * 2 + 5)

        self.current_chat = None
        self.is_group_chat = False
        self.current_list = "users"
        self.selected_group_name = None
        self.selected_group_joined = False

        self.joined_groups = []
        self.chat_history = {}
        self.file_items = {}
        self.pending_offers = {}
        self.active_downloads = {}
        self.action_tags = []
        self.action_tag_index = 0
        self.unread_counts = {}

        self.all_users = []
        self.all_groups = []
        self.group_members_cache = {}
        self.user_list_map = []
        self.joined_group_map = []
        self.discover_group_map = []

        self.load_local_data()
        os.makedirs(self.DOWNLOAD_PATH, exist_ok=True)

        self.build_gui()
        self.message_handlers = self.build_message_handlers()
        self.refresh_session_header()
        self.refresh_group_detail()
        self.refresh_chat_view()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def build_message_handlers(self):
        return {
            MESSAGE_TYPES["REGISTER_RESPONSE"]: self.handle_register_response,
            MESSAGE_TYPES["LOGIN_RESPONSE"]: self.handle_login_response,
            MESSAGE_TYPES["MESSAGE"]: self.handle_chat_message,
            MESSAGE_TYPES["USER_LIST"]: lambda data: self.update_user_directory(data.get("users", [])),
            MESSAGE_TYPES["GROUP_LIST"]: lambda data: self.update_group_catalog(data.get("groups", [])),
            MESSAGE_TYPES["USER_STATUS"]: lambda data: self.update_user_status(data.get("username"), data.get("status")),
            MESSAGE_TYPES["GROUP_MEMBERS"]: self.handle_group_members,
            MESSAGE_TYPES["GROUP_HISTORY_SYNC"]: self.handle_group_history_sync,
            MESSAGE_TYPES["GROUP_MEMBER_ADDED"]: self.handle_group_member_added,
            MESSAGE_TYPES["GROUP_CREATED"]: self.handle_group_created,
            MESSAGE_TYPES["GROUP_JOINED"]: self.handle_group_joined,
            MESSAGE_TYPES["GROUP_LEFT"]: self.handle_group_left,
            MESSAGE_TYPES["FILE_TRANSFER"]: self.handle_file_transfer_notice,
            MESSAGE_TYPES["FILE_DATA"]: self.handle_file_data,
            MESSAGE_TYPES["HEARTBEAT_RESPONSE"]: self.handle_heartbeat_response,
            MESSAGE_TYPES["ERROR"]: self.handle_error_message,
        }

    def connect_to_server(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))
            with self.connection_lock:
                self.client_socket = sock
                self.is_connected = True
                self.recv_buffer = b""
                self.connection_generation += 1
                self.last_server_activity = time.time()
                generation = self.connection_generation
            self.root.after(0, lambda: self.set_status("Connected to the server"))
            self.root.after(0, self.refresh_session_header)
            threading.Thread(target=self.receive_messages, args=(sock, generation), daemon=True).start()
            return True
        except Exception as exc:
            with self.connection_lock:
                self.client_socket = None
                self.is_connected = False
            messagebox.showerror("Error", f"Failed to connect to the server: {exc}")
            self.set_status("Failed to connect to the server", is_error=True)
            return False

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Warning", "Please enter both username and password.")
            return
        if not self.is_connected and not self.connect_to_server():
            return
        self.send_message_to_server({"type": MESSAGE_TYPES["REGISTER"], "data": {"username": username, "password": password}})

    def login(self):
        if self.username and self.chat_frame.winfo_ismapped() and not self.is_reconnecting:
            self.set_status(f"Already logged in as {self.username}")
            return
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Warning", "Please enter both username and password.")
            return
        self.pending_login_username = username
        self.pending_login_password = password
        if not self.is_connected and not self.connect_to_server():
            return
        self.send_message_to_server({"type": MESSAGE_TYPES["LOGIN"], "data": {"username": username, "password": password}})

    def send_login(self, event=None):
        self.login()

    def receive_messages(self, sock, generation):
        recv_buffer = b""
        while not self.is_closing and self.connection_generation == generation:
            try:
                while len(recv_buffer) < 4:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("The server connection was closed")
                    recv_buffer += chunk

                message_length = int.from_bytes(recv_buffer[:4], byteorder="big")
                recv_buffer = recv_buffer[4:]

                while len(recv_buffer) < message_length:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("The server connection was closed")
                    recv_buffer += chunk

                raw_message = recv_buffer[:message_length]
                recv_buffer = recv_buffer[message_length:]
                message = json.loads(raw_message.decode("utf-8"))
                self.root.after(0, self.process_message, message)
            except Exception as exc:
                if self.is_closing or self.connection_generation != generation or sock is not self.client_socket:
                    break
                print(f"Failed to receive message: {exc}")
                error_message = f"Disconnected from the server: {exc}"
                self.root.after(0, lambda msg=error_message: self.handle_connection_lost(msg))
                break

    def process_message(self, message):
        self.last_server_activity = time.time()
        handler = self.message_handlers.get(message.get("type"))
        if handler:
            handler(message.get("data", {}))

    def handle_register_response(self, data):
        if data.get("success"):
            messagebox.showinfo("Success", "Registration succeeded. Please sign in.")
            self.set_status("Registration succeeded. Please sign in.")
            return
        messagebox.showerror("Error", data.get("message", "Registration failed"))
        self.set_status("Registration failed", is_error=True)

    def handle_login_response(self, data):
        if data.get("success"):
            self.handle_login_success(data)
            return
        if self.is_reconnecting:
            self.is_reconnecting = False
            self.is_connected = False
            self.close_socket()
            self.set_status("Automatic re-login failed. Please sign in again after checking the server state.", is_error=True)
            self.refresh_session_header()
            return
        messagebox.showerror("Error", data.get("message", "Login failed"))
        self.set_status("Login failed", is_error=True)

    def handle_chat_message(self, data):
        item = self.normalize_server_message(data)
        if item:
            self.append_history_item(item, dedupe=True, refresh=True, incoming=True)

    def handle_file_data(self, data):
        self.handle_file_chunk(
            data.get("file_id"),
            data.get("offset", 0),
            data.get("data"),
            data.get("is_end", False),
        )

    def handle_heartbeat_response(self, data):
        self.last_server_activity = time.time()

    def handle_error_message(self, data):
        messagebox.showerror("Error", data.get("message", "Unknown error"))
        self.set_status(data.get("message", "Unknown error"), is_error=True)

    def handle_login_success(self, data):
        previous_chat = self.current_chat
        previous_is_group = self.is_group_chat
        previous_selected_group = self.selected_group_name
        is_relogin = bool(self.username)

        self.username = self.pending_login_username or self.last_login_username or self.username_entry.get().strip()
        self.last_login_username = self.username
        self.last_login_password = self.pending_login_password or self.last_login_password
        self.pending_login_username = None
        self.pending_login_password = None
        self.is_reconnecting = False
        self.last_server_activity = time.time()
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.username_entry.configure(state=tk.DISABLED)
        self.password_entry.configure(state=tk.DISABLED)
        self.login_button.configure(state=tk.DISABLED)
        self.register_button.configure(state=tk.DISABLED)
        self.root.focus_set()

        # Text history is synchronized from the server on every login. Local
        # persistence is kept for file cards and download state only.
        self.strip_local_text_history()
        self.merge_server_history(data.get("history", []))
        self.update_user_directory(data.get("all_users", []))
        self.update_group_catalog(data.get("all_groups", []), preserve_selection=is_relogin)

        if previous_chat and not previous_is_group:
            self.current_chat = previous_chat
            self.is_group_chat = False
        if previous_is_group and previous_chat in self.joined_groups:
            self.current_chat = previous_chat
            self.is_group_chat = True
        if previous_selected_group and self.get_group_info(previous_selected_group):
            self.selected_group_name = previous_selected_group
            self.selected_group_joined = bool(self.get_group_info(previous_selected_group).get("joined", False))
            self.request_group_members(previous_selected_group)

        self.refresh_session_header()
        self.refresh_group_detail()
        self.refresh_chat_view()
        status_message = f"Reconnected and restored session: {self.username}" if is_relogin else f"Signed in: {self.username}"
        self.set_status(status_message)

        generation = self.connection_generation
        threading.Thread(target=self.send_heartbeat, args=(generation,), daemon=True).start()
        threading.Thread(target=self.monitor_connection_health, args=(generation,), daemon=True).start()
        self.save_local_data()

    def send_message_to_server(self, message):
        if not self.client_socket or not self.is_connected:
            return False
        try:
            data = json.dumps(message, ensure_ascii=False).encode("utf-8")
            with self.send_lock:
                self.client_socket.sendall(len(data).to_bytes(4, byteorder="big"))
                self.client_socket.sendall(data)
            return True
        except Exception as exc:
            print(f"Failed to send message: {exc}")
            if not self.is_closing:
                error_message = f"Failed to send message: {exc}"
                self.root.after(0, lambda msg=error_message: self.handle_connection_lost(msg))
            return False

    def send_message(self, event=None):
        if not self.current_chat:
            messagebox.showwarning("Warning", "Please choose a chat target first.")
            return

        content = self.message_entry.get().strip()
        if not content:
            return

        timestamp = time.time()
        item = self.create_text_item(
            sender=self.username,
            chat_target=self.current_chat,
            content=content,
            timestamp=timestamp,
            is_group=self.is_group_chat,
        )
        self.append_history_item(item, refresh=True)
        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["SEND_MESSAGE"],
                "data": {
                    "sender": self.username,
                    "receiver": self.current_chat,
                    "content": content,
                    "timestamp": timestamp,
                    "is_group": self.is_group_chat,
                },
            }
        )
        self.message_entry.delete(0, tk.END)

    def send_heartbeat(self, generation):
        while self.username and not self.is_closing and self.connection_generation == generation:
            time.sleep(HEARTBEAT_INTERVAL)
            if not self.is_connected or self.connection_generation != generation or self.is_reconnecting:
                break
            self.send_message_to_server(
                {
                    "type": MESSAGE_TYPES["HEARTBEAT"],
                    "data": {"username": self.username, "timestamp": time.time()},
                }
            )

    def monitor_connection_health(self, generation):
        while self.username and not self.is_closing and self.connection_generation == generation:
            time.sleep(1)
            if not self.is_connected or self.connection_generation != generation or self.is_reconnecting:
                break
            if self.last_server_activity and (time.time() - self.last_server_activity) > self.connection_stall_timeout:
                self.root.after(0, lambda: self.handle_connection_lost("No server response for too long. Reconnecting automatically..."))
                break

    def close_socket(self):
        sock = self.client_socket
        self.client_socket = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass

    def handle_connection_lost(self, reason="Disconnected from the server"):
        if self.is_closing:
            return

        should_reconnect = False
        with self.connection_lock:
            self.is_connected = False
            self.recv_buffer = b""
            self.close_socket()
            if self.last_login_username and self.last_login_password and not self.is_reconnecting:
                self.is_reconnecting = True
                should_reconnect = True

        self.reset_transfer_state_after_disconnect()
        self.set_status("Server connection lost. Reconnecting automatically..." if self.last_login_username else reason, is_error=True)
        self.refresh_session_header()
        self.refresh_group_detail()
        self.refresh_chat_view()

        if should_reconnect:
            threading.Thread(target=self.reconnect_loop, daemon=True).start()

    def reconnect_loop(self):
        while self.is_reconnecting and not self.is_closing:
            if self.connect_to_server_silently():
                self.pending_login_username = self.last_login_username
                self.pending_login_password = self.last_login_password
                sent = self.send_message_to_server(
                    {
                        "type": MESSAGE_TYPES["LOGIN"],
                        "data": {
                            "username": self.last_login_username,
                            "password": self.last_login_password,
                        },
                    }
                )
                if sent:
                    self.root.after(0, lambda: self.set_status("Reconnected. Restoring the session..."))
                    return
            time.sleep(self.reconnect_interval)

    def connect_to_server_silently(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))
            with self.connection_lock:
                self.client_socket = sock
                self.is_connected = True
                self.recv_buffer = b""
                self.connection_generation += 1
                self.last_server_activity = time.time()
                generation = self.connection_generation
            threading.Thread(target=self.receive_messages, args=(sock, generation), daemon=True).start()
            return True
        except Exception:
            with self.connection_lock:
                self.client_socket = None
                self.is_connected = False
            return False

    def on_closing(self):
        self.is_closing = True
        self.save_local_data()
        self.is_connected = False
        self.is_reconnecting = False
        self.close_socket()
        self.root.destroy()


if __name__ == "__main__":
    Client()
