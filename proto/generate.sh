#!/usr/bin/env bash
# Regenera os stubs Python a partir do .proto
# Execute a partir da raiz do monorepo: bash proto/generate.sh

set -e
PROTO_DIR="proto"
PROTO_FILE="$PROTO_DIR/biblioteca.proto"

echo "Gerando stubs para grpc-service/ ..."
python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="grpc-service/" \
  --grpc_python_out="grpc-service/" \
  "$PROTO_FILE"

echo "Gerando stubs para api-web/biblioteca/grpc_generated/ ..."
python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="api-web/biblioteca/grpc_generated/" \
  --grpc_python_out="api-web/biblioteca/grpc_generated/" \
  "$PROTO_FILE"

echo "Stubs gerados com sucesso."
