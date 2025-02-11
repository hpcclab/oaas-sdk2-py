
compose cri="docker":
    {{cri}} compose up -d

protoc:
    poetry run python -m grpc_tools.protoc \
      -Ioaas_sdk2_py/pb=./protos \
      --python_betterproto_out=oaas_sdk2_py/pb \
      --python_betterproto_opt=pydantic_dataclasses,typing.310 \
      ./protos/oprc-data.proto \
      ./protos/oprc-invoke.proto

restart-func cri="docker":
    {{cri}} compose restart hello-fn

step-1:
  #echo "{}" | http POST :10000/api/class/example.hello/*/invokes/new
  echo "{}" | oprc-cli i -g http://localhost:10002 example.hello 0 new -p -

step-1-verify id="1":
  oprc-cli o g example.hello 0 {{id}} -z tcp/127.0.0.1:17447 --peer

step-2 id="1":
  #echo "{}" | http POST :10000/api/class/example.hello/0/objects/{{id}}/invokes/greet
  echo "{}" | oprc-cli i -g http://localhost:10002 example.hello 0 greet -p -
