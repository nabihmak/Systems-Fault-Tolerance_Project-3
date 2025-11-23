import grpc
from concurrent import futures
import time
import random
import threading
import argparse
import sys
import os
import raft_pb2
import raft_pb2_grpc

# --- CONFIG ---
ELECTION_TIMEOUT_MIN = 3.0
ELECTION_TIMEOUT_MAX = 6.0
HEARTBEAT_INTERVAL = 1.0

class RaftNode(raft_pb2_grpc.RaftServiceServicer):
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = peers
        
        # State
        self.state = "Follower"
        self.current_term = 0
        self.voted_for = None
        self.current_leader = None
        
        # Log Data
        self.log = [] # List of objects {term, command}
        self.commit_index = -1
        
        # Timers
        self.last_heartbeat = time.time()
        self.lock = threading.RLock()

    # --- CLIENT REQUEST HANDLER (Q4 Requirement) ---
    def ExecuteCommand(self, request, context):
        with self.lock:
            # If I am not leader, forward to leader (or tell client who is)
            if self.state != "Leader":
                print(f"Node {self.node_id} received client request but is NOT Leader. Forwarding...", flush=True)
                return raft_pb2.CommandResponse(success=False, message="Not Leader", leader_id=str(self.current_leader))
            
            # I am Leader: Append to local log
            entry = raft_pb2.LogEntry(term=self.current_term, command=request.command)
            self.log.append(entry)
            print(f"Node {self.node_id} (Leader) received client command: '{request.command}'. Appended to Log.", flush=True)
            
            # In a real Raft, we wait for replication. 
            # For this simplified assignment, we replicate on next heartbeat.
            return raft_pb2.CommandResponse(success=True, message="Command Accepted", leader_id=self.node_id)

    # --- RPC HANDLERS ---
    def RequestVote(self, request, context):
        print(f"Node {self.node_id} runs RPC RequestVote called by Node {request.candidate_id}", flush=True)
        with self.lock:
            if request.term > self.current_term:
                self.current_term = request.term
                self.state = "Follower"
                self.voted_for = None
            
            vote_granted = False
            if request.term == self.current_term and (self.voted_for is None or self.voted_for == request.candidate_id):
                vote_granted = True
                self.voted_for = request.candidate_id
                self.last_heartbeat = time.time() 
            
            return raft_pb2.VoteResponse(term=self.current_term, vote_granted=vote_granted)

    def AppendEntries(self, request, context):
        # REQUIRED LOG
        print(f"Node {self.node_id} runs RPC AppendEntries called by Node {request.leader_id}", flush=True)
        
        with self.lock:
            if request.term >= self.current_term:
                self.current_term = request.term
                self.state = "Follower"
                self.current_leader = request.leader_id
                self.last_heartbeat = time.time()
                
                # Q4: Replicate Log
                if len(request.entries) > 0:
                    for entry in request.entries:
                        self.log.append(entry)
                        print(f"Node {self.node_id} committed data: {entry.command}", flush=True)
                
                return raft_pb2.AppendEntryResponse(term=self.current_term, success=True)
            
            return raft_pb2.AppendEntryResponse(term=self.current_term, success=False)

    # --- ACTIONS ---
    def start_election(self):
        with self.lock:
            self.state = "Candidate"
            self.current_term += 1
            self.voted_for = self.node_id
            print(f"!!! Node {self.node_id} starting Election for Term {self.current_term} !!!", flush=True)

        for peer in self.peers:
            threading.Thread(target=self.send_vote_request, args=(peer,)).start()

    def send_vote_request(self, peer):
        try:
            peer_id = peer.split(':')[0]
            print(f"Node {self.node_id} sends RPC RequestVote to Node {peer_id}", flush=True)
            
            channel = grpc.insecure_channel(peer)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            response = stub.RequestVote(raft_pb2.VoteRequest(term=self.current_term, candidate_id=self.node_id), timeout=0.2)
            
            with self.lock:
                if self.state == "Candidate" and response.vote_granted:
                    threading.Thread(target=self.become_leader).start()
        except:
            pass

    def become_leader(self):
        with self.lock:
            if self.state != "Candidate": return
            self.state = "Leader"
            self.current_leader = self.node_id
            print(f"*** Node {self.node_id} became Leader ***", flush=True)
            
        while self.state == "Leader":
            self.send_heartbeats()
            time.sleep(HEARTBEAT_INTERVAL)

    def send_heartbeats(self):
        with self.lock:
            # For simulation: If I have logs, send them!
            entries_to_send = self.log # simplified: send whole log
        
        for peer in self.peers:
            threading.Thread(target=self.send_heartbeat_single, args=(peer, entries_to_send)).start()
            
    def send_heartbeat_single(self, peer, entries):
        try:
            peer_id = peer.split(':')[0]
            print(f"Node {self.node_id} sends RPC AppendEntries to Node {peer_id}", flush=True)
            
            channel = grpc.insecure_channel(peer)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            
            stub.AppendEntries(raft_pb2.AppendEntryRequest(
                term=self.current_term, 
                leader_id=self.node_id,
                entries=entries # Q4: Sending Data!
            ), timeout=0.2)
        except:
            pass

# --- MAIN ---
def run_node(node_id, port, peers):
    node = RaftNode(node_id, peers)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServiceServicer_to_server(node, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Node {node_id} listening on {port}", flush=True)
    
    timeout = random.uniform(ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX)
    
    while True:
        time.sleep(0.5)
        with node.lock:
            if node.state != "Leader":
                if time.time() - node.last_heartbeat > timeout:
                    node.start_election()
                    timeout = random.uniform(ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX)
                    node.last_heartbeat = time.time()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, required=True)
    parser.add_argument('--peers', type=str, required=True)
    args = parser.parse_args()
    
    peers_list = [p for p in args.peers.split(',') if p != ""]
    run_node(args.id, '50052', peers_list)