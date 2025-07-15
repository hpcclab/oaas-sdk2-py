#!/usr/bin/env python3
"""
Debug test to identify failing test
"""

import sys
import traceback
from test_phase2_week3_enhanced_decorators import TestEnhancedDecorators, TestConcurrencyAndThreadSafety

def run_individual_tests():
    """Run individual tests to identify the failing one"""
    
    # Test suite 1: Enhanced Decorators
    suite1 = TestEnhancedDecorators()
    test_methods_1 = [
        'test_backward_compatibility',
        'test_enhanced_method_decorator_features', 
        'test_enhanced_service_decorator_basic',
        'test_error_handling_and_debugging',
        'test_performance_optimizations',
        'test_system_management',
        'test_type_safe_state_serialization'
    ]
    
    print("Testing Enhanced Decorators:")
    print("=" * 50)
    
    for test_name in test_methods_1:
        print(f"\n🧪 Running {test_name}...")
        try:
            test_method = getattr(suite1, test_name)
            result = test_method()
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED (returned False)")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            traceback.print_exc()
    
    # Test suite 2: Concurrency and Thread Safety
    suite2 = TestConcurrencyAndThreadSafety()
    test_methods_2 = [
        'test_concurrent_service_access',
        'test_thread_safety_with_state'
    ]
    
    print("\n\nTesting Concurrency and Thread Safety:")
    print("=" * 50)
    
    for test_name in test_methods_2:
        print(f"\n🧪 Running {test_name}...")
        try:
            test_method = getattr(suite2, test_name)
            result = test_method()
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED (returned False)")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    run_individual_tests()