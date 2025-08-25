"""
RPC Future Management Utilities

This module provides utilities for managing non-blocking RPC calls,
including batch execution, timeouts, and coordination.
"""

import asyncio
import time
from typing import Any, List, Optional, Dict, Union, Awaitable
from concurrent.futures import Future
import logging

import oprc_py


class RpcFuture:
    """
    Python wrapper for non-blocking RPC calls with additional utilities.
    
    This class wraps the Python awaitable returned from Rust and provides
    additional functionality like timeouts, status checking, and coordination.
    """
    
    def __init__(self, awaitable: Awaitable, request_id: Optional[str] = None):
        """
        Initialize RPC future wrapper.
        
        Args:
            awaitable: Python awaitable from Rust RPC manager
            request_id: Optional request identifier for tracking
        """
        self._awaitable = awaitable
        self._request_id = request_id or f"rpc_{int(time.time() * 1000)}"
        self._result: Optional[oprc_py.InvocationResponse] = None
        self._error: Optional[Exception] = None
        self._completed = False
        self._task: Optional[asyncio.Task] = None
        
    @property
    def request_id(self) -> str:
        """Get the request ID for this RPC call."""
        return self._request_id
        
    @property
    def completed(self) -> bool:
        """Check if the RPC call has completed."""
        return self._completed
        
    @property
    def result(self) -> Optional[oprc_py.InvocationResponse]:
        """Get the result if completed successfully."""
        return self._result
        
    @property
    def error(self) -> Optional[Exception]:
        """Get the error if completed with error."""
        return self._error
        
    async def wait_for(self, timeout: Optional[float] = None) -> oprc_py.InvocationResponse:
        """
        Wait for the RPC call to complete with optional timeout.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            InvocationResponse when completed
            
        Raises:
            asyncio.TimeoutError: If timeout expires
            Exception: If RPC call fails
        """
        try:
            if timeout:
                result = await asyncio.wait_for(self._awaitable, timeout=timeout)
            else:
                result = await self._awaitable
                
            self._result = result
            self._completed = True
            return result
            
        except Exception as e:
            self._error = e
            self._completed = True
            raise
    
    async def __await__(self):
        """Make RpcFuture directly awaitable."""
        return await self.wait_for()
        
    def start_background(self) -> asyncio.Task:
        """
        Start the RPC call in the background and return a task.
        
        Returns:
            asyncio.Task that can be managed separately
        """
        if self._task is None:
            self._task = asyncio.create_task(self._awaitable)
        return self._task
        
    def cancel(self) -> bool:
        """
        Cancel the RPC call if it's running as a background task.
        
        Returns:
            True if successfully cancelled
        """
        if self._task and not self._task.done():
            return self._task.cancel()
        return False


class RpcBatch:
    """
    Manages multiple concurrent RPC calls for batch execution.
    
    This class provides utilities for executing multiple RPC calls
    in parallel and coordinating their results.
    """
    
    def __init__(self):
        """Initialize empty RPC batch."""
        self._futures: List[RpcFuture] = []
        self._tags: Dict[str, RpcFuture] = {}
        
    def add(self, future: RpcFuture, tag: Optional[str] = None) -> 'RpcBatch':
        """
        Add an RPC future to the batch.
        
        Args:
            future: RpcFuture to add
            tag: Optional tag for identifying this future
            
        Returns:
            Self for method chaining
        """
        self._futures.append(future)
        if tag:
            self._tags[tag] = future
        return self
        
    def get_by_tag(self, tag: str) -> Optional[RpcFuture]:
        """Get a future by its tag."""
        return self._tags.get(tag)
        
    @property
    def size(self) -> int:
        """Get the number of futures in the batch."""
        return len(self._futures)
        
    async def wait_all(self, timeout: Optional[float] = None) -> List[oprc_py.InvocationResponse]:
        """
        Wait for all RPC calls in the batch to complete.
        
        Args:
            timeout: Optional timeout for all calls
            
        Returns:
            List of InvocationResponses in the same order as added
            
        Raises:
            asyncio.TimeoutError: If timeout expires
        """
        awaitables = [future._awaitable for future in self._futures]
        
        if timeout:
            results = await asyncio.wait_for(
                asyncio.gather(*awaitables, return_exceptions=False),
                timeout=timeout
            )
        else:
            results = await asyncio.gather(*awaitables, return_exceptions=False)
            
        # Update future states
        for i, result in enumerate(results):
            self._futures[i]._result = result
            self._futures[i]._completed = True
            
        return results
        
    async def wait_any(self, timeout: Optional[float] = None) -> tuple[RpcFuture, oprc_py.InvocationResponse]:
        """
        Wait for any RPC call in the batch to complete.
        
        Args:
            timeout: Optional timeout
            
        Returns:
            Tuple of (completed_future, result)
            
        Raises:
            asyncio.TimeoutError: If timeout expires
        """
        tasks = [(i, asyncio.create_task(future._awaitable)) for i, future in enumerate(self._futures)]
        
        try:
            if timeout:
                done, pending = await asyncio.wait_for(
                    asyncio.wait([task for _, task in tasks], return_when=asyncio.FIRST_COMPLETED),
                    timeout=timeout
                )
            else:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks], 
                    return_when=asyncio.FIRST_COMPLETED
                )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                
            # Get the completed result
            completed_task = done.pop()
            result = await completed_task
            
            # Find which future completed
            for i, (_, task) in enumerate(tasks):
                if task == completed_task:
                    future = self._futures[i]
                    future._result = result
                    future._completed = True
                    return future, result
                    
        except Exception as e:
            # Cancel all tasks on error
            for _, task in tasks:
                if not task.done():
                    task.cancel()
            raise
            
        raise RuntimeError("No completed task found")  # Should never reach here
        
    def get_completed(self) -> List[RpcFuture]:
        """Get all completed futures."""
        return [future for future in self._futures if future.completed]
        
    def get_pending(self) -> List[RpcFuture]:
        """Get all pending futures."""
        return [future for future in self._futures if not future.completed]


class RpcTaskManager:
    """
    Advanced task management and coordination for RPC calls.
    
    This class provides sophisticated task management including
    priority queues, resource limits, and coordination patterns.
    """
    
    def __init__(self, max_concurrent: int = 100):
        """
        Initialize task manager.
        
        Args:
            max_concurrent: Maximum number of concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, RpcFuture] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._logger = logging.getLogger(__name__)
        
    async def add_task(self, task_id: str, future: RpcFuture) -> None:
        """
        Add a task to the manager.
        
        Args:
            task_id: Unique identifier for the task
            future: RpcFuture to manage
        """
        if task_id in self._tasks:
            raise ValueError(f"Task {task_id} already exists")
            
        self._tasks[task_id] = future
        
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> oprc_py.InvocationResponse:
        """
        Wait for a specific task to complete.
        
        Args:
            task_id: Task identifier
            timeout: Optional timeout
            
        Returns:
            InvocationResponse for the task
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
            
        future = self._tasks[task_id]
        return await future.wait_for(timeout)
        
    async def wait_for_any(self, task_ids: Optional[List[str]] = None) -> tuple[str, oprc_py.InvocationResponse]:
        """
        Wait for any task to complete.
        
        Args:
            task_ids: Optional list of specific task IDs to wait for
            
        Returns:
            Tuple of (task_id, result)
        """
        if task_ids:
            tasks_to_wait = {task_id: self._tasks[task_id] for task_id in task_ids if task_id in self._tasks}
        else:
            tasks_to_wait = self._tasks.copy()
            
        if not tasks_to_wait:
            raise ValueError("No tasks to wait for")
            
        # Create batch and wait for any
        batch = RpcBatch()
        task_id_map = {}
        
        for task_id, future in tasks_to_wait.items():
            batch.add(future)
            task_id_map[future.request_id] = task_id
            
        completed_future, result = await batch.wait_any()
        task_id = task_id_map[completed_future.request_id]
        
        return task_id, result
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successfully cancelled
        """
        if task_id in self._tasks:
            return self._tasks[task_id].cancel()
        return False
        
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status information for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with task status information
        """
        if task_id not in self._tasks:
            return {"exists": False}
            
        future = self._tasks[task_id]
        return {
            "exists": True,
            "completed": future.completed,
            "request_id": future.request_id,
            "has_result": future.result is not None,
            "has_error": future.error is not None
        }


# Utility functions for common patterns
async def gather_rpc(*futures: RpcFuture, timeout: Optional[float] = None) -> List[oprc_py.InvocationResponse]:
    """
    Gather results from multiple RPC futures (similar to asyncio.gather).
    
    Args:
        *futures: RpcFuture instances to gather
        timeout: Optional timeout for all futures
        
    Returns:
        List of InvocationResponses
    """
    batch = RpcBatch()
    for future in futures:
        batch.add(future)
    return await batch.wait_all(timeout)


async def timeout_rpc(future: RpcFuture, timeout: float) -> oprc_py.InvocationResponse:
    """
    Add timeout to an RPC future.
    
    Args:
        future: RpcFuture to add timeout to
        timeout: Timeout in seconds
        
    Returns:
        InvocationResponse
        
    Raises:
        asyncio.TimeoutError: If timeout expires
    """
    return await future.wait_for(timeout)


def create_rpc_future(awaitable: Awaitable, request_id: Optional[str] = None) -> RpcFuture:
    """
    Create an RpcFuture from an awaitable.
    
    Args:
        awaitable: Python awaitable from RPC manager
        request_id: Optional request identifier
        
    Returns:
        RpcFuture wrapper
    """
    return RpcFuture(awaitable, request_id)