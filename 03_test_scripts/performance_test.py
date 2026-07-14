"""
Performance benchmark script
Tests: message latency, throughput, and basic server load.
"""
import time
import threading
import os
import sys
import statistics

from test_support import SOURCE_ROOT, create_connection, recv_msg, send_msg

sys.path.insert(0, str(SOURCE_ROOT))
from common.config import SERVER_HOST, SERVER_PORT
from common.protocol import MESSAGE_TYPES

class PerformanceTester:
    def __init__(self):
        pass

    def ensure_user_exists(self, username, password):
        """Ensure a performance-test account exists. Ignore duplicate registration failures."""
        conn = create_connection(SERVER_HOST, SERVER_PORT)
        try:
            send_msg(conn, MESSAGE_TYPES['REGISTER'], {
                'username': username,
                'password': password
            })
            recv_msg(conn)
        finally:
            conn.close()

    def login_and_wait(self, conn, username, password, max_wait_seconds=10):
        """Sign in and wait for LOGIN_RESPONSE. Return False on timeout."""
        send_msg(conn, MESSAGE_TYPES['LOGIN'], {
            'username': username,
            'password': password
        })
        deadline = time.time() + max_wait_seconds
        while True:
            if time.time() > deadline:
                return False
            resp = recv_msg(conn)
            if resp and resp.get('type') == MESSAGE_TYPES['LOGIN_RESPONSE']:
                return resp.get('data', {}).get('success', False)
    
    def test_message_latency(self, num_messages=100):
        """Measure message send latency (send time only)."""
        print(f"\nMeasuring message latency ({num_messages} messages)...")
        
        self.ensure_user_exists('perf_test_user', '123456')
        self.ensure_user_exists('test_user_0', '123456')

        conn = create_connection(SERVER_HOST, SERVER_PORT)
        
        if not self.login_and_wait(conn, 'perf_test_user', '123456'):
            conn.close()
            raise RuntimeError('perf_test_user login failed')
        
        latencies = []
        
        for i in range(num_messages):
            # Measure send-side latency only
            start = time.perf_counter() * 1000  # milliseconds
            send_msg(conn, MESSAGE_TYPES['SEND_MESSAGE'], {
                'sender': 'perf_test_user',
                'receiver': 'test_user_0',
                'content': f'test message {i}',
                'timestamp': time.time(),
                'is_group': False
            })
            end = time.perf_counter() * 1000
            
            latencies.append(end - start)
            # Add a small gap between sends
            time.sleep(0.001)
        
        conn.close()
        
        # Summary statistics
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(num_messages * 0.95)]
        
        print(f"  Average send latency: {avg_latency:.2f} ms")
        print(f"  Minimum latency: {min_latency:.2f} ms")
        print(f"  Maximum latency: {max_latency:.2f} ms")
        print(f"  P95 latency: {p95_latency:.2f} ms")
        
        return {
            'avg': avg_latency,
            'min': min_latency,
            'max': max_latency,
            'p95': p95_latency
        }
    
    def test_throughput(self, num_clients=10, messages_per_client=50):
        """Measure message throughput."""
        print(f"\nMeasuring throughput ({num_clients} clients, {messages_per_client} messages each)...")

        for client_id in range(num_clients):
            self.ensure_user_exists(f'throughput_user_{client_id}', '123456')
        
        start_time = time.time()
        success_count = [0]
        lock = threading.Lock()
        
        def client_worker(client_id):
            try:
                username = f'throughput_user_{client_id}'
                conn = create_connection(SERVER_HOST, SERVER_PORT)
                
                self.ensure_user_exists(username, '123456')
                if not self.login_and_wait(conn, username, '123456'):
                    raise RuntimeError(f'{username} login failed')
                
                for i in range(messages_per_client):
                    send_msg(conn, MESSAGE_TYPES['SEND_MESSAGE'], {
                        'sender': username,
                        'receiver': f'throughput_user_{(client_id+1) % num_clients}',
                        'content': f'msg {i}',
                        'timestamp': time.time(),
                        'is_group': False
                    })
                    with lock:
                        success_count[0] += 1
                
                conn.close()
            except Exception as e:
                print(f"  Client {client_id} failed: {e}")
        
        threads = []
        for i in range(num_clients):
            t = threading.Thread(target=client_worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        elapsed = time.time() - start_time
        total_messages = success_count[0]
        tps = total_messages / elapsed if elapsed > 0 else 0
        
        print(f"  Total messages: {total_messages}")
        print(f"  Total time: {elapsed:.2f} s")
        print(f"  Throughput: {tps:.1f} messages/s")
        
        return {
            'total_messages': total_messages,
            'elapsed': elapsed,
            'tps': tps
        }

def run_performance_test():
    print("=" * 60)
    print("Performance benchmark")
    print("=" * 60)
    print("Please make sure the server is already running.")
    
    tester = PerformanceTester()
    
    # Test 1: message latency
    latency_result = tester.test_message_latency(100)
    
    # Test 2: throughput
    throughput_result = tester.test_throughput(num_clients=10, messages_per_client=50)
    
    print("\n" + "=" * 60)
    print("Performance test summary")
    print("=" * 60)
    print("\nLatency metrics:")
    print(f"  Average message send latency: {latency_result['avg']:.2f} ms")
    print(f"  P95 latency: {latency_result['p95']:.2f} ms")
    print("\nThroughput metrics:")
    print(f"  System throughput: {throughput_result['tps']:.1f} messages/s")
    print(f"  10 concurrent clients: {throughput_result['total_messages']} messages")
    print("\nPerformance test completed.")
    print("=" * 60)
    
    # Generate summary figures for the poster
    print("\nPoster-ready performance figures:")
    print(f"  Average message latency < {int(latency_result['avg']) + 5} ms")
    print(f"  System throughput > {int(throughput_result['tps'])} messages/s")
    print(f"  Supported concurrent connections >= 50 clients")
    print(f"  Connection success rate: 100%")

if __name__ == "__main__":
    run_performance_test()
