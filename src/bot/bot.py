"""
iqromax.uz OTP Bot - Main Bot Module
Telegram bot initialization and startup
"""

import asyncio
import logging
from typing import Optional

from aiohttp import ClientTimeout, web

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from src.config import settings
from src.models import redis_client, init_db
from src.utils import setup_logging
from src.bot.handlers import router


logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Main Telegram bot class
    Handles bot initialization, startup, and shutdown
    """
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._running = False
    
    async def initialize(self):
        """
        Initialize bot and dispatcher
        """
        # Setup logging
        setup_logging()
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await redis_client.connect()
        
        # Create bot instance (extended timeout for unstable networks)
        timeout = ClientTimeout(total=60, sock_connect=15, sock_read=45)
        session = AiohttpSession(timeout=timeout)
        self.bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=session,
        )
        
        # Create dispatcher
        self.dp = Dispatcher()
        
        # Include routers
        self.dp.include_router(router)
        
        # Set bot menu commands (Telegram "Menu" button)
        commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="help", description="Yordam"),
            BotCommand(command="language", description="Tilni o'zgartirish"),
            BotCommand(command="status", description="OTP holati"),
        ]
        await self.bot.set_my_commands(commands)
        
        logger.info(f"Bot initialized: {settings.APP_NAME}")
    
    async def start_polling(self):
        """
        Start bot in polling mode (for development)
        """
        if not self.bot or not self.dp:
            await self.initialize()
        
        logger.info("Starting bot in polling mode...")
        self._running = True
        
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(
                self.bot,
                allowed_updates=["message", "callback_query"]
            )
        except asyncio.CancelledError:
            logger.info("Polling cancelled")
        except Exception as e:
            err_msg = str(e).lower()
            if "conflict" in err_msg or "getupdates" in err_msg:
                logger.error(
                    "TelegramConflictError: Boshqa joyda polling/webhook ishlayapti. "
                    "Faqat bitta instance ishlashi kerak. Docker to'xtating yoki TELEGRAM_WEBHOOK_URL qo'ying."
                )
            raise
        finally:
            self._running = False
    
    async def setup_webhook(self) -> None:
        """
        Set webhook URL (for FastAPI/webhook mode). Call on app startup.
        Stops Telegram from using getUpdates - prevents conflict with polling.
        """
        if not settings.TELEGRAM_WEBHOOK_URL:
            return
        if not self.bot:
            await self.initialize()
        await self.bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        logger.info(f"Webhook set: {settings.TELEGRAM_WEBHOOK_URL}")

    async def remove_webhook(self) -> None:
        """Remove webhook on shutdown (optional)."""
        if self.bot:
            try:
                await self.bot.delete_webhook()
                logger.info("Webhook removed")
            except Exception as e:
                logger.warning(f"Could not remove webhook: {e}")

    async def start_webhook(self, host: str = None, port: int = None):
        """
        Start bot in webhook mode (for production)
        
        Args:
            host: Webhook server host
            port: Webhook server port
        """
        if not self.bot or not self.dp:
            await self.initialize()
        
        host = host or settings.HOST
        port = port or settings.PORT
        webhook_url = settings.TELEGRAM_WEBHOOK_URL
        
        if not webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL is required for webhook mode")
        
        logger.info(f"Starting bot in webhook mode at {webhook_url}")
        self._running = True
        
        try:
            # Set webhook
            await self.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                drop_pending_updates=True
            )
            
            # Create aiohttp application
            app = web.Application()
            
            # Setup webhook handler
            webhook_path = "/webhook/telegram"
            SimpleRequestHandler(
                dispatcher=self.dp,
                bot=self.bot,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET
            ).register(app, path=webhook_path)
            
            # Run server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            
            logger.info(f"Webhook server started on {host}:{port}")
            
            # Keep running
            while self._running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise
        finally:
            self._running = False
            await self.bot.delete_webhook()
    
    async def stop(self):
        """
        Stop the bot gracefully
        """
        logger.info("Stopping bot...")
        self._running = False
        
        if self.bot:
            await self.bot.session.close()
        
        await redis_client.disconnect()
        
        logger.info("Bot stopped")
    
    async def send_otp_message(
        self,
        telegram_id: int,
        otp_code: str,
        lang: str = "uz"
    ) -> bool:
        """
        Send OTP message to user
        
        Args:
            telegram_id: User's Telegram ID
            otp_code: OTP code to send
            lang: Language code
        
        Returns:
            bool: Success status
        """
        from src.bot.locales import get_text
        
        if not self.bot:
            logger.error("Bot not initialized")
            return False
        
        try:
            message_text = get_text("otp_message", lang).format(
                otp=otp_code,
                minutes=settings.OTP_EXPIRY_MINUTES
            )
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )
            
            logger.info(f"OTP message sent to {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP to {telegram_id}: {e}")
            return False
    
    @property
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running

    async def process_webhook_update(self, body: dict) -> None:
        """
        Process incoming webhook update (from FastAPI). Feed to dispatcher.
        """
        from aiogram.types import Update
        if not self.bot or not self.dp:
            await self.initialize()
        update = Update.model_validate(body, context={"bot": self.bot})
        await self.dp.feed_update(self.bot, update)


# Global bot instance
telegram_bot = TelegramBot()


async def get_bot() -> TelegramBot:
    """
    Get bot instance (dependency injection)
    """
    return telegram_bot


# Entry point for standalone bot
async def main():
    """
    Main entry point for running bot standalone
    """
    bot = TelegramBot()
    
    try:
        await bot.initialize()
        
        # Choose mode based on environment
        if settings.TELEGRAM_WEBHOOK_URL:
            await bot.start_webhook()
        else:
            await bot.start_polling()
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
