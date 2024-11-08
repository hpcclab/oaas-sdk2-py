

protoc:
    poetry run python -m grpc_tools.protoc \
      -Ioaas_sdk2_py/pb=./protos \
      --python_betterproto_out=oaas_sdk2_py/pb \
      --python_betterproto_opt=pydantic_dataclasses,typing.310 \
      ./protos/oprc-data.proto \
      ./protos/oprc-invoke.proto

