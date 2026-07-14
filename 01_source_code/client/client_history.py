"""History and local persistence helpers for the chat client."""

import json
import os
import time


class ClientHistoryMixin:
    def create_text_item(self, sender, chat_target, content, timestamp, is_group=False, message_id=None, recalled=False):
        return {
            "kind": "text",
            "sender": sender or "System",
            "chat_target": chat_target,
            "content": content or "",
            "timestamp": float(timestamp or time.time()),
            "is_group": bool(is_group),
            "message_id": message_id,
            "recalled": bool(recalled),
        }

    def create_file_item(
        self,
        sender,
        chat_target,
        is_group,
        file_name,
        file_size,
        file_id,
        direction,
        download_status,
        local_path=None,
        timestamp=None,
    ):
        return {
            "kind": "file",
            "sender": sender or "System",
            "chat_target": chat_target,
            "timestamp": float(timestamp or time.time()),
            "is_group": bool(is_group),
            "file_name": file_name,
            "file_size": int(file_size or 0),
            "file_id": file_id,
            "direction": direction,
            "download_status": download_status,
            "local_path": local_path,
            "downloaded_size": 0,
        }

    def normalize_server_message(self, message):
        chat_target = self.resolve_chat_target(message)
        if not chat_target:
            return None
        return self.create_text_item(
            sender=message.get("sender") or "System",
            chat_target=chat_target,
            content=message.get("content", ""),
            timestamp=message.get("timestamp", time.time()),
            is_group=message.get("is_group", False),
            message_id=message.get("message_id"),
            recalled=message.get("recalled", False),
        )

    def resolve_chat_target(self, message):
        if not isinstance(message, dict):
            return None
        if message.get("chat_target"):
            return message.get("chat_target")
        sender = message.get("sender")
        receiver = message.get("receiver") or message.get("group_name")
        msg_type = message.get("type")
        is_group = bool(message.get("is_group", False))
        if is_group:
            return receiver
        if msg_type == "sent":
            return receiver
        if msg_type == "received":
            return sender
        if sender == self.username and receiver:
            return receiver
        return sender or receiver

    def merge_server_history(self, history):
        for message in history:
            item = self.normalize_server_message(message)
            if item:
                self.append_history_item(item, dedupe=True, refresh=False, save=False)

    def strip_local_text_history(self):
        # After login, text history should come from the server. Local storage is
        # kept only for file-message UI state and backward compatibility.
        cleaned_history = {}
        for chat_target, items in self.chat_history.items():
            file_items = [item for item in items if isinstance(item, dict) and item.get("kind") == "file"]
            if file_items:
                cleaned_history[chat_target] = file_items
        self.chat_history = cleaned_history
        self.rebuild_file_index()

    def append_history_item(self, item, dedupe=False, refresh=False, save=True, incoming=False):
        chat_target = item.get("chat_target")
        if not chat_target:
            return
        self.chat_history.setdefault(chat_target, [])
        if dedupe:
            signature = self.history_item_signature(item)
            for existing in self.chat_history[chat_target]:
                if self.history_item_signature(existing) == signature:
                    return
        self.chat_history[chat_target].append(item)
        if item.get("kind") == "file" and item.get("file_id"):
            self.file_items[item["file_id"]] = item
        if incoming and chat_target != self.current_chat:
            self.unread_counts[chat_target] = self.unread_counts.get(chat_target, 0) + 1
            self.refresh_conversation_lists()
        if refresh and chat_target == self.current_chat:
            self.refresh_chat_view()
        if save:
            self.save_local_data()

    def refresh_conversation_lists(self):
        self.refresh_user_list()
        self.refresh_group_lists()

    def clear_unread(self, chat_target):
        if not chat_target:
            return
        if chat_target in self.unread_counts:
            del self.unread_counts[chat_target]
            self.refresh_conversation_lists()

    def history_item_signature(self, item):
        if not isinstance(item, dict):
            return ("legacy", str(item))
        if item.get("kind") == "file":
            return ("file", item.get("file_id"), item.get("direction"))
        if item.get("kind") == "legacy_text":
            return ("legacy", item.get("raw", ""))
        if item.get("message_id"):
            return ("text_id", item.get("message_id"), item.get("chat_target"))
        return (
            "text",
            item.get("sender"),
            item.get("chat_target"),
            item.get("content"),
            round(float(item.get("timestamp", 0)), 3),
            bool(item.get("recalled", False)),
        )

    def update_user_status(self, username, status):
        if not username:
            return
        updated = False
        for user in self.all_users:
            if user.get("username") == username:
                user["status"] = status
                updated = True
                break
        if not updated:
            self.all_users.append({"username": username, "status": status, "is_self": username == self.username})
            self.all_users.sort(key=lambda item: item["username"])

        for members in self.group_members_cache.values():
            for member in members:
                if isinstance(member, dict) and member.get("username") == username:
                    member["status"] = status

        self.refresh_user_list()
        if self.selected_group_name:
            self.refresh_group_detail()

    def load_local_data(self):
        os.makedirs(self.LOCAL_DATA_PATH, exist_ok=True)
        self.joined_groups = []
        self.chat_history = {}
        if os.path.exists(self.CHAT_HISTORY_FILE):
            try:
                with open(self.CHAT_HISTORY_FILE, "r", encoding="utf-8") as file_obj:
                    self.chat_history = self.migrate_chat_history(json.load(file_obj))
            except Exception:
                self.chat_history = {}
        self.rebuild_file_index()

    def migrate_chat_history(self, raw_history):
        if not isinstance(raw_history, dict):
            return {}
        migrated = {}
        for chat_target, items in raw_history.items():
            normalized_items = []
            for item in items if isinstance(items, list) else []:
                normalized = self.normalize_local_history_item(item, chat_target)
                if normalized:
                    normalized_items.append(normalized)
            migrated[chat_target] = normalized_items
        return migrated

    def normalize_local_history_item(self, item, chat_target):
        if isinstance(item, str):
            return {"kind": "legacy_text", "chat_target": chat_target, "raw": item}
        if not isinstance(item, dict):
            return None
        kind = item.get("kind")
        if kind == "file":
            local_path = item.get("local_path")
            status = item.get("download_status", "pending")
            if status == "downloading":
                status = "pending"
            if status == "done" and local_path and not os.path.exists(local_path):
                status = "pending"
                local_path = None
            return {
                "kind": "file",
                "sender": item.get("sender") or "System",
                "chat_target": item.get("chat_target") or chat_target,
                "timestamp": float(item.get("timestamp", time.time())),
                "is_group": bool(item.get("is_group", False)),
                "file_name": item.get("file_name") or "Untitled file",
                "file_size": int(item.get("file_size") or 0),
                "file_id": item.get("file_id"),
                "direction": item.get("direction", "received"),
                "download_status": status,
                "local_path": local_path,
                "downloaded_size": int(item.get("downloaded_size") or 0),
            }
        if kind == "text":
            return self.create_text_item(
                sender=item.get("sender") or "System",
                chat_target=item.get("chat_target") or chat_target,
                content=item.get("content", ""),
                timestamp=item.get("timestamp", time.time()),
                is_group=item.get("is_group", False),
                message_id=item.get("message_id"),
                recalled=item.get("recalled", False),
            )
        if kind == "legacy_text":
            return {"kind": "legacy_text", "chat_target": chat_target, "raw": item.get("raw", "")}
        if {"sender", "content"} <= set(item.keys()):
            return self.create_text_item(
                sender=item.get("sender") or "System",
                chat_target=item.get("chat_target") or chat_target,
                content=item.get("content", ""),
                timestamp=item.get("timestamp", time.time()),
                is_group=item.get("is_group", False),
                message_id=item.get("message_id"),
                recalled=item.get("recalled", False),
            )
        return None

    def rebuild_file_index(self):
        self.file_items = {}
        self.pending_offers = {}
        self.active_downloads = {}
        for items in self.chat_history.values():
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("kind") != "file":
                    continue
                file_id = item.get("file_id")
                if not file_id:
                    continue
                self.file_items[file_id] = item
                if item.get("direction") == "received" and item.get("download_status") in {"pending", "rejected", "failed"}:
                    self.pending_offers[file_id] = item

    def save_local_data(self):
        os.makedirs(self.LOCAL_DATA_PATH, exist_ok=True)
        with open(self.CHAT_HISTORY_FILE, "w", encoding="utf-8") as file_obj:
            json.dump(self.chat_history, file_obj, ensure_ascii=False, indent=2)
