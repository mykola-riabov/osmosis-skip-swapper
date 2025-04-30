
# SkipTrade Bot for Osmosis

This project is a bot for automating token swaps on the Osmosis DEX via the Skip Protocol.

## What the script does

- Finds the optimal swap route for tokens via the [Skip Protocol API](https://docs.skip.build/go/general/getting-started).
- Builds a ready-to-use command for the `osmosisd` client.
- Executes the swap automatically or saves the command to a file.
- Sends a notification to Telegram about the transaction result.
- Supports `dry-run` mode (command construction without execution) and `pre-check` (minimum output validation).

## Requirements

- Installed and configured **`osmosisd`** client (Osmosis node running in **client mode**, no validator required).  
  👉 Setup guide available in the [official Osmosis documentation](https://docs.osmosis.zone/osmosis-core/osmosisd).
- An Osmosis account with a configured wallet (`osmosisd keys add your_wallet_name`).
- Telegram bot tokens and user IDs obtained via [BotFather](https://t.me/BotFather) and Telegram API commands.
- Python 3.8+.
- Installed Python packages: `requests`, `argparse`.

## Installation

1. Install and configure the Osmosis client (`osmosisd`) following the [official documentation](https://docs.osmosis.zone/osmosis-core/osmosisd).
2. Clone the repository:
   ```bash
   git clone https://github.com/your_username/skiptrade-bot.git
   cd skiptrade-bot
   ```
3. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure the following files:
   - `config_skiptrade.json`
   - `config_bot_user.json`
   - `assets_config.json`
5. Ensure all paths and settings are properly set.

## Configuration files explained

| File                    | Purpose |
|:------------------------|:--------|
| **config_skiptrade.json** | Main configuration file. Contains paths to other files, Osmosis account data (`account_name`, `account_address`, `account_password`), fee and slippage settings, and Telegram bot setup. |
| **config_bot_user.json** | Telegram bot and user settings. Lists Telegram bots (`username`, `token`) and users (`username`, `id`) for swap notifications. |
| **assets_config.json**    | List of token pools on Osmosis. Defines token pairs, their `denoms`, pool addresses, and divisors for correct base unit calculations. Used for building swap commands. |

## Usage

Basic swap execution:

```bash
python3 skiptrade.py --from ATOM --to OSMO --amount 10
```

Supported arguments:

| Argument               | Description |
|:-----------------------|:------------|
| `--from`                | Token name to swap from (e.g., ATOM). |
| `--to`                  | Token name to swap to (e.g., OSMO). |
| `--amount`              | Amount of tokens to swap. |
| `--split`               | Allow using split routes with multiple pools. |
| `--only-osmosis`        | Restrict routing to Osmosis pools only. |
| `--dry-run`             | Build and save the command without executing it. |
| `--gas-adjustment`      | Custom gas adjustment factor. |
| `--fees`                | Custom fee amount. |
| `--slippage-percent`    | Acceptable slippage percentage. |
| `--pre-check`           | Verify minimum acceptable output before executing. |

### Examples

1. Swap 10 ATOM to OSMO:
   ```bash
   python3 skiptrade.py --from ATOM --to OSMO --amount 10
   ```

2. Save the command to a file without executing:
   ```bash
   python3 skiptrade.py --from ATOM --to OSMO --amount 10 --dry-run
   ```

3. Pre-check minimum output before swapping:
   ```bash
   python3 skiptrade.py --from ATOM --to OSMO --amount 10 --pre-check
   ```

## Project extension possibilities

The project is built modularly and can be easily adapted for additional automated tasks, such as:

- Automatic market making on Osmosis pools.
- Automated arbitrage trading between different DEX platforms.
- Scheduled or conditional swap execution (e.g., at specific times or price conditions).
- Portfolio rebalancing scripts to maintain token ratios.
- Liquidity monitoring and notification bots.

## Important notes

- You must deploy and synchronize an **Osmosis node in client mode** before using the script.
- Telegram bot tokens and user IDs must be obtained and configured beforehand.
- All file paths must be correctly set in `config_skiptrade.json`.
- Your Osmosis wallet must be unlocked and able to sign transactions.
- The Telegram bot is used **only** for sending notifications and does **not** have access to your wallet.

---
