FROM python:3.9-slim

WORKDIR /app

# 1. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy all source code
COPY . .

# 3. Generate gRPC code (This creates two_pc_pb2.py and two_pc_pb2_grpc.py)
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. two_pc.proto

# 4. Default command (overridden by compose)
CMD ["python", "two_pc_node.py"]