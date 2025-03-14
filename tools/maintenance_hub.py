#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WhatsApp Group Summary Bot - Maintenance Hub

This script provides a centralized interface to run all the testing,
validation, and maintenance tools for the WhatsApp Group Summary Bot.
It presents a menu of available tools and guides the user through
the process of maintaining and validating the bot's functionality.

Usage:
    python tools/maintenance_hub.py
"""

import os
import sys
import subprocess
import traceback
from pathlib import Path
import importlib.util
import time

# Add the project root to the path so we can import our modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Try to import the menu module for a consistent interface
try:
    from utils.menu.core_menu import clear_screen, print_header, show_menu, display_error_and_continue
    USE_CORE_MENU = True
except ImportError:
    USE_CORE_MENU = False
    print("Note: Core menu module could not be imported. Using fallback menu.")


def fallback_clear_screen():
    """Fallback clear screen function if core_menu is not available"""
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Unix/Linux/MacOS
        os.system('clear')


def fallback_print_header(title):
    """Fallback header printing function if core_menu is not available"""
    print("=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)
    print()


def fallback_show_menu(title, options):
    """Fallback menu function if core_menu is not available"""
    while True:
        fallback_clear_screen()
        fallback_print_header(title)
        
        for option in options:
            print(f"[{option['key']}] {option['text']}")
        
        print()
        choice = input("Enter your choice: ").strip()
        
        if any(option['key'] == choice for option in options):
            return choice
        else:
            print(f"Invalid choice: {choice}")
            time.sleep(1)


def fallback_display_error_and_continue(message, wait_for_input=True):
    """Fallback error display function if core_menu is not available"""
    print("\nERROR: " + message)
    if wait_for_input:
        input("\nPress Enter to continue...")


# Use appropriate menu functions based on availability
clear_screen = clear_screen if USE_CORE_MENU else fallback_clear_screen
print_header = print_header if USE_CORE_MENU else fallback_print_header
show_menu = show_menu if USE_CORE_MENU else fallback_show_menu
display_error_and_continue = display_error_and_continue if USE_CORE_MENU else fallback_display_error_and_continue


def run_tool(script_path, args=None):
    """Run a Python script as a subprocess"""
    if args is None:
        args = []
    
    cmd = [sys.executable, str(script_path)] + args
    
    try:
        process = subprocess.run(cmd, check=True)
        return process.returncode == 0
    except subprocess.CalledProcessError as e:
        display_error_and_continue(f"Tool execution failed with return code {e.returncode}")
        return False
    except Exception as e:
        display_error_and_continue(f"Error running tool: {e}")
        return False


def check_script_exists(script_path):
    """Check if a script exists and is executable"""
    return script_path.exists() and os.access(script_path, os.X_OK) if os.name != 'nt' else script_path.exists()


def run_menu_tests():
    """Run the menu test script"""
    clear_screen()
    print_header("Running Menu Tests")
    
    script_path = project_root / "utils" / "menu" / "test_menu.py"
    
    if check_script_exists(script_path):
        print("Starting menu tests...")
        success = run_tool(script_path)
        
        if success:
            print("\nMenu tests completed successfully!")
        else:
            print("\nMenu tests failed.")
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"Menu test script not found at {script_path}")


def run_menu_version_check():
    """Run the menu version compatibility check"""
    clear_screen()
    print_header("Running Menu Version Check")
    
    script_path = project_root / "utils" / "menu" / "version_check.py"
    
    if check_script_exists(script_path):
        print("Checking menu compatibility...")
        success = run_tool(script_path)
        
        if success:
            print("\nMenu is compatible with the current system!")
        else:
            print("\nMenu compatibility check failed. See above for details.")
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"Menu version check script not found at {script_path}")


def run_system_health_check():
    """Run the system health check tool"""
    clear_screen()
    print_header("Running System Health Check")
    
    script_path = project_root / "tools" / "system_health_check.py"
    
    if check_script_exists(script_path):
        print("Do you want to check API connections as well? (y/n)")
        check_apis = input("> ").strip().lower() == 'y'
        
        print("Do you want verbose output? (y/n)")
        verbose = input("> ").strip().lower() == 'y'
        
        args = []
        if check_apis:
            args.append("--check-apis")
        if verbose:
            args.append("--verbose")
        
        print("\nRunning system health check...")
        success = run_tool(script_path, args)
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"System health check script not found at {script_path}")


def run_full_test_suite():
    """Run the full test suite"""
    clear_screen()
    print_header("Running Full Test Suite")
    
    script_path = project_root / "tests" / "test_core_functionality.py"
    
    if check_script_exists(script_path):
        print("Running comprehensive tests...")
        success = run_tool(script_path)
        
        if success:
            print("\nAll tests completed!")
        else:
            print("\nSome tests failed. See above for details.")
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"Test suite script not found at {script_path}")


def generate_bug_report():
    """Generate a bug report"""
    clear_screen()
    print_header("Generating Bug Report")
    
    script_path = project_root / "tools" / "bug_report_generator.py"
    
    if check_script_exists(script_path):
        print("Include log files in the report? (y/n)")
        include_logs = input("> ").strip().lower() == 'y'
        
        print("Run diagnostic tests as part of the report? (y/n)")
        run_tests = input("> ").strip().lower() == 'y'
        
        args = []
        if include_logs:
            args.append("--include-logs")
        if run_tests:
            args.append("--run-tests")
        
        print("\nGenerating bug report...")
        success = run_tool(script_path, args)
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"Bug report generator script not found at {script_path}")


def check_environment_setup():
    """Check the environment setup for the bot"""
    clear_screen()
    print_header("Environment Setup Check")
    
    # Check Python version
    py_version = sys.version_info
    print(f"Python version: {sys.version.split()[0]}")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 7):
        print("⚠️ WARNING: Python version is below 3.7, which may cause compatibility issues")
    else:
        print("✓ Python version is compatible")
    
    # Check for .env file
    env_file = project_root / ".env"
    if env_file.exists():
        print("✓ .env file found")
    else:
        print("⚠️ WARNING: No .env file found. Environment variables should be set in your system")
    
    # Check for critical environment variables
    critical_vars = [
        "GREEN_API_INSTANCE_ID",
        "GREEN_API_INSTANCE_TOKEN",
        "OPENAI_API_KEY",
        "DEFAULT_LANGUAGE",
    ]
    
    missing_vars = [var for var in critical_vars if os.environ.get(var) is None]
    
    if missing_vars:
        print(f"⚠️ WARNING: Missing critical environment variables: {', '.join(missing_vars)}")
    else:
        print("✓ All critical environment variables are set")
    
    # Check for user settings
    user_settings = project_root / "user_settings.json"
    if user_settings.exists():
        print("✓ user_settings.json file found")
    else:
        print("ℹ️ No user_settings.json file found (optional)")
    
    # Check requirements installation
    try:
        import pkg_resources
        required_packages = ["openai", "python-dotenv", "requests", "supabase"]
        missing_packages = []
        
        for package in required_packages:
            try:
                pkg_resources.get_distribution(package)
            except pkg_resources.DistributionNotFound:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"⚠️ WARNING: Missing Python packages: {', '.join(missing_packages)}")
            print("  Run: pip install -r requirements.txt")
        else:
            print("✓ All required Python packages are installed")
    except ImportError:
        print("⚠️ Cannot check package installation (pkg_resources not available)")
    
    input("\nPress Enter to return to the main menu...")


def view_documentation():
    """View the project documentation"""
    while True:
        clear_screen()
        print_header("Project Documentation")
        
        docs = [
            {"path": "docs/architecture.md", "title": "System Architecture"},
            {"path": "docs/current_functionality.md", "title": "Current Functionality Documentation"},
            {"path": "utils/menu/README.md", "title": "Menu Module Documentation"},
            {"path": "README.md", "title": "Main README"}
        ]
        
        # Filter out docs that don't exist
        available_docs = [doc for doc in docs if (project_root / doc["path"]).exists()]
        
        if not available_docs:
            display_error_and_continue("No documentation files found.")
            return
        
        options = [{"key": str(i+1), "text": doc["title"]} for i, doc in enumerate(available_docs)]
        options.append({"key": "b", "text": "Back to main menu"})
        
        choice = show_menu("Select documentation to view:", options)
        
        if choice == "b":
            return
        
        try:
            doc_index = int(choice) - 1
            doc_path = project_root / available_docs[doc_index]["path"]
            
            clear_screen()
            print_header(f"Documentation: {available_docs[doc_index]['title']}")
            
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple terminal pager implementation
            lines = content.split("\n")
            page_size = os.get_terminal_size().lines - 5
            
            for i in range(0, len(lines), page_size):
                print("\n".join(lines[i:i+page_size]))
                
                if i + page_size < len(lines):
                    print("\n-- Press Enter for more, or 'q' to quit --")
                    if input().lower().strip() == 'q':
                        break
            
            input("\nPress Enter to return to documentation menu...")
        except (ValueError, IndexError):
            display_error_and_continue("Invalid selection.")
        except Exception as e:
            display_error_and_continue(f"Error displaying documentation: {e}")


def run_summary_tool():
    """Run the summary tool"""
    clear_screen()
    print_header("Generate WhatsApp Group Summary")
    
    script_path = project_root / "summary_menu.py"
    
    if check_script_exists(script_path):
        print("Running the summary menu...")
        success = run_tool(script_path)
        
        input("\nPress Enter to return to the main menu...")
    else:
        display_error_and_continue(f"Summary menu script not found at {script_path}")


def main():
    """Main function that displays the maintenance hub menu"""
    while True:
        clear_screen()
        print_header("WhatsApp Group Summary Bot - Maintenance Hub")
        
        options = [
            {"key": "1", "text": "Run Menu Tests"},
            {"key": "2", "text": "Check Menu Compatibility"},
            {"key": "3", "text": "Run System Health Check"},
            {"key": "4", "text": "Run Full Test Suite"},
            {"key": "5", "text": "Generate Bug Report"},
            {"key": "6", "text": "Check Environment Setup"},
            {"key": "7", "text": "View Documentation"},
            {"key": "8", "text": "Run Summary Tool"},
            {"key": "q", "text": "Quit"}
        ]
        
        choice = show_menu("Select a maintenance tool:", options)
        
        if choice == "1":
            run_menu_tests()
        elif choice == "2":
            run_menu_version_check()
        elif choice == "3":
            run_system_health_check()
        elif choice == "4":
            run_full_test_suite()
        elif choice == "5":
            generate_bug_report()
        elif choice == "6":
            check_environment_setup()
        elif choice == "7":
            view_documentation()
        elif choice == "8":
            run_summary_tool()
        elif choice == "q":
            clear_screen()
            print_header("Goodbye!")
            print("Thank you for using the Maintenance Hub.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMaintenance Hub interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1) 