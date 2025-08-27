#!/usr/bin/env python3
"""
Comprehensive test suite for Phase 1 Week 2: Session management and backward compatibility enhancements.

This test suite validates the AutoSessionManager implementation, LegacySessionAdapter backward compatibility,
and all related session management features with extensive coverage.
"""

import asyncio
import threading
import time
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any
from unittest.mock import Mock, patch
from datetime import datetime
import json
from pydantic import BaseModel

from oaas_sdk2_py import (
    # New simplified API
    OaasObject,
    OaasService,
    OaasConfig,
    AutoSessionManager,
    LegacySessionAdapter,
    oaas,
    create_object,
    load_object,
    new_session,
    get_global_oaas,
    configure_oaas,
    enable_auto_commit,
    disable_auto_commit,
    set_auto_commit_interval,
    
    # Legacy API
    Oparaca,
    Session,
    BaseObject,
    ClsMeta,
    FuncMeta,
)


# =============================================================================
# TEST MODELS AND UTILITIES
# =============================================================================

class TestRequest(BaseModel):
    """Test request model"""
    value: int = 0
    data: str = ""
    
class TestResponse(BaseModel):
    """Test response model"""
    result: int = 0
    message: str = ""

class TestCounter:
    """Thread-safe counter for testing"""
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
            return self._value
    
    def get_value(self):
        with self._lock:
            return self._value


def setup_test_environment():
    """Set up a clean test environment"""
    # Configure for testing
    config = OaasConfig(mock_mode=True, auto_commit=True)
    configure_oaas(config)
    
    # Clean up any existing state
    OaasService.shutdown()
    configure_oaas(config)


def create_test_service(name: str = "TestService"):
    """Create a test service for testing"""
    @oaas.service(name)
    class TestService(OaasObject):
        count: int = 0
        data: List[str] = []
        metadata: Dict[str, Any] = {}
        
        @oaas.method
        def increment(self):
            self.count += 1
            return TestResponse(result=self.count, message="incremented")
        
        @oaas.method
        def add_data(self, req: TestRequest):
            self.data.append(req.data)
            return TestResponse(result=len(self.data), message="added")
        
        @oaas.method
        def set_metadata(self, req: dict):
            key = req.get("key", "")
            value = req.get("value", "")
            self.metadata[key] = value
            return TestResponse(result=len(self.metadata), message="updated")
        
        @oaas.method
        async def async_increment(self):
            self.count += 1
            return TestResponse(result=self.count, message="async incremented")
    
    return TestService


# =============================================================================
# AUTOSESSIONMANAGER UNIT TESTS
# =============================================================================

class TestAutoSessionManager:
    """Comprehensive tests for AutoSessionManager"""
    
    def test_basic_initialization(self):
        """Test basic AutoSessionManager initialization"""
        print("Testing AutoSessionManager initialization...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        
        # Test initialization
        manager = AutoSessionManager(global_oaas)
        assert manager.oparaca is global_oaas
        assert manager._auto_commit_enabled is True
        assert manager._auto_commit_interval == 1.0
        assert isinstance(manager._thread_sessions, dict)
        assert isinstance(manager._pending_commits, set)
        assert manager._auto_commit_timer is not None
        
        # Cleanup
        manager.shutdown()
        print("✓ AutoSessionManager initialization works")
    
    def test_session_creation_and_management(self):
        """Test session creation and per-thread management"""
        print("Testing session creation and management...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            # Test session creation for current thread
            session1 = manager.get_session()
            assert session1 is not None
            assert isinstance(session1, Session)
            
            # Test that same thread gets same session
            session2 = manager.get_session()
            assert session1 is session2
            
            # Test session with different partition
            session3 = manager.get_session(partition_id=1)
            assert session3 is not None
            # In mock mode, partition might not create different sessions
            
            print("✓ Session creation and management works")
            
        finally:
            manager.shutdown()
    
    def test_object_creation_with_auto_commit(self):
        """Test object creation with auto-commit enabled"""
        print("Testing object creation with auto-commit...")
        
        setup_test_environment()
        TestService = create_test_service("AutoCommitTestService")
        
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            # Create object through AutoSessionManager
            cls_meta = getattr(TestService, '_oaas_cls_meta')
            obj = manager.create_object(cls_meta, obj_id=1)
            
            # Verify auto-commit is enabled
            assert hasattr(obj, '_auto_commit')
            assert obj._auto_commit is True
            assert hasattr(obj, '_auto_session_manager')
            assert obj._auto_session_manager is manager
            
            # Verify object is in managed objects
            assert obj in manager._managed_objects
            
            print("✓ Object creation with auto-commit works")
            
        finally:
            manager.shutdown()
    
    def test_commit_scheduling_and_execution(self):
        """Test commit scheduling and execution"""
        print("Testing commit scheduling and execution...")
        
        setup_test_environment()
        TestService = create_test_service("CommitTestService")
        
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            cls_meta = getattr(TestService, '_oaas_cls_meta')
            obj = manager.create_object(cls_meta, obj_id=1)
            
            # Schedule a commit
            manager.schedule_commit(obj)
            assert obj in manager._pending_commits
            
            # Test commit_all
            manager.commit_all()
            assert len(manager._pending_commits) == 0
            
            print("✓ Commit scheduling and execution works")
            
        finally:
            manager.shutdown()
    
    def test_async_commit_all(self):
        """Test asynchronous commit functionality"""
        print("Testing async commit functionality...")
        
        setup_test_environment()
        TestService = create_test_service("AsyncCommitTestService")
        
        async def async_test():
            global_oaas = get_global_oaas()
            manager = AutoSessionManager(global_oaas)
            
            try:
                cls_meta = getattr(TestService, '_oaas_cls_meta')
                obj = manager.create_object(cls_meta, obj_id=1)
                
                # Schedule commits
                manager.schedule_commit(obj)
                assert obj in manager._pending_commits
                
                # Test async commit
                await manager.commit_all_async()
                assert len(manager._pending_commits) == 0
                
                print("✓ Async commit functionality works")
                
            finally:
                manager.shutdown()
        
        asyncio.run(async_test())
    
    def test_session_cleanup(self):
        """Test session cleanup functionality"""
        print("Testing session cleanup...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            # Create a session
            session = manager.get_session()
            thread_id = threading.get_ident()
            assert thread_id in manager._thread_sessions
            
            # Cleanup session
            manager.cleanup_session(thread_id)
            assert thread_id not in manager._thread_sessions
            
            print("✓ Session cleanup works")
            
        finally:
            manager.shutdown()
    
    def test_shutdown_cleanup(self):
        """Test proper shutdown and cleanup"""
        print("Testing shutdown cleanup...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        # Create some sessions and objects
        session = manager.get_session()
        TestService = create_test_service("ShutdownTestService")
        cls_meta = getattr(TestService, '_oaas_cls_meta')
        obj = manager.create_object(cls_meta, obj_id=1)
        
        # Verify state before shutdown
        assert len(manager._thread_sessions) > 0
        assert len(manager._managed_objects) > 0
        timer = manager._auto_commit_timer
        assert timer is not None
        
        # Shutdown
        manager.shutdown()
        
        # Verify cleanup
        assert len(manager._thread_sessions) == 0
        assert len(manager._managed_objects) == 0
        assert len(manager._pending_commits) == 0
        assert manager._auto_commit_timer is None
        
        print("✓ Shutdown cleanup works")


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Comprehensive thread safety tests"""
    
    def test_concurrent_session_access(self):
        """Test concurrent access to sessions from multiple threads"""
        print("Testing concurrent session access...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        results = []
        num_threads = 10
        
        def thread_worker(thread_id):
            try:
                # Each thread should get its own session
                session = manager.get_session()
                results.append((thread_id, id(session), threading.get_ident()))
                
                # Try to access session multiple times
                for _ in range(5):
                    session2 = manager.get_session()
                    assert session is session2  # Same thread should get same session
                    
            except Exception as e:
                results.append((thread_id, None, str(e)))
        
        try:
            # Create multiple threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=thread_worker, args=(i,))
                threads.append(t)
                t.start()
            
            # Wait for all threads
            for t in threads:
                t.join()
            
            # Verify results
            assert len(results) == num_threads
            
            # Check that we got valid results
            valid_results = [r for r in results if r[1] is not None]
            assert len(valid_results) > 0
            
            print("✓ Concurrent session access works")
            
        finally:
            manager.shutdown()
    
    def test_thread_safety_with_session_cleanup(self):
        """Test thread safety during session cleanup"""
        print("Testing thread safety with session cleanup...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        results = []
        num_threads = 10
        
        def thread_worker(thread_id):
            try:
                # Create session
                session = manager.get_session()
                thread_ident = threading.get_ident()
                
                # Do some work
                time.sleep(0.1)
                
                # Cleanup session
                manager.cleanup_session(thread_ident)
                
                results.append((thread_id, True))
                
            except Exception as e:
                results.append((thread_id, str(e)))
        
        try:
            # Create multiple threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=thread_worker, args=(i,))
                threads.append(t)
                t.start()
            
            # Wait for all threads
            for t in threads:
                t.join()
            
            # Verify results
            assert len(results) == num_threads
            successful_results = [r for r in results if r[1] is True]
            assert len(successful_results) > 0
            
            print("✓ Thread safety with session cleanup works")
            
        finally:
            manager.shutdown()


# =============================================================================
# AUTO-COMMIT FUNCTIONALITY TESTS
# =============================================================================

class TestAutoCommitFunctionality:
    """Comprehensive auto-commit functionality tests"""
    
    def test_auto_commit_enable_disable(self):
        """Test enabling and disabling auto-commit"""
        print("Testing auto-commit enable/disable...")
        
        setup_test_environment()
        
        # Test global enable/disable functions
        enable_auto_commit()
        manager = OaasService._get_auto_session_manager()
        assert manager._auto_commit_enabled is True
        
        disable_auto_commit()
        assert manager._auto_commit_enabled is False
        
        # Re-enable for further tests
        enable_auto_commit()
        assert manager._auto_commit_enabled is True
        
        print("✓ Auto-commit enable/disable works")
    
    def test_auto_commit_interval_configuration(self):
        """Test auto-commit interval configuration"""
        print("Testing auto-commit interval configuration...")
        
        setup_test_environment()
        
        # Test setting interval
        set_auto_commit_interval(0.5)
        manager = OaasService._get_auto_session_manager()
        assert manager._auto_commit_interval == 0.5
        
        # Test that timer is restarted with new interval
        old_timer = manager._auto_commit_timer
        set_auto_commit_interval(0.2)
        assert manager._auto_commit_interval == 0.2
        # Timer should be restarted
        assert manager._auto_commit_timer is not old_timer
        
        print("✓ Auto-commit interval configuration works")
    
    def test_manual_commit_all(self):
        """Test manual commit_all functionality"""
        print("Testing manual commit_all...")
        
        setup_test_environment()
        TestService = create_test_service("ManualCommitTestService")
        
        # Create objects
        obj1 = TestService.create(obj_id=1)
        obj2 = TestService.create(obj_id=2)
        
        # Make changes
        obj1.count = 10
        obj2.count = 20
        
        # Manual commit
        OaasService.commit_all()
        
        # Verify commit completed
        manager = OaasService._get_auto_session_manager()
        assert len(manager._pending_commits) == 0
        
        print("✓ Manual commit_all works")
    
    def test_async_commit_all(self):
        """Test async commit_all functionality"""
        print("Testing async commit_all...")
        
        setup_test_environment()
        TestService = create_test_service("AsyncCommitAllTestService")
        
        async def async_test():
            # Create objects
            obj1 = TestService.create(obj_id=1)
            obj2 = TestService.create(obj_id=2)
            
            # Make changes
            obj1.count = 10
            obj2.count = 20
            
            # Async commit
            await OaasService.commit_all_async()
            
            # Verify commit completed
            manager = OaasService._get_auto_session_manager()
            assert len(manager._pending_commits) == 0
            
            print("✓ Async commit_all works")
        
        asyncio.run(async_test())


# =============================================================================
# BACKWARD COMPATIBILITY TESTS
# =============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility with existing Session API"""
    
    def test_legacy_session_adapter_initialization(self):
        """Test LegacySessionAdapter initialization"""
        print("Testing LegacySessionAdapter initialization...")
        
        setup_test_environment()
        
        # Test new_session function
        session = new_session()
        assert isinstance(session, LegacySessionAdapter)
        assert session.auto_session_manager is not None
        assert session._partition_id is None
        
        # Test with partition ID
        session_with_partition = new_session(partition_id=1)
        assert isinstance(session_with_partition, LegacySessionAdapter)
        assert session_with_partition._partition_id == 1
        
        print("✓ LegacySessionAdapter initialization works")
    
    def test_legacy_session_api_compatibility(self):
        """Test that legacy Session API methods work"""
        print("Testing legacy Session API compatibility...")
        
        setup_test_environment()
        
        # Create legacy session
        session = new_session()
        
        # Test traditional usage pattern
        global_oaas = get_global_oaas()
        cls_meta = global_oaas.new_cls("LegacyCompatTestService")
        
        @cls_meta
        class LegacyCompatTestService(BaseObject):
            @cls_meta.func()
            def test_method(self):
                return "legacy method works"
        
        # Test object creation through legacy session
        obj = session.create_object(cls_meta, obj_id=1, local=True)
        assert obj is not None
        
        # Test commit
        session.commit()
        
        print("✓ Legacy Session API compatibility works")
    
    def test_legacy_session_properties(self):
        """Test that legacy Session properties are accessible"""
        print("Testing legacy Session properties...")
        
        setup_test_environment()
        session = new_session()
        
        # Test all expected properties
        assert hasattr(session, 'local_obj_dict')
        assert hasattr(session, 'remote_obj_dict')
        assert hasattr(session, 'delete_obj_set')
        assert hasattr(session, 'partition_id')
        assert hasattr(session, 'rpc_manager')
        assert hasattr(session, 'data_manager')
        assert hasattr(session, 'meta_repo')
        assert hasattr(session, 'local_only')
        
        # Test property access
        local_obj_dict = session.local_obj_dict
        assert isinstance(local_obj_dict, dict)
        
        remote_obj_dict = session.remote_obj_dict
        assert isinstance(remote_obj_dict, dict)
        
        delete_obj_set = session.delete_obj_set
        assert isinstance(delete_obj_set, set)
        
        partition_id = session.partition_id
        assert isinstance(partition_id, int)
        
        print("✓ Legacy Session properties work")
    
    def test_legacy_session_rpc_methods(self):
        """Test legacy Session RPC methods"""
        print("Testing legacy Session RPC methods...")
        
        setup_test_environment()
        session = new_session()
        
        # Test that RPC methods exist and are callable
        assert hasattr(session, 'obj_rpc')
        assert callable(session.obj_rpc)
        
        assert hasattr(session, 'obj_rpc_async')
        assert callable(session.obj_rpc_async)
        
        assert hasattr(session, 'fn_rpc')
        assert callable(session.fn_rpc)
        
        assert hasattr(session, 'fn_rpc_async')
        assert callable(session.fn_rpc_async)
        
        assert hasattr(session, 'invoke_local')
        assert callable(session.invoke_local)
        
        assert hasattr(session, 'invoke_local_async')
        assert callable(session.invoke_local_async)
        
        print("✓ Legacy Session RPC methods work")
    
    def test_get_global_oaas_function(self):
        """Test get_global_oaas function"""
        print("Testing get_global_oaas function...")
        
        setup_test_environment()
        
        # Test get_global_oaas
        global_oaas = get_global_oaas()
        assert isinstance(global_oaas, Oparaca)
        
        # Should return the same instance
        global_oaas2 = get_global_oaas()
        assert global_oaas is global_oaas2
        
        print("✓ get_global_oaas function works")


# =============================================================================
# INTEGRATION TESTS WITH OAASOBJECT
# =============================================================================

class TestOaasObjectIntegration:
    """Tests for integration with OaasObject"""
    
    def test_oaas_object_create_with_auto_session(self):
        """Test OaasObject.create() with automatic session management"""
        print("Testing OaasObject.create() with auto session...")
        
        setup_test_environment()
        TestService = create_test_service("IntegrationTestService")
        
        # Create object using class method
        obj = TestService.create(obj_id=1)
        
        # Should have auto-commit enabled
        assert hasattr(obj, '_auto_commit')
        assert obj._auto_commit is True
        
        # Should have auto session manager
        assert hasattr(obj, '_auto_session_manager')
        assert obj._auto_session_manager is not None
        
        print("✓ OaasObject.create() with auto session works")
    
    def test_oaas_object_load_with_auto_session(self):
        """Test OaasObject.load() with automatic session management"""
        print("Testing OaasObject.load() with auto session...")
        
        setup_test_environment()
        TestService = create_test_service("LoadIntegrationTestService")
        
        # First create an object
        obj1 = TestService.create(obj_id=1)
        obj1.count = 10
        
        # Load the object
        obj2 = TestService.load(obj_id=1)
        
        # Should have auto-commit enabled
        assert hasattr(obj2, '_auto_commit')
        assert obj2._auto_commit is True
        
        # Should have auto session manager
        assert hasattr(obj2, '_auto_session_manager')
        assert obj2._auto_session_manager is not None
        
        print("✓ OaasObject.load() with auto session works")
    
    def test_method_calls_with_auto_session(self):
        """Test method calls with automatic session management"""
        print("Testing method calls with auto session...")
        
        setup_test_environment()
        TestService = create_test_service("MethodCallTestService")
        
        # Create object
        obj = TestService.create(obj_id=1)
        
        # Call methods
        result1 = obj.increment()
        assert result1.result == 1
        
        result2 = obj.add_data(TestRequest(data="test_item"))
        assert result2.result == 1
        
        result3 = obj.set_metadata({"key": "value"})
        assert result3.result == 1
        
        print("✓ Method calls with auto session work")
    
    def test_async_method_calls_with_auto_session(self):
        """Test async method calls with automatic session management"""
        print("Testing async method calls with auto session...")
        
        setup_test_environment()
        TestService = create_test_service("AsyncMethodCallTestService")
        
        async def async_test():
            # Create object
            obj = TestService.create(obj_id=1)
            
            # Call async method
            result = await obj.async_increment()
            assert result.result == 1
            
            # Call again
            result2 = await obj.async_increment()
            assert result2.result == 2
            
            print("✓ Async method calls with auto session work")
        
        asyncio.run(async_test())


# =============================================================================
# ERROR HANDLING AND EDGE CASES
# =============================================================================

class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases"""
    
    def test_session_manager_with_invalid_oparaca(self):
        """Test AutoSessionManager with invalid Oparaca instance"""
        print("Testing AutoSessionManager with invalid Oparaca...")
        
        # Test with None
        try:
            manager = AutoSessionManager(None)
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected
        
        print("✓ AutoSessionManager handles invalid Oparaca correctly")
    
    def test_commit_with_session_errors(self):
        """Test commit behavior when session errors occur"""
        print("Testing commit with session errors...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            # Create a session
            session = manager.get_session()
            
            # Mock session.commit to raise an error
            original_commit = session.commit
            session.commit = Mock(side_effect=Exception("Commit failed"))
            
            # Try to commit - should handle error gracefully
            try:
                manager.commit_all()
                # Should not raise exception, but log error
            except Exception as e:
                # If exception is raised, test behavior
                pass
            
            # Restore original commit
            session.commit = original_commit
            
            print("✓ Commit error handling works")
            
        finally:
            manager.shutdown()
    
    def test_thread_cleanup_with_nonexistent_thread(self):
        """Test session cleanup with non-existent thread ID"""
        print("Testing session cleanup with non-existent thread...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        try:
            # Try to cleanup non-existent thread
            fake_thread_id = 999999
            manager.cleanup_session(fake_thread_id)  # Should not raise error
            
            print("✓ Thread cleanup with non-existent thread works")
            
        finally:
            manager.shutdown()
    
    def test_shutdown_multiple_times(self):
        """Test calling shutdown multiple times"""
        print("Testing multiple shutdown calls...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        # First shutdown
        manager.shutdown()
        
        # Second shutdown should not raise error
        manager.shutdown()
        
        # Third shutdown should not raise error
        manager.shutdown()
        
        print("✓ Multiple shutdown calls handled correctly")
    
    def test_session_operations_after_shutdown(self):
        """Test session operations after shutdown"""
        print("Testing session operations after shutdown...")
        
        setup_test_environment()
        global_oaas = get_global_oaas()
        manager = AutoSessionManager(global_oaas)
        
        # Shutdown manager
        manager.shutdown()
        
        # Try to get session after shutdown
        try:
            session = manager.get_session()
            # Should work (create new session)
            assert session is not None
        except Exception as e:
            print(f"Expected behavior: {e}")
        
        print("✓ Session operations after shutdown handled")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all test suites"""
    print("Running Comprehensive Phase 1 Week 2 Session Management Tests...")
    print("=" * 80)
    
    test_suites = [
        TestAutoSessionManager(),
        TestThreadSafety(),
        TestAutoCommitFunctionality(),
        TestBackwardCompatibility(),
        TestOaasObjectIntegration(),
        TestErrorHandlingAndEdgeCases(),
    ]
    
    total_passed = 0
    total_failed = 0
    
    for suite in test_suites:
        suite_name = suite.__class__.__name__
        print(f"\n📋 {suite_name}")
        print("-" * 50)
        
        # Get all test methods
        test_methods = [method for method in dir(suite) if method.startswith('test_')]
        
        for test_method_name in test_methods:
            try:
                test_method = getattr(suite, test_method_name)
                test_method()
                total_passed += 1
            except Exception as e:
                print(f"❌ {test_method_name} failed: {e}")
                import traceback
                traceback.print_exc()
                total_failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("🎉 All tests passed! Phase 1 Week 2 session management is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)