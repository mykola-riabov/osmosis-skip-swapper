#!/usr/bin/python3
import argparse
import json
import requests
import subprocess
import logging
import re
from pathlib import Path

# Load configuration
CONFIG_PATH = Path("/home/your_path/config_skiptrade.json")
CONFIG_BOT_USER_PATH = Path("/home/your_path/config_bot_user.json")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

with open(CONFIG_BOT_USER_PATH, "r") as f:
    bot_config = json.load(f)

ASSETS_PATH = Path(config["assets_config_path"])
CMD_TEXT_PATH = Path(config["command_output_path"])
LOG_FILE_PATH = Path(config["log_file_path"])

CHAIN_ID = config["chain_id"]
DEFAULT_GAS_ADJUSTMENT = config["gas_adjustment"]
DEFAULT_FEES = config["fees"]
GAS_TOKEN = config["gas_token"]
ACCOUNT_NAME = config["account_name"]
ACCOUNT_PASSWORD = config["account_password"]
ACCOUNT_ADDRESS = config["account_address"]
DEFAULT_SLIPPAGE_PERCENT = config.get("slippage_percent", 1.5)

BOT_USERNAME = config["telegram_bot_username"]
USERNAMES = config["telegram_usernames"]

# Functions to load bot token and user IDs
def get_bot_token(bot_list, bot_username):
    for bot in bot_list:
        if bot["username"] == bot_username:
            return bot["token"]
    raise ValueError(f"Bot {bot_username} not found")

def get_user_id(user_list, username):
    for user in user_list:
        if user["username"] == username:
            return user["id"]
    raise ValueError(f"User {username} not found")

BOT_TOKEN = get_bot_token(bot_config["bots"], BOT_USERNAME)
RECIPIENTS = [get_user_id(bot_config["users"], username) for username in USERNAMES]

SKIP_API_URL = "https://api.skip.build/v2/fungible/route"

# Logging setup
MAX_LOG_SIZE = 10 * 1024 * 1024
if LOG_FILE_PATH.exists() and LOG_FILE_PATH.stat().st_size > MAX_LOG_SIZE:
    LOG_FILE_PATH.unlink()

logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# Telegram message sender
def send_telegram_message(message):
    for chat_id in RECIPIENTS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload)
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")

# Token mapping loader
def load_token_mapping():
    with open(ASSETS_PATH, "r") as f:
        data = json.load(f)

    token_to_denom = {}
    denom_to_token = {}
    denom_to_divisor = {}

    for pool in data.values():
        t1 = pool["token_name_1"].upper()
        t2 = pool["token_name_2"].upper()
        d1 = pool["denom_1"]
        d2 = pool["denom_2"]
        div1 = pool["divisor_denom_1"]
        div2 = pool["divisor_denom_2"]

        token_to_denom[t1] = d1
        token_to_denom[t2] = d2
        denom_to_token[d1] = t1
        denom_to_token[d2] = t2
        denom_to_divisor[d1] = div1
        denom_to_divisor[d2] = div2

    return token_to_denom, denom_to_token, denom_to_divisor

# Convert display units to base units
def to_base_units(amount_display, divisor):
    return str(int(amount_display * divisor))

# Convert base units to display units
def to_display_units(amount_base, divisor):
    return float(amount_base) / divisor

# Request route from Skip API
def get_skip_route(data):
    try:
        response = requests.post(SKIP_API_URL, headers={"Content-Type": "application/json"}, json=data)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Skip API error: {e}")
        logging.error(f"Skip API error: {e}")
        return None
# Execute osmosisd command
def execute_command(command, password, dry_run_mode):
    if dry_run_mode:
        print(f"\n📋 Osmosisd command:\n{command}\n")
        with open(CMD_TEXT_PATH, "w") as f:
            f.write(command + "\n")
        logging.info("Dry-run mode: command saved and printed.")
        return None, None

    print(f"\n📋 Executing osmosisd command:\n{command}\n")
    with open(CMD_TEXT_PATH, "w") as f:
        f.write(command + "\n")

    try:
        result = subprocess.run(command, input=password + "\n", capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"❌ Command failed:\n{result.stderr}")
            logging.error(f"Command execution failed: {result.stderr.strip()}")
            return None, None

        txhash_match = re.search(r"txhash:\s*([A-F0-9]+)", result.stdout)
        if txhash_match:
            txhash = txhash_match.group(1)
            print(f"🔗 Transaction Hash: {txhash}")
            logging.info(f"Transaction Hash: {txhash}")
            return txhash, result.stdout
        else:
            logging.warning("Transaction hash not found in output.")
            return None, result.stdout

    except Exception as e:
        print(f"❌ Execution error: {e}")
        logging.error(f"Execution error: {e}")
        return None, None
def main():
    parser = argparse.ArgumentParser(description="Skip Protocol swap executor for Osmosis")
    parser.add_argument("--from", dest="token_from", required=True)
    parser.add_argument("--to", dest="token_to", required=True)
    parser.add_argument("--amount", type=float, required=True)
    parser.add_argument("--split", action="store_true")
    parser.add_argument("--only-osmosis", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--gas-adjustment", type=float)
    parser.add_argument("--fees", type=int)
    parser.add_argument("--slippage-percent", type=float)
    parser.add_argument("--pre-check", action="store_true")
    args = parser.parse_args()

    token_map, denom_to_token, divisors = load_token_mapping()

    token_from = args.token_from.upper()
    token_to = args.token_to.upper()
    amount_display = args.amount

    gas_adjustment = args.gas_adjustment if args.gas_adjustment is not None else DEFAULT_GAS_ADJUSTMENT
    fees = args.fees if args.fees is not None else DEFAULT_FEES
    slippage_percent = args.slippage_percent if args.slippage_percent is not None else DEFAULT_SLIPPAGE_PERCENT

    if token_from not in token_map or token_to not in token_map:
        print(f"❌ Unknown token: {token_from} or {token_to}")
        logging.error(f"Unknown token: {token_from} or {token_to}")
        return

    denom_from = token_map[token_from]
    denom_to = token_map[token_to]
    divisor_from = divisors[denom_from]
    divisor_to = divisors[denom_to]
    amount_in_base = to_base_units(amount_display, divisor_from)

    payload = {
        "amount_in": amount_in_base,
        "source_asset_denom": denom_from,
        "source_asset_chain_id": CHAIN_ID,
        "dest_asset_denom": denom_to,
        "dest_asset_chain_id": CHAIN_ID,
        "cumulative_affiliate_fee_bps": "0",
        "allow_multi_tx": False,
        "allow_unsafe": True,
        "smart_swap_options": {"split_routes": args.split}
    }

    if args.only_osmosis:
        payload["swap_venues"] = [{"chain_id": CHAIN_ID, "name": "osmosis-poolmanager"}]

    result = get_skip_route(payload)
    if not result:
        print(f"❌ No route found from {token_from} to {token_to}")
        logging.error(f"No route found from {token_from} to {token_to}")
        return

    estimated_out_display = to_display_units(int(result["estimated_amount_out"]), divisor_to)

    print(f"\n✅ Optimal route from {token_from} to {token_to}")
    print(f"   Input: {amount_display} {token_from}")
    print(f"   Estimated output: {estimated_out_display:.6f} {token_to}")

    if args.pre_check:
        slippage_factor = 1.0 - (slippage_percent / 100)
        minimum_acceptable_output = int(result["estimated_amount_out"]) * slippage_factor
        if int(result["estimated_amount_out"]) < minimum_acceptable_output:
            print(f"\n❌ Pre-check failed: Estimated output too low.")
            logging.warning(f"Pre-check failed: {token_from} -> {token_to}")
            return

    for op in result.get("operations", []):
        swap_obj = op.get("swap", {}).get("swap_in") or op.get("swap", {}).get("smart_swap_in")
        if not swap_obj or "swap_operations" not in swap_obj:
            continue

        pool_ids = [str(hop["pool"]) for hop in swap_obj["swap_operations"]]
        token_in_denom = swap_obj["swap_operations"][0]["denom_in"]
        token_in_amount = amount_in_base

        slippage_factor = 1.0 - (slippage_percent / 100)
        token_out_min = str(int(int(result["estimated_amount_out"]) * slippage_factor))

        from_value = ACCOUNT_ADDRESS if args.dry_run else ACCOUNT_NAME

        command = (
            f"osmosisd tx gamm swap-exact-amount-in "
            f"{token_in_amount}{token_in_denom} {token_out_min} "
            f"--swap-route-pool-ids {','.join(pool_ids)} "
            f"--swap-route-denoms {','.join(hop['denom_out'] for hop in swap_obj['swap_operations'])} "
            f"--from {from_value} --chain-id {CHAIN_ID} "
            f"--gas auto --gas-adjustment {gas_adjustment} "
            f"--fees {fees}{GAS_TOKEN} -y"
        )

        print(f"\n📊 Pools in route: {' -> '.join(pool_ids)}")
        
        txhash, _ = execute_command(command, ACCOUNT_PASSWORD, args.dry_run)

        if txhash:
            msg = (
                f"✅ *Swap Executed!*\n\n"
                f"🔹 *From:* `{token_from}`\n"
                f"🔹 *To:* `{token_to}`\n"
                f"🔹 *Amount IN:* `{amount_display} {token_from}`\n"
                f"🔹 *Amount OUT:* `{estimated_out_display:.6f} {token_to}`\n"
                f"🔹 *Pools:* `{','.join(pool_ids)}`\n"
                f"🔹 *Sender:* `{ACCOUNT_ADDRESS}`\n"
                f"🔹 *TxHash:* `{txhash}`"
            )
            send_telegram_message(msg)

        break

if __name__ == "__main__":
    main()
