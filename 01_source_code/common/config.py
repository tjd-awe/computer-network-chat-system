# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8888

# Heartbeat settings (seconds)
HEARTBEAT_INTERVAL = 30
HEARTBEAT_TIMEOUT = 60

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Persistent storage paths
MESSAGE_HISTORY_PATH = 'data/messages.json'
USER_DATA_PATH = 'data/users.json'
GROUP_DATA_PATH = 'data/groups.json'
GROUP_MESSAGE_HISTORY_PATH = 'data/group_messages.json'

# LLM API configuration
LLM_API_URL_FALLBACK = 'https://open.bigmodel.cn/api/paas/v4'
LLM_API_KEY_FALLBACK = ''  # Keep empty in public repositories.
LLM_MODEL_FALLBACK = 'glm-4-flash'

# Resolution order: environment variable > fallback
LLM_API_URL = os.getenv('LLM_API_URL') or LLM_API_URL_FALLBACK
LLM_API_KEY = os.getenv('LLM_API_KEY') or LLM_API_KEY_FALLBACK
LLM_MODEL = os.getenv('LLM_MODEL') or LLM_MODEL_FALLBACK

# File transfer settings
FILE_CHUNK_SIZE = 4096
FILE_STORAGE_PATH = os.path.join(DATA_DIR, 'files')

# Message recall time limit (seconds)
RECALL_TIME_LIMIT = 120
