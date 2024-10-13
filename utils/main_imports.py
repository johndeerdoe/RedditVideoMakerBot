import asyncio
import argparse
import logging
import sys
import math
from pathlib import Path
from subprocess import Popen
from sys import exit, platform as name
from utils.console import print_step, print_substep
from reddit.subreddit import get_subreddit_threads
from video_creation.voices import save_text_to_mp3
from video_creation.background import get_background_config, download_background_video, download_background_audio, chop_background
from video_creation.final_video import make_final_video
from video_creation.screenshot_downloader import get_screenshots_of_reddit_posts
from utils import settings
from utils.id import extract_id  
import toml
from logging.handlers import RotatingFileHandler
from utils.ffmpeg_install import ffmpeg_install
from utils.version import checkversion
from utils.console import print_markdown, print_step, print_substep
from utils.cleanup import cleanup
from typing import NoReturn
from prawcore import ResponseException
from utils.arg_parser import  get_args



#file for Imports for the main.py file to keep it clean