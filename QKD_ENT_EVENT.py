#! usr/bin/python3
import netsquid as ns 
from random import randint
from netsquid.components.qchannel import QuantumChannel
from netsquid.components import QuantumMemory
from netsquid.qubits import StateSampler
from netsquid.protocols import NodeProtocol, Signals
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
from pydynaa import EventExpression

class ClassicalConnectionA2B(Connection):
        def __init__(self, length):
            super().__init__(name="ClassicalConnection")
            self.add_subcomponent(ClassicalChannel("Channel_A2B", length=length,models={"delay_model": FibreDelayModel()}))
            self.ports['A'].forward_input(self.subcomponents["Channel_A2B"].ports['send'])
            self.subcomponents["Channel_A2B"].ports['recv'].forward_output(self.ports['B'])

class EntanglingConnection(Connection):
        def __init__(self, length, source_frequency):
                super().__init__(name="EntanglingConnection")
                timing_model = FixedDelayModel(delay=(1e9 / source_frequency))
                qsource = QSource("qsource", StateSampler([ks.b00], [1.0]), num_ports=2,timing_model=timing_model, status=SourceStatus.INTERNAL)
                self.add_subcomponent(qsource)
                qchannel_c2a = QuantumChannel("qchannel_C2A", length=length / 2,models={"delay_model": FibreDelayModel()})
                qchannel_c2b = QuantumChannel("qchannel_C2B", length=length / 2,models={"delay_model": FibreDelayModel()})
                # Add channels and forward quantum channel output to external port output:
                self.add_subcomponent(qchannel_c2a, forward_output=[("A", "recv")])
                self.add_subcomponent(qchannel_c2b, forward_output=[("B", "recv")])
                # Connect qsource output to quantum channel input:
                qsource.ports["qout0"].connect(qchannel_c2a.ports["send"])
                qsource.ports["qout1"].connect(qchannel_c2b.ports["send"])

def example_network_setup(node_distance=4e-3, depolar_rate=1e7):
    # Setup nodes Alice and Bob with quantum memories:
    noise_model = DepolarNoiseModel(depolar_rate=depolar_rate)
    #alice = Node("Alice", port_names=['qin_charlie', 'cout_bob','cin_bob'],qmemory=QuantumMemory("AliceMemory", num_positions=2,memory_noise_models=[noise_model] * 2))
    alice = Node("Alice", port_names=['qin_charlie', 'cout_bob','cin_bob'],qmemory=QuantumMemory("AliceMemory", num_positions=2))
    alice.ports['qin_charlie'].forward_input(alice.qmemory.ports['qin1'])
    #bob = Node("Bob", port_names=['qin_charlie', 'cin_alice','cout_alice'], qmemory=QuantumMemory("BobMemory", num_positions=1, memory_noise_models=[noise_model]))
    bob = Node("Bob", port_names=['qin_charlie', 'cin_alice','cout_alice'], qmemory=QuantumMemory("BobMemory", num_positions=1))
    bob.ports['qin_charlie'].forward_input(bob.qmemory.ports['qin0']) 
    # Setup classical connection between nodes:
    c_conn1 = ClassicalConnectionA2B(length=node_distance)
    c_conn2 = ClassicalConnectionA2B(length=node_distance)
    alice.ports['cout_bob'].connect(c_conn1.ports['A'])
    bob.ports['cin_alice'].connect(c_conn1.ports['B'])
    alice.ports['cin_bob'].connect(c_conn2.ports['B'])
    bob.ports['cout_alice'].connect(c_conn2.ports['A'])
    #Setup entangling connection between nodes:
    q_conn = EntanglingConnection(length=node_distance, source_frequency=2e7)
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


class qubitCreation(NodeProtocol):
    def run(self):
        try:
            mem_pos = self.node.qmemory.unused_positions[0]
        except:
            self.send_signal(signal_label=Signals.FAIL)
            print("Failed to get unused memory locations")
            self.node.qmemory.discard(0)
            mem_pos = self.node.qmemory.unused_positions[0]
        qubit=create_qubits(1,system_name="Q")
        self.node.qmemory.put(qubit,mem_pos)
        self.send_signal(signal_label=Signals.SUCCESS, result=mem_pos)
        self.stop()

            

class AliceProtocol(NodeProtocol):
    def __init__(self, node,length,createQubit):
        super().__init__(node)
        self.matchList=[]
        self.length=length
        self.ent_swap=False
        self.add_subprotocol(createQubit, 'createQubit')
        self.qubitFlag=False
        self.entangled=False
        self.matchFlag=False

    def run(self):
        self.key_A=[]
        self.qubitCounter=0
        received_flag=False
        sent_flag=False
        mem_pos = self.node.qmemory.unused_positions[0]
        evexpr_signal = self.await_signal(sender=self.subprotocols['createQubit'], signal_label=Signals.SUCCESS)
        evexpr_port = self.await_port_input(self.node.ports["qin_charlie"])
        evexpr_port_out_bob = self.await_port_output(self.node.ports["cout_bob"])
        evexpr_port_in_bob = self.await_port_input(self.node.ports["cin_bob"])
        while True:
                #print("Start of ALice")
                #evexpr_port.reprime()
                if self.qubitCounter<self.length and self.is_connected:
                    if not self.qubitFlag:
                        self.start_subprotocols()
                    if not self.qubitFlag or not self.entangled:
                        #print(self.qubitFlag, self.entangled);
                        #print("Alice: Waiting for Entanglement")
                        expression = yield evexpr_signal | self.await_port_input(self.node.ports["qin_charlie"])
                        #print(evexpr_port.triggered_events)
                    if expression.first_term.value and not self.qubitFlag:
                        #print("ALICE:Got qubit");
                        state=randint(0,3)
                        #print(state)
                        #Random operation
                        if   state == 0: # 0 state
                            pass
                        elif state == 1: # 1 state    #X
                            self.node.qmemory.operate(ns.X,mem_pos)
                        elif state == 2: # + state    #H
                            self.node.qmemory.operate(ns.H,mem_pos)
                        elif state == 3: # - state    #XH
                            self.node.qmemory.operate(ns.X,mem_pos)
                            self.node.qmemory.operate(ns.H,mem_pos)
                        else :
                            print("Create random bits ERROR!!")
                        self.qubitFlag=True
                        #evexpr_signal.reprime()
                    else:
                        #print("ALICE: Entanglement")
                        self.entangled=True
                        #evexpr_port.reprime()
                    #yield self.await_port_input(self.node.ports["qin_charlie"])
                    #Completes Entanglement and does Bell Measurement
                    if self.qubitFlag and  self.entangled:
                        if not received_flag and not sent_flag:
                            self.node.qmemory.operate(ns.CNOT, [0, 1])
                            self.node.qmemory.operate(ns.H,0)
                            m, _ = self.node.qmemory.measure([0, 1])
                    #Sends measurement to Bob for correction
                            self.node.ports["cout_bob"].tx_output(m)
                        #print("ALICE: QUBIT ENTANGLED")
                        #print("ALICE: WAITING FOR BOB QUBIT STATELIST")
                        expression2= yield evexpr_port_in_bob | evexpr_port_out_bob
                        if expression2.first_term.value and not received_flag:
                            meas_results = self.node.ports["cin_bob"].rx_input().items
                            received_flag=True
                        elif received_flag:
                            sent_flag=True

                        if received_flag:
                            evexpr_port_out_bob.reprime()
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
                        if sent_flag:
                            if self.matchFlag:
                               # print("ALICE: MATCH FOUND")
                                self.key_A.append(state%2) #quantum state 0,+:0    1,-:1
                                self.qubitCounter+=1
                            self.qubitFlag=False
                            self.entangled=False

                            if received_flag:
                            #evexpr_signal.reprime()
                                self.matchFlag=False
                                self.qubitFlag=False
                                self.entangled=False
                                received_flag=False
                                sent_flag=False
                                #print(f"ALICE: Key Length={self.qubitCounter}")
                else:
                    print(f"{ns.sim_time():.1f}")
                    break
        print(f"Key at Alice: {self.key_A}")
        print("END OF ALICE PROTOCOL")

    def start(self):
        super().start()
        #self.start_subprotocols()
            
        
class BobProtocol(NodeProtocol):
    def __init__(self,node,length):
        super().__init__(node)
        self.length=length
        self.qubitCounter=0
        self.stateList=[]
        self.result=[]
        self.B_basis=[]
        self.key_B=[]
    def run(self):
        entangled=False
        meas_results=None
        while True:
            meas_results=None
            if self.qubitCounter<length and self.is_connected:
                self.node.ports["cout_alice"].tx_output([])
                evexpr_port_a = self.await_port_input(self.node.ports["cin_alice"])
                evexpr_port_c = self.await_port_input(self.node.ports["qin_charlie"])
                expression = yield evexpr_port_a | evexpr_port_c
               # print("BOB:Waiting for Entanglement")
                #Waiting for entanglement control qubit
                if expression.first_term.value:
                    #Waiting for Alice Bell Measurements for Corrections
                    meas_results = self.node.ports["cin_alice"].rx_input().items
                    #evexpr_port_a.reprime()
                #Correction of teleported qubit
                else:
                    #expression.reprime()
                    entangled=True
                    #evexpr_port_c.reprime()
                if meas_results is not None and entangled:
                    if meas_results[0]:
                        self.node.qmemory.operate(ns.Z, 0)
                    if meas_results[1]:
                        self.node.qmemory.operate(ns.X, 0)
                    #print("BOB:QUBIT ENTANGLED")
                    #Redording Fidelity strength
                    fidelity = ns.qubits.fidelity(self.node.qmemory.peek(0)[0],ns.y0, squared=True)
                    print(f"{ns.sim_time():.1f}: Bob received entangled qubit and " f"corrections! Fidelity = {fidelity:.3f}")
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
                        #meas_results=None
                        #entangled=False
                    else:
                        print("BOB: MATCH NOT FOUND")
                    #Sending buffer to inform Alice Bob is ready for next bit
                    self.node.ports["cout_alice"].tx_output("")
                    #print(f"BOB:Key Length = {self.qubitCounter}")
                    entangled=False
                    meas_results=None
                    #evexpr_port_a.reprime()
                    #evexpr_port_c.reprime()
                    #expression.reprime()
            else:
                print(f"{ns.sim_time():.1f}")
                break
        print(f"Key at BOB: {self.key_B}")
        print("END OF BOB PROTOCOL")
print("Please input length of key:")
length= int(input())
ns.set_qstate_formalism(ns.QFormalism.DM)
alice, bob, qconn = example_network_setup()
createQubits=qubitCreation(alice)
aliceProtocol=AliceProtocol(alice,length,createQubits).start()
bobProtocol=BobProtocol(bob,length).start()

stats = ns.sim_run(6000000000)





