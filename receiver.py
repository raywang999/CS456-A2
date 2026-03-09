import argparse
import utils
import socket
from packet import Packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "emulator_host",
        choices=utils.VALID_HOSTNAMES,
        help="hostname for the network emulator",
    )
    parser.add_argument(
        "emulator_ack_port",
        type=int,
        help="UDP port number used by the link emulator to receive ACKs from the receiver",
    )
    parser.add_argument(
        "receiver_data_port",
        type=int,
        help="UDP port number used by the receiver to receive data from the emulator",
    )
    parser.add_argument(
        "output_file",
        help="name of the file into which the received data is written",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # open file for output
    out_f = open(args.output_file, 'w') 

    # The address for sending UDP packets back into the nEmulator
    nemu_addr = (args.emulator_host, args.emulator_ack_port)

    # UDP socket to receive packets sent via the nEmulator
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', args.receiver_data_port))

    # cumulative ce_count the receiver needs to maintain 
    ce_total = 0 

    # expected seqnum on the receiver, initially 0 since that's what we start 
    exp_seqnum = 0 

    # buffer for (potentially) out-of-order recieved packets 
    pkt_buffer : dict[int, Packet] = {}

    def send_ack() -> None: 
        """
        sends ACK packet back to sender via nEmulator
        """
        pkt = Packet(
            utils.PACKET_TYPE_ACK, 
            # the most recent in-order packet is exp_seqnum - 1 mod 32
            (exp_seqnum - 1 + utils.MOD_SIZE)%utils.MOD_SIZE, 
            0, 
            0, 
            ce_total, 
            ""
        )
        sock.sendto(pkt.encode(), nemu_addr)


    # listen for packets 
    while True: 
        # read and decode packet from socket 
        data, _ = sock.recvfrom(1024)
        recv_packet = Packet(data)

        # check if seqnum is not the expected one
        if exp_seqnum != recv_packet.seqnum: 
            # if seqnum is within next 10 sequence numbers, 
            # store recv_packet in buffer
            if utils.seqnum_diff(exp_seqnum, recv_packet.seqnum) <= 10: 
                pkt_buffer.append(recv_packet)
            # otherwise, discard the packet 

            # in both cases, send ACK for most recently received in-order packet
            send_ack()
            continue # process next packet 

        # otherwise, the sequence number is the expected one so 
        # 1. check if EOT. if so, send back EOT and terminate 
        # 2. otherwise, write data to output file 
        # 3. if packet with next seqnum is in buffer
        #    remove it from buffer, write data to output file, repeat
        cur_pkt = recv_packet
        while cur_pkt is not None:  
            # 1. check if EOT. if so, send back EOT and terminate 
            if cur_pkt.typ == utils.PACKET_TYPE_EOT: 
                eot_pkt = Packet(
                    utils.PACKET_TYPE_EOT, 
                    0, # unused for EOT
                    0, # unused for EOT
                    0, # unused for EOT
                    0, # unused for EOT
                    "", # unused for EOT
                )
                sock.sendto(eot_pkt.encode(), nemu_addr)
                return

            # 2. otherwise, write data to output file 
            out_f.write(cur_pkt.data)
            
            # 2.5: we should also update ce_total here 
            # since its the next in-order packet written to disk
            ce_total += cur_pkt.ecn

            # 3. check if packet with next seqnum is in buffer
            # first update expected seqnum 
            exp_seqnum = (exp_seqnum + 1) % utils.MOD_SIZE

            # if next packet isn't in buffer, exit loop into step 4
            cur_pkt = pkt_buffer.get(exp_seqnum)
            # otherwise, packet is in buffer so remove it and repeat
            pkt_buffer.pop(exp_seqnum)

        # 4. otherwise, packet with next seqnum DNE in buffer
        # so send back ACK and process next packet
        send_ack()


if __name__ == "__main__":
    main()
