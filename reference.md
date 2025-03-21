# *OaaS-SDK2-PY*
Contents:
- [Description](#description)
- [Prerequisites](#prerequisites)
- [Tutorial](#tutorial)
    - [Installation](#installation)
    - [Create a base code](#create-a-base-code)
    - [Set up configurations](#set-up-configurations)
    - [Deploy functions](#deploy-functions)
- [List of Functions](#list-of-functions)
- [Configuration](#configuration)
- [oprc-cli](#oprc-cli)

## *Description*
The OaaS-SDK2-PY project was designed to provide a Python-based interface for seamless interaction with OaaS. Using this python library, developers can implement classes and functions, and the created functions can be invoked for actual execution. 

In summary of overall development, the process consists of three major steps to successfully implemenet and launch a program
1. Application development with `OaaS-SDK2-PY`
2. Configuration setup with a YAML file 
3. Deployement and invocation with `oprc-cli`

For more details, since OaaS adopts the concept of OOP (Object-Oriented-Programing), a class needs to be created priorly. Each class may contain several functions that can be invoked later. 

After completion of a program development, configurations for the service of a program need to be defined, using a YAML-based file. 
>NOTE: The current version of OaaS-SDK2-PY provides only the separation of software development and configuration for higher customization and better service organization. Our future work may include in-one-site service in which both software development and configuration can be done in single file.

## *Prerequisites*
There are several prerequisites to be installed priorly.
- cargo (install via [rust](https://rustup.rs/))
- oprc-cli `cargo install --git https://github.com/pawissanutt/oaas-rs.git oprc-cli`
- [uv](https://github.com/astral-sh/uv) (python package manager)
- docker or podman

### Tutorial 
This section provides a tutorial using the `helloworld` example to demonstrate how to use OaaS-SDK2-PY.

1. Installation 
1. Create a base code 
2. Set up configurations
3. Deploy functions

### Installation
Of course, the first step to use the python library is to install OaaS-SDK2-PY. 

Run the following command to install OaaS-SDK2-PY

```python
installation code here
```

### Create a base code


The basic structure of a class looks like below 
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





### Set up configurations 


### Deploy functions


## *List of Functions*


## *Configuration*
The current OaaS provides two different methods for interactive connection calls: gRPC and Zenoh. Based on the selected interactive connection, configuration settings in `docker-compose.yml` should be modified accordingly 

## *oprc-cli*