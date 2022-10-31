#! usr/bin/python3
import netsquid as ns 
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

class ClassicalConnectionA2B(Connection):
        def __init__(self, length):
            super().__init__(name="ClassicalConnection")
            self.add_subcomponent(ClassicalChannel("Channel_A2B", length=length,models={"delay_model": FibreDelayModel()}))
            self.ports['A'].forward_input(self.subcomponents["Channel_A2B"].ports['send'])
            self.subcomponents["Channel_A2B"].ports['recv'].forward_output(self.ports['B'])

class ClassicalConnectionB2A(Connection):
        def __init__(self, length):
            super().__init__(name="ClassicalConnection")
            self.add_subcomponent(ClassicalChannel("Channel_B2A", length=length,models={"delay_model": FibreDelayModel()}))
            self.ports['A'].forward_input(self.subcomponents["Channel_B2A"].ports['send'])
            self.subcomponents["Channel_B2A"].ports['recv'].forward_output(self.ports['A'])

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
    alice = Node("Alice", port_names=['qin_charlie', 'cout_bob','cin_bob'],qmemory=QuantumMemory("AliceMemory", num_positions=2,memory_noise_models=[noise_model] * 2))
    alice.ports['qin_charlie'].forward_input(alice.qmemory.ports['qin1'])
    bob = Node("Bob", port_names=['qin_charlie', 'cin_alice','cout_alice'], qmemory=QuantumMemory("BobMemory", num_positions=1, memory_noise_models=[noise_model]))
    bob.ports['qin_charlie'].forward_input(bob.qmemory.ports['qin0']) 
    # Setup classical connection between nodes:
    c_conn1 = ClassicalConnectionA2B(length=node_distance)
    c_conn2 = ClassicalConnectionA2B(length=node_distance)
    #cchannel1=ClassicalChannel(name="cchannel[Alice|Bob]",length=node_distance,models={"delay_model": FibreDelayModel()})
    #cchannel2=ClassicalChannel(name="cchannel[Bob|Alice]",length=node_distance,models={"delay_model": FibreDelayModel()})
    #cconnection = DirectConnection(name="cconn[Alice|Bob]",channel_AtoB=cchannel1, channel_BtoA=cchannel2)
    #alice.connect_to(remote_node=bob, connection=cconnection, local_port_name="cport", remote_port_name="cport")
    #bob.connect_to(remote_node=alice, connection=cconnection, local_port_name="cport", remote_port_name="cport")
    alice.ports['cout_bob'].connect(c_conn1.ports['A'])
    bob.ports['cin_alice'].connect(c_conn1.ports['B'])
    alice.ports['cin_bob'].connect(c_conn2.ports['B'])
    bob.ports['cout_alice'].connect(c_conn2.ports['A'])
    #Setup entangling connection between nodes:
    q_conn = EntanglingConnection(length=node_distance, source_frequency=2e7)
    alice.ports['qin_charlie'].connect(q_conn.ports['A'])
    bob.ports['qin_charlie'].connect(q_conn.ports['B'])
    return alice, bob, q_conn

def Create_random_qubits(num_bits):
    res_state=[]
    qlist=[]
    qlist=create_qubits(num_bits,system_name="Q") 
    for i in range(0,num_bits):
        res_state.append(randint(0,3))
    for a,b in zip(res_state, qlist):
            if   a == 0: # 0 state
                #print("0",b.qstate.dm)
                pass
            elif a == 1: # 1 state    #X
                ns.qubits.operate(b,ns.X)
                #print("1",b.qstate.dm)
            elif a == 2: # + state    #H
                ns.qubits.operate(b,ns.H)
                #print("+",b.qstate.dm)
            elif a == 3: # - state    #XH
                ns.qubits.operate(b,ns.X)
                ns.qubits.operate(b,ns.H)
                #print("-",b.qstate.dm)
            else :
                print("Create random bits ERROR!!")
            print(b.name)
    return res_state, qlist

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

def Random_ZX_measure(num_bits,qlist):
    opList = [2]*num_bits
    loc_res_measure=[2]*num_bits
    num=0
    print(type(qlist))
    for q in qlist:
        rbit = randint(0,3)
        #print(int(q.name))
        #num=int(q.name[1:]) # get value before qubit name "Q"
        print(type(q))
        opList[num] = rbit
        if rbit==0:
            loc_res_measure[num]=ns.qubits.qubitapi.measure(q,observable=Z) #measure in standard basis
        elif rbit==1:
            loc_res_measure[num]=ns.qubits.qubitapi.measure(q,observable=X) #measure in Hadamard basis
        else:
            print("measuring ERROR!!\n")
        num+=1
    return opList,loc_res_measure

class AliceProtocol(NodeProtocol):
    def __init__(self, node):
        super().__init__(node)
        self.stateList, self.qlist=Create_random_qubits(1)
        print(self.stateList)
        self.matchList=[]

    def run(self):
        self.key_A=[]
        qubitCounter=0
        while True:
                if qubitCounter<=0:
                    self.node.qmemory.put(self.qlist[qubitCounter])
                    print("ALICE: Waiting for Entanglement")
                    yield self.await_port_input(self.node.ports["qin_charlie"])
                    print("ALICE: QUBIT ENTANGLED")
                    qubitCounter+=1
                elif self.key_A==[]:
                    print("ALICE: WAITING FOR BOB QUBIT STATELIST")
                    yield self.await_port_input(self.node.ports["cin_bob"])
                    print("ALICE: RECEIVED BOB QUBIT STATELIST")
                    meas_results = self.node.ports["cin_bob"].rx_input().items
                    print("Meas_res",meas_results)
                    self.matchList=Compare_measurement(1,self.stateList,meas_results)
                    print(self.matchList)
                    self.node.ports["cout_bob"].tx_output(self.matchList)
                    print("ALICE: SENT MATCH LIST")
                    yield self.await_port_input(self.node.ports["cin_bob"])
                    for i in self.matchList:
                        self.key_A.append(self.stateList[i]%2) #quantum state 0,+:0    1,-:1
                    print(self.key_A)
        print("END OF ALICE PROTOCOL")

            
        
class BobProtocol(NodeProtocol):
    def __init__(self,node):
        super().__init__(node)
        self.qubitCounter=0
        self.stateList=[]
        self.result=[]
        self.B_basis=[]
        self.key_B=[]
        self.tempQubit=create_qubits(1,system_name="Q")
    def run(self):
        while True:
            if self.qubitCounter<=0 and self.is_connected:
                print("BOB:Waiting for Entanglement")
                yield self.await_port_input(self.node.ports["qin_charlie"])
                print("BOB:QUBIT ENTANGLED")
                r=randint(0,1)
                print(r)
                if r == 0:
                    self.result.append(self.node.qmemory.measure(observable=ns.Z))
                elif r==1:
                    self.result.append(self.node.qmemory.measure(observable=ns.X))
                print(self.result)
                self.B_basis.append(r)
                self.qubitCounter+=1
            #elif self.key_B==[]:
                #B_basis,randomLocMeas=Random_ZX_measure(5,self.stateList)
            if self.B_basis[0] == 0 or self.B_basis[0] == 1 or self.B_basis[0] == 2:
                # B send measurement
                print("BOB:SENDING STATE LIST")
                self.node.ports["cout_alice"].tx_output(self.B_basis)
            else :
                print("B measuring failed!!")
                print(self.B_basis[0])
            print("BOB: WAITING FOR MATCH LIST") 
            yield(self.await_port_input(self.node.ports["cin_alice"]))
            print("BOB: RECEIVED MATCH LIST")
            matchList=self.node.ports["cin_alice"].rx_input().items
            self.node.ports["cout_alice"].tx_output("got")
            for i in matchList:
                if len(matchList)>0:
                    self.key_B.append(self.result[i]%2)
            print(self.key_B)
        print("END OF BOB PROTOCOL")



        

ns.set_qstate_formalism(ns.QFormalism.DM)
#node_distance=4e-3
alice, bob, qconn = example_network_setup()
#cchannel1=ClassicalChannel(name="cchannel[Alice|Bob]",length=node_distance)
#cchannel2=ClassicalChannel(name="cchannel[Bob|Alice]",length=node_distance)
#cconnection = DirectConnection(name="cconn[Alice|Bob]",channel_AtoB=cchannel1, channel_BtoA=cchannel2)
#alice.connect_to(remote_node=bob, connection=cconnection, local_port_name="cport", remote_port_name="cport")
aliceProtocol=AliceProtocol(alice).start()
bobProtocol=BobProtocol(bob).start()

stats = ns.sim_run(300)

#qA, = alice.qmemory.peek(positions=[1])
#
#qB, = bob.qmemory.peek(positions=[0])
#
#qA, qB
#
#fidelity = ns.qubits.fidelity([qA, qB], ns.b00)
#
#print(f"Entangled fidelity (after 5 ns wait) = {fidelity:.3f}")
