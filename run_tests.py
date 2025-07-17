#!/usr/bin/env python3
"""
Test runner script for OaaS SDK pytest tests.
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run pytest with appropriate configuration."""
    
    # Change to project root directory
    project_root = Path(__file__).parent
    
    # Basic pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",  # verbose output
        "--tb=short",  # shorter traceback format
        "tests/test_primitive_types.py",
        "tests/test_parameter_types.py", 
        "tests/test_server_agent_management.py"
    ]
    
    print("Running OaaS SDK tests with pytest...")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_specific_test(test_name):
    """Run a specific test file."""
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        f"tests/{test_name}"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running test {test_name}: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if not test_name.startswith("test_"):
            test_name = f"test_{test_name}"
        if not test_name.endswith(".py"):
            test_name = f"{test_name}.py"
        
        exit_code = run_specific_test(test_name)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)
