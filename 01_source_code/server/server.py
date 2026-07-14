"""Public release docstring."""

# ============================================================
# ============================================================
import socket
import threading
import json
import time
import os
import base64
import sys
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# ============================================================
from common.protocol import MESSAGE_TYPES, STATUS
from common.config import (SERVER_HOST, SERVER_PORT, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT,
                           USER_DATA_PATH, GROUP_DATA_PATH, MESSAGE_HISTORY_PATH,
                           GROUP_MESSAGE_HISTORY_PATH,
                           FILE_CHUNK_SIZE, RECALL_TIME_LIMIT)
from llm_assistant import LLMAssistant
from content_analyzer import ContentAnalyzer
from file_transfer import FileTransfer


class Server:
    """Public release docstring."""

    def __init__(self):
        """Public release docstring."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((SERVER_HOST, SERVER_PORT))
        self.server_socket.listen(50)
        self.server_socket.settimeout(1.0)
        self.running = True
        self.users = {}
        self.groups = {}
        self.message_history = {}
        self.group_message_history = {}
        self.users_lock = threading.Lock()
        self.groups_lock = threading.Lock()
        self.history_lock = threading.Lock()
        self.group_history_lock = threading.Lock()
        self.llm_assistant = LLMAssistant()
        self.content_analyzer = ContentAnalyzer()
        self.file_transfer = FileTransfer()
        self.load_data()
        threading.Thread(target=self.heartbeat_check, daemon=True).start()
        print(f"Server started successfully on port {SERVER_PORT}")

    # ============================================================
    # ============================================================

    def load_data(self):
        """Public release docstring."""
        os.makedirs('data', exist_ok=True)
        if os.path.exists(USER_DATA_PATH):
            try:
                with open(USER_DATA_PATH, 'r', encoding='utf-8') as f:
                    loaded_users = json.load(f)
                    for u, info in loaded_users.items():
                        self.users[u] = {
                            'password': info.get('password', ''),
                            'status': STATUS['OFFLINE'],
                            'conn': None,
                            'last_heartbeat': 0
                        }
            except Exception:
                pass
        if os.path.exists(GROUP_DATA_PATH):
            try:
                with open(GROUP_DATA_PATH, 'r', encoding='utf-8') as f:
                    self.groups = json.load(f)
            except Exception:
                self.groups = {}
        if os.path.exists(MESSAGE_HISTORY_PATH):
            try:
                with open(MESSAGE_HISTORY_PATH, 'r', encoding='utf-8') as f:
                    self.message_history = json.load(f)
            except Exception:
                self.message_history = {}
        if os.path.exists(GROUP_MESSAGE_HISTORY_PATH):
            try:
                with open(GROUP_MESSAGE_HISTORY_PATH, 'r', encoding='utf-8') as f:
                    self.group_message_history = json.load(f)
            except Exception:
                self.group_message_history = {}

    def save_data(self):
        """Public release docstring."""
        users_to_save = {}
        with self.users_lock:
            for u, info in self.users.items():
                users_to_save[u] = {
                    'password': info.get('password', ''),
                    'status': info.get('status', STATUS['OFFLINE'])
                }
        with open(USER_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(users_to_save, f, ensure_ascii=False, indent=2)
        with self.groups_lock:
            with open(GROUP_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.groups, f, ensure_ascii=False, indent=2)
        with self.history_lock:
            with open(MESSAGE_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.message_history, f, ensure_ascii=False, indent=2)
        with self.group_history_lock:
            with open(GROUP_MESSAGE_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.group_message_history, f, ensure_ascii=False, indent=2)

    # ============================================================
    # ============================================================

    def heartbeat_check(self):
        """Public release docstring."""
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)
            now = time.time()
            offline_users = []
            with self.users_lock:
                for u, info in self.users.items():
                    if info.get('status') == STATUS['ONLINE'] and 'last_heartbeat' in info:
                        if now - info['last_heartbeat'] > HEARTBEAT_TIMEOUT:
                            offline_users.append(u)
            for u in offline_users:
                self.set_user_offline(u)

    def set_user_offline(self, username):
        """Public release docstring."""
        with self.users_lock:
            if username in self.users:
                self.users[username]['status'] = STATUS['OFFLINE']
                old_conn = self.users[username].get('conn')
                self.users[username]['conn'] = None
                if old_conn:
                    try:
                        old_conn.close()
                    except Exception:
                        pass
        print(f"User {username} went offline")
        self.broadcast_user_status(username, STATUS['OFFLINE'])
        self.save_data()

    def broadcast_user_status(self, username, status):
        """Public release docstring."""
        msg = {
            'type': MESSAGE_TYPES['USER_STATUS'],
            'data': {'username': username, 'status': status}
        }
        with self.users_lock:
            for u, info in self.users.items():
                if info.get('status') == STATUS['ONLINE'] and info.get('conn'):
                    try:
                        self.send_message(info['conn'], msg)
                    except Exception:
                        pass

    # ============================================================
    # ============================================================

    def handle_client(self, conn, addr):
        """Public release docstring."""
        username = None
        buffer = b''
        try:
            print(f"New client connected: {addr}")
            conn.settimeout(HEARTBEAT_TIMEOUT * 2)

            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while len(buffer) >= 4:
                        msg_len = int.from_bytes(buffer[:4], byteorder='big')
                        if len(buffer) >= 4 + msg_len:
                            msg_data = buffer[4:4+msg_len]
                            buffer = buffer[4+msg_len:]
                            try:
                                message = json.loads(msg_data.decode('utf-8'))
                                username = self.process_message(conn, message) or username
                            except json.JSONDecodeError:
                                self.send_message(conn, {
                                    'type': MESSAGE_TYPES['ERROR'],
                                    'data': {'code': 400, 'message': 'Invalid JSON'}
                                })
                        else:
                            break
                except socket.timeout:
                    continue
        except Exception as e:
            print(f"Error while handling client {addr}: {e}")
        finally:
            if username:
                self.set_user_offline(username)
            conn.close()

    # ============================================================
    # ============================================================

    def process_message(self, conn, message):
        """Public release docstring."""
        msg_type = message.get('type')
        data = message.get('data', {})
        handlers = {
            MESSAGE_TYPES['REGISTER']: self.handle_register,
            MESSAGE_TYPES['LOGIN']: self.handle_login,
            MESSAGE_TYPES['SEND_MESSAGE']: self.handle_send_message,
            MESSAGE_TYPES['CREATE_GROUP']: self.handle_create_group,
            MESSAGE_TYPES['JOIN_GROUP']: self.handle_join_group,
            MESSAGE_TYPES['LEAVE_GROUP']: self.handle_leave_group,
            MESSAGE_TYPES['GET_GROUP_MEMBERS']: self.handle_get_group_members,
            MESSAGE_TYPES['ADD_GROUP_MEMBER']: self.handle_add_group_member,
            MESSAGE_TYPES['HEARTBEAT']: self.handle_heartbeat,
            MESSAGE_TYPES['FILE_TRANSFER']: self.handle_file_transfer,
            MESSAGE_TYPES['FILE_REQUEST']: self.handle_file_request,
            MESSAGE_TYPES['RECALL_MESSAGE']: self.handle_recall_message,
        }

        if msg_type in handlers:
            return handlers[msg_type](conn, data)
        else:
            self.send_message(conn, {
                'type': MESSAGE_TYPES['ERROR'],
                'data': {'code': 400, 'message': 'Unknown type'}
            })
            return None

    # ============================================================
    # ============================================================

    def handle_register(self, conn, data):
        """Public release docstring."""
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            self.send_message(conn, {
                'type': MESSAGE_TYPES['REGISTER_RESPONSE'],
                'data': {'success': False, 'message': 'Missing fields'}
            })
            return None

        with self.users_lock:
            if username in self.users:
                self.send_message(conn, {
                    'type': MESSAGE_TYPES['REGISTER_RESPONSE'],
                    'data': {'success': False, 'message': 'Username exists'}
                })
                return None
            self.users[username] = {
                'password': password,
                'status': STATUS['OFFLINE'],
                'conn': None,
                'last_heartbeat': 0
            }
        with self.history_lock:
            if username not in self.message_history:
                self.message_history[username] = []

        self.send_message(conn, {
            'type': MESSAGE_TYPES['REGISTER_RESPONSE'],
            'data': {'success': True}
        })
        self.save_data()
        self.broadcast_user_directories()
        return None

    # ============================================================
    # ============================================================

    def build_user_directory(self, current_user=None):
        """Public release docstring."""
        with self.users_lock:
            usernames = sorted(self.users.keys())
            return [
                {
                    'username': username,
                    'status': self.users[username].get('status', STATUS['OFFLINE']),
                    'is_self': username == current_user,
                }
                for username in usernames
            ]

    def build_group_catalog(self, current_user=None):
        """Public release docstring."""
        with self.groups_lock:
            group_names = sorted(self.groups.keys())
            catalog = []
            for group_name in group_names:
                members = list(self.groups.get(group_name, []))
                catalog.append({
                    'group_name': group_name,
                    'member_count': len(members),
                    'joined': current_user in members if current_user else False,
                    'creator': members[0] if members else '',
                })
        return catalog

    def build_group_members_payload(self, group_name):
        """Public release docstring."""
        with self.groups_lock:
            members = list(self.groups.get(group_name, []))
        with self.users_lock:
            payload = [
                {
                    'username': username,
                    'status': self.users.get(username, {}).get('status', STATUS['OFFLINE']),
                }
                for username in members
            ]
        payload.sort(key=lambda item: item['username'])
        return payload

    def get_group_history(self, group_name):
        """Public release docstring."""
        with self.group_history_lock:
            history = []
            for msg in self.group_message_history.get(group_name, []):
                msg_copy = dict(msg)
                msg_copy.setdefault('receiver', group_name)
                history.append(msg_copy)
        history.sort(key=lambda item: item.get('timestamp', 0))
        return history

    # ============================================================
    # ============================================================

    def push_user_directory_to_user(self, username):
        """Public release docstring."""
        payload = {
            'type': MESSAGE_TYPES['USER_LIST'],
            'data': {'users': self.build_user_directory(username)}
        }
        self.safe_send_to_user(username, payload)

    def push_group_catalog_to_user(self, username):
        """Public release docstring."""
        payload = {
            'type': MESSAGE_TYPES['GROUP_LIST'],
            'data': {'groups': self.build_group_catalog(username)}
        }
        self.safe_send_to_user(username, payload)

    def broadcast_user_directories(self):
        """Public release docstring."""
        with self.users_lock:
            online_users = [
                username for username, info in self.users.items()
                if info.get('status') == STATUS['ONLINE'] and info.get('conn')
            ]
        for username in online_users:
            try:
                self.push_user_directory_to_user(username)
            except Exception as e:
                print(f"Failed to send user directory: {e}")

    def broadcast_group_catalogs(self):
        """Public release docstring."""
        with self.users_lock:
            online_users = [
                username for username, info in self.users.items()
                if info.get('status') == STATUS['ONLINE'] and info.get('conn')
            ]
        for username in online_users:
            try:
                self.push_group_catalog_to_user(username)
            except Exception as e:
                print(f"Failed to send group catalog: {e}")

    def get_user_full_history(self, username):
        """Public release docstring."""
        history = []
        with self.history_lock:
            personal = self.message_history.get(username, [])
            history.extend(personal)
        with self.groups_lock:
            user_groups = [g for g, members in self.groups.items() if username in members]
        for group in user_groups:
            history.extend(self.get_group_history(group))
        history.sort(key=lambda x: x.get('timestamp', 0))
        return history

    # ============================================================
    # ============================================================

    def handle_login(self, conn, data):
        """Public release docstring."""
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            self.send_message(conn, {
                'type': MESSAGE_TYPES['LOGIN_RESPONSE'],
                'data': {'success': False, 'message': 'Missing fields'}
            })
            return None

        with self.users_lock:
            if username not in self.users:
                self.send_message(conn, {
                    'type': MESSAGE_TYPES['LOGIN_RESPONSE'],
                    'data': {'success': False, 'message': 'User not found'}
                })
                return None
            if self.users[username]['password'] != password:
                self.send_message(conn, {
                    'type': MESSAGE_TYPES['LOGIN_RESPONSE'],
                    'data': {'success': False, 'message': 'Wrong password'}
                })
                return None
            old_conn = self.users[username].get('conn')
            self.users[username]['status'] = STATUS['ONLINE']
            self.users[username]['conn'] = conn
            self.users[username]['last_heartbeat'] = time.time()
        if old_conn and old_conn is not conn:
            try:
                old_conn.close()
            except Exception:
                pass
        with self.groups_lock:
            user_groups = [g for g, members in self.groups.items() if username in members]
        full_history = self.get_user_full_history(username)
        self.send_message(conn, {
            'type': MESSAGE_TYPES['LOGIN_RESPONSE'],
            'data': {
                'success': True,
                'history': full_history,
                'joined_groups': user_groups,
                'all_groups': self.build_group_catalog(username),
                'all_users': self.build_user_directory(username),
            }
        })
        self.broadcast_user_status(username, STATUS['ONLINE'])
        return username

    # ============================================================
    # ============================================================

    def handle_send_message(self, conn, data):
        """Public release docstring."""
        sender = data.get('sender')
        receiver = data.get('receiver')
        content = data.get('content')
        timestamp = data.get('timestamp', time.time())
        is_group = data.get('is_group', False)

        if not sender or not receiver or content is None:
            return sender
        is_sensitive, reason = self.content_analyzer.analyze_content(content)
        if is_sensitive:
            with self.users_lock:
                if sender in self.users and self.users[sender].get('conn'):
                    self.send_message(self.users[sender]['conn'], {
                        'type': MESSAGE_TYPES['ERROR'],
                        'data': {'code': 403, 'message': f'Sensitive content detected: {reason}'}
                    })
            return sender

        message_id = str(uuid.uuid4())

        if is_group:
            group_msg_data = {
                'sender': sender,
                'content': content,
                'timestamp': timestamp,
                'is_group': True,
                'receiver': receiver,
                'message_id': message_id
            }
            with self.group_history_lock:
                if receiver not in self.group_message_history:
                    self.group_message_history[receiver] = []
                self.group_message_history[receiver].append(group_msg_data)
        else:
            msg_record_sent = {
                'type': 'sent',
                'sender': sender,
                'receiver': receiver,
                'content': content,
                'timestamp': timestamp,
                'is_group': False,
                'message_id': message_id
            }
            msg_record_received = {
                'type': 'received',
                'sender': sender,
                'receiver': receiver,
                'content': content,
                'timestamp': timestamp,
                'is_group': False,
                'message_id': message_id
            }
            with self.history_lock:
                if sender not in self.message_history:
                    self.message_history[sender] = []
                self.message_history[sender].append(msg_record_sent)
                if receiver not in self.message_history:
                    self.message_history[receiver] = []
                self.message_history[receiver].append(msg_record_received)
        out_msg = {
            'type': MESSAGE_TYPES['MESSAGE'],
            'data': {
                'sender': sender,
                'content': content,
                'timestamp': timestamp,
                'is_group': is_group,
                'message_id': message_id,
                'receiver': receiver
            }
        }
        if is_group:
            with self.groups_lock:
                members = self.groups.get(receiver, [])
            for m in members:
                if m == sender:
                    continue
                self.safe_send_to_user(m, out_msg)
        else:
            self.safe_send_to_user(receiver, out_msg)
        if '@AI' in content and is_group:
            ai_response = self.llm_assistant.handle_ai_command(data)
            if ai_response:
                ai_msg = {
                    'type': MESSAGE_TYPES['MESSAGE'],
                    'data': {
                        'sender': 'AI Assistant',
                        'content': ai_response,
                        'timestamp': time.time(),
                        'is_group': is_group,
                        'receiver': receiver
                    }
                }
                with self.group_history_lock:
                    if receiver not in self.group_message_history:
                        self.group_message_history[receiver] = []
                    self.group_message_history[receiver].append(ai_msg['data'])
                with self.groups_lock:
                    members = self.groups.get(receiver, [])
                for m in members:
                    self.safe_send_to_user(m, ai_msg)

        self.save_data()
        return sender

    # ============================================================
    # ============================================================

    def handle_create_group(self, conn, data):
        """Public release docstring."""
        group_name = data.get('group_name')
        creator = data.get('creator')

        if not group_name or not creator:
            return creator

        with self.groups_lock:
            if group_name in self.groups:
                self.safe_send_to_user(creator, {
                    'type': MESSAGE_TYPES['GROUP_CREATED'],
                    'data': {'success': False, 'message': 'Group exists'}
                })
                return creator
            self.groups[group_name] = [creator]

        self.safe_send_to_user(creator, {
            'type': MESSAGE_TYPES['GROUP_CREATED'],
            'data': {'success': True, 'group_name': group_name}
        })
        self.save_data()
        self.broadcast_group_catalogs()
        return creator

    # ============================================================
    # ============================================================

    def handle_join_group(self, conn, data):
        """Public release docstring."""
        group_name = data.get('group_name')
        username = data.get('username')

        if not group_name or not username:
            return username

        with self.groups_lock:
            if group_name not in self.groups:
                self.safe_send_to_user(username, {
                    'type': MESSAGE_TYPES['GROUP_JOINED'],
                    'data': {'success': False, 'message': 'Group not found'}
                })
                return username
            if username in self.groups[group_name]:
                self.safe_send_to_user(username, {
                    'type': MESSAGE_TYPES['GROUP_JOINED'],
                    'data': {'success': False, 'message': 'Already in group'}
                })
                return username
            self.groups[group_name].append(username)
        self.safe_send_to_user(username, {
            'type': MESSAGE_TYPES['GROUP_JOINED'],
            'data': {'success': True, 'group_name': group_name}
        })
        sys_msg_data = {
            'sender': 'System',
            'content': f'{username} joined the group',
            'timestamp': time.time(),
            'is_group': True,
            'receiver': group_name
        }
        with self.group_history_lock:
            if group_name not in self.group_message_history:
                self.group_message_history[group_name] = []
            self.group_message_history[group_name].append(sys_msg_data)
        sys_msg = {'type': MESSAGE_TYPES['MESSAGE'], 'data': sys_msg_data}
        with self.groups_lock:
            members = self.groups.get(group_name, [])
        for m in members:
            self.safe_send_to_user(m, sys_msg)
            self.safe_send_to_user(m, {
                'type': MESSAGE_TYPES['GROUP_MEMBERS'],
                'data': {
                    'group_name': group_name,
                    'members': self.build_group_members_payload(group_name)
                }
            })
        self.push_group_catalog_to_user(username)
        self.safe_send_to_user(username, {
            'type': MESSAGE_TYPES['GROUP_HISTORY_SYNC'],
            'data': {
                'group_name': group_name,
                'history': self.get_group_history(group_name)
            }
        })

        self.save_data()
        self.broadcast_group_catalogs()
        return username

    # ============================================================
    # ============================================================

    def safe_send_to_user(self, username, message):
        """Public release docstring."""
        with self.users_lock:
            if username not in self.users:
                return False
            user_info = self.users[username]
            if user_info.get('status') != STATUS['ONLINE']:
                return False
            conn = user_info.get('conn')
            if not conn:
                return False
        try:
            self.send_message(conn, message)
            return True
        except Exception as e:
            print(f"Failed to send message to user {username}: {e}")
            return False

    # ============================================================
    # ============================================================

    def handle_get_group_members(self, conn, data):
        """Public release docstring."""
        group_name = data.get('group_name')
        username = data.get('username')

        if not group_name or not username:
            return username

        with self.groups_lock:
            if group_name not in self.groups:
                self.safe_send_to_user(username, {
                    'type': MESSAGE_TYPES['ERROR'],
                    'data': {'code': 404, 'message': 'Group not found'}
                })
                return username

        self.safe_send_to_user(username, {
            'type': MESSAGE_TYPES['GROUP_MEMBERS'],
            'data': {
                'group_name': group_name,
                'members': self.build_group_members_payload(group_name)
            }
        })
        return username

    # ============================================================
    # ============================================================

    def handle_add_group_member(self, conn, data):
        """Public release docstring."""
        group_name = data.get('group_name')
        operator = data.get('operator')
        target_user = data.get('target_user')

        if not group_name or not operator or not target_user:
            return operator
        with self.groups_lock:
            if group_name not in self.groups:
                self.safe_send_to_user(operator, {
                    'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
                    'data': {'success': False, 'message': 'Group not found', 'group_name': group_name}
                })
                return operator
            if operator not in self.groups[group_name]:
                self.safe_send_to_user(operator, {
                    'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
                    'data': {'success': False, 'message': 'Only group members can add new members', 'group_name': group_name}
                })
                return operator
            if target_user in self.groups[group_name]:
                self.safe_send_to_user(operator, {
                    'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
                    'data': {'success': False, 'message': 'User already in group', 'group_name': group_name}
                })
                return operator
        with self.users_lock:
            if target_user not in self.users:
                self.safe_send_to_user(operator, {
                    'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
                    'data': {'success': False, 'message': 'Target user not found', 'group_name': group_name}
                })
                return operator
        with self.groups_lock:
            self.groups[group_name].append(target_user)
        sys_msg_data = {
            'sender': 'System',
            'content': f'{operator} added {target_user} to the group',
            'timestamp': time.time(),
            'is_group': True,
            'receiver': group_name
        }
        with self.group_history_lock:
            if group_name not in self.group_message_history:
                self.group_message_history[group_name] = []
            self.group_message_history[group_name].append(sys_msg_data)
        self.safe_send_to_user(operator, {
            'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
            'data': {
                'success': True,
                'group_name': group_name,
                'operator': operator,
                'target_user': target_user
            }
        })
        self.safe_send_to_user(target_user, {
            'type': MESSAGE_TYPES['GROUP_MEMBER_ADDED'],
            'data': {
                'success': True,
                'group_name': group_name,
                'operator': operator,
                'target_user': target_user
            }
        })
        sys_msg = {'type': MESSAGE_TYPES['MESSAGE'], 'data': sys_msg_data}
        with self.groups_lock:
            members = list(self.groups.get(group_name, []))
        for member in members:
            self.safe_send_to_user(member, sys_msg)
            self.push_group_catalog_to_user(member)
        self.safe_send_to_user(target_user, {
            'type': MESSAGE_TYPES['GROUP_HISTORY_SYNC'],
            'data': {
                'group_name': group_name,
                'history': self.get_group_history(group_name)
            }
        })
        members_payload = {
            'type': MESSAGE_TYPES['GROUP_MEMBERS'],
            'data': {
                'group_name': group_name,
                'members': self.build_group_members_payload(group_name)
            }
        }
        for member in members:
            self.safe_send_to_user(member, members_payload)

        self.save_data()
        self.broadcast_group_catalogs()
        return operator

    # ============================================================
    # ============================================================

    def handle_leave_group(self, conn, data):
        """Public release docstring."""
        group_name = data.get('group_name')
        username = data.get('username')

        if not group_name or not username:
            return username

        with self.groups_lock:
            if group_name not in self.groups or username not in self.groups[group_name]:
                self.safe_send_to_user(username, {
                    'type': MESSAGE_TYPES['GROUP_LEFT'],
                    'data': {'success': False, 'message': 'Not in group'}
                })
                return username
            self.groups[group_name].remove(username)
            group_deleted = not self.groups[group_name]
            if group_deleted:
                del self.groups[group_name]

        self.safe_send_to_user(username, {
            'type': MESSAGE_TYPES['GROUP_LEFT'],
            'data': {'success': True, 'group_name': group_name}
        })

        if group_deleted:
            with self.group_history_lock:
                self.group_message_history.pop(group_name, None)
        else:
            sys_msg_data = {
                'sender': 'System',
                'content': f'{username} left the group',
                'timestamp': time.time(),
                'is_group': True,
                'receiver': group_name
            }
            with self.group_history_lock:
                if group_name not in self.group_message_history:
                    self.group_message_history[group_name] = []
                self.group_message_history[group_name].append(sys_msg_data)
            sys_msg = {'type': MESSAGE_TYPES['MESSAGE'], 'data': sys_msg_data}
            with self.groups_lock:
                members = self.groups.get(group_name, [])
            for m in members:
                self.safe_send_to_user(m, sys_msg)
                self.safe_send_to_user(m, {
                    'type': MESSAGE_TYPES['GROUP_MEMBERS'],
                    'data': {
                        'group_name': group_name,
                        'members': self.build_group_members_payload(group_name)
                    }
                })

        self.save_data()
        self.broadcast_group_catalogs()
        return username

    # ============================================================
    # ============================================================

    def handle_heartbeat(self, conn, data):
        """Public release docstring."""
        username = data.get('username')
        if username:
            with self.users_lock:
                if username in self.users:
                    self.users[username]['last_heartbeat'] = time.time()
                    self.send_message(conn, {
                        'type': MESSAGE_TYPES['HEARTBEAT_RESPONSE'],
                        'data': {'timestamp': time.time()}
                    })
        return username

    # ============================================================
    # ============================================================

    def handle_file_transfer(self, conn, data):
        """Public release docstring."""
        sender = data.get('sender')
        receiver = data.get('receiver')
        file_name = data.get('file_name')
        file_size = data.get('file_size')
        file_id = data.get('file_id')
        chunk_b64 = data.get('chunk_data')
        offset = data.get('offset', 0)
        is_end = data.get('is_end', False)
        is_group = data.get('is_group', False)

        if not sender or not receiver:
            return sender
        if chunk_b64 is not None:
            try:
                chunk_data = base64.b64decode(chunk_b64)
                if offset == 0:
                    self.file_transfer.create_file(file_id, file_size)
                self.file_transfer.save_file_chunk(file_id, chunk_data, offset)
            except Exception as e:
                print(f"File storage error: {e}")
                return sender
        if is_end:
            notify = {
                'type': MESSAGE_TYPES['FILE_TRANSFER'],
                'data': {
                    'sender': sender,
                    'receiver': receiver,
                    'file_name': file_name,
                    'file_size': file_size,
                    'file_id': file_id,
                    'is_group': is_group
                }
            }
            if is_group:
                with self.groups_lock:
                    members = self.groups.get(receiver, [])
                for m in members:
                    if m != sender:
                        self.safe_send_to_user(m, notify)
            else:
                self.safe_send_to_user(receiver, notify)
        return sender

    # ============================================================
    # ============================================================

    def handle_file_request(self, conn, data):
        """Public release docstring."""
        username = data.get('username')
        file_id = data.get('file_id')
        offset = data.get('offset', 0)

        if not username or not file_id:
            return username

        chunk_data = self.file_transfer.get_file_chunk(file_id, offset, FILE_CHUNK_SIZE)
        file_size = self.file_transfer.get_file_size(file_id)

        if chunk_data is not None:
            chunk_b64 = base64.b64encode(chunk_data).decode('utf-8')
            resp = {
                'type': MESSAGE_TYPES['FILE_DATA'],
                'data': {
                    'file_id': file_id,
                    'offset': offset,
                    'data': chunk_b64,
                    'is_end': (offset + len(chunk_data) >= file_size)
                }
            }
        else:
            resp = {
                'type': MESSAGE_TYPES['ERROR'],
                'data': {'code': 404, 'message': 'File not found'}
            }

        with self.users_lock:
            if username in self.users and self.users[username].get('conn'):
                self.send_message(self.users[username]['conn'], resp)
        return username

    # ============================================================
    # ============================================================

    def handle_recall_message(self, conn, data):
        """Public release docstring."""
        sender = data.get('sender')
        message_id = data.get('message_id')
        timestamp = data.get('timestamp')
        receiver = data.get('receiver')
        is_group = data.get('is_group', False)
        if time.time() - timestamp > RECALL_TIME_LIMIT:
            self.send_message(conn, {
                'type': MESSAGE_TYPES['RECALL_RESPONSE'],
                'data': {'success': False, 'message': 'Time limit exceeded'}
            })
            return sender
        if is_group:
            with self.group_history_lock:
                if receiver in self.group_message_history:
                    for msg in self.group_message_history[receiver]:
                        if msg.get('message_id') == message_id:
                            msg['recalled'] = True
                            msg['content'] = '[Message recalled]'
                            break
        else:
            with self.history_lock:
                if sender in self.message_history:
                    for msg in self.message_history[sender]:
                        if msg.get('message_id') == message_id:
                            msg['recalled'] = True
                            msg['content'] = '[Message recalled]'
                            break
                if receiver in self.message_history:
                    for msg in self.message_history[receiver]:
                        if msg.get('message_id') == message_id:
                            msg['recalled'] = True
                            msg['content'] = '[Message recalled]'
                            break
        self.save_data()
        recall_msg = {
            'type': MESSAGE_TYPES['RECALL_RESPONSE'],
            'data': {'success': True, 'message_id': message_id, 'sender': sender}
        }
        with self.users_lock:
            if sender in self.users and self.users[sender].get('conn'):
                self.send_message(self.users[sender]['conn'], recall_msg)
        if not is_group:
            self.safe_send_to_user(receiver, recall_msg)
        else:
            with self.groups_lock:
                members = self.groups.get(receiver, [])
            for m in members:
                self.safe_send_to_user(m, recall_msg)
        return sender

    # ============================================================
    # ============================================================

    def send_message(self, conn, message):
        """Public release docstring."""
        try:
            data = json.dumps(message, ensure_ascii=False).encode('utf-8')
            conn.sendall(len(data).to_bytes(4, byteorder='big'))
            conn.sendall(data)
        except Exception as e:
            print(f"Failed to send message: {e}")

    # ============================================================
    # ============================================================

    def shutdown(self):
        """Public release docstring."""
        if not self.running:
            return
        self.running = False
        print("Shutting down server...")
        self.save_data()
        with self.users_lock:
            for info in self.users.values():
                conn = info.get('conn')
                info['conn'] = None
                info['status'] = STATUS['OFFLINE']
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        try:
            self.server_socket.close()
        except Exception:
            pass

        print("Server closed")

    # ============================================================
    # ============================================================

    def start(self):
        """Public release docstring."""
        try:
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Preparing to exit...")
        finally:
            self.shutdown()


# ============================================================
# ============================================================
if __name__ == '__main__':
    Server().start()
