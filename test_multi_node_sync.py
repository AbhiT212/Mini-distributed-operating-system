"""
Multi-Node Sync Test Script
Tests file synchronization between multiple MiniDOS nodes
"""

import sys
import time
import socket
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.commands import CommandExecutor


class MultiNodeTester:
    """Test synchronization between multiple nodes"""
    
    def __init__(self, nodes):
        """
        Initialize tester with node configurations
        nodes: List of (name, host, port) tuples
        """
        self.nodes = {}
        for name, host, port in nodes:
            self.nodes[name] = CommandExecutor(host, port)
        
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def print_header(self, text):
        """Print section header"""
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}\n")
    
    def test(self, name, node_name, command, args, expected_success=True):
        """Run a test on a specific node"""
        print(f"📝 TEST: {name}")
        print(f"   Node: {node_name}")
        print(f"   Command: {command} {' '.join(str(a) for a in args)}")
        
        try:
            executor = self.nodes[node_name]
            success, message, data = executor.execute(command, args, "")
            
            if success == expected_success:
                print(f"   ✅ PASSED: {message[:100]}")
                self.passed += 1
                self.tests.append((name, "PASSED"))
                return True
            else:
                print(f"   ❌ FAILED: {message}")
                self.failed += 1
                self.tests.append((name, "FAILED"))
                return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            self.failed += 1
            self.tests.append((name, "EXCEPTION"))
            return False
    
    def verify_file_exists(self, name, node_name, filepath, should_exist=True):
        """Verify a file exists on a node"""
        print(f"🔍 VERIFY: {name}")
        print(f"   Node: {node_name}")
        print(f"   File: {filepath}")
        print(f"   Expected: {'EXISTS' if should_exist else 'NOT EXISTS'}")
        
        try:
            executor = self.nodes[node_name]
            success, message, data = executor.execute("read", [filepath], "")
            
            file_exists = success
            
            if file_exists == should_exist:
                print(f"   ✅ VERIFIED: File {'exists' if file_exists else 'does not exist'} as expected")
                self.passed += 1
                self.tests.append((name, "PASSED"))
                return True
            else:
                print(f"   ❌ FAILED: File {'exists' if file_exists else 'does not exist'} - unexpected!")
                self.failed += 1
                self.tests.append((name, "FAILED"))
                return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            self.failed += 1
            self.tests.append((name, "EXCEPTION"))
            return False
    
    def verify_file_content(self, name, node_name, filepath, expected_content):
        """Verify file content matches"""
        print(f"🔍 VERIFY CONTENT: {name}")
        print(f"   Node: {node_name}")
        print(f"   File: {filepath}")
        
        try:
            executor = self.nodes[node_name]
            success, content, data = executor.execute("read", [filepath], "")
            
            if success and content == expected_content:
                print(f"   ✅ VERIFIED: Content matches")
                self.passed += 1
                self.tests.append((name, "PASSED"))
                return True
            else:
                print(f"   ❌ FAILED: Content mismatch")
                print(f"      Expected: '{expected_content}'")
                print(f"      Got: '{content}'")
                self.failed += 1
                self.tests.append((name, "FAILED"))
                return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            self.failed += 1
            self.tests.append((name, "EXCEPTION"))
            return False
    
    def check_peer_connection(self, name, node_name):
        """Check if node has active peer connections"""
        print(f"🔗 CHECK PEERS: {name}")
        print(f"   Node: {node_name}")
        
        try:
            executor = self.nodes[node_name]
            success, message, data = executor.execute("loadbal", [], "")
            
            if success and "peer" in message.lower():
                # Extract peer count from message
                if "0" not in message:
                    print(f"   ✅ VERIFIED: Node has peer connections")
                    self.passed += 1
                    self.tests.append((name, "PASSED"))
                    return True
            
            print(f"   ⚠️  WARNING: No peers detected or cannot verify")
            print(f"   {message[:150]}")
            self.tests.append((name, "WARNING"))
            return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            self.failed += 1
            self.tests.append((name, "EXCEPTION"))
            return False
    
    def summary(self):
        """Print test summary"""
        print(f"\n\n{'='*80}")
        print(f"  TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        if self.passed + self.failed > 0:
            success_rate = (self.passed / (self.passed + self.failed)) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        print(f"{'='*80}\n")


def detect_nodes():
    """Try to detect available nodes"""
    print("🔍 Detecting MiniDOS nodes...")
    nodes = []
    
    # Try common configurations
    test_configs = [
        ("Local Node", "localhost", 9000),
        ("Node on 192.168.1.100", "192.168.1.100", 9000),
        ("Node on 192.168.1.101", "192.168.1.101", 9000),
    ]
    
    for name, host, port in test_configs:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"   ✅ Found: {name} at {host}:{port}")
                nodes.append((name, host, port))
            else:
                print(f"   ❌ Not found: {name} at {host}:{port}")
        except Exception as e:
            print(f"   ❌ Error checking {name}: {e}")
    
    return nodes


def main():
    """Run multi-node synchronization tests"""
    
    print("="*80)
    print("  MiniDOS Multi-Node Synchronization Test")
    print("="*80)
    print("\nThis script tests file synchronization between nodes")
    print("Make sure ALL nodes have their daemons running!")
    print("\nExample setup:")
    print("  - Abhi's Device: 192.168.1.100:9000")
    print("  - Urvish's Device: 192.168.1.101:9000")
    print("="*80)
    
    # Detect available nodes
    detected_nodes = detect_nodes()
    
    if len(detected_nodes) < 2:
        print("\n⚠️  WARNING: Found less than 2 nodes!")
        print("You need at least 2 nodes to test synchronization.")
        print("\nManual configuration:")
        
        use_manual = input("\nDo you want to manually specify nodes? (y/n): ")
        if use_manual.lower() == 'y':
            nodes = []
            while len(nodes) < 2:
                name = input(f"Node {len(nodes)+1} name: ")
                host = input(f"Node {len(nodes)+1} host (e.g., 192.168.1.100 or localhost): ")
                port = input(f"Node {len(nodes)+1} port (default 9000): ") or "9000"
                nodes.append((name, host, int(port)))
                
                more = input("Add another node? (y/n): ")
                if more.lower() != 'y' and len(nodes) >= 2:
                    break
        else:
            print("\n❌ Cannot proceed without at least 2 nodes.")
            print("Please start daemons on both machines and try again.")
            return
    else:
        nodes = detected_nodes
    
    print(f"\n✅ Testing with {len(nodes)} nodes:")
    for name, host, port in nodes:
        print(f"   - {name}: {host}:{port}")
    
    input("\n📋 Press Enter to start tests...")
    
    # Initialize tester
    tester = MultiNodeTester(nodes)
    node_names = [name for name, _, _ in nodes]
    
    # =================================================================
    # TEST GROUP 1: Peer Connection Verification
    # =================================================================
    tester.print_header("GROUP 1: Verify Peer Connections")
    
    for i, node_name in enumerate(node_names):
        tester.check_peer_connection(f"1.{i+1}: Check {node_name} has peers", node_name)
    
    time.sleep(2)
    
    # =================================================================
    # TEST GROUP 2: Basic File Sync - Node 1 to Node 2
    # =================================================================
    tester.print_header("GROUP 2: File Sync from Node 1 to Node 2")
    
    node1 = node_names[0]
    node2 = node_names[1]
    
    print(f"\n📤 Creating file on {node1}...")
    tester.test("2.1: Create file on Node 1", node1, "create", ["sync_test_1.txt"])
    
    print(f"\n✍️  Writing content on {node1}...")
    tester.test("2.2: Write to file on Node 1", node1, "write", ["sync_test_1.txt", "Hello from Node 1!"])
    
    print(f"\n⏳ Waiting 4 seconds for sync...")
    time.sleep(4)
    
    print(f"\n📥 Checking if file appeared on {node2}...")
    tester.verify_file_exists("2.3: File exists on Node 2", node2, "sync_test_1.txt", should_exist=True)
    
    print(f"\n🔍 Verifying content matches on {node2}...")
    tester.verify_file_content("2.4: Content matches on Node 2", node2, "sync_test_1.txt", "Hello from Node 1!")
    
    # =================================================================
    # TEST GROUP 3: Reverse Sync - Node 2 to Node 1
    # =================================================================
    tester.print_header("GROUP 3: File Sync from Node 2 to Node 1")
    
    print(f"\n📤 Creating file on {node2}...")
    tester.test("3.1: Create file on Node 2", node2, "create", ["sync_test_2.txt"])
    
    print(f"\n✍️  Writing content on {node2}...")
    tester.test("3.2: Write to file on Node 2", node2, "write", ["sync_test_2.txt", "Hello from Node 2!"])
    
    print(f"\n⏳ Waiting 4 seconds for sync...")
    time.sleep(4)
    
    print(f"\n📥 Checking if file appeared on {node1}...")
    tester.verify_file_exists("3.3: File exists on Node 1", node1, "sync_test_2.txt", should_exist=True)
    
    print(f"\n🔍 Verifying content matches on {node1}...")
    tester.verify_file_content("3.4: Content matches on Node 1", node1, "sync_test_2.txt", "Hello from Node 2!")
    
    # =================================================================
    # TEST GROUP 4: Bidirectional Updates
    # =================================================================
    tester.print_header("GROUP 4: Bidirectional File Updates")
    
    print(f"\n📝 Updating file from {node1}...")
    tester.test("4.1: Update file on Node 1", node1, "write", ["sync_test_1.txt", "Updated from Node 1!"])
    
    print(f"\n⏳ Waiting 4 seconds for sync...")
    time.sleep(4)
    
    print(f"\n🔍 Checking update reached {node2}...")
    tester.verify_file_content("4.2: Updated content on Node 2", node2, "sync_test_1.txt", "Updated from Node 1!")
    
    # =================================================================
    # TEST GROUP 5: File Deletion Sync
    # =================================================================
    tester.print_header("GROUP 5: File Deletion Sync")
    
    print(f"\n🗑️  Deleting file on {node1}...")
    tester.test("5.1: Delete file on Node 1", node1, "delete", ["sync_test_1.txt"])
    
    print(f"\n⏳ Waiting 4 seconds for sync...")
    time.sleep(4)
    
    print(f"\n🔍 Checking deletion synced to {node2}...")
    tester.verify_file_exists("5.2: File deleted on Node 2", node2, "sync_test_1.txt", should_exist=False)
    
    # =================================================================
    # TEST GROUP 6: Directory and Nested Files
    # =================================================================
    tester.print_header("GROUP 6: Directory and Nested File Sync")
    
    print(f"\n📁 Creating directory on {node1}...")
    tester.test("6.1: Create directory on Node 1", node1, "mkdir", ["shared_folder"])
    
    print(f"\n📄 Creating file in directory on {node1}...")
    tester.test("6.2: Create nested file on Node 1", node1, "create", ["shared_folder/nested_file.txt"])
    
    print(f"\n✍️  Writing to nested file on {node1}...")
    tester.test("6.3: Write to nested file on Node 1", node1, "write", ["shared_folder/nested_file.txt", "Nested content"])
    
    print(f"\n⏳ Waiting 4 seconds for sync...")
    time.sleep(4)
    
    print(f"\n📥 Checking nested file on {node2}...")
    tester.verify_file_exists("6.4: Nested file exists on Node 2", node2, "shared_folder/nested_file.txt", should_exist=True)
    
    print(f"\n🔍 Verifying nested content on {node2}...")
    tester.verify_file_content("6.5: Nested content matches on Node 2", node2, "shared_folder/nested_file.txt", "Nested content")
    
    # =================================================================
    # TEST GROUP 7: If 3+ Nodes, Test Multi-Node Sync
    # =================================================================
    if len(nodes) >= 3:
        tester.print_header("GROUP 7: Multi-Node Sync (3+ Nodes)")
        
        node3 = node_names[2]
        
        print(f"\n📤 Creating file on {node1}...")
        tester.test("7.1: Create file on Node 1", node1, "create", ["multi_sync_test.txt"])
        
        print(f"\n✍️  Writing content on {node1}...")
        tester.test("7.2: Write to file on Node 1", node1, "write", ["multi_sync_test.txt", "Multi-node sync!"])
        
        print(f"\n⏳ Waiting 3 seconds for sync...")
        time.sleep(3)
        
        print(f"\n📥 Checking on {node2}...")
        tester.verify_file_exists("7.3: File on Node 2", node2, "multi_sync_test.txt", should_exist=True)
        
        print(f"\n📥 Checking on {node3}...")
        tester.verify_file_exists("7.4: File on Node 3", node3, "multi_sync_test.txt", should_exist=True)
        
        print(f"\n🔍 Verifying content on {node3}...")
        tester.verify_file_content("7.5: Content on Node 3", node3, "multi_sync_test.txt", "Multi-node sync!")
    
    # =================================================================
    # SUMMARY
    # =================================================================
    tester.summary()
    
    # Final status
    if tester.failed == 0:
        print("🎉 ALL SYNCHRONIZATION TESTS PASSED! 🎉")
        print("Your MiniDOS cluster is working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nPossible issues:")
        print("  1. Nodes not properly connected (check firewall)")
        print("  2. File sync not working (check daemon logs)")
        print("  3. Network latency (increase wait times)")
        print("\nCheck logs on each node: logs\\node.log")
    
    return tester.failed == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

