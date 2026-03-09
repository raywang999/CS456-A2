import socket

from packet import Packet


VALID_HOSTNAMES = (
    "localhost",
    "ubuntu2404-004.student.cs.uwaterloo.ca",
)


# Packet type values
PACKET_TYPE_ACK = 0
PACKET_TYPE_DATA = 1
PACKET_TYPE_EOT = 2

# we use 32 as the mod on seqnum for this assignment 
MOD_SIZE = 32

def seqnum_diff(prv: int, nxt: int) -> int: 
    return (nxt - prv + MOD_SIZE) % MOD_SIZE
