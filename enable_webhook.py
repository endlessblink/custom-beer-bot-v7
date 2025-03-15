#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Green API Webhook Enabler

This script enables the webhook for the Green API instance.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv(override=True)

def main():
    """Enable the webhook for the Green API instance"""
    print("\n==== Green API Webhook Enabler ====\n")
    
    # Get API credentials
    instance_id = os.environ.get('GREEN_API_ID_INSTANCE')
    api_token = os.environ.get('GREEN_API_TOKEN')
    
    if not instance_id or not api_token:
        print("❌ Missing GREEN_API_ID_INSTANCE or GREEN_API_TOKEN environment variables")
        return
    
    print(f"Instance ID: {instance_id}")
    
    # Get current settings
    try:
        print("\n1. Retrieving current settings...")
        settings_url = f"https://api.green-api.com/waInstance{instance_id}/getSettings/{api_token}"
        settings_response = requests.get(settings_url)
        
        if settings_response.status_code == 200:
            settings = settings_response.json()
            
            webhook_url = settings.get('webhookUrl', '')
            webhook_enabled = settings.get('webhookEnabled', False)
            
            print(f"✅ Current settings retrieved")
            print(f"   Current Webhook URL: {webhook_url if webhook_url else 'Not set'}")
            print(f"   Webhook Enabled: {'Yes' if webhook_enabled else 'No'}")
            
            # Check if webhook URL is already set
            if not webhook_url:
                print("\n⚠️ No webhook URL is set. Setting webhook URL is required.")
                webhook_url = input("Please enter webhook URL: ")
                if not webhook_url:
                    print("❌ No webhook URL provided. Exiting.")
                    return
            else:
                # Ask if user wants to change webhook URL
                change_url = input(f"\nDo you want to change the webhook URL? (y/n) [default: n]: ")
                if change_url.lower() == 'y':
                    webhook_url = input("Please enter new webhook URL: ")
                    if not webhook_url:
                        print("❌ No webhook URL provided. Keeping current URL.")
                        webhook_url = settings.get('webhookUrl', '')
            
            # Prepare data for updating settings
            update_data = {
                "webhookUrl": webhook_url,
                "webhookEnabled": True
            }
            
            # Update settings
            print("\n2. Enabling webhook...")
            update_url = f"https://api.green-api.com/waInstance{instance_id}/setSettings/{api_token}"
            update_response = requests.post(
                update_url,
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            
            if update_response.status_code == 200:
                print("✅ Webhook has been successfully enabled!")
                print(f"   Webhook URL: {webhook_url}")
            else:
                print(f"❌ Failed to update settings: {update_response.status_code} {update_response.text}")
        else:
            print(f"❌ Failed to retrieve settings: {settings_response.status_code} {settings_response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Verify webhook
    try:
        print("\n3. Verifying webhook connection...")
        webhook_check_url = f"https://api.green-api.com/waInstance{instance_id}/checkWebhook/{api_token}"
        webhook_check_response = requests.get(webhook_check_url)
        
        if webhook_check_response.status_code == 200:
            webhook_status = webhook_check_response.json()
            if webhook_status.get('existsWhatsapp', False):
                print(f"✅ Webhook connection verified successfully")
            else:
                print(f"❌ Webhook connection failed")
                if 'webhookStatus' in webhook_status:
                    print(f"   Status: {webhook_status['webhookStatus']}")
                print("\nTIP: Make sure your webhook server is accessible from the internet")
                print("     and is properly configured to receive POST requests.")
        else:
            print(f"❌ Failed to check webhook: {webhook_check_response.status_code} {webhook_check_response.text}")
    except Exception as e:
        print(f"❌ Error verifying webhook: {str(e)}")
    
    print("\n==== Webhook Configuration Completed ====")

if __name__ == "__main__":
    main() 