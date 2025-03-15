#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Green API Webhook Checker

This script checks the status and configuration of the Green API webhooks
and verifies that the instance is active and receiving notifications.
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv(override=True)

# Import project components
from green_api.client import GreenAPIClient
from utils.logger import setup_logger

# Configure logging
logger = setup_logger("INFO")

def main():
    """Check Green API webhook status and configuration"""
    print("\n==== Green API Webhook Checker ====\n")
    
    # Get API credentials
    instance_id = os.environ.get('GREEN_API_ID_INSTANCE')
    api_token = os.environ.get('GREEN_API_TOKEN')
    
    if not instance_id or not api_token:
        print("❌ Missing GREEN_API_ID_INSTANCE or GREEN_API_TOKEN environment variables")
        return
    
    print(f"Instance ID: {instance_id}")
    
    # Initialize Green API client
    try:
        print("\n1. Initializing Green API client...")
        green_api_client = GreenAPIClient(
            instance_id=instance_id,
            instance_token=api_token
        )
        print("✅ Green API client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Green API client: {str(e)}")
        return
    
    # Check instance state
    try:
        print("\n2. Checking instance state...")
        
        # Direct API call to getStateInstance
        api_url = f"https://api.green-api.com/waInstance{instance_id}/getStateInstance/{api_token}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            state_data = response.json()
            print(f"✅ Instance state retrieved successfully")
            print(f"   State: {state_data.get('stateInstance', 'Unknown')}")
            print(f"   Status: {state_data.get('statusInstance', 'Unknown')}")
            
            if state_data.get('stateInstance') != 'authorized':
                print("❌ Instance is not authorized. Please scan the QR code to authorize.")
                # Get QR code link if needed
                try:
                    qr_api_url = f"https://api.green-api.com/waInstance{instance_id}/qr/{api_token}"
                    qr_response = requests.get(qr_api_url)
                    if qr_response.status_code == 200:
                        qr_data = qr_response.json()
                        if 'urlCode' in qr_data:
                            print(f"   QR Code URL: {qr_data['urlCode']}")
                    else:
                        print(f"   Failed to retrieve QR code: {qr_response.status_code} {qr_response.text}")
                except Exception as qr_ex:
                    print(f"   Error retrieving QR code: {str(qr_ex)}")
                
                return
        else:
            print(f"❌ Failed to retrieve instance state: {response.status_code} {response.text}")
            return
    except Exception as e:
        print(f"❌ Error checking instance state: {str(e)}")
        return
    
    # Check webhook settings
    try:
        print("\n3. Checking webhook settings...")
        
        # Direct API call to getSettings
        settings_url = f"https://api.green-api.com/waInstance{instance_id}/getSettings/{api_token}"
        settings_response = requests.get(settings_url)
        
        if settings_response.status_code == 200:
            settings = settings_response.json()
            
            webhook_url = settings.get('webhookUrl', 'Not set')
            webhook_enabled = settings.get('webhookEnabled', False)
            incoming_webhook = settings.get('incomingWebhook', 'Not set')
            outgoing_webhook = settings.get('outgoingWebhook', 'Not set')
            
            print(f"✅ Settings retrieved successfully")
            print(f"   Webhook URL: {webhook_url}")
            print(f"   Webhook Enabled: {'Yes' if webhook_enabled else 'No'}")
            print(f"   Incoming Webhook: {incoming_webhook}")
            print(f"   Outgoing Webhook: {outgoing_webhook}")
            
            # Check if webhook is properly configured
            if not webhook_url or not webhook_enabled:
                print("❌ Webhook is not properly configured")
                print("   To set webhook URL, run:")
                print(f"   curl -X POST 'https://api.green-api.com/waInstance{instance_id}/setSettings/{api_token}' -H 'Content-Type: application/json' -d '{{'webhookUrl': 'YOUR_WEBHOOK_URL', 'webhookEnabled': true}}'")
            else:
                # Verify webhook connectivity
                try:
                    print("\n4. Verifying webhook connectivity...")
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
                    else:
                        print(f"❌ Failed to check webhook: {webhook_check_response.status_code} {webhook_check_response.text}")
                except Exception as verify_ex:
                    print(f"❌ Error verifying webhook: {str(verify_ex)}")
        else:
            print(f"❌ Failed to retrieve settings: {settings_response.status_code} {settings_response.text}")
    except Exception as e:
        print(f"❌ Error checking webhook settings: {str(e)}")
    
    # Check available webhooks
    try:
        print("\n5. Checking available webhooks...")
        webhooks = green_api_client.get_available_webhooks()
        
        if isinstance(webhooks, dict):
            print(f"✅ Available webhooks retrieved")
            for hook_type, enabled in webhooks.items():
                print(f"   {hook_type}: {'Enabled' if enabled else 'Disabled'}")
            
            # Check if the needed webhook types are enabled
            if not webhooks.get('incomingMessageReceived', False):
                print("❌ 'incomingMessageReceived' webhook is disabled")
                print("   This is required to receive incoming messages")
        else:
            print(f"❌ Failed to retrieve available webhooks: {webhooks}")
    except Exception as e:
        print(f"❌ Error checking available webhooks: {str(e)}")
    
    # Check recent notifications
    try:
        print("\n6. Checking recent notifications...")
        
        # Direct API call to receive notification
        receive_url = f"https://api.green-api.com/waInstance{instance_id}/receiveNotification/{api_token}"
        
        # Try to get a few notifications
        notification_count = 0
        for _ in range(5):
            receive_response = requests.get(receive_url)
            
            if receive_response.status_code == 200:
                notification = receive_response.json()
                
                if notification:
                    notification_count += 1
                    
                    receipt_id = notification.get('receiptId')
                    body = notification.get('body', {})
                    
                    webhook_type = body.get('typeWebhook', 'Unknown')
                    timestamp = body.get('timestamp', 0)
                    
                    if timestamp:
                        try:
                            date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            date = 'Unknown'
                    else:
                        date = 'Unknown'
                    
                    print(f"✅ Notification #{notification_count} found")
                    print(f"   Type: {webhook_type}")
                    print(f"   Date: {date}")
                    
                    # Delete the notification after processing
                    delete_url = f"https://api.green-api.com/waInstance{instance_id}/deleteNotification/{api_token}/{receipt_id}"
                    requests.delete(delete_url)
                else:
                    # No more notifications
                    break
            else:
                print(f"❌ Failed to receive notification: {receive_response.status_code} {receive_response.text}")
                break
        
        if notification_count == 0:
            print("ℹ️ No recent notifications found")
            print("   This could mean:")
            print("   1. The webhook is not receiving any messages")
            print("   2. All notifications have been processed")
    except Exception as e:
        print(f"❌ Error checking recent notifications: {str(e)}")
    
    print("\n==== Webhook Check Completed ====")
    
    # Recommendations
    print("\n📋 Recommendations:")
    print("1. Ensure the instance is authorized (scan QR code if needed)")
    print("2. Make sure webhookUrl is set correctly and webhookEnabled is true")
    print("3. Verify that 'incomingMessageReceived' webhook type is enabled")
    print("4. Check if your server is accessible from the internet and can receive webhooks")
    print("5. Check the bot's logs for any webhook processing errors")
    print("6. Try restarting the WhatsApp instance in Green API dashboard")
    print("7. Use the fetch_new_messages.py script to manually fetch messages")

if __name__ == "__main__":
    main() 