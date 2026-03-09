import argparse

import utils


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


if __name__ == "__main__":
    main()
