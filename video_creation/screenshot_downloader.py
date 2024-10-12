import logging 
import argparse
import json
import re
from pathlib import Path
from typing import Dict, Final

import translators
from playwright.async_api import async_playwright, ViewportSize
from rich.progress import track
import asyncpraw

from utils import settings
from utils.console import print_step, print_substep
from utils.imagenarator import imagemaker
from utils.playwright import clear_cookie_by_name
from utils.videos import save_data

__all__ = ["get_screenshots_of_reddit_posts"]

async def get_screenshots_of_reddit_posts(reddit_object: dict, screenshot_num: int):
    """Downloads screenshots of reddit posts as seen on the web. Downloads to assets/temp/png
    
    Args:
        reddit_object (Dict): Reddit object received from reddit/subreddit.py
        screenshot_num (int): Number of screenshots to download
    """
    # Sets args so if logs are on headless mode is off
    parser = argparse.ArgumentParser(description="Control Headlessmode")
    parser.add_argument('--log', action='store_true', help="Enable logging")
    args = parser.parse_args() 

    # Configure logging
    logging.basicConfig(level=logging.DEBUG if args.log else logging.INFO)
    logger = logging.getLogger(__name__)

    # settings values
    W: Final[int] = int(settings.config["settings"]["resolution_w"])
    H: Final[int] = int(settings.config["settings"]["resolution_h"])
    lang: Final[str] = settings.config["reddit"]["thread"]["post_lang"]
    storymode: Final[bool] = settings.config["settings"]["storymode"]

    print_step("Downloading screenshots of reddit posts...")
    logger.info("Starting to download screenshots of reddit posts...")
    reddit_id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    # ! Make sure the reddit screenshots folder exists
    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)

    # set the theme and turn off non-essential cookies
    if settings.config["settings"]["theme"] == "dark":
        with open("./video_creation/data/cookie-dark-mode.json", encoding="utf-8") as cookie_file:
            cookies = json.load(cookie_file)
        bgcolor = (33, 33, 36, 255)
        txtcolor = (240, 240, 240)
        transparent = False
    elif settings.config["settings"]["theme"] == "transparent":
        if storymode:
            # Transparent theme
            bgcolor = (0, 0, 0, 0)
            txtcolor = (255, 255, 255)
            transparent = True
            with open("./video_creation/data/cookie-dark-mode.json", encoding="utf-8") as cookie_file:
                cookies = json.load(cookie_file)
        else:
            # Switch to dark theme
            with open("./video_creation/data/cookie-dark-mode.json", encoding="utf-8") as cookie_file:
                cookies = json.load(cookie_file)
            bgcolor = (33, 33, 36, 255)
            txtcolor = (240, 240, 240)
            transparent = False
    else:
        with open("./video_creation/data/cookie-light-mode.json", encoding="utf-8") as cookie_file:
            cookies = json.load(cookie_file)
        bgcolor = (255, 255, 255, 255)
        txtcolor = (0, 0, 0)
        transparent = False

    if storymode and settings.config["settings"]["storymodemethod"] == 1:
        print_substep("Generating images...")
        logger.info("Generating images in story mode...")
        return imagemaker(
            theme=bgcolor,
            reddit_obj=reddit_object,
            txtclr=txtcolor,
            transparent=transparent,
        )

    async with async_playwright() as p:
        print_substep("Launching Headless Browser...")
        logger.info("Launching headless browser...")

        browser = await p.chromium.launch(
           headless=not args.log 
        ) 
        # Sets headless=false if --log is passed when running main.py
        # headless=False will show the browser for debugging purposes
        # Device scale factor (or dsf for short) allows us to increase the resolution of the screenshots
        # When the dsf is 1, the width of the screenshot is 600 pixels
        # so we need a dsf such that the width of the screenshot is greater than the final resolution of the video
        dsf = (W // 600) + 1

        context = await browser.new_context(
            locale=lang or "en-us",
            color_scheme="dark",
            viewport=ViewportSize(width=W, height=H),
            device_scale_factor=dsf,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        )
        await context.add_cookies(cookies)  # load preference cookies

        # Increase default timeout for all actions
        context.set_default_timeout(60000)

        # Login to Reddit
        print_substep("Logging in to Reddit...")
        logger.info("Logging in to Reddit...")
        page = await context.new_page()
        await page.goto("https://www.reddit.com/login", timeout=0)
        await page.set_viewport_size(ViewportSize(width=1920, height=1080))
        await page.wait_for_load_state()

        await page.locator(f'input[name="username"]').fill(settings.config["reddit"]["creds"]["username"])
        await page.locator(f'input[name="password"]').fill(settings.config["reddit"]["creds"]["password"])
        await page.get_by_role("button", name="Log In").click()
        await page.wait_for_timeout(5000)

        login_error_div = page.locator(".AnimatedForm__errorMessage").first
        if await login_error_div.is_visible():
            login_error_message = await login_error_div.inner_text()
            if login_error_message.strip() == "":
                # The div element is empty, no error
                pass
            else:
                # The div contains an error message
                print_substep(
                    "Your reddit credentials are incorrect! Please modify them accordingly in the config.toml file.",
                    style="red",
                )
                logger.error("Reddit credentials are incorrect.")
                exit()
        else:
            pass

        await page.wait_for_load_state()
        # Handle the redesign
        # Check if the redesign optout cookie is set
        if await page.locator("#redesign-beta-optin-btn").is_visible():
            # Clear the redesign optout cookie
            await clear_cookie_by_name(context, "redesign_optout")
            # Reload the page for the redesign to take effect
            await page.reload()
        # Get the thread screenshot
        await page.goto(reddit_object["thread_url"], timeout=0)
        await page.set_viewport_size(ViewportSize(width=W, height=H))
        await page.wait_for_load_state()
        await page.wait_for_timeout(5000)

        if await page.locator(
            "#t3_12hmbug > div > div._3xX726aBn29LDbsDtzr_6E._1Ap4F5maDtT1E1YuCiaO0r.D3IL3FD0RFy_mkKLPwL4 > div > div > button"
        ).is_visible():
            # This means the post is NSFW and requires to click the proceed button.

            print_substep("Post is NSFW. You are spicy...")
            logger.info("Post is NSFW. Clicking proceed button...")
            await page.locator(
                "#t3_12hmbug > div > div._3xX726aBn29LDbsDtzr_6E._1Ap4F5maDtT1E1YuCiaO0r.D3IL3FD0RFy_mkKLPwL4 > div > div > button"
            ).click()
            await page.wait_for_load_state()  # Wait for page to fully load

            # translate code
        if await page.locator(
            "#SHORTCUT_FOCUSABLE_DIV > div:nth-child(7) > div > div > div > header > div > div._1m0iFpls1wkPZJVo38-LSh > button > i"
        ).is_visible():
            await page.locator(
                "#SHORTCUT_FOCUSABLE_DIV > div:nth-child(7) > div > div > div > header > div > div._1m0iFpls1wkPZJVo38-LSh > button > i"
            ).click()  # Interest popup is showing, this code will close it

        if lang:
            print_substep("Translating post...")
            logger.info("Translating post...")
            texts_in_tl = translators.translate_text(
                reddit_object["thread_title"],
                to_language=lang,
                translator="google",
            )

            await page.evaluate(
                "tl_content => document.querySelector('[data-adclicklocation=\"title\"] > div > div > h1').textContent = tl_content",
                texts_in_tl,
            )
        else:
            print_substep("Skipping translation...")
            logger.info("Skipping translation...")

        # take a screenshot of the post title and maybe the body
        postcontentpath = f"assets/temp/{reddit_id}/png/title.png"
        if await page.locator('h1[slot="title"]').is_visible():
            logger.info("Element is visible, taking screenshot...")
            try:
                # Bring the element to the front using evaluate
                await page.evaluate('element => element.style.zIndex = 9999', await page.locator('h1[slot="title"]').element_handle())
                # Wait for the element to be visible
                await page.locator('h1[slot="title"]').wait_for(state="visible", timeout=60000)
                # Ensure fonts are loaded
                await page.evaluate('document.fonts.ready')
                # Add a short delay to ensure the element is fully rendered
                await page.wait_for_timeout(1000)
                await page.locator('h1[slot="title"]').screenshot(path=postcontentpath, timeout=60000)
            except TimeoutError:
                print_substep("TimeoutError: Skipping screenshot...", style="red")
                logger.error("TimeoutError: Skipping screenshot...")
                return
        else:
            logger.info("Element is not visible!")

        try:
            if settings.config["settings"]["zoom"] != 1:
                # store zoom settings
                zoom = settings.config["settings"]["zoom"]
                # zoom the body of the page
                await page.evaluate("document.body.style.zoom=" + str(zoom))
                # as zooming the body doesn't change the properties of the divs, we need to adjust for the zoom
                location = await page.locator('h1[slot="title"]').bounding_box()
                for i in location:
                    location[i] = float("{:.2f}".format(location[i] * zoom))
                await page.wait_for_load_state("networkidle")
                await page.locator('h1[slot="title"]').screenshot(path=postcontentpath, timeout=60000)
            else:
                await page.wait_for_load_state("networkidle")
                await page.locator('h1[slot="title"]').screenshot(path=postcontentpath, timeout=60000)
        except Exception as e:
            print_substep("Something went wrong!", style="red")
            logger.error("Something went wrong!", exc_info=True)
            resp = input(
                "Something went wrong with making the screenshots! Do you want to skip the post? (y/n) "
            )

            if resp.casefold().startswith("y"):
                save_data("", "", "skipped", reddit_id, "")
                print_substep(
                    "The post is successfully skipped! You can now restart the program and this post will skipped.",
                    "green",
                )

            resp = input("Do you want the error traceback for debugging purposes? (y/n)")
            if not resp.casefold().startswith("y"):
                exit()

            raise e

        if storymode:
            await page.locator('[data-click-id="text"]').first.screenshot(
                path=f"assets/temp/{reddit_id}/png/story_content.png"
            )
        else:
            for idx, comment in enumerate(
                track(
                    reddit_object["comments"][:screenshot_num],
                    "Downloading screenshots...",
                )
            ):
                # Stop if we have reached the screenshot_num
                if idx >= screenshot_num:
                    break

                if await page.locator('[data-testid="content-gate"]').is_visible():
                    await page.locator('[data-testid="content-gate"] button').click()

                await page.goto(f"https://new.reddit.com/{comment['comment_url']}")
                logger.info(f"Navigating to comment URL: {comment['comment_url']}")

                # translate code
                if settings.config["reddit"]["thread"]["post_lang"]:
                    comment_tl = translators.translate_text(
                        comment["comment_body"],
                        translator="google",
                        to_language=settings.config["reddit"]["thread"]["post_lang"],
                    )
                    await page.evaluate(
                        '([tl_content, tl_id]) => document.querySelector(`#t1_${tl_id} > div:nth-child(2) > div > div[data-testid="comment"] > div`).textContent = tl_content',
                        [comment_tl, comment["comment_id"]],
                    )

                try:
                    # This is where comment screenshots are taken 
                    # Using thing id isnt the most reliable way to locate the comment, but it works for now
                    # It would be to use xpath to grab it by the text content, permaling and author
                    # Example 
                    # # Using XPath to select the element by the author and a partial match of its content.
                    #    comment_locator = page.locator(
                    #    f'xpath=//shreddit-comment[contains(@permalink, "{comment["comment_id"]}") and @author="{comment["author"]}"]'
                    #    )
                    #
                    # Might be worth chaging the way we locate the comment in the future

                    comment_locator = page.locator(f'shreddit-comment[thingid="t1_{comment["comment_id"]}"]')
                    
                    logging.debug(
                        f"Checking if comment {comment['comment_id']} is visible..."
                    )
                    
                    if await comment_locator.is_visible():
                        logger.info(f"Comment {comment['comment_id']} is visible, taking screenshot...")
                        if settings.config["settings"]["zoom"] != 1:
                            # store zoom settings
                            zoom = settings.config["settings"]["zoom"]
                            # zoom the body of the page
                            await page.evaluate("document.body.style.zoom=" + str(zoom))
                            # scroll comment into view
                            await comment_locator.scroll_into_view_if_needed()
                            # as zooming the body doesn't change the properties of the divs, we need to adjust for the zoom
                            location = await comment_locator.bounding_box()
                            for i in location:
                                location[i] = float("{:.2f}".format(location[i] * zoom))
                            await page.screenshot(
                                clip=location,
                                path=f"assets/temp/{reddit_id}/png/comment_{idx}.png",
                            )
                        else:
                            await comment_locator.screenshot(
                                path=f"assets/temp/{reddit_id}/png/comment_{idx}.png"
                            )
                    else:
                        logger.info(f"Comment {comment['comment_id']} is not visible, skipping...")
                except TimeoutError:
                    logger.error(f"TimeoutError: Skipping screenshot for comment {comment['comment_id']}...")
                    continue

        # close browser instance when we are done using it
        await browser.close()

    print_substep("Screenshots downloaded Successfully.", style="bold green")
    logger.info("Screenshots downloaded Successfully.")