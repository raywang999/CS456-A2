import argparse
import utils


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
    


if __name__ == "__main__":
    main()
