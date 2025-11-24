# Two-Phase Commit Protocol Implementation

A distributed transaction coordination system implementing the Two-Phase Commit (2PC) protocol using gRPC and Python. This project demonstrates how distributed systems achieve atomic commitment across multiple nodes.

**Github Link:** https://github.com/nabihmak/Systems-Fault-Tolerance_Project-3/tree/main/2PC

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
  - [Protocol Phases](#protocol-phases)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Using Docker (Recommended)](#using-docker-recommended)
  - [Local Development](#local-development)
- [Usage](#usage)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Running Manually](#running-manually)
- [Configuration](#configuration)
  - [Docker Compose Services](#docker-compose-services)
  - [Environment Variables](#environment-variables)
- [Protocol Details](#protocol-details)
  - [gRPC Service Definition](#grpc-service-definition)
  - [Transaction Flow](#transaction-flow)
  - [Logging Format](#logging-format)
- [Fault Tolerance Features](#fault-tolerance-features)

## Overview

The Two-Phase Commit protocol ensures that all participants in a distributed transaction either commit or abort together, maintaining consistency across the system. This implementation uses a coordinator-participant architecture with gRPC for communication.

## Architecture

The system consists of:
- **1 Coordinator**: Orchestrates the transaction by collecting votes and broadcasting decisions
- **4 Participants (Nodes)**: Vote on transaction proposals and execute final decisions

### Protocol Phases

1. **Voting Phase**
   - Coordinator sends `RequestVote` RPC to all participants
   - Each participant responds with `VoteCommit` (80% probability) or `VoteAbort` (20% probability)

2. **Decision Phase**
   - Coordinator aggregates votes and makes final decision
   - If all votes are commit: sends `GlobalCommit` RPC
   - If any vote is abort: sends `GlobalAbort` RPC
   - Participants acknowledge and execute the decision

## Project Structure

```
.
├── two_pc.proto           # Protocol Buffers definition for gRPC service
├── two_pc_node.py         # Main implementation (coordinator & participant logic)
├── two_pc_pb2.py          # Generated protobuf message classes
├── two_pc_pb2_grpc.py     # Generated gRPC service stubs
├── client.py              # Client for Raft service (legacy/testing)
├── docker-compose.yml     # Container orchestration for multi-node deployment
├── Dockerfile             # Container image definition
└── requirements.txt       # Python dependencies
```

## Prerequisites

- Docker and Docker Compose
- Python 3.x (for local development)
- gRPC and Protocol Buffers

## Installation

### Using Docker (Recommended)

1. Build and start all services:
```bash
docker-compose up --build
```

This will start:
- 4 participant nodes (node1, node2, node3, node4)
- 1 coordinator node

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate gRPC code from proto file:
```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. two_pc.proto
```

## Usage

### Running with Docker Compose

```bash
docker-compose up
```

Watch the logs to see:
- Voting phase: Coordinator requests votes from participants
- Decision phase: Coordinator broadcasts final decision
- Acknowledgments from participants

### Running Manually

**Start Participant Nodes:**
```bash
python two_pc_node.py --role participant --id node1
python two_pc_node.py --role participant --id node2
python two_pc_node.py --role participant --id node3
python two_pc_node.py --role participant --id node4
```

**Start Coordinator:**
```bash
python two_pc_node.py --role coordinator --id Coordinator --participants node1:50051,node2:50051,node3:50051,node4:50051
```

## Configuration

### Docker Compose Services

- **Participants**: Run on port 50051 (internal)
- **Coordinator**: Waits 10 seconds for network initialization before starting

### Environment Variables

Modify [docker-compose.yml](docker-compose.yml) to:
- Add/remove participants
- Change network configuration
- Adjust service dependencies

## Protocol Details

### gRPC Service Definition

```protobuf
service TwoPCService {
    rpc RequestVote (VoteRequest) returns (VoteResponse);
    rpc GlobalCommit (DecisionRequest) returns (Ack);
    rpc GlobalAbort (DecisionRequest) returns (Ack);
}
```

### Transaction Flow

1. Coordinator sends `RequestVote` to all participants
2. Each participant decides (80% commit, 20% abort) and responds
3. Coordinator collects all votes
4. If unanimous commit: sends `GlobalCommit`
5. If any abort: sends `GlobalAbort`
6. Participants execute decision and acknowledge

### Logging Format

All RPC communications are logged in the format:
```
Phase <phase_name> of Node <node_id> sends RPC <rpc_name> to Phase <phase_name> of Node <node_id>
```

Example:
```
Phase Voting of Node Coordinator sends RPC RequestVote to Phase Voting of Node node1
Phase Voting of Node node1 sends RPC VoteCommit to Phase Voting of Node Coordinator
Phase Decision of Node Coordinator sends RPC GlobalCommit to Phase Decision of Node node1
```

## Fault Tolerance Features

- **Timeout Handling**: Connection failures treated as abort votes
- **Network Delays**: 10-second initialization delay for service discovery
- **Probabilistic Voting**: Simulates real-world scenarios where nodes may vote abort

## Dependencies

- `grpcio`: gRPC runtime
- `grpcio-tools`: Protocol buffer compilation
- `Flask`: Web framework (for extended functionality)
- `requests`: HTTP library

## Limitations

- No persistent storage (transactions stored in-memory)
- No recovery mechanism for coordinator failure
- Blocking protocol (participants wait for coordinator decision)
- No timeout for participant responses

## Future Enhancements

- Implement Three-Phase Commit (3PC) for non-blocking behavior
- Add persistent transaction logs
- Implement coordinator failure recovery
- Add timeout mechanisms and retry logic
- Support for dynamic participant registration

## License

This is an implementation of Q1 and Q2 from Group 5's Project 2 for Project 3

## References

- [Two-Phase Commit Protocol](https://en.wikipedia.org/wiki/Two-phase_commit_protocol)
- [gRPC Documentation](https://grpc.io/docs/)
- [Protocol Buffers](https://developers.google.com/protocol-buffers)
