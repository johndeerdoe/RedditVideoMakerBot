import asyncio
import argparse
import logging
import sys
import math
from pathlib import Path
from subprocess import Popen
from sys import exit, platform as name
import toml
from logging.handlers import RotatingFileHandler
from typing import Dict, Tuple, NoReturn
from rich.console import Console

# Common imports to keep the code cleaner