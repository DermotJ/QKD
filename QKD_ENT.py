#! usr/bin/python3
import os
import sys
import netsquid as ns
from optparse import OptionParser
from random import randint
from netsquid.components.qchannel import QuantumChannel
from netsquid.components import QuantumMemory
from netsquid.qubits import StateSampler
from netsquid.protocols import NodeProtocol
from netsquid.components.qsource import QSource, SourceStatus
from netsquid.nodes import DirectConnection
from netsquid.qubits.operators import *
from netsquid.qubits import create_qubits
from netsquid.components.models import FixedDelayModel, DepolarNoiseModel
import numpy as np
import netsquid.qubits.ketstates as ks
from netsquid.nodes import Node
from netsquid.nodes.connections import Connection
from netsquid.components import ClassicalChannel
from netsquid.components.models import FibreDelayModel
from netsquid.protocols import Protocol

def printToFile(filename, line, length):
    with open(f'{filename}{length}.txt', 'a') as f:
            f.write(line+'\n')

def addParserOptions():
    parser = OptionParser()
    parser.add_option("-l", "--length",
                      dest = "length", type = "int", help="Set length of secret key", default = 4)
    parser.add_option("-n", "--quantumNoise", default = 1e7,
                      dest = "quantumNoise", type = "int", help = "rate of depolar and dephase errors")
    parser.add_option("-f", "--sourceFrequency", default = 2e7,
                      dest = "sourceFrequency", type = "int", help = "rate of entanglement pairs")
    parser.add_option("-t", "--delay", default = 1e9,
                      dest = "setDelay", type = "int", help = "based on fraction of source frequency")
    parser.add_option("-d", "--distance", default = 1,
                      dest = "nodeDistance", type = "float", help = "Distance between nodes")
    return parser.parse_args()

class ClassicalConnectionA2B(Connection):
        def __init__(self, length):
            super().__init__(name="ClassicalConnection")
            self.add_subcomponent(ClassicalChannel("Channel_A2B", length=length,models={"delay_model": FibreDelayModel()}))
            self.ports['A'].forward_input(self.subcomponents["Channel_A2B"].ports['send'])
            self.subcomponents["Channel_A2B"].ports['recv'].forward_output(self.ports['B'])

class EntanglingConnection(Connection):
        def __init__(self, length, source_frequency, depolarRate, set_delay):
                super().__init__(name="EntanglingConnection")
                noise_model = DepolarNoiseModel(depolar_rate=depolarRate)
                timing_model = FixedDelayModel(delay=(set_delay / source_frequency))
                qsource = QSource("qsource", StateSampler([ks.b00], [1.0]), num_ports=2,timing_model=timing_model,status=SourceStatus.INTERNAL)
                self.add_subcomponent(qsource)
                qchannel_c2a = QuantumChannel("qchannel_C2A", length=length / 2,models={"delay_model": FibreDelayModel(),"noise_model": noise_model})
                qchannel_c2b = QuantumChannel("qchannel_C2B", length=length / 2,models={"delay_model": FibreDelayModel(),"noise_model": noise_model})
                # Add channels and forward quantum channel output to external port output:
                self.add_subcomponent(qchannel_c2a, forward_output=[("A", "recv")])
                self.add_subcomponent(qchannel_c2b, forward_output=[("B", "recv")])
                # Connect qsource output to quantum channel input:
                qsource.ports["qout0"].connect(qchannel_c2a.ports["send"])
                qsource.ports["qout1"].connect(qchannel_c2b.ports["send"])

def example_network_setup(node_distance, depolar_rate, source_frequency, delay):
    # Setup nodes Alice and Bob with quantum memories:
    noise_model = DepolarNoiseModel(depolar_rate=depolar_rate)
    alice = Node("Alice", port_names=['qin_charlie', 'cout_bob','cin_bob'],qmemory=QuantumMemory("AliceMemory", num_positions=2,memory_noise_models=[noise_model] * 2))
    #alice = Node("Alice", port_names=['qin_charlie', 'cout_bob','cin_bob'],qmemory=QuantumMemory("AliceMemory", num_positions=2))
    alice.ports['qin_charlie'].forward_input(alice.qmemory.ports['qin1'])
    bob = Node("Bob", port_names=['qin_charlie', 'cin_alice','cout_alice'], qmemory=QuantumMemory("BobMemory", num_positions=1, memory_noise_models=[noise_model]))
    #bob = Node("Bob", port_names=['qin_charlie', 'cin_alice','cout_alice'], qmemory=QuantumMemory("BobMemory", num_positions=1))
    bob.ports['qin_charlie'].forward_input(bob.qmemory.ports['qin0']) 
    # Setup classical connection between nodes:
    c_conn1 = ClassicalConnectionA2B(length=node_distance)
    c_conn2 = ClassicalConnectionA2B(length=node_distance)
    alice.ports['cout_bob'].connect(c_conn1.ports['A'])
    bob.ports['cin_alice'].connect(c_conn1.ports['B'])
    alice.ports['cin_bob'].connect(c_conn2.ports['B'])
    bob.ports['cout_alice'].connect(c_conn2.ports['A'])
    #Setup entangling connection between nodes:
    q_conn = EntanglingConnection(length=node_distance, source_frequency=source_frequency, depolarRate=depolar_rate, set_delay=delay)
    alice.ports['qin_charlie'].connect(q_conn.ports['A'])
    bob.ports['qin_charlie'].connect(q_conn.ports['B'])
    return alice, bob, q_conn


def Compare_measurement(num_bits,stateList,opList):
    matchList=[]
    for i in range(0,num_bits):
        if stateList[i]<2 and opList[i]==0:    #measure in standard basis
            matchList.append(i)
        elif stateList[i]>=2 and opList[i]==1: #measure in Hadamard basis
            matchList.append(i)
        else:
            pass
    return matchList

class AliceProtocol(NodeProtocol):
    def __init__(self, node,length):
        super().__init__(node)
       # self.stateList, self.qlist=Create_random_qubits(1)
        self.matchList=[]
        self.length=length
        self.ent_swap=False

    def randomState(self, mem_pos):
        state=randint(0,3)
        #Random operation
        if   state == 0: # 0 state
            pass
        elif state == 1: # 1 state    #
            self.node.qmemory.operate(ns.X,mem_pos)
        elif state == 2: # + state    #H
            self.node.qmemory.operate(ns.H,mem_pos)
        elif state == 3: # - state    #XH
            self.node.qmemory.operate(ns.X,mem_pos)
        else :
            print("Create random bits ERROR!!")
        return state

    def getKey(self):
        return self.key_A

    def getSentTimes(self):
        return self.qubitSendTimes

    def run(self):
        self.key_A=[]
        self.qubitSendTimes=[]
        self.qubitCounter=0
        mem_pos = self.node.qmemory.unused_positions[0]
        while True:
                self.matchFlag=False
                if self.qubitCounter<self.length:
                    #Creates new qubit to be teleported
                    qubit=create_qubits(1,system_name="Q")
                    #Places in node memory
                    self.node.qmemory.put(qubit,mem_pos)
                    state=self.randomState(mem_pos)
                    #print("ALICE: Waiting for Entanglement")
                    #Waits for entanglement
                    yield self.await_port_input(self.node.ports["qin_charlie"])
                    #Completes Entanglement and does Bell Measurement
                    self.qubitSendTimes.append(ns.sim_time())
                    self.node.qmemory.operate(ns.CNOT, [0, 1])
                    self.node.qmemory.operate(ns.H,0)
                    m, _ = self.node.qmemory.measure([0, 1])
                    #Sends measurement to Bob for correction
                    self.node.ports["cout_bob"].tx_output(m)
                    #print("ALICE: QUBIT ENTANGLED")
                    #print("ALICE: WAITING FOR BOB QUBIT STATELIST")
                    yield self.await_port_input(self.node.ports["cin_bob"])
                    #print("ALICE: RECEIVED BOB QUBIT STATELIST")
                    meas_results = self.node.ports["cin_bob"].rx_input().items
                    #Strips buffer from list if one is present
                    if meas_results.count("")>0:
                        meas_results.remove("")
                    statelist=[state]
                    #Compares bits
                    self.matchList=Compare_measurement(1,statelist,meas_results)
                    #Confirms match is found
                    if 0 in self.matchList or 1 in self.matchList:
                        self.matchFlag=True
                        self.node.ports["cout_bob"].tx_output(self.matchFlag)
                    else:
                        #print("ERROR")
                        self.node.ports["cout_bob"].tx_output(self.matchFlag)
                    #print("ALICE: SENT MATCH LIST")
                    if self.matchFlag:
                        #print("ALICE: MATCH FOUND")
                        self.key_A.append(state%2) #quantum state 0,+:0    1,-:1
                        self.qubitCounter+=1
                    #print("ALICE:WAITING FOR BOB TO FINISH PROCESS")
                    yield self.await_port_input(self.node.ports["cin_bob"])
                    yield_forNextEnt = self.node.ports["cin_bob"].rx_input().items 
                    #print(f"ALICE: Key Length={self.qubitCounter}")
                else:
                    printToFile('Sim_time',f"{ns.sim_time():.1f}",self.length)
                    break
        printToFile(f'Secretkeys',f"Key at Alice: {self.key_A}", self.length)
        #print("END OF ALICE PROTOCOL")
        ns.sim_stop()

            
        
class BobProtocol(NodeProtocol):
    def __init__(self,node,length):
        super().__init__(node)
        self.length=length
        self.qubitCounter=0
        self.stateList=[]
        self.result=[]
        self.B_basis=[]
        self.key_B=[]
        self.tempQubit=create_qubits(1,system_name="Q")
        self.entanglements = 0
        self.qubitRecTimes=[]

    def getKey(self):
        return self.key_B

    def getRecTimes(self):
        return self.qubitRecTimes
    
    def getEntanglements(self):
        return self.entanglements

    def run(self):
        while True:
            if self.qubitCounter<self.length and self.is_connected:
                self.node.ports["cout_alice"].tx_output([])
                #print("BOB:Waiting for Entanglement")
                #Waiting for entanglement control qubit
                yield self.await_port_input(self.node.ports["qin_charlie"])
                self.entanglements += 1
                #Waiting for Alice Bell Measurements for Corrections
                yield(self.await_port_input(self.node.ports["cin_alice"]))
                meas_results = self.node.ports["cin_alice"].rx_input().items
                #Correction of teleported qubit
                if meas_results[0]:
                    self.node.qmemory.operate(ns.Z, 0)
                if meas_results[1]:
                    self.node.qmemory.operate(ns.X, 0)
                self.qubitRecTimes.append(ns.sim_time())
                #print("BOB:QUBIT ENTANGLED")
                #Redording Fidelity strength
                fidelity = ns.qubits.fidelity(self.node.qmemory.peek(0)[0],ns.y0, squared=True)
                printToFile('Fielity',f"{ns.sim_time():.1f}: Bob received entangled qubit and corrections! Fidelity = {fidelity:.3f}", self.length)
                r=randint(0,1)
                #Completeing random measure of qubit
                if r == 0:
                    self.result=self.node.qmemory.measure(observable=Z)
                elif r==1:
                    self.result=self.node.qmemory.measure(observable=X)
                self.B_basis=r
                if self.B_basis == 0 or self.B_basis == 1 or self.B_basis == 2:
                    # B send measurement
                    #print("BOB:SENDING STATE LIST")
                    self.node.ports["cout_alice"].tx_output(self.B_basis)
                else :
                    print("B measuring failed!!")
                    print(self.B_basis[0])
                #print("BOB: WAITING FOR MATCH LIST") 
                #Waiting for  Match list from Alice
                yield(self.await_port_input(self.node.ports["cin_alice"]))
                #print("BOB: RECEIVED MATCH LIST")
                matchList=self.node.ports["cin_alice"].rx_input().items
                #print(f"BOB:match {matchList}")
                if matchList[0]:
                    #print("BOB: MATCH FOUND!")
                    self.key_B.append(self.result[int(0)][0])
                    self.qubitCounter+=1
                #else:
                    #print("BOB: MATCH NOT FOUND")
                #Sending buffer to inform Alice Bob is ready for next bit
                self.node.ports["cout_alice"].tx_output("")
                #print(f"BOB:Key Length = {self.qubitCounter}")
            else:
               # print(f"{ns.sim_time():.1f}")
                break
        printToFile(f'Secretkeys',f"Key at BOB: {self.key_B}", self.length)
        printToFile('Emtanglements',f'{self.entanglements}', self.length)
        #print("END OF BOB PROTOCOL")
#print("Please input length of key:")
#length= int(sys.argv[1])
[inputArgs, args] = addParserOptions()
ns.set_qstate_formalism(ns.QFormalism.DM)
alice, bob, qconn = example_network_setup(node_distance=inputArgs.nodeDistance/10000, depolar_rate=inputArgs.quantumNoise, source_frequency = inputArgs.sourceFrequency, delay=inputArgs.setDelay)
aliceProtocol=AliceProtocol(alice,inputArgs.length).start()
bobProtocol=BobProtocol(bob,inputArgs.length).start()
stats = ns.sim_run(6000000000000)
index=0
errors=0
for bit in aliceProtocol.getKey():
    if bit != bobProtocol.getKey()[index]:
        errors += 1
    index += 1

for index2 in range(0,1):
    printToFile(f'qunatumlatency',f"{bobProtocol.getRecTimes()[index2]-aliceProtocol.getSentTimes()[index2]}",inputArgs.length)
printToFile('QBER',f"OBER: {errors/inputArgs.length}",inputArgs.length)
