import argparse
import socket
import utils
from packet import Packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "emulator_host",
        choices=utils.VALID_HOSTNAMES,
        help="host address of the network emulator",
    )
    parser.add_argument(
        "emulator_data_port",
        type=int,
        help="UDP port number used by the emulator to receive data from the sender",
    )
    parser.add_argument(
        "sender_ack_port",
        type=int,
        help="UDP port number used by the sender to receive ACKs from the emulator",
    )
    parser.add_argument(
        "input_file",
        help="name of the file to be transferred",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # The address for sending UDP packets into the nEmulator
    nemu_addr = (args.emulator_host, args.emulator_data_port)

    # UDP socket to send/receive packets from the nEmulator
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', args.sender_ack_port))

    # open input file for reading to send over socket 
    inp_f = open(args.input_file, 'r')

    wnd_size = 1 # N i.e the current window size 

    # read file into chunks of length 500 (maximum packet data length)
    packets_to_send : list[Packet] = []
    seqnum = 0
    while True: 
        chunk = inp_f.read(500)
        if chunk == "": 
            break
        packets_to_send.append(Packet(
            utils.PACKET_TYPE_DATA, 
            seqnum, 
            len(chunk), 
            0, # ecn will be set by the nemulator 
            0, # unused for data packets 
            chunk
        ))
        seqnum += 1

    # send an EOT packet after all chunks are sent 
    packets_to_send.append(utils.EOT_PKT)


if __name__ == "__main__":
    main()
