import argparse
import socket
import utils
import time
from packet import Packet
from threading import Lock, Timer, Thread

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

    ###########################
    # data-transmission stage #
    ###########################
    # we'll use 4 threads: 
    # - sender thread that tries to send packets if window allows
    # - receiver thread that handles incoming ACKs 
    # - packet-drop timer to update window from packet drop 
    # - ecn-feedback timer to update window using ce_count

    # read file into chunks of length 500 (maximum packet data length)
    packets_to_send : list[Packet] = []
    num_packets_to_send = 0
    while True: 
        chunk = inp_f.read(500)
        if chunk == "": 
            break
        packets_to_send.append(Packet(
            utils.PACKET_TYPE_DATA, 
            num_packets_to_send, 
            len(chunk), 
            0, # ecn will be set by the nemulator 
            0, # unused for data packets 
            chunk
        ))
        num_packets_to_send += 1


    # N i.e the current window size 
    cwnd = 1 
    # largest seqnum that was ACK'd 
    acked_seqnum = -1 
    # seqnum that should be sent next by sender
    unsent_seqnum = 0

    # packet loss timer. None to indicate timer is stopped 
    pkt_loss_timer : Timer | None = None
    pkt_loss_TO = 0.3 # 300 milliseconds 
    
    # lock for the window variables and pkt_loss_timer
    lock = Lock()


    def pkt_loss_handler() -> None: 
        """
        - sets cwnd = 1 
        - sends oldest transmitted-but-not-ACK'd packet
        - resets packet loss timer 
        """
        with lock: 
            cwnd = 1 
            # timeout inflight packets
            unsent_seqnum = acked_seqnum + 1

            # send oldest trans but not ACK'd packet
            pkt = packets_to_send[unsent_seqnum]
            sock.sendto(pkt.encode(), nemu_addr)
            unsent_seqnum += 1

            # reset timer
            pkt_loss_timer = Timer(pkt_loss_TO, pkt_loss_handler)
            pkt_loss_timer.start()


    def sender() -> None: 
        """
        keep trying to send the next unsent packet, if it exists
        """
        while True: 
            with lock: 
                # if available windowsize is too small, try sending later 
                num_inflight = unsent_seqnum - acked_seqnum - 1
                if num_inflight >= cwnd: 
                    time.sleep(0) # thread yield 
                    continue
                # otherwise, send the packet 
                pkt = packets_to_send[unsent_seqnum]
                unsent_seqnum += 1
                sock.sendto(pkt.encode(), nemu_addr)

                # start packetloss timer if not already started
                if pkt_loss_timer is None: 
                    pkt_loss_timer = Timer(pkt_loss_TO, pkt_loss_handler)



    Thread(target = sender).start()

    ################################
    # Connection termination stage #
    ################################
    # send an EOT packet after all chunks are sent (assume it isn't lost)
    sock.sendto(utils.EOT_PKT.encode(), nemu_addr)

    # wait for EOT ack and close (do it in loop in case old acks arrive)
    while True: 
        eot_pkt, _ = sock.recvfrom(1024)
        if Packet(eot_pkt).typ == utils.PACKET_TYPE_EOT: 
            break  # will terminate assuming EOT is never lost

    sock.close()


if __name__ == "__main__":
    main()
