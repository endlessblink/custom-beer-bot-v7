#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Functionality Test Suite

This script tests all the critical functionality of the WhatsApp Group Summary Bot.
Run this script after any significant changes to ensure all features still work properly.

Usage:
    python tests/test_core_functionality.py
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules we need to test
from config.config_manager import ConfigManager
from utils.menu.core_menu import show_menu, confirm_action
from green_api.client import GreenAPIClient
from green_api.group_manager import GroupManager
from llm.openai_client import OpenAIClient
from processor.message_processor import MessageProcessor
from db.supabase_client import SupabaseClient


class TestConfigManager(unittest.TestCase):
    """Test the ConfigManager class"""
    
    def setUp(self):
        # Create a test environment
        self.test_env = {
            'TEST_VAR': 'test_value',
            'TEST_BOOL': 'true'
        }
        
        # Patch os.environ
        self.env_patcher = patch.dict('os.environ', self.test_env)
        self.env_patcher.start()
        
        # Create a ConfigManager instance
        self.config = ConfigManager()
    
    def tearDown(self):
        # Stop the patcher
        self.env_patcher.stop()
    
    def test_get_config(self):
        """Test getting config values"""
        # Test getting a string value
        self.assertEqual(self.config.get('TEST_VAR'), 'test_value')
        
        # Test getting a default value
        self.assertEqual(self.config.get('NON_EXISTENT', 'default'), 'default')
    
    def test_set_config(self):
        """Test setting config values"""
        # Set a new value
        self.config.set('NEW_VAR', 'new_value')
        
        # Check that it was set
        self.assertEqual(self.config.get('NEW_VAR'), 'new_value')


class TestGreenAPIClient(unittest.TestCase):
    """Test the GreenAPIClient class"""
    
    def setUp(self):
        # Create a mock GreenAPIClient
        self.client = GreenAPIClient(
            instance_id='test_id',
            instance_token='test_token',
            base_url='https://test.com'
        )
        
        # Mock the _make_request method
        self.client._make_request = MagicMock()
    
    def test_send_message_safety(self):
        """Test that the message sending safety measures work"""
        # Attempt to send a normal message (should be blocked)
        result = self.client.send_message('test_chat', 'test_message')
        
        # Check that the message was blocked
        self.assertIn('idMessage', result)
        self.assertTrue(result['idMessage'].startswith(('SAFETY', 'DISABLED', 'NON-SUMMARY')))
        
        # Attempt to send a summary message (should still be blocked by safety)
        result = self.client.send_message('test_chat', 'test_message', is_summary=True)
        
        # Check that the message was blocked
        self.assertIn('idMessage', result)
        self.assertTrue(result['idMessage'].startswith(('SAFETY', 'DISABLED')))
    
    def test_get_chat_history(self):
        """Test getting chat history"""
        # Mock the response from the API
        mock_response = [
            {'chatId': 'test_chat', 'textMessage': 'test_message', 'timestamp': 1234567890}
        ]
        self.client._make_request.return_value = mock_response
        
        # Get the chat history
        result = self.client.get_chat_history('test_chat')
        
        # Check that the correct API endpoint was called
        self.client._make_request.assert_called_once()
        call_args = self.client._make_request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertIn('getChatHistory', call_args[1])
        
        # Check that the result is the mock response
        self.assertEqual(result, mock_response)


class TestMessageProcessor(unittest.TestCase):
    """Test the MessageProcessor class"""
    
    def setUp(self):
        # Create a MessageProcessor instance
        self.processor = MessageProcessor(target_language='english')
        
        # Create some test messages
        self.test_messages = [
            {
                'chatId': 'test_chat',
                'senderName': 'Test User',
                'textMessage': 'Hello, world!',
                'timestamp': int(datetime.now().timestamp())
            },
            {
                'chatId': 'test_chat',
                'senderName': 'Test User 2',
                'textMessage': 'How are you?',
                'timestamp': int(datetime.now().timestamp()) - 60
            }
        ]
    
    def test_process_messages(self):
        """Test processing messages"""
        # Process the test messages
        processed = self.processor.process_messages(self.test_messages)
        
        # Check that we got the right number of messages
        self.assertEqual(len(processed), 2)
        
        # Check that the messages were processed correctly
        self.assertIn('sender', processed[0])
        self.assertIn('content', processed[0])
        self.assertIn('timestamp', processed[0])
        
        # Check that the sender name was extracted
        self.assertEqual(processed[0]['sender'], 'Test User')
        
        # Check that the content was extracted
        self.assertEqual(processed[0]['content'], 'Hello, world!')


class TestOpenAIClient(unittest.TestCase):
    """Test the OpenAIClient class"""
    
    def setUp(self):
        # Create a mock OpenAIClient
        self.client = OpenAIClient(
            api_key='test_key',
            model='gpt-4o-mini',
            max_tokens=1000
        )
        
        # Mock the client's OpenAI client
        self.client.client = MagicMock()
        
        # Create some test messages
        self.test_messages = [
            {
                'sender': 'Test User',
                'content': 'Hello, world!',
                'timestamp': datetime.now().isoformat()
            },
            {
                'sender': 'Test User 2',
                'content': 'How are you?',
                'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()
            }
        ]
    
    def test_generate_summary(self):
        """Test generating a summary"""
        # Mock the response from OpenAI
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test summary."
        self.client.client.chat.completions.create.return_value = mock_response
        
        # Generate a summary
        summary = self.client.generate_summary(self.test_messages)
        
        # Check that the OpenAI API was called
        self.client.client.chat.completions.create.assert_called_once()
        
        # Check that the summary is the mock response
        self.assertEqual(summary, "This is a test summary.")


class TestMenuFunctionality(unittest.TestCase):
    """Test the menu functionality"""
    
    def test_show_menu(self):
        """Test showing a menu and selecting an option"""
        options = [
            {'key': '1', 'text': 'Option 1'},
            {'key': '2', 'text': 'Option 2'},
            {'key': '3', 'text': 'Exit'}
        ]
        
        # Test with valid input
        with patch('builtins.input', return_value='2'):
            with patch('sys.stdout'):  # Suppress output
                result = show_menu("Test Menu", options)
                self.assertEqual(result, '2')
        
        # Test with invalid input then valid input
        with patch('builtins.input', side_effect=['x', '3']):
            with patch('sys.stdout'):  # Suppress output
                result = show_menu("Test Menu", options)
                self.assertEqual(result, '3')
    
    def test_confirm_action(self):
        """Test confirming an action"""
        # Test with 'y' input
        with patch('builtins.input', return_value='y'):
            with patch('sys.stdout'):  # Suppress output
                result = confirm_action("Confirm?")
                self.assertTrue(result)
        
        # Test with 'n' input
        with patch('builtins.input', return_value='n'):
            with patch('sys.stdout'):  # Suppress output
                result = confirm_action("Confirm?")
                self.assertFalse(result)


class TestUserSettings(unittest.TestCase):
    """Test user settings functionality"""
    
    def setUp(self):
        # Create a temporary user settings file
        self.settings_file = 'test_user_settings.json'
        self.test_settings = {
            'PREFERRED_GROUP_ID': 'test_group',
            'OPENAI_MODEL': 'gpt-4o-mini'
        }
        
        # Write the test settings to the file
        with open(self.settings_file, 'w') as f:
            json.dump(self.test_settings, f)
    
    def tearDown(self):
        # Remove the temporary file
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)
    
    @patch('summary_menu.os.path.exists')
    @patch('summary_menu.open')
    @patch('summary_menu.json.load')
    def test_load_user_settings(self, mock_json_load, mock_open, mock_exists):
        """Test loading user settings"""
        # Set up mocks
        mock_exists.return_value = True
        mock_json_load.return_value = self.test_settings
        
        # Import the function
        from summary_menu import load_user_settings
        
        # Create a mock environment
        with patch.dict('os.environ', {}):
            # Load user settings
            load_user_settings()
            
            # Check that the settings were loaded into environment variables
            self.assertEqual(os.environ.get('PREFERRED_GROUP_ID'), 'test_group')
            self.assertEqual(os.environ.get('OPENAI_MODEL'), 'gpt-4o-mini')


def run_all_tests():
    """Run all tests"""
    # Create a test suite with all tests
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestConfigManager))
    test_suite.addTest(unittest.makeSuite(TestGreenAPIClient))
    test_suite.addTest(unittest.makeSuite(TestMessageProcessor))
    test_suite.addTest(unittest.makeSuite(TestOpenAIClient))
    test_suite.addTest(unittest.makeSuite(TestMenuFunctionality))
    test_suite.addTest(unittest.makeSuite(TestUserSettings))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)


if __name__ == "__main__":
    print("Running tests for core functionality...")
    print("=" * 80)
    
    # Create the tests directory if it doesn't exist
    if not os.path.exists(os.path.dirname(__file__)):
        os.makedirs(os.path.dirname(__file__))
    
    # Run all tests
    run_all_tests()
    
    print("=" * 80)
    print("Tests complete!") 