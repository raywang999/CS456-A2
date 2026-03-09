import argparse


def _port(value: str) -> int:
    port = int(value)
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError("port must be in range 1-65535")
    return port


def parse_args() -> argparse.Namespace:
    parser.add_argument(
        "emulator_host",
        help="hostname for the network emulator",
    )
    parser.add_argument(
        "emulator_ack_port",
        type=_port,
        help="UDP port number used by the link emulator to receive ACKs from the receiver",
    )
    parser.add_argument(
        "receiver_data_port",
        type=_port,
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
