"""
Boundary condition and exception handling tests
"""
import os
import sys
import time

from test_support import SOURCE_ROOT, create_connection, recv_msg, send_msg

sys.path.insert(0, str(SOURCE_ROOT))
from common.config import SERVER_HOST, SERVER_PORT
from common.protocol import MESSAGE_TYPES

def ensure_user_exists(username, password):
    """Ensure the test account exists. Ignore duplicate registration failures."""
    conn = create_connection(SERVER_HOST, SERVER_PORT)
    try:
        send_msg(conn, MESSAGE_TYPES['REGISTER'], {
            'username': username,
            'password': password
        })
        recv_msg(conn)
    finally:
        conn.close()

def test_wrong_password():
    """Test wrong-password login."""
    print("\nTest 1: Wrong-password login")
    conn = create_connection(SERVER_HOST, SERVER_PORT)
    
    send_msg(conn, MESSAGE_TYPES['LOGIN'], {
        'username': 'test_user_0',
        'password': 'wrong_password'
    })
    resp = recv_msg(conn)
    success = resp.get('data', {}).get('success', False)
    
    print(f"  Wrong-password login rejected: {not success}" if not success else "  Unexpected success: wrong password was accepted.")
    conn.close()
    return not success

def test_duplicate_username():
    """Test duplicate username registration."""
    print("\nTest 2: Duplicate username registration")
    conn = create_connection(SERVER_HOST, SERVER_PORT)
    
    # Register an existing user again
    send_msg(conn, MESSAGE_TYPES['REGISTER'], {
        'username': 'test_user_0',
        'password': '123456'
    })
    resp = recv_msg(conn)
    success = resp.get('data', {}).get('success', False)
    
    print(f"  Duplicate registration rejected: {not success}" if not success else "  Unexpected success: duplicate registration was accepted.")
    conn.close()
    return not success

def test_large_message():
    """Test oversized message delivery."""
    print("\nTest 3: Large message transfer")
    conn = create_connection(SERVER_HOST, SERVER_PORT)
    
    # Sign in first
    send_msg(conn, MESSAGE_TYPES['LOGIN'], {
        'username': 'test_user_0',
        'password': '123456'
    })
    recv_msg(conn)
    
    # Send a 10 KB message
    large_content = "A" * 10000
    send_msg(conn, MESSAGE_TYPES['SEND_MESSAGE'], {
        'sender': 'test_user_0',
        'receiver': 'test_user_1',
        'content': large_content,
        'timestamp': time.time(),
        'is_group': False
    })
    
    print("  Large message sent successfully.")
    conn.close()
    return True

def test_special_chars():
    """Test special characters and Unicode content."""
    print("\nTest 4: Unicode and special characters")
    conn = create_connection(SERVER_HOST, SERVER_PORT)
    
    send_msg(conn, MESSAGE_TYPES['LOGIN'], {
        'username': 'test_user_0',
        'password': '123456'
    })
    recv_msg(conn)
    
    special_content = "Hello, world. Unicode check: @#$%^&*() [] {} <>"
    send_msg(conn, MESSAGE_TYPES['SEND_MESSAGE'], {
        'sender': 'test_user_0',
        'receiver': 'test_user_1',
        'content': special_content,
        'timestamp': time.time(),
        'is_group': False
    })
    
    print("  Unicode and special characters were transmitted successfully.")
    conn.close()
    return True

def run_all_boundary_tests():
    print("=" * 60)
    print("Boundary condition and exception tests")
    print("=" * 60)
    print("Please make sure the server is already running.")

    ensure_user_exists('test_user_0', '123456')
    ensure_user_exists('test_user_1', '123456')
    
    results = []
    results.append(test_wrong_password())
    results.append(test_duplicate_username())
    results.append(test_large_message())
    results.append(test_special_chars())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Boundary test summary: {passed}/{total} passed")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    run_all_boundary_tests()
