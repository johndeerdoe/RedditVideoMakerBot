# utils/arg_parser.py
import argparse


def get_args():
    # Create a single ArgumentParser instance
    parser = argparse.ArgumentParser(description="Control all arguments")

    # Add arguments for headless mode
    parser.add_argument('--headlessoff', action='store_true', help="Use to turn headless mode off", default=False)

    # Add arguments for logging
    parser.add_argument('--log', action='store_true', help="Enable logging", default=False)

    return parser.parse_args()
