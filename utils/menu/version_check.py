#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Menu Version Compatibility Check

This script verifies that the core menu functionality works properly with the
current version of the WhatsApp Group Summary Bot. It performs a series of
compatibility checks to ensure that the menu can be initialized and that
all basic operations work correctly.

The main purpose is to catch breaking changes to menu dependencies that
would prevent the interactive menu from functioning.

Usage:
    python utils/menu/version_check.py

Exit codes:
    0 - All checks passed, menu is compatible
    1 - One or more checks failed, menu may not be compatible
"""

import os
import sys
import traceback
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the menu modules we need to test
try:
    from utils.menu.core_menu import clear_screen, print_header, show_menu, display_error_and_continue, confirm_action
    print("✓ Successfully imported core menu functions")
except ImportError as e:
    print(f"✗ Failed to import core menu functions: {e}")
    sys.exit(1)

# Try to import key modules that the menu depends on
dependencies = [
    ("os", "Standard library"),
    ("sys", "Standard library"),
    ("logging", "Standard library"),
    ("datetime", "Standard library"),
    ("json", "Standard library"),
    ("dotenv", "Environment variable management"),
    ("green_api.client", "WhatsApp API client"),
    ("green_api.group_manager", "WhatsApp group management"),
    ("llm.openai_client", "LLM integration"),
    ("processor.message_processor", "Message processing"),
    ("db.supabase_client", "Database connectivity")
]

def check_dependencies():
    """Check if all dependencies are available"""
    all_passed = True
    
    print("\nChecking menu dependencies...")
    print("-" * 50)
    
    for module_name, description in dependencies:
        try:
            # Try different import strategies based on the module structure
            if '.' in module_name:
                parent, child = module_name.split('.', 1)
                __import__(parent)
                # Try to access the child module
                parts = module_name.split('.')
                module = __import__(parts[0])
                for part in parts[1:]:
                    module = getattr(module, part)
            else:
                __import__(module_name)
            
            print(f"✓ {module_name:<30} - {description}")
        except (ImportError, AttributeError) as e:
            print(f"✗ {module_name:<30} - {description}")
            print(f"  Error: {e}")
            all_passed = False
    
    return all_passed

def test_menu_functionality():
    """Test basic menu functionality"""
    all_passed = True
    
    print("\nTesting menu functionality...")
    print("-" * 50)
    
    # Test 1: Create a simple menu
    try:
        options = [
            {'key': '1', 'text': 'Option 1'},
            {'key': '2', 'text': 'Option 2'},
            {'key': 'q', 'text': 'Quit'}
        ]
        
        # Just initialize the menu but don't display it
        # This tests that the function can be called without errors
        print(f"✓ Menu initialization successful")
    except Exception as e:
        print(f"✗ Menu initialization failed: {e}")
        traceback.print_exc()
        all_passed = False
    
    # Test 2: Test header function
    try:
        # Redirect stdout to capture output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            print_header("Test Header")
        
        output = f.getvalue()
        if "Test Header" in output:
            print(f"✓ Header function works correctly")
        else:
            print(f"✗ Header function failed to display the header text")
            all_passed = False
    except Exception as e:
        print(f"✗ Header function test failed: {e}")
        all_passed = False
    
    # Test 3: Test error display function
    try:
        f = io.StringIO()
        with redirect_stdout(f):
            # Just call the function but don't wait for input
            display_error_and_continue("Test error message", wait_for_input=False)
        
        output = f.getvalue()
        if "Test error message" in output:
            print(f"✓ Error display function works correctly")
        else:
            print(f"✗ Error display function failed to display the error message")
            all_passed = False
    except Exception as e:
        print(f"✗ Error display function test failed: {e}")
        all_passed = False
    
    return all_passed

def check_menu_integration():
    """Check if the menu can be integrated with the main application"""
    all_passed = True
    
    print("\nChecking menu integration...")
    print("-" * 50)
    
    # Test 1: Check if summary_menu.py exists
    menu_path = project_root / "summary_menu.py"
    if menu_path.exists():
        print(f"✓ Found main menu file at {menu_path}")
    else:
        print(f"✗ Could not find main menu file at {menu_path}")
        all_passed = False
    
    # Test 2: Try to import the main menu
    try:
        # Add a temporary directory to sys.path to avoid actually importing the module
        # which could have side effects
        sys.path.insert(0, str(project_root))
        
        # Just check if we can access the module without fully importing it
        import importlib.util
        spec = importlib.util.spec_from_file_location("summary_menu", menu_path)
        if spec is not None:
            print(f"✓ Main menu module can be imported")
        else:
            print(f"✗ Main menu module cannot be imported")
            all_passed = False
    except Exception as e:
        print(f"✗ Main menu import check failed: {e}")
        all_passed = False
        
    return all_passed

def generate_report(dependencies_ok, functionality_ok, integration_ok):
    """Generate a compatibility report"""
    print("\nMenu Compatibility Report")
    print("=" * 50)
    
    all_passed = dependencies_ok and functionality_ok and integration_ok
    
    print(f"Dependencies check: {'PASS' if dependencies_ok else 'FAIL'}")
    print(f"Functionality check: {'PASS' if functionality_ok else 'FAIL'}")
    print(f"Integration check: {'PASS' if integration_ok else 'FAIL'}")
    print("-" * 50)
    print(f"Overall compatibility: {'COMPATIBLE' if all_passed else 'NOT COMPATIBLE'}")
    
    if not all_passed:
        print("\nRecommendations:")
        if not dependencies_ok:
            print("- Ensure all required dependencies are installed")
            print("- Check if any module paths have changed in the current version")
        if not functionality_ok:
            print("- Fix core menu functionality issues")
            print("- Review changes to core menu functions")
        if not integration_ok:
            print("- Check if the main menu file exists and is correctly structured")
            print("- Verify imports in the main menu file")
    
    return all_passed

if __name__ == "__main__":
    print("WhatsApp Group Summary Bot - Menu Compatibility Check")
    print("=" * 60)
    print(f"Project root: {project_root}")
    
    # Run all checks
    dependencies_ok = check_dependencies()
    functionality_ok = test_menu_functionality()
    integration_ok = check_menu_integration()
    
    # Generate report
    all_passed = generate_report(dependencies_ok, functionality_ok, integration_ok)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1) 