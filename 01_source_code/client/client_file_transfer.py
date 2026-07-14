"""File transfer helpers for the chat client."""

import base64
import os
import threading
import time
from tkinter import filedialog, messagebox

from common.config import FILE_CHUNK_SIZE
from common.protocol import MESSAGE_TYPES


class ClientFileTransferMixin:
    def reset_transfer_state_after_disconnect(self):
        changed = False
        self.active_downloads.clear()
        for file_id, item in self.file_items.items():
            status = item.get("download_status")
            if status == "downloading":
                item["download_status"] = "pending"
                self.pending_offers[file_id] = item
                changed = True
            elif status == "sending":
                item["download_status"] = "failed"
                changed = True
        if changed:
            self.save_local_data()

    def send_file(self):
        if not self.current_chat:
            messagebox.showwarning("Warning", "Please choose a chat target first.")
            return
        file_path = filedialog.askopenfilename(
            title="Select a file to send",
            filetypes=[("Text files", "*.txt *.md"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to read file: {exc}")
            return

        file_id = f"{self.username}_{int(time.time() * 1000)}_{file_name}"
        chat_target = self.current_chat
        is_group = self.is_group_chat

        item = self.create_file_item(
            sender=self.username,
            chat_target=chat_target,
            is_group=is_group,
            file_name=file_name,
            file_size=file_size,
            file_id=file_id,
            direction="sent",
            download_status="sending",
            local_path=file_path,
        )
        self.append_history_item(item, refresh=True)
        self.set_status(f"Starting file upload: {file_name}")

        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["FILE_TRANSFER"],
                "data": {
                    "sender": self.username,
                    "receiver": chat_target,
                    "file_name": file_name,
                    "file_size": file_size,
                    "file_id": file_id,
                    "is_group": is_group,
                },
            }
        )

        def upload_file():
            try:
                with open(file_path, "rb") as file_obj:
                    offset = 0
                    while True:
                        chunk = file_obj.read(FILE_CHUNK_SIZE)
                        if not chunk:
                            break
                        chunk_b64 = base64.b64encode(chunk).decode("utf-8")
                        self.send_message_to_server(
                            {
                                "type": MESSAGE_TYPES["FILE_TRANSFER"],
                                "data": {
                                    "sender": self.username,
                                    "receiver": chat_target,
                                    "file_name": file_name,
                                    "file_size": file_size,
                                    "file_id": file_id,
                                    "chunk_data": chunk_b64,
                                    "offset": offset,
                                    "is_end": offset + len(chunk) >= file_size,
                                    "is_group": is_group,
                                },
                            }
                        )
                        offset += len(chunk)
                self.root.after(0, lambda: self.update_file_status(file_id, "sent"))
                self.root.after(0, lambda: self.set_status(f"File sent: {file_name}"))
            except Exception as exc:
                print(f"File upload failed: {exc}")
                self.root.after(0, lambda: self.update_file_status(file_id, "failed"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send file: {exc}"))

        threading.Thread(target=upload_file, daemon=True).start()

    def handle_file_transfer_notice(self, data):
        sender = data.get("sender") or "Unknown user"
        file_name = data.get("file_name") or "Untitled file"
        file_size = int(data.get("file_size") or 0)
        file_id = data.get("file_id")
        is_group = bool(data.get("is_group", False))
        if not file_id:
            return
        chat_target = self.resolve_file_chat_target(data)
        if not chat_target:
            self.set_status(f"Received file {file_name}, but the target conversation could not be resolved.", is_error=True)
            return
        existing_item = self.file_items.get(file_id)
        if existing_item:
            if existing_item.get("download_status") == "done":
                return
            self.pending_offers[file_id] = existing_item
            self.refresh_chat_view()
            return
        item = self.create_file_item(
            sender=sender,
            chat_target=chat_target,
            is_group=is_group,
            file_name=file_name,
            file_size=file_size,
            file_id=file_id,
            direction="received",
            download_status="pending",
        )
        self.pending_offers[file_id] = item
        self.append_history_item(item, dedupe=True, refresh=True, incoming=True)
        self.set_status(f"Received file from {sender} : {file_name}")

    def resolve_file_chat_target(self, data):
        if data.get("is_group"):
            return data.get("receiver") or data.get("group_name")
        return data.get("sender")

    def update_file_status(self, file_id, status, local_path=None):
        item = self.file_items.get(file_id)
        if not item:
            return
        item["download_status"] = status
        if local_path:
            item["local_path"] = local_path
        if item.get("download_status") == "done":
            self.pending_offers.pop(file_id, None)
            self.active_downloads.pop(file_id, None)
        if item.get("chat_target") == self.current_chat:
            self.refresh_chat_view()
        self.save_local_data()

    def reject_file_offer(self, file_id):
        if file_id not in self.file_items:
            return
        self.pending_offers.pop(file_id, None)
        self.update_file_status(file_id, "rejected")
        self.set_status("File offer ignored.")

    def start_file_download(self, file_id):
        item = self.file_items.get(file_id)
        if not item:
            return
        local_path = item.get("local_path") or self.resolve_download_path(item["file_name"])
        offset = 0
        if os.path.exists(local_path):
            current_size = os.path.getsize(local_path)
            if current_size <= item["file_size"]:
                offset = current_size
            else:
                with open(local_path, "wb") as file_obj:
                    file_obj.truncate(0)
                offset = 0
        else:
            with open(local_path, "wb") as file_obj:
                file_obj.truncate(0)
        item["local_path"] = local_path
        item["downloaded_size"] = offset
        item["download_status"] = "downloading"
        self.pending_offers[file_id] = item
        self.active_downloads[file_id] = {
            "chat_target": item["chat_target"],
            "local_path": local_path,
            "file_size": item["file_size"],
            "offset": offset,
        }
        self.request_file_chunk(file_id, offset)
        self.set_status(f"Starting file download: {item['file_name']}")
        self.refresh_chat_view()
        self.save_local_data()

    def request_file_chunk(self, file_id, offset):
        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["FILE_REQUEST"],
                "data": {"username": self.username, "file_id": file_id, "offset": offset},
            }
        )

    def handle_file_chunk(self, file_id, offset, chunk_b64, is_end):
        if not file_id or chunk_b64 is None:
            return
        item = self.file_items.get(file_id)
        state = self.active_downloads.get(file_id)
        if not item or not state:
            return
        try:
            chunk_data = base64.b64decode(chunk_b64)
            local_path = state["local_path"]
            file_mode = "r+b" if os.path.exists(local_path) else "wb"
            with open(local_path, file_mode) as file_obj:
                file_obj.seek(offset)
                file_obj.write(chunk_data)
            next_offset = offset + len(chunk_data)
            item["downloaded_size"] = next_offset
            item["local_path"] = local_path
            if is_end:
                self.update_file_status(file_id, "done", local_path=local_path)
                self.set_status(f"File download completed: {item['file_name']}")
            else:
                item["download_status"] = "downloading"
                state["offset"] = next_offset
                self.save_local_data()
                self.request_file_chunk(file_id, next_offset)
                if item.get("chat_target") == self.current_chat:
                    self.refresh_chat_view()
        except Exception as exc:
            print(f"Failed to save file chunk: {exc}")
            self.update_file_status(file_id, "failed")
            self.set_status("Failed to save the file.", is_error=True)

    def format_file_size(self, size):
        size = float(size or 0)
        units = ["B", "KB", "MB", "GB"]
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return "0 B"

    def resolve_download_path(self, file_name):
        os.makedirs(self.DOWNLOAD_PATH, exist_ok=True)
        base_name, extension = os.path.splitext(file_name)
        candidate = os.path.join(self.DOWNLOAD_PATH, file_name)
        if not os.path.exists(candidate):
            return candidate
        counter = 1
        while True:
            candidate = os.path.join(self.DOWNLOAD_PATH, f"{base_name}_{counter}{extension}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1
