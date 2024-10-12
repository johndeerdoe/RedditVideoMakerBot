#!/usr/bin/env python
import asyncio
import argparse
import logging
import math
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

def setup_logging(log_file):
    # Set up a rotating log with a maximum size of 1MB and 3 backup files
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Get the root logger and set its level
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the default logging level to DEBUG
    logger.addHandler(handler)  # Add the rotating file handler

def load_config():
    config_path = 'C:/RedditVideoMakerBot/config.toml'  # Update this path to the actual location of your config file
    with open(config_path, 'r') as config_file:
        return toml.load(config_file)

async def main(POST_ID=None):
    # Setting up a parser to handle command-line arguments
    parser = argparse.ArgumentParser(description="Control logging")
    parser.add_argument('--log', action='store_true', help="Enable logging")
    args = parser.parse_args()

    # Enable or disable logging based on the --log argument
    if args.log:
        setup_logging('app.log')  # Call the setup_logging function
        logging.info("Logging is enabled")
    else:
        logging.disable(logging.CRITICAL)  # Disable logging by setting the level to CRITICAL
    
    settings.config = load_config()
    
    global reddit_id, reddit_object
    reddit_object = get_subreddit_threads(POST_ID)  # Removed await
    reddit_id = extract_id(reddit_object)
    print_substep(f"Thread ID is {reddit_id}", style="bold blue")
    length, number_of_comments = save_text_to_mp3(reddit_object)
    length = math.ceil(length)
    await get_screenshots_of_reddit_posts(reddit_object, number_of_comments)
    bg_config = {
        "video": get_background_config("video"),
        "audio": get_background_config("audio"),
    }
    download_background_video(bg_config["video"])
    download_background_audio(bg_config["audio"])
    chop_background(bg_config, length, reddit_object)
    make_final_video(number_of_comments, length, reddit_object, bg_config)

def run_many(times) -> None:
    for x in range(1, times + 1):
        print_step(
            f'on the {x}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[x % 10]} iteration of {times}'
        )
        asyncio.run(main())
        Popen("cls" if name == "nt" else "clear", shell=True).wait()

if __name__ == "__main__":
    asyncio.run(main())
