# Telegram Bot Architecture

## Overview

This document describes the architecture of the Telegram bot integration in BoTCoin, explaining the design decisions and best practices implemented to handle the asynchronous nature of the Telegram API while keeping the main trading loop synchronous.

## Architecture Design

### Core Principles

1. **Separation of Concerns**: The main trading loop runs synchronously while the Telegram bot operates in a separate thread with its own event loop.
2. **Thread Safety**: All shared state is protected with locks to prevent race conditions.
3. **Non-Blocking Operations**: Blocking operations in async handlers are offloaded to executors to prevent blocking the event loop.
4. **Clean Communication**: A queue-based pattern enables thread-safe communication from the sync main thread to the async Telegram thread.

### Components

#### 1. Thread-Safe State Management

```python
_state_lock = threading.Lock()
_bot_paused = False

def get_bot_paused():
    with _state_lock:
        return _bot_paused

def set_bot_paused(value):
    global _bot_paused
    with _state_lock:
        _bot_paused = value
```

**Why**: Global state like `BOT_PAUSED` needs protection when accessed from multiple threads (main thread and Telegram thread). The lock ensures atomic read/write operations.

#### 2. Message Queue Pattern

```python
self._message_queue = Queue()

def send_message(self, message):
    self._message_queue.put(message)

async def _process_message_queue(self):
    while self._running:
        if not self._message_queue.empty():
            message = self._message_queue.get_nowait()
            await self.app.bot.send_message(...)
```

**Why**: The main thread (synchronous) needs to send Telegram messages without dealing with async/await. The queue acts as a bridge:
- Main thread: Simply puts messages in the queue (thread-safe, non-blocking)
- Telegram thread: Asynchronously processes messages from the queue

**Benefits**:
- No need for `asyncio.run_coroutine_threadsafe` complexity
- No fallback to HTTP requests
- Simple, clean interface
- Natural backpressure handling

#### 3. ThreadPoolExecutor for Blocking Operations

```python
self._executor = ThreadPoolExecutor(max_workers=3)

async def market_command(self, update, context):
    loop = asyncio.get_event_loop()
    balance = await loop.run_in_executor(self._executor, get_balance)
    price = await loop.run_in_executor(self._executor, get_last_price, pair)
```

**Why**: Command handlers are async but need to call blocking functions (Kraken API, file I/O). Running these in an executor prevents blocking the event loop.

**Without Executor** (❌ Bad):
```python
async def market_command(self, update, context):
    balance = get_balance()  # BLOCKS the entire event loop!
```

**With Executor** (✅ Good):
```python
async def market_command(self, update, context):
    balance = await loop.run_in_executor(self._executor, get_balance)
    # Event loop can process other tasks while waiting
```

#### 4. Simplified Event Loop Management

**Old Approach** (Complex):
- Manually create and manage event loop
- Store loop reference (`self._loop`)
- Use `run_coroutine_threadsafe` to schedule coroutines
- Complex shutdown logic

**New Approach** (Simple):
- Let Python create the event loop for the thread
- Let python-telegram-bot manage the event loop lifecycle
- Use simple `_running` flag for shutdown coordination
- Proper cleanup of tasks and resources

```python
def run(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    self._running = True
    
    async def run_bot():
        queue_task = asyncio.create_task(self._process_message_queue())
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(...)
        
        while self._running:
            await asyncio.sleep(1)
        
        # Clean shutdown
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
    
    loop.run_until_complete(run_bot())
```

## Improvements Made

### 1. Thread Safety
- **Before**: Global `BOT_PAUSED` accessed directly from multiple threads (race condition)
- **After**: Thread-safe getters/setters with locks

### 2. Message Sending
- **Before**: Complex logic with `run_coroutine_threadsafe` and HTTP fallback
- **After**: Simple queue-based pattern

### 3. Blocking Calls in Async Context
- **Before**: Direct blocking calls in async handlers (blocks event loop)
- **After**: All blocking calls run in executor (non-blocking)

### 4. Event Loop Management
- **Before**: Manual loop management, stored references, complex shutdown
- **After**: Simple lifecycle, let library handle details

### 5. Code Clarity
- **Before**: Mixed patterns, unclear boundaries
- **After**: Clear documentation, consistent patterns, explicit async/sync boundaries

## Best Practices Implemented

1. ✅ **Never block the event loop**: All blocking operations use executors
2. ✅ **Thread-safe state**: Shared state protected with locks
3. ✅ **Clean separation**: Clear boundary between sync main loop and async Telegram thread
4. ✅ **Proper cleanup**: Resources (executor, tasks, event loop) cleaned up properly
5. ✅ **Error handling**: Comprehensive exception handling at all levels
6. ✅ **Documentation**: Docstrings explain architecture decisions

## Usage Examples

### From Main Thread (Synchronous)
```python
# Send a notification - simple and thread-safe
telegram.send_notification("🆕 New position opened!")

# Check if bot is paused
if telegram.get_bot_paused():
    # Skip trading logic
    pass
```

### Command Handlers (Asynchronous)
```python
async def market_command(self, update, context):
    # Run blocking API call in executor
    loop = asyncio.get_event_loop()
    price = await loop.run_in_executor(self._executor, get_last_price, pair)
    
    # Send response (async operation, doesn't block event loop)
    await update.message.reply_text(f"Price: {price}")
```

## Why Not Make Main Loop Async?

The main loop performs synchronous trading operations that don't benefit from async:
- Sequential processing of pairs
- Blocking Kraken API calls (library doesn't provide async interface)
- File I/O operations
- State management

Making it async would add complexity without benefits. The current architecture keeps the main loop simple while properly handling the async Telegram API in isolation.

## Performance Characteristics

- **Main Loop**: Not affected by Telegram operations (runs independently)
- **Telegram Bot**: Can handle multiple concurrent commands (event loop + executor)
- **Message Queue**: Non-blocking for sender, processed asynchronously
- **No Polling Bottlenecks**: Blocking calls don't affect Telegram's ability to receive updates

## Conclusion

This architecture provides a clean, maintainable solution that:
- Respects the asynchronous nature of the Telegram API
- Keeps the main trading loop simple and synchronous
- Ensures thread safety
- Follows Python async/await best practices
- Provides clear separation of concerns
