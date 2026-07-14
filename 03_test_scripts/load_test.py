"""
Concurrent load test script
Purpose: simulate many clients and measure concurrent handling capacity.
"""
import threading
import time
import sys
import os

from test_support import SOURCE_ROOT, create_connection, recv_msg, send_msg

sys.path.insert(0, str(SOURCE_ROOT))
from common.config import SERVER_HOST, SERVER_PORT
from common.protocol import MESSAGE_TYPES

class TestClient:
    """Simulated test client."""
    def __init__(self, client_id):
        self.client_id = client_id
        self.username = f"test_user_{client_id}"
        self.password = "123456"
        self.conn = None
        self.connected = False
        self.logged_in = False
        self.messages_received = 0
        self.errors = []
        
    def connect(self):
        """Connect to the server."""
        try:
            self.conn = create_connection(SERVER_HOST, SERVER_PORT)
            self.connected = True
            return True
        except Exception as e:
            self.errors.append(f"Connection failed: {e}")
            return False
    
    def register_and_login(self):
        """Register and sign in."""
        # Register
        send_msg(self.conn, MESSAGE_TYPES['REGISTER'], {
            'username': self.username,
            'password': self.password
        })
        recv_msg(self.conn)  # Ignore the registration reply because the account may already exist
        time.sleep(0.1)
        
        # Sign in
        send_msg(self.conn, MESSAGE_TYPES['LOGIN'], {
            'username': self.username,
            'password': self.password
        })
        resp = recv_msg(self.conn)
        if resp and resp.get('data', {}).get('success'):
            self.logged_in = True
            return True
        return False
    
    def send_heartbeat(self):
        """Send heartbeat packets."""
        while self.connected and self.logged_in:
            try:
                send_msg(self.conn, MESSAGE_TYPES['HEARTBEAT'], {
                    'username': self.username,
                    'timestamp': time.time()
                })
                time.sleep(30)
            except:
                break
    
    def close(self):
        """Close the connection."""
        self.connected = False
        self.logged_in = False
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

def run_load_test(num_clients=50):
    """Run the load test."""
    print("=" * 60)
    print(f"Starting concurrent load test, clients: {num_clients}")
    print("=" * 60)
    
    clients = []
    threads = []
    start_time = time.time()
    
    # 1. Create and connect all clients
    print("\n[1/4] Establishing connections...")
    connect_success = 0
    for i in range(num_clients):
        client = TestClient(i)
        clients.append(client)
        if client.connect():
            connect_success += 1
        if (i + 1) % 10 == 0:
            print(f"  Connected {i + 1}/{num_clients} clients")
        time.sleep(0.05)  # Slightly stagger the connections to avoid a burst
    
    print(f"  Connection success rate: {connect_success}/{num_clients} ({connect_success/num_clients*100:.1f}%)")
    
    # 2. Sign in
    print("\n[2/4] Signing in...")
    login_success = 0
    for client in clients:
        if client.connected and client.register_and_login():
            login_success += 1
            # Start heartbeat threads
            threading.Thread(target=client.send_heartbeat, daemon=True).start()
    
    print(f"  Login success rate: {login_success}/{num_clients} ({login_success/num_clients*100:.1f}%)")
    
    # 3. Keep clients online for a while
    print("\n[3/4] Staying online for 30 seconds to test stability...")
    for i in range(30, 0, -5):
        print(f"  {i} seconds remaining...")
        time.sleep(5)
    
    # 4. Summarize results
    elapsed = time.time() - start_time
    print("\n[4/4] Test finished, collecting results...")
    print("-" * 60)
    
    total_errors = sum(len(c.errors) for c in clients)
    still_connected = sum(1 for c in clients if c.connected and c.logged_in)
    
    print(f"\nLoad test report:")
    print(f"  Total clients:      {num_clients}")
    print(f"  Successful connections:      {connect_success}")
    print(f"  Successful logins:      {login_success}")
    print(f"  Clients still online:      {still_connected}")
    print(f"  Total errors:        {total_errors}")
    print(f"  Total time:          {elapsed:.2f} s")
    print(f"  Average connect time: {elapsed/num_clients*1000:.1f} ms/client")
    print(f"\nConcurrent load test {'passed' if still_connected >= num_clients * 0.95 else 'failed'}.")
    
    # Print error details
    if total_errors > 0:
        print("\nError details:")
        for client in clients:
            for err in client.errors:
                print(f"  {client.username}: {err}")
    
    # Cleanup
    print("\nClosing all connections...")
    for client in clients:
        client.close()
    
    print("=" * 60)
    return still_connected >= num_clients * 0.95

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Concurrent load test')
    parser.add_argument('-n', '--num', type=int, default=50, help='Number of clients')
    args = parser.parse_args()
    
    print("Please make sure the server is already running.")
    input("Press Enter to start the test...")
    
    run_load_test(args.num)
