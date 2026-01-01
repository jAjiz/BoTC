import threading
import time
import logging
import asyncio
import json
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from exchange.kraken import get_last_price, get_current_atr, get_balance
from core.config import TELEGRAM_TOKEN, ALLOWED_USER_ID, POLL_INTERVAL_SEC, MODE, PAIRS

# Thread-safe state management
_state_lock = threading.Lock()
_bot_paused = False

def get_bot_paused():
    """Thread-safe getter for bot pause state."""
    with _state_lock:
        return _bot_paused

def set_bot_paused(value):
    """Thread-safe setter for bot pause state."""
    global _bot_paused
    with _state_lock:
        _bot_paused = value

# Only log warnings and above from telegram library
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.bot").setLevel(logging.WARNING)

class TelegramInterface:
    """
    Telegram bot interface for BoTCoin.
    
    This class manages the Telegram bot in a separate thread with its own event loop.
    The architecture uses:
    - A dedicated thread for the async Telegram bot (required by python-telegram-bot)
    - A thread-safe queue for sending notifications from the main (sync) thread
    - ThreadPoolExecutor for running blocking operations from async handlers
    
    The separation ensures the synchronous main trading loop is not affected by
    the asynchronous nature of the Telegram API.
    """
    
    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id
        self.app = ApplicationBuilder().token(token).build()
        self._message_queue = Queue()
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=3)
    
    def _check_auth(self, update: Update) -> bool:
        """Verify that the command comes from the authorized user."""
        return update.effective_user.id == self.user_id
    
    async def send_startup_message(self):
        try:
            await self.app.bot.send_message(
                chat_id=self.user_id,
                text="🤖 BoTC started and running. Use /help to see available commands."
            )
        except Exception as e:
            logging.error(f"Failed to send startup message: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        pairs_list = ', '.join(PAIRS.keys())
        await update.message.reply_text(
            "📋 Available commands:\n\n"
            "/status - Bot status and configured pairs\n"
            "/pause - Pause bot operations\n"
            "/resume - Resume bot operations\n"
            "/market [pair] - Current market data (all or specific pair)\n"
            "/positions [pair] - Open positions (all or specific pair)\n"
            "/help - Show this help\n\n"
            f"Configured pairs: {pairs_list}\n"
            "Example: /market XBTEUR"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        status = "⏸ PAUSED" if get_bot_paused() else "▶️ RUNNING"
        pairs_list = ', '.join(PAIRS.keys())
        await update.message.reply_text(
            f"Status: {status}\n"
            f"Last activity: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Mode: {MODE.upper()}\n"
            f"Pairs: {pairs_list}\n"
        )

    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        if get_bot_paused():
            await update.message.reply_text("⚠️ Bot is already paused.")
            return
        set_bot_paused(True)
        await update.message.reply_text("⏸ BoTC paused. New operations will not be processed.")

    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        if not get_bot_paused():
            await update.message.reply_text("⚠️ Bot is already running.")
            return
        set_bot_paused(False)
        await update.message.reply_text("▶️ BoTC resumed.")

    async def market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display current market status.
        Uses executor to run blocking Kraken API calls without blocking the event loop.
        """
        if not self._check_auth(update): return
        try:
            # Check if a specific pair was requested
            pair_filter = context.args[0].upper() if context.args else None
            if pair_filter and pair_filter not in PAIRS:
                await update.message.reply_text(f"❌ Unknown pair: {pair_filter}\nAvailable: {', '.join(PAIRS.keys())}")
                return
            
            # Run blocking call in executor
            loop = asyncio.get_running_loop()
            balance = await loop.run_in_executor(self._executor, get_balance)
            
            pairs_to_show = [pair_filter] if pair_filter else list(PAIRS.keys())
            
            msg = "📈 Market Status:\n\n"
            
            for pair in pairs_to_show:
                try:
                    # Run blocking calls in executor to avoid blocking event loop
                    price = await loop.run_in_executor(
                        self._executor, get_last_price, PAIRS[pair]['primary']
                    )
                    atr = await loop.run_in_executor(
                        self._executor, get_current_atr, pair
                    )
                    
                    asset = PAIRS[pair]['base']
                    asset_balance = float(balance.get(asset, 0))
                    asset_value_eur = asset_balance * price
                    
                    msg += (
                        f"━━━ {pair} ━━━\n"
                        f"Price: {price:,.2f}€\n"
                        f"ATR(15m): {atr:,.2f}€\n"
                        f"Balance: {asset_balance:.8f} ({asset_value_eur:,.2f}€)\n\n"
                    )
                    if len(pairs_to_show) > 1:
                        await asyncio.sleep(1)  # Delay to avoid rate limits
                except Exception as e:
                    msg += f"━━━ {pair} ━━━\n❌ Error: {e}\n\n"
            
            fiat_balance = float(balance.get("ZEUR", 0))
            msg += f"💵 EUR Balance: {fiat_balance:,.2f}€"
            
            await update.message.reply_text(msg)
        except Exception as e:
            logging.error(f"Error in market_command: {e}")
            await update.message.reply_text(f"❌ Error fetching market status: {e}")

    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display open positions.
        Uses executor for file I/O and blocking API calls.
        """
        if not self._check_auth(update): return
        try:
            # Check if a specific pair was requested
            pair_filter = context.args[0].upper() if context.args else None
            if pair_filter and pair_filter not in PAIRS:
                await update.message.reply_text(f"❌ Unknown pair: {pair_filter}\nAvailable: {', '.join(PAIRS.keys())}")
                return
            
            # Read positions file in executor (I/O operation)
            loop = asyncio.get_running_loop()
            
            def read_positions():
                with open("data/trailing_state.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            
            try:
                all_positions = await loop.run_in_executor(self._executor, read_positions)
            except FileNotFoundError:
                await update.message.reply_text("ℹ️ No positions file found.")
                return
            
            pairs_to_show = [pair_filter] if pair_filter else list(PAIRS.keys())
            msg = "📊 Open Positions:\n\n"
            total_positions = 0
            
            for pair in pairs_to_show:
                pair_positions = all_positions.get(pair, {})
                if not pair_positions:
                    continue
                
                try:
                    # Run blocking API call in executor
                    current_price = await loop.run_in_executor(
                        self._executor, get_last_price, PAIRS[pair]['primary']
                    )
                    msg += f"━━━ {pair} (Price: {current_price:,.2f}€) ━━━\n"
                    
                    for pos_id, pos in pair_positions.items():
                        total_positions += 1
                        trailing_active = pos.get('trailing_price') is not None

                        side = pos.get('side', '').lower()
                        entry_price = pos.get('entry_price')
                        activation_price = pos.get('activation_price')

                        # Header with active icon if trailing is active
                        active_icon = "⚡" if trailing_active else ""  # highlight active

                        # Base lines
                        base_lines = [
                            f"{active_icon} ID: {pos_id}",
                            f"Side: {pos['side'].upper()} | Entry: {entry_price:,.2f}€",
                        ]

                        # Show either volume or cost depending on side
                        if side == 'sell':
                            base_lines.append(f"Volume: {pos['volume']:,.8f}")
                        elif side == 'buy':
                            base_lines.append(f"Cost: {pos['cost']:,.2f}€")

                        if not trailing_active:
                            # Not active: show activation only
                            base_lines.append(f"Activation: {activation_price:,.2f}€")
                            msg += "\n".join(base_lines) + "\n\n"
                        else:
                            # Active: show full trailing info and P&L
                            trailing_price = pos.get('trailing_price')
                            stop_price = pos.get('stop_price')
                            if side == 'sell':
                                pnl_pct = ((stop_price - entry_price) / entry_price * 100)
                            else:
                                pnl_pct = ((entry_price - stop_price) / entry_price * 100)
                            pnl_symbol = "🟢" if pnl_pct > 0 else "🔴"

                            base_lines.extend([
                                f"Activation: {activation_price:,.2f}€",
                                f"Trailing: {trailing_price:,.2f}€",
                                f"Stop: {stop_price:,.2f}€",
                                f"P&L: {pnl_symbol} {pnl_pct:+.2f}%",
                            ])
                            msg += "\n".join(base_lines) + "\n\n"
                    
                    if len(pairs_to_show) > 1:
                        await asyncio.sleep(1)  # Delay to avoid rate limits
                except Exception as e:
                    msg += f"❌ Error fetching {pair}: {e}\n\n"
            
            if total_positions == 0:
                await update.message.reply_text("ℹ️ No open positions.")
            else:
                await update.message.reply_text(msg[-4000:])
        except Exception as e:
            logging.error(f"Error in positions_command: {e}")
            await update.message.reply_text(f"❌ Error fetching positions: {e}")

    async def _process_message_queue(self):
        """
        Background task to process messages from the queue.
        This allows the main thread to send messages without dealing with async/await.
        """
        while self._running:
            try:
                # Check queue with timeout to allow checking _running flag
                if not self._message_queue.empty():
                    message = self._message_queue.get_nowait()
                    try:
                        await self.app.bot.send_message(chat_id=self.user_id, text=message)
                    except Exception as e:
                        logging.error(f"Failed to send queued message: {e}")
                else:
                    # Small sleep to avoid busy waiting
                    await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
    
    async def send_message_async(self, message):
        """Send a message directly (for internal use within async context)."""
        try:
            await self.app.bot.send_message(chat_id=self.user_id, text=message)
        except Exception as e:
            logging.error(f"Telegram async send error: {e}")

    def send_message(self, message):
        """
        Thread-safe method to send messages from the main (synchronous) thread.
        Messages are queued and sent by the background task in the Telegram thread.
        """
        try:
            self._message_queue.put(message)
        except Exception as e:
            logging.error(f"Failed to queue message: {e}")

    def run(self):
        """
        Run the Telegram bot in a dedicated thread.
        
        This method creates a new event loop for the thread and lets python-telegram-bot
        manage it. The event loop is properly cleaned up on exit.
        """
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._running = True
        
        try:
            # Register command handlers
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("status", self.status_command))
            self.app.add_handler(CommandHandler("pause", self.pause_command))
            self.app.add_handler(CommandHandler("resume", self.resume_command))
            self.app.add_handler(CommandHandler("market", self.market_command))
            self.app.add_handler(CommandHandler("positions", self.positions_command))

            # Send startup message
            loop.run_until_complete(self.send_startup_message())
            
            # Create background task for processing message queue
            async def run_bot():
                # Start message queue processor as background task
                queue_task = asyncio.create_task(self._process_message_queue())
                
                # Run polling (this blocks until stopped)
                await self.app.initialize()
                await self.app.start()
                await self.app.updater.start_polling(poll_interval=POLL_INTERVAL_SEC)
                
                # Wait for stop signal (polling will run indefinitely)
                try:
                    while self._running:
                        await asyncio.sleep(1)
                finally:
                    # Stop polling and clean up
                    await self.app.updater.stop()
                    await self.app.stop()
                    await self.app.shutdown()
                    queue_task.cancel()
                    try:
                        await queue_task
                    except asyncio.CancelledError:
                        pass
            
            loop.run_until_complete(run_bot())
            
        except Exception as e:
            logging.error(f"Telegram thread error: {e}")
        finally:
            self._running = False
            # Cleanup executor with timeout
            self._executor.shutdown(wait=True, cancel_futures=False)
            # Close event loop
            try:
                # Cancel all remaining tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()
            except Exception as e:
                logging.warning(f"Error closing event loop: {e}")
            logging.info("Telegram thread has exited.")

tg_interface = None

def initialize_telegram():
    global tg_interface
    tg_interface = TelegramInterface(TELEGRAM_TOKEN, int(ALLOWED_USER_ID))
    t = threading.Thread(target=tg_interface.run, daemon=True)
    t.start()
    
def send_notification(msg):
    if tg_interface is None:
        logging.warning("Telegram not initialized. Message not sent: " + msg)
        return
    tg_interface.send_message(msg)

def stop_telegram_thread():
    """
    Stop the Telegram bot thread gracefully.
    This sets the running flag to False, which will cause the bot to stop.
    """
    global tg_interface
    try:
        if tg_interface:
            logging.info("Stopping Telegram thread...")
            tg_interface._running = False
            # Give it some time to shut down gracefully
            time.sleep(2)
            logging.info("Telegram thread stop signal sent.")
        else:
            logging.info("Telegram interface not initialized.")
    except Exception as e:
        logging.error(f"Error stopping Telegram thread: {e}")