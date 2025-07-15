# OaaS-SDK2

This library helps you develop a runtime that can be run in a  Object as a Service (OaaS) serverless. For more information on the OaaS model, visit [https://github.com/hpcclab/OaaS](https://github.com/hpcclab/OaaS).

## Table of Contents
- [Documentation](#documentation)
- [Setup](#setup)
- [Installation](#installation)
- [Features](#features)
- [Examples](#examples)
- [Build the project](#build-the-project)

## Documentation

For a comprehensive guide and API reference, please see the `docs` directory:

- **[Tutorial](docs/tutorial.md)**: A step-by-step guide to getting started with the OaaS SDK.
- **[API Reference](docs/reference.md)**: A detailed reference of all classes, methods, and functions.



## Installation

To install `oaas-sdk2-py`, you can use pip:

```bash
pip install oaas-sdk2-py
```
Or, if you are using `uv`:
```bash
# For adding/installing packages with uv, the command is 'uv pip install'
uv add oaas-sdk2-py
```

## Features

- **Define Classes and Objects**: Easily define classes and create persistent objects.
- **Remote Procedure Calls (RPC)**: Invoke methods on objects remotely.
- **Data Persistence**: Object data is persisted and can be retrieved.
- **Asynchronous Support**: Built with `async/await` for non-blocking operations.
- **Mocking Framework**: Includes a mocking utility for testing your OaaS applications without needing a live environment.
- **Typed Interactions**: Leverages Pydantic for data validation and serialization.
- **Rust-Powered Core**: High-performance core components written in Rust for speed and efficiency.


## Examples

**Note (Sync/Async API):** The following examples demonstrate synchronous operations. To use `async/await` features, initialize Oparaca with `oaas = Oparaca(async_mode=True)`. You would then use methods like `get_data_async`, `set_data_async`, `commit_async`, and define your object methods with `async def`. 

**Note (Remote object):** When an object is created without the `local=True` flag (the default behavior for `mock_oaas.create_object` unless specified, and standard for objects managed by a live OaaS environment), method calls decorated with `@your_cls_meta.func()` on that object instance will result in a Remote Procedure Call (RPC) to the OaaS platform.

### Basic Usage

First, define your class and its methods using the OaaS SDK decorators.

```python
# In your_module.py
from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, BaseObject

# Initialize Oparaca (default is synchronous mode)
oaas = Oparaca()
# For asynchronous operations, use: oaas = Oparaca(async_mode=True)

# Define a class metadata
sample_cls_meta = oaas.new_cls("MySampleClass")

class Msg(BaseModel):
    content: str

class Result(BaseModel):
    status: str
    message: str

@sample_cls_meta
class SampleObj(BaseObject):
    def get_intro(self) -> str:
        raw = self.get_data(0) # Key 0 for intro data
        return raw.decode("utf-8") if raw is not None else "No intro set."

    def set_intro(self, data: str):
        self.set_data(0, data.encode("utf-8"))

    @sample_cls_meta.func()
    def greet(self) -> str:
        intro = self.get_intro()
        return f"Hello from SampleObj! Intro: {intro}"

    @sample_cls_meta.func("process_message")
    def process(self, msg: Msg) -> Result:
        # Process the message
        processed_message = f"Processed: {msg.content}"
        self.set_intro(processed_message) # Example of updating object state
        self.commit()
        return Result(status="success", message=processed_message)

```

### Interacting with Objects

```python
from oaas_sdk2_py import Oparaca
# Assuming your_module defines oaas, sample_cls_meta, SampleObj, Msg
from your_module import oaas, sample_cls_meta, SampleObj, Msg 

def main(): 

    # For local testing, you can use the mock
    mock_oaas = oaas.mock()

    # Create an object
    # obj_id can be any unique identifier, e.g., 1
    my_object: SampleObj = mock_oaas.create_object(sample_cls_meta, 1)

    # Set initial data
    my_object.set_intro("My first OaaS object!")
    my_object.commit() # Persist changes (synchronous)

    # Invoke a simple RPC method
    greeting = my_object.greet()
    print(greeting)

    # Invoke an RPC method with input and output
    response = my_object.process(Msg(content="Important data"))
    print(f"Processing Response: {response.status} - {response.message}")

    # Verify data was updated
    updated_greeting = my_object.greet()
    print(updated_greeting)

    # Load an existing object
    loaded_object: SampleObj = mock_oaas.load_object(sample_cls_meta, 1)
    intro = loaded_object.get_intro()
    print(f"Loaded object intro: {intro}")

if __name__ == "__main__":
    main()
```

### Using the Mock Framework for Tests

The SDK provides a `oaas.mock()` utility that allows you to test your object logic without connecting to a live OaaS environment. This is particularly useful for unit and integration tests.

```python
# In your tests/test_my_sample_class.py
import unittest
# import asyncio # Not needed for synchronous example
from oaas_sdk2_py import Oparaca
# Assuming your_module defines oaas, sample_cls_meta, SampleObj, Msg
from your_module import oaas, sample_cls_meta, SampleObj, Msg

class TestMySampleClass(unittest.TestCase): # Changed from IsolatedAsyncioTestCase

    def test_greeting_with_mock(self): # Changed from async def
        mock_oaas = oaas.mock()
        obj: SampleObj = mock_oaas.create_object(sample_cls_meta, 1)
        
        obj.set_intro("Mocked Intro")
        obj.commit() # In mock, this updates the in-memory store (synchronous)
        
        result = obj.greet()
        self.assertEqual(result, "Hello from SampleObj! Intro: Mocked Intro")

    def test_process_message_with_mock(self): # Changed from async def
        mock_oaas = oaas.mock()
        obj: SampleObj = mock_oaas.create_object(sample_cls_meta, 2)
        
        response = obj.process(Msg(content="Test Message"))
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "Processed: Test Message")
        
        # Verify state change
        intro = obj.get_intro()
        self.assertEqual(intro, "Processed: Test Message")

```

Refer to `tests/test_mock.py` and `tests/sample_cls.py` for more detailed examples of synchronous and asynchronous object definitions and mock usage.


## Run on OaaS


### Prerequisites
- cargo (install via [rust](https://rustup.rs/))
- oprc-cli `cargo install --git https://github.com/pawissanutt/oaas-rs.git oprc-cli`
- OaaS Platform (Oparaca)
    - Kubernetes Cluster (e.g., k3d with Docker runtime)


TODO


## Build the project

You don't need to follow this guide unless you want to build the Python package on your own.

### Prerequisites
- Python
- cargo (install via [rust](https://rustup.rs/))
- [uv](https://github.com/astral-sh/uv) (python package manager)

### Build

```bash
uv sync
uv build
```


