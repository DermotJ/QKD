#! usr/bin/python3
import os
import sys
from squanch import *
from random import randint
class Alice(Agent):
    
    def distribute_bell_pair(self, a, b):
            # Create a Bell pair and send one particle to Bob
            H(a)
            CNOT(a, b)
            self.qsend(bob, b)

    def teleport(self, q, a):
            # Perform the teleportation
            CNOT(q, a)
            H(q)
            # Tell Bob whether to apply Pauli-X and -Z over classical channel
            bob_should_apply_x = a.measure() # if Bob should apply X
            bob_should_apply_z = q.measure() # if Bob should apply Z
            self.csend(bob, [bob_should_apply_x, bob_should_apply_z])
            
    def random_state(self):
            state=randint(0,3)
            #Random operation
            if  state == 0: # 0 state
                pass
            elif state == 1: # 1 state    #X
                X(self.q)
            elif state == 2: # + state    #H
                H(self.q)
            elif state == 3: # - state    #XH
                X(self.q)
                H(self.q)
            else :
                print("Create random bits ERROR!!")
            self.state = state
            
    def compare_measurement(self,opList):
        
        if self.state<2 and opList==0:    #measure in standard basis
            matchList = 1
        elif self.state>=2 and opList==1: #measure in Hadamard basis
            matchList = 1
        else:
            matchList = 0
        return matchList
    
    def run(self):
        self.state = None
        self.key_Alice = []
        for qsystem in self.qstream:
                self.q, self.a, self.b = qsystem.qubits # q is state to teleport, a and b are Bell pair
                self.random_state()
                self.distribute_bell_pair(self.a, self.b)
                self.teleport(self.q, self.a)
                op_bob = self.crecv(bob)
                match = compare_measurement(op_bob)
                csend(match)
                if match:
                    self.key_A.append(self.state%2) #quantum state 0,+:0    1,-:1    
                else:
                    continue
        #print(self.key_Alice)
                    
        
class Bob(Agent):
    def random_measure(self, b):
        measure_for=randint(0,1)
        if measure_for == 0:
            X(b)
        else:
            Z(b)    
        return b.measure(), measure_for

            
    def run(self):
        self.key_bob=[]
        for _ in self.qstream:
                # Bob receives a qubit from Alice
                b = self.qrecv(alice)
                # Bob receives classical instructions from alice
                should_apply_x, should_apply_z = self.crecv(alice)
                if should_apply_x: X(b)
                if should_apply_z: Z(b)
                meas_result, state = random_measure(b)
                self.csend(alice, state)
                if self.crecv(alice):
                    self.key_bob.append(meas_result)
                else:
                    continue
        #print(self.key_bob)
                    
if __name__ == '__main__':                    
    qstream=QSystem(3,20)        
    # Make and connect the agents

    out = Agent.shared_output()
    alice = Alice(qstream, out)
    bob = Bob(qstream, out)
    alice.qconnect(bob) # add a quantum channel
    alice.cconnect(bob) # add a classical channel
    bob.start()
    alice.start()
    alice.join()
    bob.join()
