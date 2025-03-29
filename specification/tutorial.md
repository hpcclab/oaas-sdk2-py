# *OaaS-SDK2-PY Tutorial*
Table of Contents: 
- [Description](#description)
    - [Description Overview](#description-overview)
    - [Core Components](#core-components)
- [Tutorial](#tutorial)
    - [First Steps](#first-steps)
    - [Tutorial Overview](#tutorial-overview)
    - [Basic Example](#basic-example)
    - [Configuration setup](#configuration-setup)
    - [Working with Classes and Functions](#working-with-classes-and-functions)
- [CLI](#cli)
    - [CLI Overview](#cli-overview)
    - [Commands](#commands)
    - [Example Usage](#example-usage)
- [Deployment](#deployment)
    - [Deployment Overview](#deployment-overview)
    - [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)


## *Description*
In this section, an overview of OaaS-SDK2-PY will be provided, while the details of each individual component and process will be discussed in separate sections.
### *Description Overview*
Simply, OaaS-SDK2-PY is a python-based framework to provide software developers to seamlessly develop applications, refine requirements, deploy programs, and maintain services on OaaS. 

The process consists of three major steps to successfully implemenet and launch a program

1. Application development with `OaaS-SDK2-PY`
2. Configuration setup with a YAML file 
3. Deployement and invocation with `oprc-cli`

For more details, since OaaS adopts the concept of OOP (Object-Oriented-Programing), a class needs to be created priorly. Each class may contain several functions that can be invoked later. 

After completion of a program development, configurations for the service of a program need to be defined, using a YAML-based file. 

>NOTE: The current version of OaaS-SDK2-PY provides only the separation of software development and configuration for higher customization and better service organization. Our future work may include in-one-site service in which both software development and configuration can be done in single file.
### *Core Components*
We have organized our framework with several components based on their functionality and purpose. 
- Python-based OaaS libraries
- YAML Configuration
- CLI
- Messaging Infrastructure

Python-based OaaS libraries are essentially a Python SDK that allows applications to interact with the OaaS structure. To meet specific requirements, the configuration can be adjusted using a YAML file. Once both the application code and configuration are properly set up, these two files are bundled into one container and sent to the OaaS Package Manager via the CLI tool. The Messaging Infrastructure component supports the MQTT-based protocol for basic Pub/Sub services. For this project, we used the Zenoh protocol instead of the pure MQTT protocol.



## *Tutorial*
In this tutorial, we'll walk you through the process of setting up and using the SDK with an example `Helloworld` application. This application includes a `Greeter` class that demonstrates how to create an object, invoke methods, and handle data. By the end of this tutorial, you'll be able to extend this example to build more complex applications.
### *First Steps*
Before moving onto the main part of tutorial, there are some prerequisities to be installed if your system does not have them yet. 

- cargo (install via [rust](https://rustup.rs/))
- oprc-cli `cargo install --git https://github.com/pawissanutt/oaas-rs.git oprc-cli`
- [uv](https://github.com/astral-sh/uv) (python package manager)
- docker or podman

### *Tutorial Overview*
For an insight, the basic structure of a class looks like below 
```python
from oaas_sdk2_py import Oparaca, start_grpc_server
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import InvocationContext, BaseObject
from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ResponseStatus


oaas = Oparaca(config=OprcConfig())

example_object = oaas.new_cls(pkg="example", name="example_service")

@example_object
class ExampleService(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)

    @example_object.func(stateless=True)
    async def echo(self, req):
        return {"message": "Echo Response", "payload": req}

async def main(port=8080):
    server = await start_grpc_server(oaas, port=port)
    await server.wait_closed()

```
Here's a brief explanation: 
- `Oparaca`: The main class that manages the SDK’s operations. It is initialized with configuration via OprcConfig.
- `new_cls(pkg="example", name="example_service")`: This function creates a new class under a specified package (example in this case) and assigns it the name (example_service).
- `@example_object`: The decorator that registers the class with the Oparaca framework, linking the class to the metadata and invocation functionality.
- `BaseObject`: A base class used to define objects within the SDK. It allows interaction with object data and provides functionality for function invocation.
- `func(stateless=True)`: A decorator applied to methods to define them as callable functions. stateless=True means that the function doesn’t maintain state between invocations.
- `start_grpc_server()`: A function to start the gRPC server, which listens for incoming requests.


### *Basic Example*
Given that basic structure, now we'll be going through a sample code, `Helloworld`, step by step. 

1. **Create a New Class**

The `Oparaca` class is the main interface to the SDK. It manages class creation, context initialization, and RPC communication. In this example, we'll create a class called `Greeter` using `Oparaca`.

```python
oaas = Oparaca(config=OprcConfig())
greeter = oaas.new_cls(pkg="example", anme="hello")
```

Here, `Oparaca(config=OprcConfig())` initializes the `Oparaca` object with the configuration provided in `OprConfig`. The config handles settings like the OPRC URL. 

Next, `oaas.new_cls(pkg="example", name="hello")` creates a new class `Greeter` under the package `example` with the name `hello`.

2. **Define a Class with Methods**

Now that we have created a `Greeter` class, we can define methods in it. Let's create a method called `greet` that will return a greeting message. 

```python
@greeter
class Greeter(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)
    
    @greeter.func()
    async def greet(self, req: Greet) -> GreetResponse:
        intro = await self.get_intro()
        resp = "hello " + req.name + ". " + intro
        return GreetResponse(message=resp)
```

From the above code, @greeter decorator registers the class with `Oparaca`, so it's linked to the `Greeter` class. 

`greet(self, req: Greet) -> GreetResponse` is a function that takes in a `Greet` object and returns a `GreetResponse`. It uses the `get_intro()` function to fetch an introduction message and combines it with the greeting message. 

3. **Data Handling**

In the `Greeter` class, we use `BaseObject` to store the state (such as the introduction message). This is handled through the `data_getter` and `data_setter` decorators. 

Here is an example of `data_getter`:

```python
@greeter.data_getter(index=0)
async def get_intro(self, raw: bytes=None) -> str:
    return raw.decode("utf-8")
```

The `data_getter` decorator specified that the `get_intro` function will retrieve data from the object's state using the index `0`.

Here is an example of `data_setter`:

```python
@greeter.data_setter(index=0)
async def set_intro(self, data: str) -> bytes:
    return data.encode("utf-8")
```

The `data_setter` decorator allows us to set the introduction message in the object's state. 

4. **Define and Use REquest Models**
In the `Greeter` class, we use Pydantic models to define request and response structures. 

Here is an example of Request model:

```python
class Greet(BaseModel):
    name: str = "world"
```

The `Greet` class is a simple model that makes a `name` parameter. 

Here is an example of Response model:

```python
class GreetResponse(BaseModel):
    message: str
```

The `GreetResponse` model holds the response data, which includes the greeting message.

5. **Example Function to Change Intro**

We can also define other methods to update the state of the object, like changing the introduction message. 

```python
async def change_intro(self, req: UpdateIntro):
    await self.set_intro(req.intro)
```

This method allows the user to update the introduction message by setting a new value using the `set_intro()` function.

6. **Create an Object Instance**

Once the class and methods are defined, you can create an object instance and invoke the methods on it. 

```python
greet_request = Greet(name="Alice")
greet_response = await greeter.greet(greet_request)
```

`greet_request` is an instance of the `Greet` model with the `name` set to `"Alice"`

`greet_response` is the response from invoking the `greet` method.

7. **Run the Server**

To run the server and handle incoming requests, use the `start_grpc_server` method

```python
async def main(port=8080):
    server = await start_grpc_server(oaas, port=port)
    await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
```

`start_grpc_server(oaas, port=port)` starts a gRPC server to handle requests on the specified port. 

`await server.wait_closed()` keeps the server running until it's manually closed.

8. **Complete Code**

The complete code should look like this
```python
from oaas_sdk2_py import Oparaca, start_grpc_server
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import InvocationContext, BaseObject
from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ResponseStatus

oaas = Oparaca(config=OprcConfig())
greeter = oaas.new_cls(pkg="example", name="hello")

@greeter
class Greeter(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)  

    @greeter.func(stateless=True)
    async def greet(self, req: Greet) -> GreetResponse:
        intro = await self.get_intro()
        resp = "hello " + req.name + ". " + intro
        return GreetResponse(message=resp)  

    @greeter.data_getter(index=0)
    async def get_intro(self, raw: bytes = None) -> str:
        return raw.decode("utf-8")  

    @greeter.data_setter(index=0)
    async def set_intro(self, data: str) -> bytes:
        return data.encode("utf-8")  

async def main(port=8080):
    server = await start_grpc_server(oaas, port=port) 
    await server.wait_closed()  
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())  

```

### *Configuration setup*
TODO YAML configuration here.

### *Working with Classes and Functions*
>Make sure that docker is running on the background in your system.

The following commands are for testing an example function invocation.

```bash
docker compose up -d --build
# invoke new function of 'example.hello' class
echo "{}" | oprc-cli i -g http://localhost:10002 example.hello 0 new -p -
```

Here, the first command is for creating refined configuration with a YAML file. After that, `echo "{}"` creates an empty string value, and this value is passed to `oprc-cli` command as an input. Specificaly, the target URL, `https://localhost:10002` is 

## *CLI*
### *CLI Overview*
### *Commands*
### *Example Usage*



## *Deployment*
### *Deployment Overview*
### *Configuration*



## *Troubleshooting*



