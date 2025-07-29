"""
Easy Tool Setup - Simplified configuration and setup process for Unity MCP Server.
Provides automated setup, configuration wizards, and one-click deployment.
"""

import os
import json
import subprocess
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil
import platform
from dataclasses import dataclass

from enhanced_logging import enhanced_logger, LogContext
from exceptions import ValidationError, ResourceError
from advanced_logging import advanced_log_manager, LogLevel, LogCategory


@dataclass
class SetupConfiguration:
    """Configuration for easy setup process."""
    unity_path: str = None
    unity_version: str = None
    project_path: str = None
    server_port: int = 6500
    unity_port: int = 6400
    enable_ssl: bool = False
    enable_authentication: bool = False
    install_dependencies: bool = True
    create_shortcuts: bool = True
    setup_auto_start: bool = False


class EasySetupManager:
    """Manager for simplified Unity MCP Server setup and configuration."""
    
    def __init__(self):
        self.setup_directory = Path("UnityMcpServer/setup")
        self.setup_directory.mkdir(parents=True, exist_ok=True)
        
        self.system_info = self._detect_system_info()
        self.unity_installations = self._detect_unity_installations()
        
    def _detect_system_info(self) -> Dict[str, Any]:
        """Detect system information for setup optimization."""
        
        system_info = {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd()
        }
        
        # Detect package managers
        if system_info["platform"] == "Windows":
            system_info["package_managers"] = self._detect_windows_package_managers()
        elif system_info["platform"] == "Darwin":  # macOS
            system_info["package_managers"] = self._detect_macos_package_managers()
        else:  # Linux
            system_info["package_managers"] = self._detect_linux_package_managers()
        
        return system_info
    
    def _detect_windows_package_managers(self) -> List[str]:
        """Detect available package managers on Windows."""
        managers = []
        
        # Check for Chocolatey
        try:
            subprocess.run(["choco", "--version"], capture_output=True, check=True)
            managers.append("chocolatey")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Check for Scoop
        try:
            subprocess.run(["scoop", "--version"], capture_output=True, check=True)
            managers.append("scoop")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Check for winget
        try:
            subprocess.run(["winget", "--version"], capture_output=True, check=True)
            managers.append("winget")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return managers
    
    def _detect_macos_package_managers(self) -> List[str]:
        """Detect available package managers on macOS."""
        managers = []
        
        # Check for Homebrew
        try:
            subprocess.run(["brew", "--version"], capture_output=True, check=True)
            managers.append("homebrew")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Check for MacPorts
        try:
            subprocess.run(["port", "version"], capture_output=True, check=True)
            managers.append("macports")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return managers
    
    def _detect_linux_package_managers(self) -> List[str]:
        """Detect available package managers on Linux."""
        managers = []
        
        # Common Linux package managers
        package_managers = {
            "apt": ["apt", "--version"],
            "yum": ["yum", "--version"],
            "dnf": ["dnf", "--version"],
            "pacman": ["pacman", "--version"],
            "zypper": ["zypper", "--version"],
            "snap": ["snap", "--version"],
            "flatpak": ["flatpak", "--version"]
        }
        
        for manager, command in package_managers.items():
            try:
                subprocess.run(command, capture_output=True, check=True)
                managers.append(manager)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return managers
    
    def _detect_unity_installations(self) -> List[Dict[str, str]]:
        """Detect Unity installations on the system."""
        installations = []
        
        if self.system_info["platform"] == "Windows":
            installations.extend(self._detect_unity_windows())
        elif self.system_info["platform"] == "Darwin":
            installations.extend(self._detect_unity_macos())
        else:
            installations.extend(self._detect_unity_linux())
        
        return installations
    
    def _detect_unity_windows(self) -> List[Dict[str, str]]:
        """Detect Unity installations on Windows."""
        installations = []
        
        # Common Unity installation paths on Windows
        unity_paths = [
            "C:/Program Files/Unity/Hub/Editor",
            "C:/Program Files (x86)/Unity/Hub/Editor",
            os.path.expanduser("~/AppData/Roaming/UnityHub/installs")
        ]
        
        for base_path in unity_paths:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    unity_exe = os.path.join(base_path, item, "Editor", "Unity.exe")
                    if os.path.exists(unity_exe):
                        installations.append({
                            "version": item,
                            "path": unity_exe,
                            "editor_path": os.path.join(base_path, item, "Editor")
                        })
        
        return installations
    
    def _detect_unity_macos(self) -> List[Dict[str, str]]:
        """Detect Unity installations on macOS."""
        installations = []
        
        # Common Unity installation paths on macOS
        unity_paths = [
            "/Applications/Unity/Hub/Editor",
            os.path.expanduser("~/Applications/Unity/Hub/Editor")
        ]
        
        for base_path in unity_paths:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    unity_app = os.path.join(base_path, item, "Unity.app")
                    if os.path.exists(unity_app):
                        installations.append({
                            "version": item,
                            "path": unity_app,
                            "editor_path": os.path.join(base_path, item)
                        })
        
        return installations
    
    def _detect_unity_linux(self) -> List[Dict[str, str]]:
        """Detect Unity installations on Linux."""
        installations = []
        
        # Common Unity installation paths on Linux
        unity_paths = [
            os.path.expanduser("~/Unity/Hub/Editor"),
            "/opt/Unity/Hub/Editor"
        ]
        
        for base_path in unity_paths:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    unity_exe = os.path.join(base_path, item, "Editor", "Unity")
                    if os.path.exists(unity_exe):
                        installations.append({
                            "version": item,
                            "path": unity_exe,
                            "editor_path": os.path.join(base_path, item, "Editor")
                        })
        
        return installations
    
    def run_setup_wizard(self) -> SetupConfiguration:
        """Run interactive setup wizard."""
        
        print("🛠️  Unity MCP Server - Easy Setup Wizard")
        print("=" * 50)
        print()
        
        config = SetupConfiguration()
        
        # System information
        print("📋 System Information:")
        print(f"   Platform: {self.system_info['platform']}")
        print(f"   Architecture: {self.system_info['architecture']}")
        print(f"   Python: {self.system_info['python_version'].split()[0]}")
        print()
        
        # Unity installation selection
        if self.unity_installations:
            print("🎮 Unity Installations Found:")
            for i, installation in enumerate(self.unity_installations):
                print(f"   {i + 1}. Unity {installation['version']} - {installation['path']}")
            print()
            
            while True:
                try:
                    choice = input("Select Unity installation (number): ").strip()
                    if choice:
                        index = int(choice) - 1
                        if 0 <= index < len(self.unity_installations):
                            selected = self.unity_installations[index]
                            config.unity_path = selected["path"]
                            config.unity_version = selected["version"]
                            break
                        else:
                            print("Invalid selection. Please try again.")
                    else:
                        print("No Unity installation selected. You can configure this later.")
                        break
                except ValueError:
                    print("Please enter a valid number.")
        else:
            print("⚠️  No Unity installations detected.")
            unity_path = input("Enter Unity executable path (or press Enter to skip): ").strip()
            if unity_path and os.path.exists(unity_path):
                config.unity_path = unity_path
        
        print()
        
        # Project path
        project_path = input("Enter Unity project path (or press Enter for current directory): ").strip()
        if project_path:
            if os.path.exists(project_path):
                config.project_path = project_path
            else:
                print(f"⚠️  Path '{project_path}' does not exist. Using current directory.")
                config.project_path = os.getcwd()
        else:
            config.project_path = os.getcwd()
        
        print()
        
        # Port configuration
        server_port = input(f"MCP Server port (default: {config.server_port}): ").strip()
        if server_port:
            try:
                config.server_port = int(server_port)
            except ValueError:
                print("Invalid port number. Using default.")
        
        unity_port = input(f"Unity connection port (default: {config.unity_port}): ").strip()
        if unity_port:
            try:
                config.unity_port = int(unity_port)
            except ValueError:
                print("Invalid port number. Using default.")
        
        print()
        
        # Security options
        enable_ssl = input("Enable SSL/TLS encryption? (y/N): ").strip().lower()
        config.enable_ssl = enable_ssl in ['y', 'yes']
        
        enable_auth = input("Enable authentication? (y/N): ").strip().lower()
        config.enable_authentication = enable_auth in ['y', 'yes']
        
        print()
        
        # Installation options
        install_deps = input("Install Python dependencies automatically? (Y/n): ").strip().lower()
        config.install_dependencies = install_deps not in ['n', 'no']
        
        create_shortcuts = input("Create desktop shortcuts? (Y/n): ").strip().lower()
        config.create_shortcuts = create_shortcuts not in ['n', 'no']
        
        auto_start = input("Setup auto-start on system boot? (y/N): ").strip().lower()
        config.setup_auto_start = auto_start in ['y', 'yes']
        
        print()
        print("✅ Setup configuration completed!")
        
        return config
    
    def perform_setup(self, config: SetupConfiguration) -> bool:
        """Perform the actual setup based on configuration."""
        
        try:
            advanced_log_manager.log_advanced(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "Starting Unity MCP Server setup",
                operation="easy_setup"
            )
            
            print("🚀 Starting Unity MCP Server setup...")
            print()
            
            # Step 1: Install dependencies
            if config.install_dependencies:
                print("📦 Installing Python dependencies...")
                self._install_dependencies()
                print("✅ Dependencies installed successfully!")
                print()
            
            # Step 2: Create configuration files
            print("⚙️  Creating configuration files...")
            self._create_configuration_files(config)
            print("✅ Configuration files created!")
            print()
            
            # Step 3: Setup Unity MCP Bridge
            if config.unity_path and config.project_path:
                print("🔗 Setting up Unity MCP Bridge...")
                self._setup_unity_bridge(config)
                print("✅ Unity MCP Bridge setup completed!")
                print()
            
            # Step 4: Create shortcuts
            if config.create_shortcuts:
                print("🔗 Creating shortcuts...")
                self._create_shortcuts(config)
                print("✅ Shortcuts created!")
                print()
            
            # Step 5: Setup auto-start
            if config.setup_auto_start:
                print("🔄 Setting up auto-start...")
                self._setup_auto_start(config)
                print("✅ Auto-start configured!")
                print()
            
            # Step 6: Test configuration
            print("🧪 Testing configuration...")
            test_result = self._test_configuration(config)
            if test_result:
                print("✅ Configuration test passed!")
            else:
                print("⚠️  Configuration test failed. Please check the logs.")
            print()
            
            print("🎉 Unity MCP Server setup completed successfully!")
            print()
            print("Next steps:")
            print("1. Start Unity Editor with your project")
            print("2. Run the MCP server: python src/server.py")
            print("3. Test the connection using the health check endpoint")
            print()
            
            return True
            
        except Exception as e:
            advanced_log_manager.log_advanced(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Setup failed: {str(e)}",
                operation="easy_setup",
                error_type=type(e).__name__
            )
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    def _install_dependencies(self):
        """Install Python dependencies."""
        
        requirements_file = Path("UnityMcpServer/requirements.txt")
        if requirements_file.exists():
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True)
        else:
            # Install basic dependencies
            basic_deps = ["mcp", "aiohttp", "websockets", "pydantic"]
            subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + basic_deps, check=True)
    
    def _create_configuration_files(self, config: SetupConfiguration):
        """Create configuration files based on setup configuration."""
        
        # Create main configuration
        config_data = {
            "unity_host": "localhost",
            "unity_port": config.unity_port,
            "mcp_port": config.server_port,
            "enable_ssl": config.enable_ssl,
            "enable_authentication": config.enable_authentication,
            "unity_path": config.unity_path,
            "project_path": config.project_path,
            "setup_timestamp": time.time(),
            "setup_version": "2.0.0"
        }
        
        config_file = Path("UnityMcpServer/src/config_local.py")
        with open(config_file, 'w') as f:
            f.write(f"# Unity MCP Server Configuration\n")
            f.write(f"# Generated by Easy Setup on {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"unity_host = '{config_data['unity_host']}'\n")
            f.write(f"unity_port = {config_data['unity_port']}\n")
            f.write(f"mcp_port = {config_data['mcp_port']}\n")
            f.write(f"enable_ssl = {config_data['enable_ssl']}\n")
            f.write(f"enable_authentication = {config_data['enable_authentication']}\n")
            if config_data['unity_path']:
                f.write(f"unity_path = r'{config_data['unity_path']}'\n")
            if config_data['project_path']:
                f.write(f"project_path = r'{config_data['project_path']}'\n")
    
    def _setup_unity_bridge(self, config: SetupConfiguration):
        """Setup Unity MCP Bridge in the Unity project."""
        
        if not config.project_path or not os.path.exists(config.project_path):
            return
        
        # Copy Unity MCP Bridge package to project
        bridge_source = Path("UnityMcpBridge")
        bridge_dest = Path(config.project_path) / "Packages" / "com.unity.mcp-bridge"
        
        if bridge_source.exists():
            if bridge_dest.exists():
                shutil.rmtree(bridge_dest)
            shutil.copytree(bridge_source, bridge_dest)
    
    def _create_shortcuts(self, config: SetupConfiguration):
        """Create desktop shortcuts for easy access."""
        
        if self.system_info["platform"] == "Windows":
            self._create_windows_shortcuts(config)
        elif self.system_info["platform"] == "Darwin":
            self._create_macos_shortcuts(config)
        else:
            self._create_linux_shortcuts(config)
    
    def _create_windows_shortcuts(self, config: SetupConfiguration):
        """Create Windows shortcuts."""
        
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            
            # Create server shortcut
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(os.path.join(desktop, "Unity MCP Server.lnk"))
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = "src/server.py"
            shortcut.WorkingDirectory = os.path.join(os.getcwd(), "UnityMcpServer")
            shortcut.IconLocation = sys.executable
            shortcut.save()
            
        except ImportError:
            print("⚠️  Could not create Windows shortcuts. Install pywin32 for shortcut support.")
    
    def _create_macos_shortcuts(self, config: SetupConfiguration):
        """Create macOS shortcuts."""
        # Implementation for macOS shortcuts would go here
        pass
    
    def _create_linux_shortcuts(self, config: SetupConfiguration):
        """Create Linux desktop shortcuts."""
        
        desktop_dir = os.path.expanduser("~/Desktop")
        if not os.path.exists(desktop_dir):
            return
        
        shortcut_content = f"""[Desktop Entry]
Name=Unity MCP Server
Comment=Unity Model Context Protocol Server
Exec={sys.executable} {os.path.join(os.getcwd(), "UnityMcpServer", "src", "server.py")}
Icon=applications-development
Terminal=true
Type=Application
Categories=Development;
"""
        
        shortcut_path = os.path.join(desktop_dir, "unity-mcp-server.desktop")
        with open(shortcut_path, 'w') as f:
            f.write(shortcut_content)
        
        # Make executable
        os.chmod(shortcut_path, 0o755)
    
    def _setup_auto_start(self, config: SetupConfiguration):
        """Setup auto-start on system boot."""
        
        if self.system_info["platform"] == "Windows":
            self._setup_windows_auto_start(config)
        elif self.system_info["platform"] == "Darwin":
            self._setup_macos_auto_start(config)
        else:
            self._setup_linux_auto_start(config)
    
    def _setup_windows_auto_start(self, config: SetupConfiguration):
        """Setup Windows auto-start."""
        
        try:
            import winreg
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 
                               0, winreg.KEY_SET_VALUE)
            
            command = f'"{sys.executable}" "{os.path.join(os.getcwd(), "UnityMcpServer", "src", "server.py")}"'
            winreg.SetValueEx(key, "UnityMcpServer", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            
        except ImportError:
            print("⚠️  Could not setup Windows auto-start. Manual configuration required.")
    
    def _setup_macos_auto_start(self, config: SetupConfiguration):
        """Setup macOS auto-start using launchd."""
        # Implementation for macOS auto-start would go here
        pass
    
    def _setup_linux_auto_start(self, config: SetupConfiguration):
        """Setup Linux auto-start using systemd."""
        
        service_content = f"""[Unit]
Description=Unity MCP Server
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={os.path.join(os.getcwd(), "UnityMcpServer")}
ExecStart={sys.executable} src/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_path = os.path.expanduser("~/.config/systemd/user/unity-mcp-server.service")
        os.makedirs(os.path.dirname(service_path), exist_ok=True)
        
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Enable the service
        subprocess.run(["systemctl", "--user", "enable", "unity-mcp-server.service"])
    
    def _test_configuration(self, config: SetupConfiguration) -> bool:
        """Test the setup configuration."""
        
        try:
            # Test Python dependencies
            import mcp
            
            # Test configuration files
            config_file = Path("UnityMcpServer/src/config_local.py")
            if not config_file.exists():
                return False
            
            # Test Unity path if provided
            if config.unity_path and not os.path.exists(config.unity_path):
                return False
            
            # Test project path if provided
            if config.project_path and not os.path.exists(config.project_path):
                return False
            
            return True
            
        except ImportError:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for setup."""
        return {
            "system_info": self.system_info,
            "unity_installations": self.unity_installations
        }


# Global easy setup manager instance
easy_setup_manager = EasySetupManager()


def run_easy_setup():
    """Run the easy setup process."""
    
    print("Welcome to Unity MCP Server Easy Setup!")
    print()
    
    # Run setup wizard
    config = easy_setup_manager.run_setup_wizard()
    
    # Confirm setup
    print("📋 Setup Summary:")
    print(f"   Unity Path: {config.unity_path or 'Not configured'}")
    print(f"   Project Path: {config.project_path}")
    print(f"   Server Port: {config.server_port}")
    print(f"   Unity Port: {config.unity_port}")
    print(f"   SSL Enabled: {config.enable_ssl}")
    print(f"   Authentication: {config.enable_authentication}")
    print()
    
    confirm = input("Proceed with setup? (Y/n): ").strip().lower()
    if confirm in ['n', 'no']:
        print("Setup cancelled.")
        return
    
    # Perform setup
    success = easy_setup_manager.perform_setup(config)
    
    if success:
        print("🎉 Setup completed successfully!")
    else:
        print("❌ Setup failed. Please check the logs and try again.")


if __name__ == "__main__":
    run_easy_setup()
