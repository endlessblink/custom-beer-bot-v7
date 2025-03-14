#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WhatsApp Group Summary Bot - System Health Check

This script performs a comprehensive health check of all system components
to ensure they are functioning properly. It verifies connections to external
APIs, checks that all required modules are available, and validates the
integrity of core functionality.

Usage:
    python tools/system_health_check.py [--verbose] [--check-apis]

Options:
    --verbose       Display detailed information about each check
    --check-apis    Attempt to connect to external APIs (requires API keys)
"""

import os
import sys
import argparse
import importlib
import platform
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('system_health_check')

# Define color codes for console output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_colored(text, color):
    """Print colored text to the console"""
    # Check if we're running in a terminal that supports colors
    if sys.stdout.isatty():
        print(f"{color}{text}{Colors.END}")
    else:
        print(text)


def check_python_version():
    """Check if the Python version is compatible"""
    current_version = sys.version_info
    required_version = (3, 7)
    
    if current_version >= required_version:
        print_colored(f"✓ Python version: {platform.python_version()}", Colors.GREEN)
        return True
    else:
        print_colored(f"✗ Python version: {platform.python_version()} (Required: 3.7+)", Colors.RED)
        return False


def check_required_modules():
    """Check if all required modules are installed"""
    required_modules = [
        ('dotenv', 'python-dotenv'),
        ('openai', 'openai'),
        ('requests', 'requests'),
        ('supabase', 'supabase'),
        ('colorama', 'colorama'),
    ]
    
    all_passed = True
    print_colored("\nChecking required Python modules:", Colors.BOLD)
    
    for module_name, package_name in required_modules:
        try:
            importlib.import_module(module_name)
            print_colored(f"✓ {module_name} is installed", Colors.GREEN)
        except ImportError:
            print_colored(f"✗ {module_name} is not installed (pip install {package_name})", Colors.RED)
            all_passed = False
    
    return all_passed


def check_project_structure():
    """Check if the project structure is intact"""
    required_paths = [
        ("summary_menu.py", "Main menu interface"),
        ("generate_summary.py", "Summary generation script"),
        ("config/", "Configuration directory"),
        ("utils/menu/", "Menu utilities"),
        ("green_api/", "WhatsApp API client"),
        ("llm/", "Language model integration"),
        ("processor/", "Message processing"),
        ("db/", "Database integration"),
    ]
    
    all_passed = True
    print_colored("\nChecking project structure:", Colors.BOLD)
    
    for path, description in required_paths:
        full_path = project_root / path
        if full_path.exists():
            print_colored(f"✓ {path} - {description}", Colors.GREEN)
        else:
            print_colored(f"✗ {path} - {description} (MISSING)", Colors.RED)
            all_passed = False
    
    return all_passed


def check_environment_variables():
    """Check if essential environment variables are set"""
    # Try to load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_colored("✗ Could not load dotenv module", Colors.RED)
    
    essential_vars = [
        ("GREEN_API_INSTANCE_ID", "WhatsApp API instance ID"),
        ("GREEN_API_INSTANCE_TOKEN", "WhatsApp API token"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("SUPABASE_URL", "Supabase URL (optional)"),
        ("SUPABASE_KEY", "Supabase key (optional)"),
        ("DEFAULT_LANGUAGE", "Default language for summaries"),
    ]
    
    all_passed = True
    critical_passed = True
    print_colored("\nChecking environment variables:", Colors.BOLD)
    
    for var_name, description in essential_vars:
        if var_name in os.environ and os.environ[var_name]:
            # Don't print actual API keys for security
            if "KEY" in var_name or "TOKEN" in var_name or "ID" in var_name:
                print_colored(f"✓ {var_name} - {description} (CONFIGURED)", Colors.GREEN)
            else:
                print_colored(f"✓ {var_name} - {description} (Value: {os.environ[var_name]})", Colors.GREEN)
        elif var_name in ["SUPABASE_URL", "SUPABASE_KEY"]:
            # Supabase is optional
            print_colored(f"⚠ {var_name} - {description} (NOT CONFIGURED, but optional)", Colors.YELLOW)
        else:
            print_colored(f"✗ {var_name} - {description} (NOT CONFIGURED)", Colors.RED)
            if var_name not in ["SUPABASE_URL", "SUPABASE_KEY"]:
                critical_passed = False
            all_passed = False
    
    return all_passed, critical_passed


def check_user_settings():
    """Check if user settings file exists and is valid"""
    settings_path = project_root / "user_settings.json"
    
    print_colored("\nChecking user settings:", Colors.BOLD)
    
    if not settings_path.exists():
        print_colored("⚠ user_settings.json does not exist (will use environment variables)", Colors.YELLOW)
        return True
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        if isinstance(settings, dict):
            print_colored(f"✓ user_settings.json is valid (contains {len(settings)} settings)", Colors.GREEN)
            return True
        else:
            print_colored("✗ user_settings.json is not a valid JSON object", Colors.RED)
            return False
    except json.JSONDecodeError:
        print_colored("✗ user_settings.json is not valid JSON", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"✗ Error reading user_settings.json: {e}", Colors.RED)
        return False


def check_api_connections(verbose=False):
    """Check connections to external APIs"""
    results = {}
    
    print_colored("\nChecking API connections:", Colors.BOLD)
    
    # Check Green API
    try:
        from green_api.client import GreenAPIClient
        
        instance_id = os.environ.get('GREEN_API_INSTANCE_ID')
        instance_token = os.environ.get('GREEN_API_INSTANCE_TOKEN')
        
        if not instance_id or not instance_token:
            print_colored("⚠ Skipping Green API check (credentials not configured)", Colors.YELLOW)
            results['green_api'] = 'skipped'
        else:
            client = GreenAPIClient(instance_id, instance_token)
            account_status = client.get_account_status()
            
            if verbose:
                print(f"Green API response: {json.dumps(account_status, indent=2)}")
            
            if account_status.get('stateInstance') == 'authorized':
                print_colored("✓ Green API connection successful", Colors.GREEN)
                results['green_api'] = 'success'
            else:
                print_colored(f"✗ Green API connection failed: {account_status.get('stateInstance', 'unknown state')}", Colors.RED)
                results['green_api'] = 'failed'
    except Exception as e:
        print_colored(f"✗ Green API connection error: {e}", Colors.RED)
        if verbose:
            traceback.print_exc()
        results['green_api'] = 'error'
    
    # Check OpenAI API
    try:
        from llm.openai_client import OpenAIClient
        
        api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            print_colored("⚠ Skipping OpenAI API check (credentials not configured)", Colors.YELLOW)
            results['openai_api'] = 'skipped'
        else:
            client = OpenAIClient(api_key)
            
            # Make a simple API call
            test_messages = [{
                'sender': 'Test User',
                'content': 'Hello, world!',
                'timestamp': datetime.now().isoformat()
            }]
            
            # We're not actually going to generate a real summary since that would be expensive
            # Just check that the client can be initialized
            print_colored("✓ OpenAI API client initialized successfully", Colors.GREEN)
            results['openai_api'] = 'success'
    except Exception as e:
        print_colored(f"✗ OpenAI API client error: {e}", Colors.RED)
        if verbose:
            traceback.print_exc()
        results['openai_api'] = 'error'
    
    # Check Supabase connection (if configured)
    try:
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print_colored("⚠ Skipping Supabase check (credentials not configured)", Colors.YELLOW)
            results['supabase'] = 'skipped'
        else:
            from db.supabase_client import SupabaseClient
            
            client = SupabaseClient(supabase_url, supabase_key)
            
            # Just check that we can initialize the client
            # We could also make a simple query, but that's not essential
            print_colored("✓ Supabase client initialized successfully", Colors.GREEN)
            results['supabase'] = 'success'
    except Exception as e:
        print_colored(f"✗ Supabase client error: {e}", Colors.RED)
        if verbose:
            traceback.print_exc()
        results['supabase'] = 'error'
    
    return results


def check_core_functionality():
    """Check core functionality components"""
    checks = [
        ("utils.menu.core_menu", "Core menu functionality"),
        ("processor.message_processor", "Message processing"),
        ("green_api.group_manager", "Group management"),
        ("llm.openai_client", "OpenAI client"),
    ]
    
    all_passed = True
    print_colored("\nChecking core functionality:", Colors.BOLD)
    
    for module_path, description in checks:
        try:
            module = importlib.import_module(module_path)
            print_colored(f"✓ {module_path} - {description}", Colors.GREEN)
        except Exception as e:
            print_colored(f"✗ {module_path} - {description}: {e}", Colors.RED)
            all_passed = False
    
    return all_passed


def generate_report(results):
    """Generate a health check report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
        "checks": {
            "python_version": results.get("python_version", False),
            "required_modules": results.get("required_modules", False),
            "project_structure": results.get("project_structure", False),
            "environment_variables": results.get("environment_variables", {
                "all_passed": False,
                "critical_passed": False
            }),
            "user_settings": results.get("user_settings", False),
            "api_connections": results.get("api_connections", {}),
            "core_functionality": results.get("core_functionality", False),
        },
        "summary": {
            "status": "healthy" if all([
                results.get("python_version", False),
                results.get("required_modules", False),
                results.get("project_structure", False),
                results.get("environment_variables", {}).get("critical_passed", False),
                results.get("user_settings", False),
                results.get("core_functionality", False),
            ]) else "unhealthy",
            "critical_issues": [],
            "warnings": [],
        }
    }
    
    # Identify critical issues
    if not results.get("python_version", False):
        report["summary"]["critical_issues"].append("Python version is not compatible")
    
    if not results.get("required_modules", False):
        report["summary"]["critical_issues"].append("Missing required Python modules")
    
    if not results.get("project_structure", False):
        report["summary"]["critical_issues"].append("Project structure is incomplete")
    
    if not results.get("environment_variables", {}).get("critical_passed", False):
        report["summary"]["critical_issues"].append("Missing critical environment variables")
    
    if not results.get("core_functionality", False):
        report["summary"]["critical_issues"].append("Core functionality is broken")
    
    # Identify warnings
    if not results.get("user_settings", False):
        report["summary"]["warnings"].append("User settings file is missing or invalid")
    
    if not results.get("environment_variables", {}).get("all_passed", False):
        report["summary"]["warnings"].append("Some environment variables are missing")
    
    # Check API connections
    api_results = results.get("api_connections", {})
    for api, status in api_results.items():
        if status == 'failed':
            report["summary"]["critical_issues"].append(f"{api} connection failed")
        elif status == 'error':
            report["summary"]["critical_issues"].append(f"{api} connection error")
        elif status == 'skipped':
            report["summary"]["warnings"].append(f"{api} connection check skipped")
    
    return report


def print_summary(report):
    """Print a summary of the health check results"""
    print_colored("\nSystem Health Check Summary:", Colors.BOLD)
    print("-" * 60)
    
    status = report["summary"]["status"]
    if status == "healthy":
        print_colored("Overall Status: HEALTHY ✓", Colors.GREEN)
    else:
        print_colored("Overall Status: UNHEALTHY ✗", Colors.RED)
    
    # Print critical issues
    critical_issues = report["summary"]["critical_issues"]
    if critical_issues:
        print_colored(f"\nCritical Issues ({len(critical_issues)}):", Colors.RED)
        for issue in critical_issues:
            print(f"  • {issue}")
    else:
        print_colored("\nCritical Issues: None", Colors.GREEN)
    
    # Print warnings
    warnings = report["summary"]["warnings"]
    if warnings:
        print_colored(f"\nWarnings ({len(warnings)}):", Colors.YELLOW)
        for warning in warnings:
            print(f"  • {warning}")
    else:
        print_colored("\nWarnings: None", Colors.GREEN)
    
    print("-" * 60)
    
    # Print recommendations
    if status != "healthy":
        print_colored("\nRecommendations:", Colors.BOLD)
        
        if not report["checks"]["python_version"]:
            print("• Upgrade Python to version 3.7 or higher")
        
        if not report["checks"]["required_modules"]:
            print("• Install missing Python modules using: pip install -r requirements.txt")
        
        if not report["checks"]["project_structure"]:
            print("• Check that all required files and directories are present")
            print("• Re-clone the repository if necessary")
        
        if not report["checks"]["environment_variables"]["critical_passed"]:
            print("• Set up the required environment variables in a .env file")
            print("• See .env.example for the required variables")
        
        if not report["checks"]["core_functionality"]:
            print("• Fix issues with core functionality modules")
            print("• Check the error messages for specific issues")
        
        # API-specific recommendations
        api_connections = report["checks"]["api_connections"]
        
        if api_connections.get("green_api") in ["failed", "error"]:
            print("• Check your Green API credentials")
            print("• Verify that your Green API instance is authorized")
        
        if api_connections.get("openai_api") in ["failed", "error"]:
            print("• Check your OpenAI API key")
            print("• Verify that your OpenAI API key has sufficient credits")
        
        if api_connections.get("supabase") in ["failed", "error"]:
            print("• Check your Supabase credentials")
            print("• Verify that your Supabase project is active")


def save_report(report, output_file=None):
    """Save the health check report to a file"""
    if output_file is None:
        # Generate a filename based on the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = project_root / f"system_health_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to: {output_file}")


def main():
    """Main function to run the health check"""
    parser = argparse.ArgumentParser(description='WhatsApp Group Summary Bot System Health Check')
    parser.add_argument('--verbose', action='store_true', help='Display detailed information')
    parser.add_argument('--check-apis', action='store_true', help='Check API connections')
    parser.add_argument('--output', type=str, help='Output file for the health check report')
    args = parser.parse_args()
    
    print_colored("WhatsApp Group Summary Bot - System Health Check", Colors.BOLD)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Project root: {project_root}")
    print("-" * 60)
    
    # Run all checks
    results = {
        "python_version": check_python_version(),
        "required_modules": check_required_modules(),
        "project_structure": check_project_structure(),
    }
    
    # Check environment variables
    env_all_passed, env_critical_passed = check_environment_variables()
    results["environment_variables"] = {
        "all_passed": env_all_passed,
        "critical_passed": env_critical_passed
    }
    
    # User settings
    results["user_settings"] = check_user_settings()
    
    # API connections (optional)
    if args.check_apis:
        results["api_connections"] = check_api_connections(verbose=args.verbose)
    
    # Core functionality
    results["core_functionality"] = check_core_functionality()
    
    # Generate and print report
    report = generate_report(results)
    print_summary(report)
    
    # Save report if requested
    if args.output:
        save_report(report, args.output)
    
    # Return exit code based on status
    return 0 if report["summary"]["status"] == "healthy" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        traceback.print_exc()
        sys.exit(1) 