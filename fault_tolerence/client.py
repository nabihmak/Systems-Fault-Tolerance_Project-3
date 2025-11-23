import grpc
import raft_pb2
import raft_pb2_grpc
import sys

def send_command(target_node, command):
    print(f"Connecting to {target_node}...")
    try:
        channel = grpc.insecure_channel(f"{target_node}:50052")
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        print(f"Sending command: {command}")
        response = stub.ExecuteCommand(raft_pb2.CommandRequest(command=command))
        
        if response.success:
            print("SUCCESS: Leader executed command.")
        else:
            print(f"FAILED: Not Leader. Leader is {response.leader_id}")
            if response.leader_id and response.leader_id != "None":
                print(f"Redirecting to Leader {response.leader_id}...")
                send_command(response.leader_id, command)
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    # Usage: python client.py node1 "x=100"
    target = sys.argv[1] if len(sys.argv) > 1 else "node1"
    cmd = sys.argv[2] if len(sys.argv) > 2 else "SET X=10"
    send_command(target, cmd)