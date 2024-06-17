# Duo Workflow Service

## Getting Started

### Compile protobufs

```
python -m grpc_tools.protoc  \
  --python_out=. --pyi_out=. --grpc_python_out=. \
  -I=../../../../../duo-workflow/duo-workflow-executor/pkg/service \
  ../../../../../duo-workflow/duo-workflow-executor/pkg/service/contract.proto
```
