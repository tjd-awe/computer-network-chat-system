"""Tkinter UI helpers for the chat client."""

import os
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

from common.protocol import MESSAGE_TYPES, STATUS


class ClientUiMixin:
    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.root.geometry("1120x760")
        self.root.minsize(980, 680)
        self.root.configure(bg=self.COLORS["bg"])

        self.login_frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self._build_login_card()

        self.chat_frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        self._build_sidebar()
        self._build_chat_area()
        self._build_status_bar()

        self.switch_tab("users")
        self.update_message_input_state()

    def _build_login_card(self):
        login_card = tk.Frame(
            self.login_frame,
            bg=self.COLORS["panel"],
            bd=1,
            relief=tk.SOLID,
            padx=28,
            pady=28,
        )
        login_card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(
            login_card,
            text="LAN Chat Client",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Microsoft YaHei UI", 18, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 18), sticky="w")

        tk.Label(
            login_card,
            text="Username",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.username_entry = tk.Entry(login_card, width=30, font=("Microsoft YaHei UI", 11), relief=tk.FLAT)
        self.username_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14), ipady=8)

        tk.Label(
            login_card,
            text="Password",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 10),
        ).grid(row=3, column=0, sticky="w", pady=(0, 6))
        self.password_entry = tk.Entry(
            login_card,
            width=30,
            show="*",
            font=("Microsoft YaHei UI", 11),
            relief=tk.FLAT,
        )
        self.password_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 18), ipady=8)
        self.password_entry.bind("<Return>", self.send_login)

        self.login_button = tk.Button(
            login_card,
            text="Sign in",
            command=self.login,
            bg=self.COLORS["primary"],
            fg="white",
            activebackground=self.COLORS["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=18,
            pady=8,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )
        self.login_button.grid(row=5, column=0, sticky="ew", padx=(0, 8))

        self.register_button = tk.Button(
            login_card,
            text="Register",
            command=self.register,
            bg=self.COLORS["success"],
            fg="white",
            activebackground="#0b5f58",
            activeforeground="white",
            relief=tk.FLAT,
            padx=18,
            pady=8,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )
        self.register_button.grid(row=5, column=1, sticky="ew")

        login_card.grid_columnconfigure(0, weight=1)
        login_card.grid_columnconfigure(1, weight=1)

    def _build_sidebar(self):
        self.sidebar = tk.Frame(
            self.chat_frame,
            width=300,
            bg=self.COLORS["panel_alt"],
            bd=1,
            relief=tk.SOLID,
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 10), pady=16)
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="Conversations",
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(anchor="w", padx=14, pady=(14, 10))

        self.tab_frame = tk.Frame(self.sidebar, bg=self.COLORS["panel_alt"])
        self.tab_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        self.user_tab = tk.Button(
            self.tab_frame,
            text="Users",
            command=lambda: self.switch_tab("users"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.user_tab.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.group_tab = tk.Button(
            self.tab_frame,
            text="Groups",
            command=lambda: self.switch_tab("groups"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.group_tab.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.sidebar_content = tk.Frame(self.sidebar, bg=self.COLORS["panel_alt"])
        self.sidebar_content.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.user_panel = tk.Frame(self.sidebar_content, bg=self.COLORS["panel_alt"])
        self.group_panel = tk.Frame(self.sidebar_content, bg=self.COLORS["panel_alt"])

        self.user_search_var = tk.StringVar()
        self.user_search_var.trace_add("write", lambda *_: self.refresh_user_list())
        self.group_search_var = tk.StringVar()
        self.group_search_var.trace_add("write", lambda *_: self.refresh_group_lists())

        self._build_user_panel()
        self._build_group_panel()

    def _build_user_panel(self):
        user_search_entry = tk.Entry(
            self.user_panel,
            textvariable=self.user_search_var,
            font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        )
        user_search_entry.pack(fill=tk.X, pady=(0, 10), ipady=7)

        self.user_list = tk.Listbox(self.user_panel, **self._listbox_style())
        self.user_list.pack(fill=tk.BOTH, expand=True)
        self.user_list.bind("<<ListboxSelect>>", self.on_user_select)

    def _build_group_panel(self):
        group_top_row = tk.Frame(self.group_panel, bg=self.COLORS["panel_alt"])
        group_top_row.pack(fill=tk.X, pady=(0, 10))

        self.group_search_entry = tk.Entry(
            group_top_row,
            textvariable=self.group_search_var,
            font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        )
        self.group_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7)

        self.create_group_button = tk.Button(
            group_top_row,
            text="Create group",
            command=self.create_group,
            bg=self.COLORS["success"],
            fg="white",
            activebackground="#0b5f58",
            activeforeground="white",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.create_group_button.pack(side=tk.RIGHT, padx=(8, 0))

        tk.Label(
            self.group_panel,
            text="My groups",
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self.joined_group_list = tk.Listbox(self.group_panel, height=8, **self._listbox_style())
        self.joined_group_list.pack(fill=tk.BOTH, expand=True)
        self.joined_group_list.bind("<<ListboxSelect>>", self.on_joined_group_select)

        tk.Label(
            self.group_panel,
            text="Discover groups",
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w", pady=(12, 6))
        self.discover_group_list = tk.Listbox(self.group_panel, height=8, **self._listbox_style())
        self.discover_group_list.pack(fill=tk.BOTH, expand=True)
        self.discover_group_list.bind("<<ListboxSelect>>", self.on_discover_group_select)

    def _build_chat_area(self):
        self.chat_area_frame = tk.Frame(
            self.chat_frame,
            bg=self.COLORS["panel"],
            bd=1,
            relief=tk.SOLID,
        )
        self.chat_area_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 16), pady=16)
        self.chat_area_frame.pack_propagate(False)

        self.top_panel = tk.Frame(self.chat_area_frame, bg=self.COLORS["panel"])
        self.top_panel.pack(side=tk.TOP, fill=tk.X)

        self.composer_panel = tk.Frame(self.chat_area_frame, bg=self.COLORS["panel"])
        self.composer_panel.pack(side=tk.BOTTOM, fill=tk.X)

        self.history_panel = tk.Frame(self.chat_area_frame, bg=self.COLORS["panel"])
        self.history_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._build_session_header()
        self._build_group_detail_card()
        self._build_history_panel()
        self._build_composer_panel()

    def _build_session_header(self):
        self.chat_header = tk.Frame(self.top_panel, bg=self.COLORS["panel"], padx=18, pady=14)
        self.chat_header.pack(fill=tk.X)

        self.session_title_var = tk.StringVar(value="Choose a user or group")
        self.session_subtitle_var = tk.StringVar(value="Sign in to chat, search users, or browse groups.")

        tk.Label(
            self.chat_header,
            textvariable=self.session_title_var,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.chat_header,
            textvariable=self.session_subtitle_var,
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(4, 0))

    def _build_group_detail_card(self):
        self.group_detail_frame = tk.Frame(
            self.top_panel,
            bg=self.COLORS["panel_soft"],
            bd=1,
            relief=tk.SOLID,
            padx=14,
            pady=10,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )

        detail_top = tk.Frame(self.group_detail_frame, bg=self.COLORS["panel_soft"])
        detail_top.pack(fill=tk.X)

        self.group_detail_title_var = tk.StringVar(value="")
        self.group_detail_meta_var = tk.StringVar(value="")

        tk.Label(
            detail_top,
            textvariable=self.group_detail_title_var,
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            detail_top,
            textvariable=self.group_detail_meta_var,
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(3, 0))

        self.group_action_frame = tk.Frame(self.group_detail_frame, bg=self.COLORS["panel_soft"])
        self.group_action_frame.pack(fill=tk.X, pady=(10, 8))

        self.join_selected_group_button = tk.Button(
            self.group_action_frame,
            text="Join group",
            command=self.join_selected_group,
            bg=self.COLORS["primary"],
            fg="white",
            activebackground=self.COLORS["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.add_member_button = tk.Button(
            self.group_action_frame,
            text="Add member",
            command=self.add_group_member,
            bg=self.COLORS["success"],
            fg="white",
            activebackground="#0b5f58",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.leave_selected_group_button = tk.Button(
            self.group_action_frame,
            text="Leave group",
            command=self.leave_selected_group,
            bg=self.COLORS["warning"],
            fg="white",
            activebackground="#92400e",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )

        tk.Label(
            self.group_detail_frame,
            text="Members",
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w")
        self.group_members_list = tk.Listbox(
            self.group_detail_frame,
            height=4,
            font=("Microsoft YaHei UI", 9),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
            selectbackground="#d9ecff",
            selectforeground=self.COLORS["text"],
        )
        self.group_members_list.pack(fill=tk.X, pady=(6, 0))

    def _build_history_panel(self):
        self.chat_text = scrolledtext.ScrolledText(
            self.history_panel,
            wrap=tk.WORD,
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["text"],
            relief=tk.FLAT,
            padx=18,
            pady=14,
            font=("Microsoft YaHei UI", 10),
            insertbackground=self.COLORS["primary"],
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.chat_text.config(state=tk.DISABLED)
        self.configure_chat_tags()

    def _build_composer_panel(self):
        self.message_frame = tk.Frame(
            self.composer_panel,
            bg=self.COLORS["panel_soft"],
            bd=1,
            relief=tk.SOLID,
            padx=12,
            pady=10,
        )
        self.message_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.message_frame.configure(highlightbackground=self.COLORS["border"], highlightthickness=1)

        tk.Label(
            self.message_frame,
            text="Message input",
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        self.message_input_row = tk.Frame(self.message_frame, bg=self.COLORS["panel_soft"])
        self.message_input_row.pack(fill=tk.X)

        self.file_button = tk.Button(
            self.message_input_row,
            text="Send file",
            command=self.send_file,
            bg="#eaf3ff",
            fg=self.COLORS["primary_dark"],
            activebackground="#dbeaff",
            activeforeground=self.COLORS["primary_dark"],
            relief=tk.FLAT,
            padx=12,
            pady=8,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        )
        self.file_button.pack(side=tk.RIGHT, padx=(8, 0))

        self.send_button = tk.Button(
            self.message_input_row,
            text="Send",
            command=self.send_message,
            bg=self.COLORS["primary"],
            fg="white",
            activebackground=self.COLORS["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=18,
            pady=8,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )
        self.send_button.pack(side=tk.RIGHT)

        self.message_entry = tk.Entry(
            self.message_input_row,
            font=("Microsoft YaHei UI", 11),
            relief=tk.SOLID,
            bd=1,
            bg="#ffffff",
            fg=self.COLORS["text"],
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["primary"],
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=9)
        self.message_entry.bind("<Return>", self.send_message)

        self.message_hint_var = tk.StringVar(value="Choose a user or joined group before typing a message.")
        self.message_hint_label = tk.Label(
            self.message_frame,
            textvariable=self.message_hint_var,
            bg=self.COLORS["panel_soft"],
            fg=self.COLORS["light_text"],
            font=("Microsoft YaHei UI", 8),
        )
        self.message_hint_label.pack(anchor="w", pady=(8, 0))

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bd=0,
            relief=tk.FLAT,
            anchor=tk.W,
            bg="#eef4ff",
            fg=self.COLORS["primary_dark"],
            padx=16,
            pady=7,
            font=("Microsoft YaHei UI", 9),
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _listbox_style(self):
        return {
            "font": ("Microsoft YaHei UI", 10),
            "bg": self.COLORS["panel"],
            "fg": self.COLORS["text"],
            "selectbackground": "#d9ecff",
            "selectforeground": self.COLORS["text"],
            "relief": tk.FLAT,
            "highlightthickness": 0,
            "bd": 0,
        }

    def configure_chat_tags(self):
        self.chat_text.tag_config("hint", foreground=self.COLORS["light_text"], font=("Microsoft YaHei UI", 10))
        self.chat_text.tag_config("my_header", foreground=self.COLORS["primary_dark"], font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_config("my_body", foreground=self.COLORS["text"], font=("Microsoft YaHei UI", 10))
        self.chat_text.tag_config("other_header", foreground=self.COLORS["muted"], font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_config("other_body", foreground=self.COLORS["text"], font=("Microsoft YaHei UI", 10))
        self.chat_text.tag_config("ai_header", foreground="#7c3aed", font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_config("system_header", foreground=self.COLORS["muted"], font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_config("system_body", foreground=self.COLORS["muted"], font=("Microsoft YaHei UI", 9, "italic"))
        self.chat_text.tag_config("recall_body", foreground=self.COLORS["warning"], font=("Microsoft YaHei UI", 9, "italic"))
        self.chat_text.tag_config("file_header", foreground=self.COLORS["muted"], font=("Microsoft YaHei UI", 9, "bold"))
        self.chat_text.tag_config("file_name", foreground=self.COLORS["text"], font=("Microsoft YaHei UI", 10, "bold"))
        self.chat_text.tag_config("file_meta", foreground=self.COLORS["muted"], font=("Microsoft YaHei UI", 9))
        self.chat_text.tag_config("file_action", foreground=self.COLORS["primary"], font=("Microsoft YaHei UI", 9, "underline"))
        self.chat_text.tag_config("legacy_text", foreground=self.COLORS["text"], font=("Microsoft YaHei UI", 10))

    def update_user_directory(self, users):
        normalized = []
        for user in users:
            if not isinstance(user, dict):
                continue
            normalized.append(
                {
                    "username": user.get("username", ""),
                    "status": user.get("status", STATUS["OFFLINE"]),
                    "is_self": bool(user.get("is_self", False)),
                }
            )
        normalized.sort(key=lambda item: item["username"])
        self.all_users = normalized
        self.refresh_user_list()

    def update_group_catalog(self, groups, preserve_selection=True):
        previous_selection = self.selected_group_name if preserve_selection else None
        normalized = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            normalized.append(
                {
                    "group_name": group.get("group_name", ""),
                    "member_count": int(group.get("member_count", 0)),
                    "joined": bool(group.get("joined", False)),
                    "creator": group.get("creator", ""),
                }
            )
        normalized.sort(key=lambda item: item["group_name"])
        self.all_groups = normalized
        self.joined_groups = [item["group_name"] for item in normalized if item.get("joined")]

        if previous_selection and self.get_group_info(previous_selection):
            self.selected_group_name = previous_selection
            self.selected_group_joined = bool(self.get_group_info(previous_selection).get("joined"))
        elif self.selected_group_name and not self.get_group_info(self.selected_group_name):
            self.unread_counts.pop(self.selected_group_name, None)
            if self.current_chat == self.selected_group_name:
                self.current_chat = None
                self.is_group_chat = False
            self.selected_group_name = None
            self.selected_group_joined = False

        if self.current_chat and self.is_group_chat and self.current_chat not in self.joined_groups:
            self.current_chat = None
            self.is_group_chat = False

        self.refresh_group_lists()
        self.refresh_group_detail()
        self.refresh_session_header()
        self.refresh_chat_view()
        self.save_local_data()

    def refresh_user_list(self):
        keyword = self.user_search_var.get().strip().lower()
        self.user_list_map = []
        self.user_list.delete(0, tk.END)
        selected_index = None
        for user in self.all_users:
            username = user.get("username")
            if not username or user.get("is_self"):
                continue
            if keyword and keyword not in username.lower():
                continue
            label = self.build_user_list_label(user)
            self.user_list.insert(tk.END, label)
            self.user_list_map.append(username)
            row_index = len(self.user_list_map) - 1
            self.apply_unread_style(self.user_list, row_index, username)
            if self.current_chat == username and not self.is_group_chat:
                selected_index = row_index
        if selected_index is not None:
            self.user_list.selection_clear(0, tk.END)
            self.user_list.selection_set(selected_index)
            self.user_list.activate(selected_index)

    def refresh_group_lists(self):
        keyword = self.group_search_var.get().strip().lower()
        self.joined_group_map = []
        self.discover_group_map = []
        self.joined_group_list.delete(0, tk.END)
        self.discover_group_list.delete(0, tk.END)
        joined_selected_index = None
        discover_selected_index = None

        for group in self.all_groups:
            group_name = group.get("group_name")
            if not group_name:
                continue
            if keyword and keyword not in group_name.lower():
                continue
            label = self.build_group_list_label(group)
            if group.get("joined"):
                self.joined_group_list.insert(tk.END, label)
                self.joined_group_map.append(group_name)
                row_index = len(self.joined_group_map) - 1
                self.apply_unread_style(self.joined_group_list, row_index, group_name)
                if self.current_chat == group_name and self.is_group_chat:
                    joined_selected_index = row_index
            else:
                self.discover_group_list.insert(tk.END, label)
                self.discover_group_map.append(group_name)
                row_index = len(self.discover_group_map) - 1
                self.apply_unread_style(self.discover_group_list, row_index, group_name)
                if self.selected_group_name == group_name and not self.selected_group_joined:
                    discover_selected_index = row_index
        if joined_selected_index is not None:
            self.joined_group_list.selection_clear(0, tk.END)
            self.joined_group_list.selection_set(joined_selected_index)
            self.joined_group_list.activate(joined_selected_index)
        if discover_selected_index is not None:
            self.discover_group_list.selection_clear(0, tk.END)
            self.discover_group_list.selection_set(discover_selected_index)
            self.discover_group_list.activate(discover_selected_index)

    def build_user_list_label(self, user):
        username = user.get("username", "")
        status = "Online" if user.get("status") == STATUS["ONLINE"] else "Offline"
        suffix = "  *" if self.unread_counts.get(username, 0) > 0 else ""
        return f"{username} ({status}){suffix}"

    def build_group_list_label(self, group):
        group_name = group.get("group_name", "")
        member_count = group.get("member_count", 0)
        suffix = "  *" if self.unread_counts.get(group_name, 0) > 0 else ""
        return f"{group_name} ({member_count} members){suffix}"

    def apply_unread_style(self, listbox, index, chat_target):
        try:
            if self.unread_counts.get(chat_target, 0) > 0:
                listbox.itemconfig(index, foreground=self.COLORS["notification"])
            else:
                listbox.itemconfig(index, foreground=self.COLORS["text"])
        except tk.TclError:
            pass

    def switch_tab(self, tab):
        self.user_panel.pack_forget()
        self.group_panel.pack_forget()
        if tab == "users":
            self.user_panel.pack(fill=tk.BOTH, expand=True)
            self.current_list = "users"
        else:
            self.group_panel.pack(fill=tk.BOTH, expand=True)
            self.current_list = "groups"
        self.update_tab_styles()

    def update_tab_styles(self):
        active = {
            "bg": "#e9f3ff",
            "fg": self.COLORS["primary_dark"],
            "activebackground": "#d8ebff",
            "activeforeground": self.COLORS["primary_dark"],
        }
        inactive = {
            "bg": "#eef0f4",
            "fg": self.COLORS["muted"],
            "activebackground": "#e5e7ec",
            "activeforeground": self.COLORS["text"],
        }
        self.user_tab.configure(**(active if self.current_list == "users" else inactive))
        self.group_tab.configure(**(active if self.current_list == "groups" else inactive))

    def on_user_select(self, event):
        selection = self.user_list.curselection()
        if not selection:
            return
        username = self.user_list_map[selection[0]]
        self.clear_unread(username)
        self.current_chat = username
        self.is_group_chat = False
        self.selected_group_name = None
        self.selected_group_joined = False
        self.refresh_group_detail()
        self.refresh_session_header()
        self.refresh_chat_view()

    def on_joined_group_select(self, event):
        selection = self.joined_group_list.curselection()
        if not selection:
            return
        group_name = self.joined_group_map[selection[0]]
        self.select_group(group_name, joined=True)

    def on_discover_group_select(self, event):
        selection = self.discover_group_list.curselection()
        if not selection:
            return
        group_name = self.discover_group_map[selection[0]]
        self.select_group(group_name, joined=False)

    def select_group(self, group_name, joined):
        self.selected_group_name = group_name
        self.selected_group_joined = joined
        if joined:
            self.clear_unread(group_name)
            self.current_chat = group_name
            self.is_group_chat = True
        else:
            self.current_chat = None
            self.is_group_chat = False
        self.request_group_members(group_name)
        self.refresh_group_detail()
        self.refresh_session_header()
        self.refresh_chat_view()

    def request_group_members(self, group_name):
        if not self.is_connected or not self.username or not group_name:
            return
        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["GET_GROUP_MEMBERS"],
                "data": {"group_name": group_name, "username": self.username},
            }
        )

    def handle_group_members(self, data):
        group_name = data.get("group_name")
        members = data.get("members", [])
        if not group_name:
            return
        self.group_members_cache[group_name] = members
        if self.selected_group_name == group_name:
            self.refresh_group_detail()

    def handle_group_history_sync(self, data):
        group_name = data.get("group_name")
        history = data.get("history", [])
        if not group_name:
            return
        # Historical replay after join should not become unread noise.
        for message in history:
            item = self.normalize_server_message(message)
            if item:
                self.append_history_item(item, dedupe=True, refresh=False, save=False)
        if self.selected_group_name == group_name and self.selected_group_joined:
            self.current_chat = group_name
            self.is_group_chat = True
        self.refresh_session_header()
        self.refresh_chat_view()
        self.save_local_data()

    def refresh_group_detail(self):
        for widget in self.group_action_frame.winfo_children():
            widget.pack_forget()

        self.group_members_list.delete(0, tk.END)
        should_show = bool(self.selected_group_name)
        if not should_show:
            self.group_detail_frame.pack_forget()
            return

        if not self.group_detail_frame.winfo_ismapped():
            self.group_detail_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        group_info = self.get_group_info(self.selected_group_name) or {}
        member_count = group_info.get("member_count", 0)
        creator = group_info.get("creator") or "Unknown"
        self.selected_group_joined = bool(group_info.get("joined", self.selected_group_joined))

        self.group_detail_title_var.set(self.selected_group_name)
        button_state = tk.NORMAL if self.is_connected else tk.DISABLED
        if self.selected_group_joined:
            self.group_detail_meta_var.set(f"Joined - {member_count} members - Owner {creator}")
            self.add_member_button.configure(state=button_state)
            self.leave_selected_group_button.configure(state=button_state)
            self.add_member_button.pack(side=tk.LEFT)
            self.leave_selected_group_button.pack(side=tk.LEFT, padx=(8, 0))
        else:
            self.group_detail_meta_var.set(f"Not joined - {member_count} members - Owner {creator}")
            self.join_selected_group_button.configure(state=button_state)
            self.join_selected_group_button.pack(side=tk.LEFT)

        members = self.group_members_cache.get(self.selected_group_name, [])
        if members:
            for member in members:
                if isinstance(member, dict):
                    label = f"{member.get('username', '')} ({'Online' if member.get('status') == STATUS['ONLINE'] else 'Offline'})"
                else:
                    label = str(member)
                self.group_members_list.insert(tk.END, label)
        else:
            self.group_members_list.insert(tk.END, "Loading member list...")

    def refresh_session_header(self):
        if not self.username:
            self.session_title_var.set("Choose a user or group")
            self.session_subtitle_var.set("Sign in to chat, search users, or browse groups.")
            self.update_message_input_state()
            return
        if self.is_reconnecting or not self.is_connected:
            title = self.current_chat or self.selected_group_name or f"Welcome, {self.username}"
            self.session_title_var.set(title)
            self.session_subtitle_var.set("The server connection was lost. Reconnecting automatically and restoring the current conversation.")
            self.update_message_input_state()
            return
        if self.current_chat and not self.is_group_chat:
            self.session_title_var.set(self.current_chat)
            self.session_subtitle_var.set("Direct chat - Search all registered users, including offline users.")
            self.update_message_input_state()
            return
        if self.current_chat and self.is_group_chat:
            self.session_title_var.set(self.current_chat)
            self.session_subtitle_var.set("Group chat - Server-side group history has been synchronized.")
            self.update_message_input_state()
            return
        if self.selected_group_name:
            self.session_title_var.set(self.selected_group_name)
            self.session_subtitle_var.set("Not joined - Join the group to view the full server-side history immediately.")
            self.update_message_input_state()
            return
        self.session_title_var.set(f"Welcome, {self.username}")
        self.session_subtitle_var.set("Use the left panel to search users or groups, then start a conversation.")
        self.update_message_input_state()

    def refresh_chat_view(self):
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.clear_action_tags()

        if self.username and (self.is_reconnecting or not self.is_connected):
            self.chat_text.insert(tk.END, "The server connection was lost. The client is reconnecting automatically.\n", "system_header")
            self.chat_text.insert(tk.END, "After reconnection, the client will sign in again and refresh users, groups, and chat history.\n\n", "system_body")

        if self.selected_group_name and not self.selected_group_joined:
            self.chat_text.insert(tk.END, "Join the group to view the full server-side group history immediately.\n", "hint")
            self.chat_text.config(state=tk.DISABLED)
            return

        if not self.current_chat:
            self.chat_text.insert(tk.END, "Choose a user or group to start chatting.\n", "hint")
            self.chat_text.config(state=tk.DISABLED)
            return

        history = self.chat_history.get(self.current_chat, [])
        if not history:
            self.chat_text.insert(tk.END, "No messages yet in this conversation. Send the first one.\n", "hint")
            self.chat_text.config(state=tk.DISABLED)
            return

        for item in history:
            self.render_history_item(item)

        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def handle_group_created(self, data):
        if data.get("success"):
            group_name = data.get("group_name")
            self.selected_group_name = group_name
            self.selected_group_joined = True
            self.current_chat = group_name
            self.is_group_chat = True
            self.request_group_members(group_name)
            messagebox.showinfo("Success", f"Group {group_name} was created successfully")
            self.set_status(f"Created group: {group_name}")
            self.refresh_session_header()
            self.refresh_group_detail()
            self.refresh_chat_view()
        else:
            messagebox.showerror("Error", data.get("message", "Failed to create group"))

    def handle_group_joined(self, data):
        if data.get("success"):
            group_name = data.get("group_name")
            self.selected_group_name = group_name
            self.selected_group_joined = True
            self.current_chat = group_name
            self.is_group_chat = True
            self.request_group_members(group_name)
            messagebox.showinfo("Success", f"Joined group {group_name} successfully")
            self.set_status(f"Joined group: {group_name}")
            self.refresh_session_header()
        else:
            messagebox.showerror("Error", data.get("message", "Failed to join group"))

    def handle_group_left(self, data):
        if data.get("success"):
            group_name = data.get("group_name")
            messagebox.showinfo("Success", f"Left group {group_name} successfully")
            self.unread_counts.pop(group_name, None)
            if self.current_chat == group_name:
                self.current_chat = None
                self.is_group_chat = False
            if self.selected_group_name == group_name:
                self.selected_group_name = group_name
                self.selected_group_joined = False
            self.group_members_cache.pop(group_name, None)
            self.set_status(f"Left group: {group_name}")
            self.refresh_group_detail()
            self.refresh_session_header()
            self.refresh_chat_view()
        else:
            messagebox.showerror("Error", data.get("message", "Failed to leave group"))

    def handle_group_member_added(self, data):
        if not data.get("success"):
            messagebox.showerror("Error", data.get("message", "Failed to add group member"))
            return
        group_name = data.get("group_name")
        operator = data.get("operator")
        target_user = data.get("target_user")
        if target_user == self.username:
            self.selected_group_name = group_name
            self.selected_group_joined = True
            self.current_chat = group_name
            self.is_group_chat = True
            self.set_status(f"{operator} added you to group {group_name}")
        elif operator == self.username:
            self.set_status(f"Added {target_user} to group {group_name}")
            messagebox.showinfo("Success", f"Added {target_user} to group {group_name}")
        else:
            self.set_status(f"{operator} added {target_user} to group {group_name}")
        self.request_group_members(group_name)
        self.refresh_group_detail()
        self.refresh_session_header()

    def join_selected_group(self):
        if not self.selected_group_name:
            messagebox.showwarning("Warning", "Please select a group first.")
            return
        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["JOIN_GROUP"],
                "data": {"group_name": self.selected_group_name, "username": self.username},
            }
        )

    def leave_selected_group(self):
        target = self.selected_group_name or (self.current_chat if self.is_group_chat else None)
        if not target:
            messagebox.showwarning("Warning", "Please select a joined group first.")
            return
        self.send_message_to_server(
            {
                "type": MESSAGE_TYPES["LEAVE_GROUP"],
                "data": {"group_name": target, "username": self.username},
            }
        )

    def add_group_member(self):
        if not self.selected_group_name or not self.selected_group_joined:
            messagebox.showwarning("Warning", "Please select a joined group first.")
            return
        members = {item.get("username") for item in self.group_members_cache.get(self.selected_group_name, []) if isinstance(item, dict)}
        candidates = [user for user in self.all_users if not user.get("is_self") and user.get("username") not in members]
        if not candidates:
            messagebox.showinfo("Notice", "No new members are available to add.")
            return
        self.open_user_picker(candidates)

    def open_user_picker(self, candidates):
        window = tk.Toplevel(self.root)
        window.title(f"Add members to {self.selected_group_name}")
        window.geometry("360x420")
        window.configure(bg=self.COLORS["panel"])
        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text="Search and choose a user to add to the group",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 10))

        search_var = tk.StringVar()
        search_entry = tk.Entry(window, textvariable=search_var, font=("Microsoft YaHei UI", 10), relief=tk.FLAT)
        search_entry.pack(fill=tk.X, padx=16, pady=(0, 12), ipady=7)

        listbox = tk.Listbox(
            window,
            font=("Microsoft YaHei UI", 10),
            bg="#fbfdff",
            fg=self.COLORS["text"],
            selectbackground=self.COLORS["primary"],
            selectforeground="white",
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        candidate_map = []

        def refresh_candidates(*_):
            keyword = search_var.get().strip().lower()
            candidate_map.clear()
            listbox.delete(0, tk.END)
            filtered = [user for user in candidates if not keyword or keyword in user.get("username", "").lower()]
            filtered.sort(key=lambda item: item.get("username", ""))
            for user in filtered:
                label = f"{user.get('username')} ({'Online' if user.get('status') == STATUS['ONLINE'] else 'Offline'})"
                listbox.insert(tk.END, label)
                candidate_map.append(user.get("username"))

        def confirm_add():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please choose a user.", parent=window)
                return
            target_user = candidate_map[selection[0]]
            self.send_message_to_server(
                {
                    "type": MESSAGE_TYPES["ADD_GROUP_MEMBER"],
                    "data": {
                        "group_name": self.selected_group_name,
                        "operator": self.username,
                        "target_user": target_user,
                    },
                }
            )
            window.destroy()

        search_var.trace_add("write", refresh_candidates)
        refresh_candidates()

        button_row = tk.Frame(window, bg=self.COLORS["panel"])
        button_row.pack(fill=tk.X, padx=16, pady=(0, 16))
        tk.Button(
            button_row,
            text="Cancel",
            command=window.destroy,
            bg="#e2e8f0",
            fg=self.COLORS["text"],
            relief=tk.FLAT,
            padx=12,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT)
        tk.Button(
            button_row,
            text="Add",
            command=confirm_add,
            bg=self.COLORS["primary"],
            fg="white",
            activebackground=self.COLORS["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(0, 8))

        search_entry.focus_set()

    def get_group_info(self, group_name):
        for group in self.all_groups:
            if group.get("group_name") == group_name:
                return group
        return None

    def create_group(self):
        if not self.is_connected:
            self.set_status("The server connection was lost. Reconnecting automatically...", is_error=True)
            return
        group_name = simpledialog.askstring("Create Group", "Enter the group name:")
        if group_name:
            self.send_message_to_server(
                {
                    "type": MESSAGE_TYPES["CREATE_GROUP"],
                    "data": {"group_name": group_name, "creator": self.username},
                }
            )

    def update_message_input_state(self):
        if not hasattr(self, "message_entry"):
            return

        can_chat = bool(self.current_chat) and self.is_connected and not self.is_reconnecting
        if hasattr(self, "create_group_button"):
            self.create_group_button.configure(state=tk.NORMAL if self.is_connected else tk.DISABLED)
        if can_chat:
            self.message_entry.configure(state=tk.NORMAL, disabledbackground="#ffffff", disabledforeground=self.COLORS["muted"])
            self.send_button.configure(state=tk.NORMAL)
            self.file_button.configure(state=tk.NORMAL)
            self.message_hint_var.set("Press Enter to send a message, or use the button on the right to send a file.")
        else:
            self.message_entry.configure(state=tk.DISABLED, disabledbackground="#f1f2f6", disabledforeground=self.COLORS["muted"])
            self.send_button.configure(state=tk.DISABLED)
            self.file_button.configure(state=tk.DISABLED)
            if not self.is_connected or self.is_reconnecting:
                self.message_hint_var.set("The server connection was lost. Reconnecting automatically so you can continue sending messages afterwards.")
            elif self.selected_group_name and not self.selected_group_joined:
                self.message_hint_var.set("You must join this group before sending messages.")
            else:
                self.message_hint_var.set("Choose a user or joined group before typing a message.")

    def clear_action_tags(self):
        for tag_name in self.action_tags:
            try:
                self.chat_text.tag_delete(tag_name)
            except tk.TclError:
                pass
        self.action_tags.clear()

    def render_history_item(self, item):
        kind = item.get("kind")
        if kind == "file":
            self.render_file_item(item)
        elif kind == "legacy_text":
            self.render_legacy_item(item)
        else:
            self.render_text_item(item)

    def render_text_item(self, item):
        sender = item.get("sender") or "System"
        content = item.get("content", "")
        time_str = self.format_time(item.get("timestamp"))
        recalled = item.get("recalled", False)
        if recalled:
            self.chat_text.insert(tk.END, f"[{time_str}] Message status\n", "system_header")
            self.chat_text.insert(tk.END, "[Message recalled]\n\n", "recall_body")
            return
        if sender == self.username:
            self.chat_text.insert(tk.END, f"[{time_str}] Me\n", "my_header")
            self.chat_text.insert(tk.END, f"{content}\n\n", "my_body")
            return
        if sender == "AI Assistant":
            self.chat_text.insert(tk.END, f"[{time_str}] AI Assistant\n", "ai_header")
            self.chat_text.insert(tk.END, f"{content}\n\n", "other_body")
            return
        if sender == "System":
            self.chat_text.insert(tk.END, f"[{time_str}] System message\n", "system_header")
            self.chat_text.insert(tk.END, f"{content}\n\n", "system_body")
            return
        self.chat_text.insert(tk.END, f"[{time_str}] {sender}\n", "other_header")
        self.chat_text.insert(tk.END, f"{content}\n\n", "other_body")

    def render_legacy_item(self, item):
        raw_text = item.get("raw", "")
        tag = "legacy_text"
        if "AI:" in raw_text:
            tag = "other_body"
        elif "[Message recalled]" in raw_text:
            tag = "recall_body"
        elif "System:" in raw_text:
            tag = "system_body"
        elif "Me:" in raw_text:
            tag = "my_body"
        self.chat_text.insert(tk.END, raw_text, tag)
        if not raw_text.endswith("\n"):
            self.chat_text.insert(tk.END, "\n", tag)

    def render_file_item(self, item):
        sender_label = "Me" if item.get("sender") == self.username else item.get("sender", "Unknown user")
        time_str = self.format_time(item.get("timestamp"))
        status = self.FILE_STATUS_LABELS.get(item.get("download_status"), "Unknown status")
        self.chat_text.insert(tk.END, f"[{time_str}] {sender_label} sent a file\n", "file_header")
        self.chat_text.insert(tk.END, f"{item.get('file_name', 'Untitled file')}\n", "file_name")
        meta_parts = [self.format_file_size(item.get("file_size", 0)), status]
        if item.get("download_status") == "downloading":
            downloaded = item.get("downloaded_size", 0)
            meta_parts.append(f"{self.format_file_size(downloaded)} / {self.format_file_size(item.get('file_size', 0))}")
        self.chat_text.insert(tk.END, " - ".join(meta_parts) + "\n", "file_meta")
        actions = self.get_file_actions(item)
        if actions:
            for index, (label, callback) in enumerate(actions):
                tag_name = self.register_action_tag(callback)
                self.chat_text.insert(tk.END, label, ("file_action", tag_name))
                if index < len(actions) - 1:
                    self.chat_text.insert(tk.END, "   ", "file_meta")
            self.chat_text.insert(tk.END, "\n", "file_meta")
        self.chat_text.insert(tk.END, "\n", "file_meta")

    def get_file_actions(self, item):
        file_id = item.get("file_id")
        local_path = item.get("local_path")
        status = item.get("download_status")
        direction = item.get("direction")
        if direction == "received":
            if status in {"pending", "rejected", "failed"}:
                primary = "Retry" if status == "failed" else "Receive"
                return [
                    (primary, lambda fid=file_id: self.start_file_download(fid)),
                    ("Ignore", lambda fid=file_id: self.reject_file_offer(fid)),
                ]
            if status == "done":
                return [
                    ("Open File", lambda path=local_path: self.open_file(path)),
                    ("Open Folder", lambda path=local_path: self.open_folder(path)),
                ]
            return []
        if local_path:
            return [
                ("Open File", lambda path=local_path: self.open_file(path)),
                ("Open Folder", lambda path=local_path: self.open_folder(path)),
            ]
        return []

    def register_action_tag(self, callback):
        tag_name = f"action_tag_{self.action_tag_index}"
        self.action_tag_index += 1
        self.action_tags.append(tag_name)
        self.chat_text.tag_bind(tag_name, "<Button-1>", lambda event, cb=callback: cb())
        self.chat_text.tag_bind(tag_name, "<Enter>", lambda event: self.chat_text.configure(cursor="hand2"))
        self.chat_text.tag_bind(tag_name, "<Leave>", lambda event: self.chat_text.configure(cursor="xterm"))
        return tag_name

    def open_file(self, path):
        if not path or not os.path.exists(path):
            messagebox.showwarning("Notice", "The file does not exist or the download is not finished yet.")
            return
        try:
            os.startfile(path)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to open file: {exc}")

    def open_folder(self, path):
        if not path:
            messagebox.showwarning("Notice", "The folder does not exist.")
            return
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if not os.path.exists(folder):
            messagebox.showwarning("Notice", "The folder does not exist.")
            return
        try:
            os.startfile(folder)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to open folder: {exc}")

    def format_time(self, timestamp):
        try:
            return time.strftime("%H:%M:%S", time.localtime(float(timestamp or time.time())))
        except Exception:
            return time.strftime("%H:%M:%S", time.localtime(time.time()))

    def set_status(self, message, is_error=False):
        self.status_var.set(message)
        if is_error:
            self.status_bar.configure(bg="#fff2f0", fg=self.COLORS["danger"])
        else:
            self.status_bar.configure(bg="#eef4ff", fg=self.COLORS["primary_dark"])
