# BoTCoin 🤖💰

Automated cryptocurrency trading bot with Kraken integration and Telegram notifications.

## 📋 Description

BoTCoin is an algorithmic trading system designed to operate on the Kraken exchange automatically. It uses ATR (Average True Range) based strategies to manage positions with dynamic trailing stops, allowing profit maximization while limiting losses.

The bot includes two configurable trading strategies and offers complete remote control through a Telegram bot, enabling real-time monitoring and operation management from any device.

## ✨ Key Features

- **Automated Trading**: Executes buy/sell operations automatically based on market conditions
- **Two Trading Strategies**:
  - **Multipliers**: ATR multiplier-based strategy with minimum margins
  - **Rebuy**: Rebuy strategy with adjustable activation distances
- **Dynamic Trailing Stops**: Profit protection through automatically adjusting stops
- **Risk Management**:
  - Minimum asset allocation control
  - Automatic recalibration based on volatility (ATR)
  - Protection against operations that unbalance the portfolio
- **Telegram Integration**:
  - Real-time notifications of all operations
  - Commands to query status, market, and positions
  - Pause/resume the bot remotely
- **State Persistence**: Saves position state to continue after restarts
- **Multi-Pair**: Support for trading multiple cryptocurrency pairs simultaneously

## 🏗️ Architecture

```
BoTCoin/
├── main.py                 # Main entry point and bot logic
├── core/                   # Core modules
│   ├── config.py          # Configuration and environment variables
│   ├── logging.py         # Logging system
│   └── state.py           # Persistent state management
├── exchange/              # Exchange integrations
│   └── kraken.py         # Kraken API
├── strategies/            # Trading strategies
│   ├── multipliers.py    # Multipliers strategy
│   └── rebuy.py          # Rebuy strategy
├── services/              # External services
│   └── telegram.py       # Telegram bot
└── requirements.txt       # Python dependencies
```

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Kraken account with API Key and Secret
- Telegram Bot (create with [@BotFather](https://t.me/botfather))
- Your Telegram User ID (get it from [@userinfobot](https://t.me/userinfobot))

### Installation Steps

1. **Clone the repository**:
```bash
git clone https://github.com/jAjiz/BoTCoin.git
cd BoTCoin
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:

Create a `.env` file in the project root with the following content:

```env
# Kraken API Credentials
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret

# Telegram Bot Credentials
TELEGRAM_TOKEN=your_telegram_token
ALLOWED_USER_ID=your_telegram_user_id

# Bot Configuration
MODE=rebuy                    # Options: "rebuy" or "multipliers"
SLEEPING_INTERVAL=60          # Interval between sessions (seconds)
ATR_DATA_DAYS=60             # Days of historical data for ATR calculation
POLL_INTERVAL_SEC=20         # Telegram polling interval

# Trading Pairs (comma-separated)
PAIRS=XBTEUR,ETHEUR

# Trading Parameters (global)
K_ACT=4.5                    # Activation multiplier
K_STOP_SELL=2.5              # Stop multiplier for sells
K_STOP_BUY=2.5               # Stop multiplier for buys
MIN_MARGIN=0.01              # Minimum margin (1%)

# Minimum Asset Allocation (per pair)
MIN_ALLOCATION_XBTEUR=0.5    # 50% minimum in BTC
MIN_ALLOCATION_ETHEUR=0.3    # 30% minimum in ETH

# Pair-Specific Parameters (optional)
# K_ACT_XBTEUR=5.0
# K_STOP_SELL_XBTEUR=3.0
# K_STOP_BUY_XBTEUR=3.0
```

## ⚙️ Configuration

### Trading Strategies

#### "Multipliers" Strategy
This strategy uses ATR multipliers to set activation and stop loss levels, with a guaranteed minimum margin to protect profits.

- **Activation Distance**: `K_ACT × ATR`
- **Stop Loss**: `K_STOP × ATR` (limited by minimum margin)
- **Minimum ATR**: Automatically calculated based on `MIN_MARGIN / (K_ACT - K_STOP)`

#### "Rebuy" Strategy
This strategy adds a fixed component based on the entry price, ideal for scaled rebuys.

- **Activation Distance**: 
  - Sell: `K_STOP_SELL × ATR + 1.06% × Entry_Price`
  - Buy: `K_STOP_BUY × ATR + 0.1% × Entry_Price`
- **Stop Loss**: `K_STOP × ATR`

### Key Parameters

- **K_ACT**: Controls the trailing stop activation distance
- **K_STOP_SELL/K_STOP_BUY**: Control the stop loss distance
- **MIN_MARGIN**: Guaranteed minimum profit margin (%)
- **MIN_ALLOCATION**: Minimum percentage of asset that must be maintained

### Per-Pair Configuration

You can customize parameters for specific pairs by adding the pair name as a suffix:

```env
K_ACT_XBTEUR=5.0
K_STOP_SELL_XBTEUR=3.0
MIN_ALLOCATION_XBTEUR=0.5
```

## 🎮 Usage

### Start the Bot

```bash
python main.py
```

The bot will start monitoring the configured pairs and execute operations according to the selected strategy.

### Telegram Commands

Once started, you can control the bot from Telegram:

- `/status` - Bot status and configured pairs
- `/pause` - Pause bot operations
- `/resume` - Resume operations
- `/market [pair]` - View current market data
- `/positions [pair]` - View open positions
- `/help` - Show help with available commands

**Examples**:
```
/market XBTEUR
/positions
/pause
```

## 🔄 Operation Flow

1. **Monitoring**: The bot queries current prices and ATR at each configured interval
2. **Closed Order Detection**: Identifies executed orders on Kraken
3. **Position Creation**: For each closed order, creates a position with trailing stop
4. **Activation**: When the price reaches the activation level, the trailing stop is activated
5. **Trailing**: The stop adjusts dynamically following the favorable price
6. **Closure**: When the price reaches the stop, the closing order is executed
7. **Recalibration**: ATR is recalculated periodically to adjust stops to current volatility

### Risk Management

- **Inventory Protection**: Prevents sells that reduce the asset below the configured minimum
- **Position Consolidation**: Automatically merges similar nearby positions
- **Dynamic Recalibration**: Adjusts stops when ATR varies more than ±20%

## 📊 Strategies in Detail

### Example: Multipliers Strategy

Assuming:
- BTC Price: €50,000
- Current ATR: €1,000
- K_ACT: 4.5
- K_STOP: 2.5
- MIN_MARGIN: 1%

**Buy executed at €50,000**:
- New position: SELL (opposite)
- Activation: 50,000 + (4.5 × 1,000) = €54,500
- When price ≥ €54,500:
  - Trailing active
  - Initial stop: 54,500 - (2.5 × 1,000) = €52,000
  - Guaranteed margin: €500 (1% of €50,000)

If price rises to €56,000:
- New trailing: €56,000
- New stop: 56,000 - 2,500 = €53,500 (limited by minimum margin)

## 🗂️ Data Structure

### Position State

The bot maintains a `data/trailing_state.json` file with information about all positions:

```json
{
  "XBTEUR": {
    "ORDER_ID": {
      "mode": "rebuy",
      "created_time": "2025-12-15 10:30:00",
      "opening_order": ["ORDER_ID"],
      "side": "sell",
      "entry_price": 50000.0,
      "volume": 0.1,
      "cost": 5000.0,
      "activation_atr": 1000.0,
      "activation_price": 54500.0,
      "activation_time": "2025-12-15 11:00:00",
      "trailing_price": 56000.0,
      "stop_atr": 1000.0,
      "stop_price": 53500.0
    }
  }
}
```

### Closed Positions

Closed positions are saved in `data/closed_positions.json` with complete information about PnL and associated orders.

## 🚦 Deployment

The repository includes a GitHub Actions configuration (`.github/workflows/deploy.yml`) for automatic deployment via SSH. The workflow runs automatically when pushing to the `main` branch.

### Secrets Configuration

To enable automatic deployment, configure these secrets in GitHub:

- `VM_IP`: Server IP address
- `VM_USER`: SSH user
- `VM_KEY`: SSH private key

## 📝 Logs and Monitoring

- Logs are stored in `logs/`
- Each important operation is logged and notified via Telegram
- Distinctive emojis for each event type:
  - 🆕 New position created
  - 🔀 Positions merged
  - ⚡ Trailing stop activated
  - 📈 Trailing price updated
  - ♻️ ATR recalibration
  - ⛔ Position closed
  - 💸 PnL result
  - 🛡️ Operation blocked by protection

## 🔒 Security

- **Never** share your `.env` or upload it to GitHub (it's in `.gitignore`)
- Use limited Kraken API permissions (trading only, no withdrawals)
- Keep your ALLOWED_USER_ID private to prevent unauthorized access to the Telegram bot
- Regularly review logs to detect anomalous behavior

## 🤝 Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This software is provided "as is", without warranties of any kind. Cryptocurrency trading carries significant risks and you may lose your investment. Use this bot at your own risk and consider starting with small amounts to test the system.

**We are not responsible for financial losses resulting from the use of this software.**

## 📄 License

This project is open source and available under the MIT license.

## 👤 Author

**jAjiz**

- GitHub: [@jAjiz](https://github.com/jAjiz)

## 🙏 Acknowledgments

- [Kraken](https://www.kraken.com/) - Cryptocurrency exchange
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram library
- [krakenex](https://github.com/veox/python3-krakenex) - Kraken API client

---

**⭐ If you find this project useful, consider giving it a star on GitHub!**
