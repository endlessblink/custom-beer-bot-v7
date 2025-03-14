#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Menu Testing Utility

This script tests the core menu functionality to ensure it's working properly.
Run this script periodically or after any major changes to verify that the 
menu system is intact and functioning as expected.

Usage:
    python utils/menu/test_menu.py
"""

import os
import sys
import time
from io import StringIO
from unittest.mock import patch

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the menu module
from utils.menu.core_menu import clear_screen, print_header, show_menu, display_error_and_continue, confirm_action

def test_print_header():
    """Test the print_header function"""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        print_header("TEST HEADER")
        output = fake_out.getvalue()
        
        # Check that the header was printed
        assert "=" * 60 in output
        assert "TEST HEADER" in output
        
        print("✅ print_header test passed")

def test_show_menu():
    """Test the show_menu function with mocked input"""
    options = [
        {'key': '1', 'text': 'Option 1'},
        {'key': '2', 'text': 'Option 2'},
        {'key': '3', 'text': 'Exit'}
    ]
    
    # Test with valid input
    with patch('builtins.input', return_value='2'):
        with patch('sys.stdout', new=StringIO()):
            result = show_menu("Test Menu", options)
            assert result == '2', f"Expected '2', got '{result}'"
    
    # Test with invalid input then valid input
    with patch('builtins.input', side_effect=['x', '3']):
        with patch('sys.stdout', new=StringIO()):
            result = show_menu("Test Menu", options)
            assert result == '3', f"Expected '3', got '{result}'"
    
    print("✅ show_menu test passed")

def test_show_menu_with_requirements():
    """Test the show_menu function with component requirements"""
    options = [
        {'key': '1', 'text': 'Option 1', 'requires': ['component1']},
        {'key': '2', 'text': 'Option 2', 'requires': ['component2']},
        {'key': '3', 'text': 'Exit'}
    ]
    
    components = {
        'component1': True,
        'component2': None
    }
    
    # Test selecting an option with an available required component
    with patch('builtins.input', return_value='1'):
        with patch('sys.stdout', new=StringIO()):
            result = show_menu("Test Menu", options, components)
            assert result == '1', f"Expected '1', got '{result}'"
    
    # Test selecting an option with an unavailable required component, then a valid option
    with patch('builtins.input', side_effect=['2', '3']):
        with patch('sys.stdout', new=StringIO()):
            with patch('builtins.input', side_effect=['', '3']):  # For the "Press Enter to continue"
                result = show_menu("Test Menu", options, components)
                assert result == '3', f"Expected '3', got '{result}'"
    
    print("✅ show_menu with requirements test passed")

def test_confirm_action():
    """Test the confirm_action function"""
    # Test with 'y' input
    with patch('builtins.input', return_value='y'):
        with patch('sys.stdout', new=StringIO()):
            result = confirm_action("Confirm?")
            assert result is True, f"Expected True, got {result}"
    
    # Test with 'n' input
    with patch('builtins.input', return_value='n'):
        with patch('sys.stdout', new=StringIO()):
            result = confirm_action("Confirm?")
            assert result is False, f"Expected False, got {result}"
    
    # Test with Hebrew input
    with patch('builtins.input', return_value='כ'):
        with patch('sys.stdout', new=StringIO()):
            result = confirm_action("Confirm?")
            assert result is True, f"Expected True, got {result}"
    
    print("✅ confirm_action test passed")

def run_menu_tests():
    """Run all menu tests"""
    print("🧪 Running menu tests...")
    print("=" * 60)
    
    try:
        test_print_header()
        test_show_menu()
        test_confirm_action()
        
        print("=" * 60)
        print("✅ All tests passed! The menu module is functioning correctly.")
        return True
    except AssertionError as e:
        print("=" * 60)
        print(f"❌ Test failed: {str(e)}")
        return False
    except Exception as e:
        print("=" * 60)
        print(f"❌ Unexpected error during tests: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_menu_tests()
    sys.exit(0 if success else 1) 