"""
MiniShell
Centralized command-line interface for MiniDOS
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.commands import CommandExecutor

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Fallback for no colorama
    class Fore:
        RED = GREEN = YELLOW = CYAN = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""


class MiniShell:
    """Interactive shell for MiniDOS"""
    
    def __init__(self, node_address: str = "localhost", node_port: int = 9000):
        self.executor = CommandExecutor(node_address, node_port)
        self.running = False
        self.history = []
        self.current_dir = ""  # Current working directory (relative to VFS root)
        
        # Setup minimal logging for CLI
        logging.basicConfig(
            level=logging.WARNING,
            format='%(message)s'
        )
    
    def start(self):
        """Start the interactive shell"""
        self.running = True
        
        self._print_banner()
        
        while self.running:
            try:
                # Display prompt with current directory
                if HAS_COLOR:
                    dir_display = f"/{self.current_dir}" if self.current_dir else "/"
                    prompt = f"{Fore.CYAN}{Style.BRIGHT}MiniDOS:{dir_display}>{Style.RESET_ALL} "
                else:
                    dir_display = f"/{self.current_dir}" if self.current_dir else "/"
                    prompt = f"MiniDOS:{dir_display}> "
                
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Add to history
                self.history.append(user_input)
                
                # Parse command
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:]
                
                # Check for exit
                if command in ['exit', 'quit']:
                    self._print_info("Goodbye!")
                    break
                
                # Check for cd command (handled locally)
                if command == 'cd':
                    self._handle_cd(args)
                    continue
                
                # Check for pwd command (handled locally)
                if command == 'pwd':
                    self._handle_pwd()
                    continue
                
                # Execute command (with current directory context)
                success, message, data = self.executor.execute(command, args, self.current_dir)
                
                # Display result
                if success:
                    self._print_success(message)
                else:
                    self._print_error(message)
                
            except KeyboardInterrupt:
                print()
                self._print_info("Use 'exit' to quit")
            except EOFError:
                print()
                break
            except Exception as e:
                self._print_error(f"Shell error: {e}")
        
        self.running = False
    
    def _print_banner(self):
        """Print startup banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              MiniDOS - Distributed OS Shell               ║
║                    Version 1.0.0                          ║
║                                                           ║
║  Type 'help' for available commands                       ║
║  Type 'exit' to quit                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
        if HAS_COLOR:
            print(f"{Fore.CYAN}{banner}{Style.RESET_ALL}")
        else:
            print(banner)
    
    def _print_success(self, message: str):
        """Print success message"""
        if HAS_COLOR:
            print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
        else:
            print(f"[OK] {message}")
    
    def _print_error(self, message: str):
        """Print error message"""
        if HAS_COLOR:
            print(f"{Fore.RED}Error: {message}{Style.RESET_ALL}")
        else:
            print(f"[ERROR] {message}")
    
    def _print_info(self, message: str):
        """Print info message"""
        if HAS_COLOR:
            print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
        else:
            print(f"[INFO] {message}")
    
    def _handle_cd(self, args):
        """Handle cd (change directory) command"""
        if not args:
            # cd with no args goes to root
            self.current_dir = ""
            self._print_success("Changed to root directory")
            return
        
        target = args[0]
        
        # Handle special cases
        if target == "/":
            self.current_dir = ""
            self._print_success("Changed to root directory")
            return
        
        if target == "..":
            # Go up one directory
            if self.current_dir:
                parts = self.current_dir.split("/")
                if len(parts) > 1:
                    self.current_dir = "/".join(parts[:-1])
                else:
                    self.current_dir = ""
                self._print_success(f"Changed to /{self.current_dir}" if self.current_dir else "Changed to root directory")
            else:
                self._print_info("Already at root directory")
            return
        
        # Build new path
        if target.startswith("/"):
            # Absolute path
            new_path = target.lstrip("/")
        else:
            # Relative path
            if self.current_dir:
                new_path = f"{self.current_dir}/{target}"
            else:
                new_path = target
        
        # Verify directory exists by trying to list it
        success, message, data = self.executor.execute("ls", [new_path], "")
        if success:
            self.current_dir = new_path
            self._print_success(f"Changed to /{new_path}")
        else:
            self._print_error(f"Directory not found: {target}")
    
    def _handle_pwd(self):
        """Handle pwd (print working directory) command"""
        if self.current_dir:
            self._print_success(f"/{self.current_dir}")
        else:
            self._print_success("/")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MiniDOS Interactive Shell")
    parser.add_argument('--host', default='localhost', help='Node daemon host')
    parser.add_argument('--port', type=int, default=9000, help='Node daemon port')
    args = parser.parse_args()
    
    shell = MiniShell(args.host, args.port)
    
    try:
        shell.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

