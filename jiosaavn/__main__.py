import logging
import logging.config
import importlib
import asyncio
import signal
import threading
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


def start_ping_loop():
    """Run the ping_url loop in a separate event loop (background thread)."""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ping_url())


def handle_exit(signum=None, frame=None):
    """Handle termination signals gracefully."""
    global running
    if running:
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
    bot_module = importlib.import_module("jiosaavn.bot")
    bot = bot_module.Bot()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Start ping loop in background thread
    threading.Thread(target=start_ping_loop, daemon=True).start()

    # Run the bot (Pyrogram manages its own loop)
    bot.run()

    # When bot stops, stop the ping loop too
    handle_exit()
    logging.info("✅ Bot stopped. Exiting...")


if __name__ == "__main__":
    main()
