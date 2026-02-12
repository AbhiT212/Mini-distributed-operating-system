"""
Comprehensive Test Suite for MiniDOS Filesystem
Tests navigation, nested folders, and file operations
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.commands import CommandExecutor


class TestRunner:
    """Run comprehensive filesystem tests"""
    
    def __init__(self):
        self.executor = CommandExecutor("localhost", 9000)
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name: str, command: str, args: list, current_dir: str = ""):
        """Run a single test"""
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"Command: {command} {' '.join(args)}")
        print(f"Current Dir: /{current_dir}" if current_dir else "Current Dir: /")
        print(f"{'='*70}")
        
        try:
            success, message, data = self.executor.execute(command, args, current_dir)
            
            if success:
                print(f"✅ PASSED")
                print(f"Result: {message[:200]}")  # Limit output
                self.passed += 1
                self.tests.append((name, "PASSED", message))
            else:
                print(f"❌ FAILED")
                print(f"Error: {message}")
                self.failed += 1
                self.tests.append((name, "FAILED", message))
            
            return success, message
            
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            self.failed += 1
            self.tests.append((name, "EXCEPTION", str(e)))
            return False, str(e)
    
    def summary(self):
        """Print test summary"""
        print(f"\n\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/(self.passed + self.failed)*100):.1f}%" if self.passed + self.failed > 0 else "0%")
        print(f"{'='*70}")
        
        if self.failed > 0:
            print(f"\nFailed Tests:")
            for name, status, msg in self.tests:
                if status == "FAILED":
                    print(f"  ❌ {name}: {msg}")


def main():
    """Run all tests"""
    runner = TestRunner()
    
    print("="*70)
    print("MiniDOS Filesystem Comprehensive Test Suite")
    print("Testing: Navigation, Nested Folders, File Operations")
    print("="*70)
    
    time.sleep(1)  # Give user time to see header
    
    # =================================================================
    # TEST GROUP 1: Basic Directory Creation
    # =================================================================
    print("\n\n🧪 GROUP 1: Basic Directory Creation")
    
    runner.test("1.1: Create root level folder", "mkdir", ["projects"], "")
    runner.test("1.2: Create another root folder", "mkdir", ["documents"], "")
    runner.test("1.3: Create third root folder", "mkdir", ["media"], "")
    
    # =================================================================
    # TEST GROUP 2: Nested Directory Structure
    # =================================================================
    print("\n\n🧪 GROUP 2: Nested Directory Structure")
    
    runner.test("2.1: Create nested folder", "mkdir", ["projects/web"], "")
    runner.test("2.2: Create deeper nested folder", "mkdir", ["projects/web/frontend"], "")
    runner.test("2.3: Create parallel nested folder", "mkdir", ["projects/web/backend"], "")
    runner.test("2.4: Create another branch", "mkdir", ["projects/mobile"], "")
    runner.test("2.5: Create deep branch", "mkdir", ["projects/mobile/ios"], "")
    runner.test("2.6: Create deep branch 2", "mkdir", ["projects/mobile/android"], "")
    
    # =================================================================
    # TEST GROUP 3: File Creation in Root
    # =================================================================
    print("\n\n🧪 GROUP 3: File Creation in Root")
    
    runner.test("3.1: Create file in root", "create", ["readme.txt"], "")
    runner.test("3.2: Write to root file", "write", ["readme.txt", '"MiniDOS Test Suite"'], "")
    runner.test("3.3: Read root file", "read", ["readme.txt"], "")
    
    # =================================================================
    # TEST GROUP 4: Files in Nested Directories (Absolute Paths)
    # =================================================================
    print("\n\n🧪 GROUP 4: Files in Nested Directories (Absolute Paths)")
    
    runner.test("4.1: Create file in projects", "create", ["projects/project_list.txt"], "")
    runner.test("4.2: Write to nested file", "write", ["projects/project_list.txt", '"1. Web App\n2. Mobile App"'], "")
    runner.test("4.3: Create file in web", "create", ["projects/web/index.html"], "")
    runner.test("4.4: Write HTML content", "write", ["projects/web/index.html", '"<html><body>Test</body></html>"'], "")
    runner.test("4.5: Create file in frontend", "create", ["projects/web/frontend/app.js"], "")
    runner.test("4.6: Write JS content", "write", ["projects/web/frontend/app.js", '"console.log(Hello);"'], "")
    runner.test("4.7: Create file in backend", "create", ["projects/web/backend/server.py"], "")
    runner.test("4.8: Write Python content", "write", ["projects/web/backend/server.py", '"print(Server running)"'], "")
    
    # =================================================================
    # TEST GROUP 5: Files with Relative Paths (Simulated cd)
    # =================================================================
    print("\n\n🧪 GROUP 5: Files with Relative Paths")
    
    runner.test("5.1: Create file relative to projects", "create", ["notes.txt"], "projects")
    runner.test("5.2: Write to relative file", "write", ["notes.txt", '"Project Notes"'], "projects")
    runner.test("5.3: Read relative file", "read", ["notes.txt"], "projects")
    runner.test("5.4: Create file in web subdir", "create", ["config.json"], "projects/web")
    runner.test("5.5: Write JSON", "write", ["config.json", '"{port: 3000}"'], "projects/web")
    runner.test("5.6: Create file in frontend", "create", ["component.jsx"], "projects/web/frontend")
    runner.test("5.7: Write JSX", "write", ["component.jsx", '"const App = () => <div>Test</div>"'], "projects/web/frontend")
    
    # =================================================================
    # TEST GROUP 6: Multiple Files in Same Directory
    # =================================================================
    print("\n\n🧪 GROUP 6: Multiple Files in Same Directory")
    
    runner.test("6.1: Create file 1 in mobile", "create", ["projects/mobile/readme.md"], "")
    runner.test("6.2: Create file 2 in mobile", "create", ["projects/mobile/config.xml"], "")
    runner.test("6.3: Create file 3 in mobile", "create", ["projects/mobile/package.json"], "")
    runner.test("6.4: Write to mobile readme", "write", ["projects/mobile/readme.md", '"# Mobile Project"'], "")
    runner.test("6.5: Write to mobile config", "write", ["projects/mobile/config.xml", '"<config></config>"'], "")
    runner.test("6.6: Write to mobile package", "write", ["projects/mobile/package.json", '"{name: mobile-app}"'], "")
    
    # =================================================================
    # TEST GROUP 7: Directory Listing
    # =================================================================
    print("\n\n🧪 GROUP 7: Directory Listing")
    
    runner.test("7.1: List root directory", "ls", [], "")
    runner.test("7.2: List projects directory", "ls", ["projects"], "")
    runner.test("7.3: List web directory", "ls", ["projects/web"], "")
    runner.test("7.4: List frontend directory", "ls", ["projects/web/frontend"], "")
    runner.test("7.5: List mobile directory", "ls", ["projects/mobile"], "")
    
    # =================================================================
    # TEST GROUP 8: Reading Files
    # =================================================================
    print("\n\n🧪 GROUP 8: Reading Files from Various Locations")
    
    runner.test("8.1: Read root readme", "read", ["readme.txt"], "")
    runner.test("8.2: Read project list", "read", ["projects/project_list.txt"], "")
    runner.test("8.3: Read index.html", "read", ["projects/web/index.html"], "")
    runner.test("8.4: Read app.js", "read", ["projects/web/frontend/app.js"], "")
    runner.test("8.5: Read server.py", "read", ["projects/web/backend/server.py"], "")
    runner.test("8.6: Read component.jsx", "read", ["projects/web/frontend/component.jsx"], "")
    
    # =================================================================
    # TEST GROUP 9: File Operations with Context
    # =================================================================
    print("\n\n🧪 GROUP 9: File Operations in Context")
    
    runner.test("9.1: Create in ios folder", "create", ["Info.plist"], "projects/mobile/ios")
    runner.test("9.2: Write to ios file", "write", ["Info.plist", '"<plist>iOS Config</plist>"'], "projects/mobile/ios")
    runner.test("9.3: Create in android folder", "create", ["AndroidManifest.xml"], "projects/mobile/android")
    runner.test("9.4: Write to android file", "write", ["AndroidManifest.xml", '"<manifest>Android</manifest>"'], "projects/mobile/android")
    
    # =================================================================
    # TEST GROUP 10: History and Monitoring
    # =================================================================
    print("\n\n🧪 GROUP 10: History and Monitoring")
    
    runner.test("10.1: Check history", "history", ["20"], "")
    runner.test("10.2: Check node stats", "nodestats", [], "")
    runner.test("10.3: Check load balancing", "loadbal", [], "")
    
    # =================================================================
    # FINAL SUMMARY
    # =================================================================
    runner.summary()
    
    # =================================================================
    # VISUAL TREE
    # =================================================================
    print("\n\n📁 Expected Directory Structure:")
    print("""
/
├── readme.txt
├── projects/
│   ├── notes.txt
│   ├── project_list.txt
│   ├── web/
│   │   ├── index.html
│   │   ├── config.json
│   │   ├── frontend/
│   │   │   ├── app.js
│   │   │   └── component.jsx
│   │   └── backend/
│   │       └── server.py
│   └── mobile/
│       ├── readme.md
│       ├── config.xml
│       ├── package.json
│       ├── ios/
│       │   └── Info.plist
│       └── android/
│           └── AndroidManifest.xml
├── documents/
└── media/
""")
    
    return runner.passed, runner.failed


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Make sure the MiniDOS daemon is running!")
    print("Run: .\\scripts\\start_node.bat\n")
    
    input("Press Enter to start tests...")
    
    passed, failed = main()
    
    print(f"\n\n{'='*70}")
    if failed == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
    else:
        print(f"⚠️  {failed} test(s) failed. Review output above.")
    print(f"{'='*70}\n")
    
    sys.exit(0 if failed == 0 else 1)

