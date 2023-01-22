#! usr/bin/python3
import os
import sys
import numpy as np
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
            
    def random_state(self,q):
            state=randint(0,3)
            #Random operation
            if  state == 0: # 0 state
                pass
            elif state == 1: # 1 state    #X
                X(q)
            elif state == 2: # + state    #H
                H(q)
            elif state == 3: # - state    #XH
                X(q)
                H(q)
            else :
                print("Create random bits ERROR!!")
            return state
            
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
                #self.state=self.random_state(qsystem.qubit(0))
                print(qsystem.state)
                q, a, b = qsystem.qubits # q is state to teleport, a and b are Bell pair
                self.state=self.random_state(q)
                print(self.state)
                print(qsystem.state)
                self.distribute_bell_pair(a, b)
                self.teleport(q, a)
                op_bob = self.crecv(bob)
                match = self.compare_measurement(op_bob)
                self.csend(bob, match)
                if match:
                    self.key_Alice.append(self.state%2) #quantum state 0,+:0    1,-:1    
                else:
                    continue
        print("Alice:",self.key_Alice)
                    
        
class Bob(Agent):
    def random_measure(self, b):
        measure_for=randint(0,1)
        if measure_for == 0:
            meas = b.measure(Z)
        else:
            meas = b.measure(X)
        meas=b.measure()
        print(meas, measure_for)
        return meas, measure_for

            
    def run(self):
        self.key_bob=[]
        for _ in self.qstream:
                # Bob receives a qubit from Alice
                b = self.qrecv(alice)
                # Bob receives classical instructions from alice
                should_apply_x, should_apply_z = self.crecv(alice)
                if should_apply_x: X(b)
                if should_apply_z: Z(b)
                meas_result, state = self.random_measure(b)
                self.csend(alice, state)
                match = self.crecv(alice)
                print(b)
                if match == 1:
                    print("Appending")
                    self.key_bob.append(meas_result)
                else:
                    continue
        print("Bob:",self.key_bob)
                               
qstream=QStream(3,10)    
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

