# OaaS-SDK2

Python Lib for OaaS-IoT

## Prerequisites
- cargo (install via [rust](https://rustup.rs/))
- oprc-cli `cargo install --git https://github.com/pawissanutt/oaas-rs.git oprc-cli`
- [uv](https://github.com/astral-sh/uv) (python package manager)
- docker or podman

## Setup

```bash
uv sync
./.venv/Scripts/activate
```

## Run Example with Docker Compose

```bash
docker compose up -d
# invoke new function of 'example.hello' class
echo "{}" | oprc-cli i -g http://localhost:10002 example.hello 0 new -p 

```

### Oprc-CLI




## TODOs



### Features

- [x] read data  
- [x] Write data  
- [x] Serve gRPC for invocation  
- [ ] Create an object reference  
- [ ] Call gRPC to invoke a foreign function 
- [ ] Implement thread Pool  
- [ ] Connect to Zenoh  
- [ ] Device Agent:  
    - [ ] Invoke a remote function on the referenced object  
    - [ ] Invoke a local function on the referenced object  
    - [ ] Invoke a local function on device agent from the anywhere else  
    - [ ] Access data from the referenced object  

- [ ] create interface of referenced object 
- [ ] declare deployment configuration in code

### QoL Features
- [ ] Improve data encode/decode
- [ ] Development CLI
    - [ ] generate project
    - [ ] setup development environment (e.g., generate docker compose for ODGM)
    - [ ] generate YAML class definition from class in Python 
    - [ ] build project
    - [ ] deploy class/object


## NOTE

- grpcio vs grpclib

    https://github.com/llucax/python-grpc-benchmark

