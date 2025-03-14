#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bug Report Generator for WhatsApp Group Summary Bot

This script generates a comprehensive bug report to help with troubleshooting.
It collects system information, configuration details, logs, and runs basic tests
to identify potential issues. The information is saved to a JSON file that can
be shared when reporting issues.

Usage:
    python tools/bug_report_generator.py [--include-logs] [--run-tests] [--output OUTPUT_FILE]

Options:
    --include-logs    Include recent log files in the report
    --run-tests       Run basic tests to identify potential issues
    --output          Specify an output file path (default: bug_report_TIMESTAMP.json)
"""

import os
import sys
import json
import platform
import logging
import argparse
import subprocess
import traceback
import importlib
from datetime import datetime
from pathlib import Path
import shutil

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
logger = logging.getLogger('bug_report_generator')


def collect_system_info():
    """Collect information about the system"""
    logger.info("Collecting system information...")
    
    system_info = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "path": sys.executable,
        },
        "environment": {
            "cwd": os.getcwd(),
            "home": os.path.expanduser("~"),
            "terminal": os.environ.get("TERM", "unknown"),
            "shell": os.environ.get("SHELL", "unknown"),
            "path": os.environ.get("PATH", ""),
        }
    }
    
    # Try to collect pip/package information
    try:
        import pkg_resources
        system_info["packages"] = [
            {"name": pkg.key, "version": pkg.version}
            for pkg in pkg_resources.working_set
        ]
    except ImportError:
        system_info["packages"] = "Unable to collect package information"
    
    # Terminal encoding
    system_info["encoding"] = {
        "stdout": getattr(sys.stdout, 'encoding', 'unknown'),
        "stderr": getattr(sys.stderr, 'encoding', 'unknown'),
        "filesystem": sys.getfilesystemencoding(),
        "default": sys.getdefaultencoding(),
    }
    
    return system_info


def collect_project_info():
    """Collect information about the project structure"""
    logger.info("Collecting project information...")
    
    # Check if this is a git repository
    git_info = None
    if (project_root / ".git").exists():
        try:
            git_info = {
                "is_git_repo": True,
                "current_branch": subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=project_root,
                    text=True
                ).strip(),
                "current_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=project_root,
                    text=True
                ).strip(),
                "latest_tags": subprocess.check_output(
                    ["git", "tag", "-l", "--sort=-creatordate"],
                    cwd=project_root,
                    text=True
                ).strip().split("\n")[:5],
            }
        except Exception as e:
            git_info = {
                "is_git_repo": True,
                "error": str(e)
            }
    else:
        git_info = {
            "is_git_repo": False
        }
    
    # Collect file listing
    file_list = []
    for root, dirs, files in os.walk(project_root):
        rel_path = os.path.relpath(root, project_root)
        if rel_path == ".":
            rel_path = ""
        
        # Skip .git and other hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        
        for file in files:
            if file.startswith("."):
                continue
                
            file_path = Path(rel_path) / file
            file_info = {
                "path": str(file_path),
                "size": os.path.getsize(project_root / file_path),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(project_root / file_path)
                ).isoformat(),
            }
            file_list.append(file_info)
    
    # Check for critical files
    critical_files = [
        "summary_menu.py",
        "generate_summary.py",
        "main.py",
        "utils/menu/core_menu.py",
        "green_api/client.py",
        "green_api/group_manager.py",
        "llm/openai_client.py",
        "processor/message_processor.py",
        "db/supabase_client.py",
        ".env",
        "user_settings.json"
    ]
    
    missing_files = []
    for file_path in critical_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    # Get information about Python packages
    requirements = None
    if (project_root / "requirements.txt").exists():
        with open(project_root / "requirements.txt", "r") as f:
            requirements = f.read()
    
    return {
        "git": git_info,
        "files": file_list,
        "missing_critical_files": missing_files,
        "requirements": requirements
    }


def collect_environment_variables():
    """Collect relevant environment variables"""
    logger.info("Collecting environment variables...")
    
    # List of environment variables that might be relevant
    relevant_vars = [
        "PYTHONPATH",
        "PYTHONHOME",
        "OPENAI_API_KEY",
        "DEFAULT_LANGUAGE",
        "GREEN_API_INSTANCE_ID",
        "GREEN_API_INSTANCE_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ]
    
    # Look for other environment variables that might be related to our application
    relevant_prefixes = [
        "PYTHON",
        "OPENAI",
        "GREEN",
        "SUPABASE",
        "WHATSAPP",
        "SUMMARY",
        "LOG",
    ]
    
    env_vars = {}
    for var_name, var_value in os.environ.items():
        # Check if the variable is directly relevant
        if var_name in relevant_vars:
            # Mask sensitive information
            if "KEY" in var_name or "TOKEN" in var_name or "PASSWORD" in var_name or "SECRET" in var_name:
                env_vars[var_name] = f"[REDACTED - value length: {len(var_value)}]"
            else:
                env_vars[var_name] = var_value
        
        # Check if the variable has a relevant prefix
        for prefix in relevant_prefixes:
            if var_name.startswith(prefix):
                # Mask sensitive information
                if "KEY" in var_name or "TOKEN" in var_name or "PASSWORD" in var_name or "SECRET" in var_name:
                    env_vars[var_name] = f"[REDACTED - value length: {len(var_value)}]"
                else:
                    env_vars[var_name] = var_value
                break
    
    # Check for .env file
    dotenv_exists = (project_root / ".env").exists()
    dotenv_example_exists = (project_root / ".env.example").exists()
    
    # Check for user_settings.json
    user_settings = None
    if (project_root / "user_settings.json").exists():
        try:
            with open(project_root / "user_settings.json", "r") as f:
                user_settings_raw = json.load(f)
                
                # Mask sensitive information
                user_settings = {}
                for key, value in user_settings_raw.items():
                    if "KEY" in key or "TOKEN" in key or "PASSWORD" in key or "SECRET" in key:
                        user_settings[key] = f"[REDACTED - value length: {len(str(value))}]"
                    else:
                        user_settings[key] = value
        except Exception as e:
            user_settings = f"Error loading user_settings.json: {str(e)}"
    
    return {
        "env_vars": env_vars,
        "dotenv_exists": dotenv_exists,
        "dotenv_example_exists": dotenv_example_exists,
        "user_settings": user_settings
    }


def collect_logs(include_logs=False):
    """Collect log files for debugging"""
    logger.info("Collecting log information...")
    
    log_dir = project_root / "logs"
    log_files = []
    
    if log_dir.exists() and log_dir.is_dir():
        for log_file in log_dir.glob("*.log"):
            log_info = {
                "name": log_file.name,
                "size": log_file.stat().st_size,
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
            }
            
            # If include_logs is True, include the content of recent log files
            if include_logs and log_file.stat().st_size < 1_000_000:  # Only include files smaller than 1MB
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        log_content = f.read()
                        
                        # If the log is too large, only include the last 1000 lines
                        if len(log_content) > 100_000:
                            lines = log_content.splitlines()
                            log_content = "\n".join(lines[-1000:])
                            log_info["truncated"] = True
                        
                        log_info["content"] = log_content
                except Exception as e:
                    log_info["error"] = f"Could not read log file: {str(e)}"
            
            log_files.append(log_info)
    
    return {
        "log_directory_exists": log_dir.exists(),
        "log_files": log_files
    }


def check_module_imports():
    """Check if all required modules can be imported"""
    logger.info("Checking module imports...")
    
    modules_to_check = [
        ("utils.menu.core_menu", "Core menu functionality"),
        ("green_api.client", "WhatsApp API client"),
        ("green_api.group_manager", "WhatsApp group management"),
        ("llm.openai_client", "OpenAI client integration"),
        ("processor.message_processor", "Message processing"),
        ("db.supabase_client", "Database integration"),
        ("config.config_manager", "Configuration management"),
    ]
    
    import_results = []
    
    for module_name, description in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            import_results.append({
                "module": module_name,
                "description": description,
                "status": "success",
            })
        except ImportError as e:
            import_results.append({
                "module": module_name,
                "description": description,
                "status": "error",
                "error": str(e),
            })
        except Exception as e:
            import_results.append({
                "module": module_name,
                "description": description,
                "status": "other_error",
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
    
    return import_results


def run_basic_tests():
    """Run basic tests to identify potential issues"""
    logger.info("Running basic tests...")
    
    test_results = []
    
    # Test 1: Check if the core menu module is working
    try:
        from utils.menu.core_menu import print_header
        
        # Test the function (redirect stdout to avoid cluttering the console)
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            print_header("Test Header")
        
        output = f.getvalue()
        if "Test Header" in output:
            test_results.append({
                "name": "Core Menu Function Test",
                "status": "success",
                "message": "Menu header function is working correctly"
            })
        else:
            test_results.append({
                "name": "Core Menu Function Test",
                "status": "error",
                "message": "Menu header function is not displaying content correctly"
            })
    except Exception as e:
        test_results.append({
            "name": "Core Menu Function Test",
            "status": "error",
            "message": f"Error testing core menu: {str(e)}",
            "traceback": traceback.format_exc()
        })
    
    # Test 2: Check if the OpenAI client can be initialized
    try:
        from llm.openai_client import OpenAIClient
        
        # Try to initialize the client with a dummy key
        client = OpenAIClient(api_key="dummy_key")
        
        test_results.append({
            "name": "OpenAI Client Initialization Test",
            "status": "success",
            "message": "OpenAI client can be initialized"
        })
    except Exception as e:
        test_results.append({
            "name": "OpenAI Client Initialization Test",
            "status": "error",
            "message": f"Error initializing OpenAI client: {str(e)}",
            "traceback": traceback.format_exc()
        })
    
    # Test 3: Check if the Green API client can be initialized
    try:
        from green_api.client import GreenAPIClient
        
        # Try to initialize the client with dummy values
        client = GreenAPIClient(instance_id="dummy_id", instance_token="dummy_token")
        
        test_results.append({
            "name": "Green API Client Initialization Test",
            "status": "success",
            "message": "Green API client can be initialized"
        })
    except Exception as e:
        test_results.append({
            "name": "Green API Client Initialization Test",
            "status": "error",
            "message": f"Error initializing Green API client: {str(e)}",
            "traceback": traceback.format_exc()
        })
    
    # Test 4: Check if the message processor can be initialized
    try:
        from processor.message_processor import MessageProcessor
        
        # Try to initialize the processor
        processor = MessageProcessor(target_language="english")
        
        test_results.append({
            "name": "Message Processor Initialization Test",
            "status": "success",
            "message": "Message processor can be initialized"
        })
    except Exception as e:
        test_results.append({
            "name": "Message Processor Initialization Test",
            "status": "error",
            "message": f"Error initializing message processor: {str(e)}",
            "traceback": traceback.format_exc()
        })
    
    return test_results


def generate_bug_report(include_logs=False, run_tests=False):
    """Generate a comprehensive bug report"""
    logger.info("Generating bug report...")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": collect_system_info(),
        "project_info": collect_project_info(),
        "environment": collect_environment_variables(),
        "logs": collect_logs(include_logs),
        "imports": check_module_imports(),
    }
    
    if run_tests:
        report["test_results"] = run_basic_tests()
    
    # Add potential issues section based on collected data
    report["potential_issues"] = identify_potential_issues(report)
    
    return report


def identify_potential_issues(report):
    """Identify potential issues based on the collected data"""
    logger.info("Identifying potential issues...")
    
    issues = []
    
    # Check for missing critical files
    if report["project_info"]["missing_critical_files"]:
        issues.append({
            "severity": "critical",
            "category": "project_structure",
            "message": f"Missing critical files: {', '.join(report['project_info']['missing_critical_files'])}",
            "recommendation": "Ensure all critical files are present. You may need to reinstall or re-clone the project."
        })
    
    # Check for environment variables
    env = report["environment"]
    missing_env_vars = []
    
    critical_env_vars = [
        "GREEN_API_INSTANCE_ID",
        "GREEN_API_INSTANCE_TOKEN",
        "OPENAI_API_KEY",
        "DEFAULT_LANGUAGE"
    ]
    
    for var in critical_env_vars:
        if var not in env["env_vars"]:
            missing_env_vars.append(var)
    
    if missing_env_vars:
        issues.append({
            "severity": "high",
            "category": "configuration",
            "message": f"Missing critical environment variables: {', '.join(missing_env_vars)}",
            "recommendation": "Set the missing environment variables in a .env file or in your system environment."
        })
    
    # Check for import errors
    import_errors = [imp for imp in report["imports"] if imp["status"] != "success"]
    if import_errors:
        for error in import_errors:
            issues.append({
                "severity": "high",
                "category": "imports",
                "message": f"Failed to import {error['module']}: {error.get('error', 'Unknown error')}",
                "recommendation": "Check if the module exists and if all dependencies are installed."
            })
    
    # Check for Python version
    python_version = tuple(map(int, report["system_info"]["python"]["version"].split(".")))
    if python_version < (3, 7):
        issues.append({
            "severity": "medium",
            "category": "environment",
            "message": f"Python version {report['system_info']['python']['version']} is lower than recommended (3.7+)",
            "recommendation": "Update Python to version 3.7 or higher."
        })
    
    # Check for platform-specific issues
    if report["system_info"]["os"]["system"] == "Windows":
        issues.append({
            "severity": "low",
            "category": "platform",
            "message": "Running on Windows may cause path and encoding issues",
            "recommendation": "Be careful with file paths and encoding, and consider using forward slashes (/) in paths."
        })
    
    # Check for test results if available
    if "test_results" in report:
        failed_tests = [test for test in report["test_results"] if test["status"] != "success"]
        for test in failed_tests:
            issues.append({
                "severity": "medium",
                "category": "tests",
                "message": f"Test '{test['name']}' failed: {test['message']}",
                "recommendation": "Check the error message and traceback for more details."
            })
    
    # If no issues found, add a positive note
    if not issues:
        issues.append({
            "severity": "info",
            "category": "general",
            "message": "No obvious issues detected",
            "recommendation": "If you're still experiencing problems, check the logs for more details."
        })
    
    return issues


def print_report_summary(report):
    """Print a summary of the bug report"""
    
    print("\n" + "=" * 80)
    print("WhatsApp Group Summary Bot - Bug Report Summary")
    print("=" * 80)
    
    # System information
    print("\nSystem Information:")
    print(f"  OS: {report['system_info']['os']['system']} {report['system_info']['os']['release']}")
    print(f"  Python: {report['system_info']['python']['version']}")
    
    # Project information
    print("\nProject Information:")
    missing_files = report["project_info"]["missing_critical_files"]
    if missing_files:
        print(f"  Missing critical files: {', '.join(missing_files)}")
    else:
        print("  All critical files present")
    
    # Import status
    print("\nImport Status:")
    import_errors = [imp for imp in report["imports"] if imp["status"] != "success"]
    if import_errors:
        for error in import_errors:
            print(f"  ✗ {error['module']}: {error.get('error', 'Unknown error')}")
    else:
        print("  ✓ All modules imported successfully")
    
    # Test results
    if "test_results" in report:
        print("\nTest Results:")
        for test in report["test_results"]:
            if test["status"] == "success":
                print(f"  ✓ {test['name']}")
            else:
                print(f"  ✗ {test['name']}: {test['message']}")
    
    # Potential issues
    print("\nPotential Issues:")
    critical_issues = [issue for issue in report["potential_issues"] if issue["severity"] == "critical"]
    high_issues = [issue for issue in report["potential_issues"] if issue["severity"] == "high"]
    medium_issues = [issue for issue in report["potential_issues"] if issue["severity"] == "medium"]
    low_issues = [issue for issue in report["potential_issues"] if issue["severity"] == "low"]
    info_issues = [issue for issue in report["potential_issues"] if issue["severity"] == "info"]
    
    if critical_issues:
        print(f"\n  Critical Issues ({len(critical_issues)}):")
        for issue in critical_issues:
            print(f"    • {issue['message']}")
            print(f"      Recommendation: {issue['recommendation']}")
    
    if high_issues:
        print(f"\n  High Priority Issues ({len(high_issues)}):")
        for issue in high_issues:
            print(f"    • {issue['message']}")
            print(f"      Recommendation: {issue['recommendation']}")
    
    if medium_issues:
        print(f"\n  Medium Priority Issues ({len(medium_issues)}):")
        for issue in medium_issues:
            print(f"    • {issue['message']}")
    
    if low_issues:
        print(f"\n  Low Priority Issues ({len(low_issues)}):")
        for issue in low_issues:
            print(f"    • {issue['message']}")
    
    if info_issues:
        print(f"\n  Information:")
        for issue in info_issues:
            print(f"    • {issue['message']}")
    
    print("\n" + "=" * 80)


def save_report(report, output_file=None):
    """Save the bug report to a file"""
    if output_file is None:
        # Generate a filename based on the timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = project_root / f"bug_report_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Bug report saved to: {output_file}")
    return str(output_file)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate a bug report for WhatsApp Group Summary Bot")
    parser.add_argument("--include-logs", action="store_true", help="Include log files in the report")
    parser.add_argument("--run-tests", action="store_true", help="Run basic tests to identify potential issues")
    parser.add_argument("--output", type=str, help="Output file path for the bug report")
    args = parser.parse_args()
    
    print("Generating bug report for WhatsApp Group Summary Bot...")
    print("This may take a moment...\n")
    
    try:
        # Generate the bug report
        report = generate_bug_report(include_logs=args.include_logs, run_tests=args.run_tests)
        
        # Print a summary
        print_report_summary(report)
        
        # Save the report
        output_file = save_report(report, args.output)
        print(f"\nFull bug report saved to: {output_file}")
        
        # Provide instructions for sharing the report
        print("\nIf you need to share this report:")
        print(f"1. Attach the file: {output_file}")
        print("2. Include a description of the issue you're experiencing")
        print("3. Include steps to reproduce the issue if possible")
        
        return 0
    except Exception as e:
        logger.error(f"Error generating bug report: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 