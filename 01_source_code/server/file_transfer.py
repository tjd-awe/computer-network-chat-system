import hashlib
import os

from common.config import FILE_CHUNK_SIZE, FILE_STORAGE_PATH


class FileTransfer:
    """Utility helpers for server-side file transfer storage."""

    def __init__(self):
        os.makedirs(FILE_STORAGE_PATH, exist_ok=True)

    def get_file_hash(self, file_path):
        """Return the MD5 hash of the target file."""
        hash_obj = hashlib.md5()
        with open(file_path, 'rb') as file_obj:
            while True:
                chunk = file_obj.read(FILE_CHUNK_SIZE)
                if not chunk:
                    break
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def save_file_chunk(self, file_id, chunk_data, offset):
        """Write one file chunk at the given offset."""
        file_path = os.path.join(FILE_STORAGE_PATH, file_id)
        with open(file_path, 'r+b') as file_obj:
            file_obj.seek(offset)
            file_obj.write(chunk_data)

    def create_file(self, file_id, file_size):
        """Create an empty file with the final target size."""
        file_path = os.path.join(FILE_STORAGE_PATH, file_id)
        with open(file_path, 'wb') as file_obj:
            file_obj.truncate(file_size)
        return file_path

    def get_file_chunk(self, file_id, offset, size):
        """Read a file chunk for download or resume support."""
        file_path = os.path.join(FILE_STORAGE_PATH, file_id)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'rb') as file_obj:
            file_obj.seek(offset)
            return file_obj.read(size)

    def get_file_size(self, file_id):
        """Return the current size of a stored file."""
        file_path = os.path.join(FILE_STORAGE_PATH, file_id)
        if not os.path.exists(file_path):
            return 0
        return os.path.getsize(file_path)
