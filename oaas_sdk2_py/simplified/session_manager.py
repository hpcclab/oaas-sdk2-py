"""
OaaS SDK Automatic Session Management

This module provides automatic session lifecycle management
for the OaaS SDK simplified interface.
"""

import asyncio
import threading
import weakref
from contextlib import contextmanager
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine import Oparaca
    from ..session import Session
    from ..model import ClsMeta
    from .objects import OaasObject


class AutoSessionManager:
    """
    Automatic session lifecycle management for OaaS SDK.
    
    This class provides transparent session management with auto-commit functionality,
    thread-safe session handling, and integration with the existing Session class.
    
    Features:
    - Automatic session creation and cleanup
    - Background auto-commit for state changes
    - Thread-safe session handling
    - Integration with existing Oparaca engine
    - Backward compatibility with manual session management
    """
    
    def __init__(self, oparaca: 'Oparaca'):
        self.oparaca = oparaca
        self._thread_sessions: Dict[int, 'Session'] = {}
        self._session_lock = threading.RLock()
        self._auto_commit_enabled = True
        self._auto_commit_interval = 1.0  # seconds
        self._auto_commit_timer = None
        self._pending_commits: set = set()
        self._commit_lock = threading.Lock()
        
        # Weak references to objects for cleanup
        self._managed_objects: weakref.WeakSet = weakref.WeakSet()
        
        # Start background auto-commit timer
        self._start_auto_commit_timer()
    
    def get_session(self, partition_id: Optional[int] = None) -> 'Session':
        """
        Get or create a session for the current thread.
        
        Args:
            partition_id: Optional partition ID (uses default if not provided)
            
        Returns:
            Session instance for the current thread
        """
        thread_id = threading.get_ident()
        
        with self._session_lock:
            if thread_id not in self._thread_sessions:
                session = self.oparaca.new_session(partition_id)
                self._thread_sessions[thread_id] = session
            return self._thread_sessions[thread_id]
    
    def create_object(self, cls_meta: 'ClsMeta', obj_id: Optional[int] = None,
                     local: bool = None, partition_id: Optional[int] = None) -> 'OaasObject':
        """
        Create a new object with automatic session management.
        
        Args:
            cls_meta: Class metadata
            obj_id: Optional object ID
            local: Whether to create locally
            partition_id: Optional partition ID
            
        Returns:
            Created object with auto-commit enabled
        """
        session = self.get_session(partition_id)
        obj = session.create_object(cls_meta, obj_id=obj_id, local=local or self.oparaca.mock_mode)
        
        # Enable auto-commit for the object
        obj._auto_commit = True
        obj._auto_session_manager = self
        
        # Add to managed objects
        self._managed_objects.add(obj)
        
        return obj
    
    def load_object(self, cls_meta: 'ClsMeta', obj_id: int,
                   partition_id: Optional[int] = None) -> 'OaasObject':
        """
        Load an existing object with automatic session management.
        
        Args:
            cls_meta: Class metadata
            obj_id: Object ID to load
            partition_id: Optional partition ID
            
        Returns:
            Loaded object with auto-commit enabled
        """
        session = self.get_session(partition_id)
        obj = session.load_object(cls_meta, obj_id)
        
        # Enable auto-commit for the object
        obj._auto_commit = True
        obj._auto_session_manager = self
        
        # Add to managed objects
        self._managed_objects.add(obj)
        
        return obj
    
    def schedule_commit(self, obj: 'OaasObject') -> None:
        """
        Schedule an object for auto-commit.
        
        Args:
            obj: Object to commit
        """
        if self._auto_commit_enabled:
            with self._commit_lock:
                self._pending_commits.add(obj)
    
    def commit_all(self) -> None:
        """
        Commit all pending changes across all managed sessions.
        """
        with self._session_lock:
            for session in self._thread_sessions.values():
                try:
                    session.commit()
                except Exception as e:
                    # Log error but continue with other sessions
                    import logging
                    logging.error(f"Error committing session: {e}")
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    async def commit_all_async(self) -> None:
        """
        Asynchronously commit all pending changes across all managed sessions.
        """
        with self._session_lock:
            sessions = list(self._thread_sessions.values())
        
        # Commit all sessions concurrently
        commit_tasks = []
        for session in sessions:
            try:
                task = asyncio.create_task(session.commit_async())
                commit_tasks.append(task)
            except Exception as e:
                # Log error but continue with other sessions
                import logging
                logging.error(f"Error creating commit task: {e}")
        
        if commit_tasks:
            await asyncio.gather(*commit_tasks, return_exceptions=True)
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    def _start_auto_commit_timer(self) -> None:
        """Start the background auto-commit timer."""
        if self._auto_commit_enabled:
            self._auto_commit_timer = threading.Timer(
                self._auto_commit_interval,
                self._auto_commit_background
            )
            self._auto_commit_timer.daemon = True
            self._auto_commit_timer.start()
    
    def _auto_commit_background(self) -> None:
        """Background auto-commit function."""
        try:
            if self._pending_commits:
                self.commit_all()
        except Exception as e:
            import logging
            logging.error(f"Error in background auto-commit: {e}")
        finally:
            # Restart timer
            self._start_auto_commit_timer()
    
    def cleanup_session(self, thread_id: Optional[int] = None) -> None:
        """
        Clean up session for a specific thread or current thread.
        
        Args:
            thread_id: Thread ID to clean up (uses current thread if not provided)
        """
        if thread_id is None:
            thread_id = threading.get_ident()
            
        with self._session_lock:
            if thread_id in self._thread_sessions:
                session = self._thread_sessions[thread_id]
                try:
                    session.commit()  # Final commit before cleanup
                except Exception as e:
                    import logging
                    logging.error(f"Error during session cleanup: {e}")
                del self._thread_sessions[thread_id]
    
    def shutdown(self) -> None:
        """
        Shutdown the auto session manager and clean up resources.
        """
        # Stop auto-commit timer
        if self._auto_commit_timer:
            self._auto_commit_timer.cancel()
            self._auto_commit_timer = None
        
        # Final commit of all sessions
        self.commit_all()
        
        # Clean up all sessions
        with self._session_lock:
            self._thread_sessions.clear()
        
        # Clear managed objects
        self._managed_objects.clear()
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    @contextmanager
    def session_scope(self, partition_id: Optional[int] = None):
        """
        Context manager for explicit session scoping.
        
        Args:
            partition_id: Optional partition ID
            
        Yields:
            Session instance
        """
        session = self.get_session(partition_id)
        try:
            yield session
        finally:
            # Commit any pending changes in this scope
            try:
                session.commit()
            except Exception as e:
                import logging
                logging.error(f"Error committing session in scope: {e}")


class LegacySessionAdapter:
    """
    Adapter to provide backward compatibility with existing Session API.
    
    This class wraps the AutoSessionManager to provide the same interface
    as the traditional Session class while benefiting from automatic management.
    """
    
    def __init__(self, auto_session_manager: AutoSessionManager, partition_id: Optional[int] = None):
        self.auto_session_manager = auto_session_manager
        self._partition_id = partition_id
        self._underlying_session = auto_session_manager.get_session(partition_id)
    
    def create_object(self, cls_meta: 'ClsMeta', obj_id: Optional[int] = None, local: bool = False) -> 'OaasObject':
        """Create an object using the legacy Session API."""
        return self.auto_session_manager.create_object(cls_meta, obj_id=obj_id, local=local, partition_id=self._partition_id)
    
    def load_object(self, cls_meta: 'ClsMeta', obj_id: int) -> 'OaasObject':
        """Load an object using the legacy Session API."""
        return self.auto_session_manager.load_object(cls_meta, obj_id, partition_id=self._partition_id)
    
    def delete_object(self, cls_meta: 'ClsMeta', obj_id: int, partition_id: Optional[int] = None):
        """Delete an object using the legacy Session API."""
        return self._underlying_session.delete_object(cls_meta, obj_id, partition_id or self._partition_id)
    
    def commit(self):
        """Commit changes using the legacy Session API."""
        return self._underlying_session.commit()
    
    async def commit_async(self):
        """Asynchronously commit changes using the legacy Session API."""
        return await self._underlying_session.commit_async()
    
    def obj_rpc(self, req):
        """Perform object RPC using the legacy Session API."""
        return self._underlying_session.obj_rpc(req)
    
    async def obj_rpc_async(self, req):
        """Asynchronously perform object RPC using the legacy Session API."""
        return await self._underlying_session.obj_rpc_async(req)
    
    def fn_rpc(self, req):
        """Perform function RPC using the legacy Session API."""
        return self._underlying_session.fn_rpc(req)
    
    async def fn_rpc_async(self, req):
        """Asynchronously perform function RPC using the legacy Session API."""
        return await self._underlying_session.fn_rpc_async(req)
    
    def invoke_local(self, req):
        """Invoke function locally using the legacy Session API."""
        return self._underlying_session.invoke_local(req)
    
    async def invoke_local_async(self, req):
        """Asynchronously invoke function locally using the legacy Session API."""
        return await self._underlying_session.invoke_local_async(req)
    
    # Expose underlying session attributes for full compatibility
    @property
    def local_obj_dict(self):
        return self._underlying_session.local_obj_dict
    
    @property
    def remote_obj_dict(self):
        return self._underlying_session.remote_obj_dict
    
    @property
    def delete_obj_set(self):
        return self._underlying_session.delete_obj_set
    
    @property
    def partition_id(self):
        return self._partition_id if self._partition_id is not None else self._underlying_session.partition_id
    
    @property
    def rpc_manager(self):
        return self._underlying_session.rpc_manager
    
    @property
    def data_manager(self):
        return self._underlying_session.data_manager
    
    @property
    def meta_repo(self):
        return self._underlying_session.meta_repo
    
    @property
    def local_only(self):
        return self._underlying_session.local_only
