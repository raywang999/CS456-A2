import argparse
import socket
import time
from threading import Lock, Thread, Timer

import utils
from packet import Packet
from math import floor


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


class Sender:
    def __init__(self, args: argparse.Namespace) -> None:
        # address used to send packets to nemulator 
        self.nemu_addr = (args.emulator_host, args.emulator_data_port)
        
        # UDP socket used to send/receive packets over nenumlator
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", args.sender_ack_port))

        # load file into a queue of packets to send 
        self.packets_to_send = self.load_packets(args.input_file)
        self.num_packets_to_send = len(self.packets_to_send)

        # real-valued cwnd 
        self.cwnd = 1.0
        # N i.e the current window size 
        self.wnd_size = 1 
        # largest index s.t. all packets <= acked_ind are ACK'd
        self.acked_ind = -1
        # index of next packet that should be sent next by sender
        self.unsent_ind = 0

        # packet loss timer. None to indicate the timer is stopped 
        self.pkt_loss_timer: Timer | None = None
        self.pkt_loss_timeout = 0.3  # 300 ms

        # flag for when data transmission stage ends
        self.done_data_trans_stage = False
        self.lock = Lock()

        # ECN feedback variables         
        self.alpha = 0.0 
        self.prev_ce_count = 0
        self.acked_in_rtt = 0 
        self.marked_in_rtt = 0 
        self.prev_seqnum = 31
        # timer used for ECN feedback 
        self.rtt_timer = Timer(0.1, self.rtt_handler) # RTT is approx 100 ms
        self.rtt_timer.start() # start initial RTT at start of program

        # log files 
        self.seqnum_log = open('seqnum.log', 'w')
        self.ack_log = open('ack.log', 'w')
        self.N_log = open('N.log', 'w')

        # timestamp for logging 
        self.timestamp = 0

        # initial log the window to be 1
        self.write_log(self.N_log, 1)

    def write_log(self, log, data) -> None: 
        """
        helper for writing to log with timestamp 
        precondition: lock is acquired by caller
        """
        log.write(f't={self.timestamp} {data}\n')

    def set_wnd_size(self, wnd_size) -> None: 
        """
        sets wnd_size and updates N.log if value of N changes
        precondition: lock is acquired by caller
        postcondition: if window shrinks, then updates unsent_ind as required
        """
        if self.wnd_size != wnd_size: 
            self.write_log(self.N_log, wnd_size)
            self.wnd_size = wnd_size
            # retransmit packets outside of the new window
            self.unsent_ind = min(self.unsent_ind, self.acked_ind + wnd_size)

    def send_packet(self, pkt: Packet) -> None: 
        """
        send a data packet via nemulator and log its seqnum 
        """
        self.sock.sendto(pkt.encode(), self.nemu_addr)
        # event occurred (a packet was sent) so update timestamp
        self.timestamp += 1 
        if pkt.typ == utils.PACKET_TYPE_EOT: 
            self.write_log(self.seqnum_log, "EOT")
        else: 
            self.write_log(self.seqnum_log, pkt.seqnum)

    def load_packets(self, input_file: str) -> list[Packet]:
        """
        read file into chunks of length 500 (maximum packet data length)
        """

        packets: list[Packet] = []
        with open(input_file, "r", encoding="ascii") as inp_f:
            packet_index = 0
            while True:
                chunk = inp_f.read(500)
                if chunk == "": # end of file
                    return packets
                packets.append(
                    Packet(
                        utils.PACKET_TYPE_DATA,
                        packet_index % utils.MOD_SIZE,
                        len(chunk),
                        0, # ecn will be set by the nemulator
                        0, # ec_count is not set by sender 
                        chunk,
                    )
                )
                packet_index += 1
    
    def rtt_handler(self) -> None:
        """
        handles at the end of every RTT timer tick for ECN feedback control
        cleans the timer and terminates if we are past data-transmission stage
        """
        with self.lock: 
            if self.done_data_trans_stage: 
                self.rtt_timer.cancel()
                return 

            # update timestamp for logs 
            self.timestamp += 1

            if self.acked_in_rtt > 0: 
                # compute fraction of marked packets received at receiver
                F = self.marked_in_rtt/self.acked_in_rtt

                # update with exp. weighted moving average
                self.alpha = (1 - 0.0625) * self.alpha + 0.0625 * F

                # ECN-based multiplicative decrease 
                self.cwnd = self.cwnd * (1 - self.alpha / 2)

                # update windowsize N and write to N_log
                self.set_wnd_size(min(10, max(1, floor(self.cwnd))))

            # reset RTT timer and state 
            self.acked_in_rtt = 0 
            self.marked_in_rtt = 0 
            self.rtt_timer.cancel()
            self.rtt_timer = Timer(0.1, self.rtt_handler)


    def num_inflight(self) -> int:
        """
        precondition: lock is acquired by the calling thread
        result: returns number of inflight packets 
        """
        return self.unsent_ind - self.acked_ind - 1

    def pkt_loss_handler(self) -> None:
        """ 
        handles when a packet is lost (i.e. pkt loss timer expires)
        """
        with self.lock:
            if self.done_data_trans_stage: 
                return  # do nothing if finished data_trans stage
            
            # update timestamp for logs 
            self.timestamp += 1

            # otherwise, update the window state and mark packets as lost
            self.set_wnd_size(1)  # update N and log if changed
            self.cwnd = 1.0

            # resend oldest un-ACK'd packet if it exists 
            if self.unsent_ind < self.num_packets_to_send:
                pkt = self.packets_to_send[self.unsent_ind]
                self.unsent_ind += 1
                self.send_packet(pkt)

            # reset the timer, cancelling previous one if it exists 
            if self.pkt_loss_timer is not None:
                self.pkt_loss_timer.cancel() 
            self.pkt_loss_timer = Timer(self.pkt_loss_timeout, self.pkt_loss_handler)
            self.pkt_loss_timer.start()

    def send_loop(self) -> None:
        """
        keep trying to send the next unsent packet, if it exists
        """
        while True:
            with self.lock:
                if self.done_data_trans_stage:
                    return

                # check if all packets are ACKd, so finished data trans. stage
                if self.acked_ind >= self.num_packets_to_send - 1:
                    self.done_data_trans_stage = True
                    return # terminate the thread 

                # if there's no space in the window to send packets, wait
                if self.num_inflight() >= self.wnd_size:
                    time.sleep(0) # thread_yield 
                    continue

                # otherwise, send a packet 
                pkt = self.packets_to_send[self.unsent_ind]
                self.unsent_ind += 1
                self.send_packet(pkt)

                # and start the pkt_loss_timer if not already started
                if self.pkt_loss_timer is None:
                    self.pkt_loss_timer = Timer(self.pkt_loss_timeout, self.pkt_loss_handler)
                    self.pkt_loss_timer.start()


    def ack_loop(self) -> None:
        """ 
        handles ACK packets from nemulator 
        """
        while True:
            with self.lock:
                # terminate thread if finished data-transmission stage
                if self.done_data_trans_stage:
                    return
                if self.acked_ind >= self.num_packets_to_send - 1:
                    self.done_data_trans_stage = True
                    return

            # wait for an ACK packet 
            recv_msg, _ = self.sock.recvfrom(1024)
            pkt = Packet(recv_msg)
            assert pkt.typ == utils.PACKET_TYPE_ACK, "sender only expects ACK"

            # update timestamp since event occurred 
            self.timestamp += 1
            # log to ack.log 
            self.write_log(self.ack_log, f'{pkt.seqnum} {pkt.ce_count}')

            with self.lock:
                # check if ACK'd seqnum is in window of inflight packets
                acked_seqnum = self.acked_ind % utils.MOD_SIZE
                pkt_diff = utils.seqnum_diff(acked_seqnum, pkt.seqnum)
                if pkt_diff == 0 or pkt_diff > self.num_inflight():
                    continue # duplicate ACK, do nothing 

                # otherwise, we received a new ACK. 
                # 1. update cumulative ACK 
                self.acked_ind += pkt_diff 
                
                # 2. restart/stop packet loss timer 
                if self.num_inflight() == 0: 
                    # stop timer if no inflight packets 
                    if self.pkt_loss_timer is not None: 
                        self.pkt_loss_timer.cancel()
                        self.pkt_loss_timer = None
                else: 
                    # restart timer if inflight packets exist
                    if self.pkt_loss_timer is not None:
                        self.pkt_loss_timer.cancel()
                    self.pkt_loss_timer = Timer(self.pkt_loss_timeout, self.pkt_loss_handler)
                    self.pkt_loss_timer.start()

                # 3. additive increase cwnd and N (i.e. wnd_size)
                self.cwnd = self.cwnd + 1.0 / self.cwnd
                self.set_wnd_size(min(10, max(1, floor(self.cwnd))))

                # 4. update ECN feedback variables
                self.acked_in_rtt += (pkt.seqnum - self.prev_seqnum + utils.MOD_SIZE) % utils.MOD_SIZE
                self.marked_in_rtt += pkt.ce_count - self.prev_ce_count
                self.prev_ce_count = pkt.ce_count
                self.prev_seqnum = pkt.seqnum


    def run(self) -> None:
        # Data transmission stage 
        # we'll use 4 threads: 
        # - sender thread that tries to send packets if window allows
        # - receiver thread that handles incoming ACKs 
        # - packet-drop timer to update window from packet drop 
        # - ecn-feedback timer to update window using ce_count

        sender_thread = Thread(target=self.send_loop)
        ack_thread = Thread(target=self.ack_loop)

        sender_thread.start()
        ack_thread.start()

        sender_thread.join()
        ack_thread.join()

        # Connection termination stage.
        # send EOT packet with correct seqnum 
        eot_pkt = utils.EOT_PKT 
        eot_pkt.seqnum = self.num_packets_to_send % utils.MOD_SIZE
        self.send_packet(eot_pkt)

        # loop incase of out-of-order ACKs 
        while True:
            recv_pkt, _ = self.sock.recvfrom(1024)
            if Packet(recv_pkt).typ == utils.PACKET_TYPE_EOT:
                break

        self.sock.close()


def main() -> None:
    args = parse_args()
    sender = Sender(args)
    sender.run()


if __name__ == "__main__":
    main()
