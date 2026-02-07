#!/usr/bin/env python3
"""
iqromax.uz OTP Bot - Main Entry Point
Runs both Telegram bot and FastAPI server
"""

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

import uvicorn

from src.config import settings
from src.utils import setup_logging
from src.bot import telegram_bot
from src.api.app import app


logger = logging.getLogger(__name__)


async def run_bot():
    """
    Run Telegram bot in polling mode
    """
    try:
        await telegram_bot.initialize()
        
        if settings.TELEGRAM_WEBHOOK_URL:
            logger.info("Bot will use webhook mode (handled by FastAPI)")
        else:
            logger.info("Starting bot in polling mode...")
            await telegram_bot.start_polling()
            
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise


def run_api():
    """
    Run FastAPI server. Tries alternative ports if default is busy.
    """
    use_reload = settings.DEBUG and sys.platform != "win32"
    ports = [settings.PORT, 8001, 8002, 8003]
    for port in ports:
        try:
            uvicorn.run(
                "src.api.app:app",
                host=settings.HOST,
                port=port,
                reload=use_reload,
                log_level=settings.LOG_LEVEL.lower(),
                access_log=settings.DEBUG
            )
            return
        except OSError as e:
            if e.errno == 10048:  # Windows: address already in use
                logger.warning(f"Port {port} busy, trying next...")
                continue
            raise
        except SystemExit as e:
            if e.code == 1 and port < ports[-1]:  # uvicorn exits 1 on bind failure
                logger.warning(f"Port {port} failed, trying next...")
                continue
            raise
    logger.error("All ports busy. API server not started.")


async def main():
    """
    Main entry point
    """
    # Setup logging
    setup_logging()
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Handle shutdown signals (Unix only; on Windows use KeyboardInterrupt)
    loop = asyncio.get_event_loop()
    if sys.platform != "win32":
        def signal_handler():
            logger.info("Received shutdown signal")
            loop.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        if settings.TELEGRAM_WEBHOOK_URL:
            # Production: Run only API (bot uses webhook)
            logger.info("Running in webhook mode - starting API server only")
            run_api()
        else:
            # Development: Run bot polling and API together
            logger.info("Running in development mode - starting bot polling and API")
            
            executor = ThreadPoolExecutor(max_workers=1)
            api_future = loop.run_in_executor(executor, run_api)

            def on_api_done(f):
                try:
                    f.result()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"API server stopped: {e}")

            api_future.add_done_callback(on_api_done)
            
            try:
                await run_bot()
            except asyncio.CancelledError:
                logger.info("Bot polling cancelled (shutdown)")
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        await telegram_bot.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Graceful exit on Ctrl+C, no traceback
