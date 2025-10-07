import logging
import logging.config
import importlib
import asyncio
import signal
import sys

import aiohttp
from dotenv import load_dotenv
from jiosaavn.config.settings import KOYEB_URL, PING_INTERVAL

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

running = True  # Used to gracefully stop the loop


async def ping_url():
    """Periodically send a GET request to the specified URL at defined intervals."""
    if not KOYEB_URL:
        logging.warning("⚠️ KOYEB_URL is not set. Skipping ping task.")
        return

    global running
    async with aiohttp.ClientSession() as session:
        while running:
            try:
                async with session.get(KOYEB_URL) as response:
                    if response.status == 200:
                        logging.info(f"✅ Successfully pinged {KOYEB_URL}")
                    else:
                        logging.warning(f"⚠️ Failed to ping {KOYEB_URL}: {response.status}")
            except Exception as e:
                logging.error(f"❌ Error pinging URL: {e}")
            await asyncio.sleep(PING_INTERVAL or 600)  # Default fallback: 10 mins


def handle_exit(signum, frame):
    """Handle termination signals gracefully."""
    global running
    logging.info("🛑 Shutting down ping loop...")
    running = False


def main():
    # Setup logging
    try:
        logging.config.fileConfig('logging.conf')
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.warning("⚠️ logging.conf not found — using basicConfig()")

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)

    # Load environment variables
    load_dotenv()

    # Import and initialize bot
    bot = importlib.import_module("jiosaavn.bot").Bot
    bot_instance = bot()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    async def run_all():
        # Run both bot and ping task concurrently
        ping_task = asyncio.create_task(ping_url())
        try:
            await bot_instance.run()
        finally:
            # Stop the ping loop once bot exits
            global running
            running = False
            ping_task.cancel()
            logging.info("Bot stopped. Exiting...")

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
