

protoc:
    poetry run python -m grpc_tools.protoc \
      -Ioaas_sdk2_py/pb=./protos \
      --python_betterproto_out=oaas_sdk2_py/pb \
      --python_betterproto_opt=pydantic_dataclasses,typing.310 \
      ./protos/oprc-data.proto \
      ./protos/oprc-invoke.proto


step-1:
  echo "{}" | http POST :10000/api/class/example.hello/*/invokes/new

step-1-verify id="1":
  oprc-cli -z tcp/127.0.0.1:7447 o g example.hello 0 {{id}} 

step-2 id="1":
  echo "{}" | http POST :10000/api/class/example.hello/0/objects/{{id}}/invokes/greet
