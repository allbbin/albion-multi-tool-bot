# ⚔️ Albion Multi Tool v4.0 — Open-Source Albion Online Economy, Island & Guild Discord Bot






**Albion Multi Tool** is an open-source, AI-assisted Discord bot built for **Albion Online** refiners, crafters, chefs, alchemists, Black Market flippers, island managers, and guild officers. It integrates real-time market orders from **[The Albion Online Data Project (AODP)](https://www.albion-online-data.com/)** and the full in-game item catalog (`ao-bin-dumps`) across all three official servers (**Europe**, **Americas/West**, and **Asia/East**).

> **AI Open-Source Disclosure:** This repository was designed, architected, and developed as an AI-assisted open-source tool for the Albion Online community. Feel free to fork, customize, and self-host it for your own guild or trading server.

## ✨ Key Features & v4.0 Highlights

* **🌐 Universal In-Game Item Resolver (`/price`, `/arbitrage`, `/enchant_flip`):** Automatically downloads and caches the official `ao-bin-dumps` catalog (12,000+ items) on startup alongside a built-in dictionary. Enter **any valid Albion item name** plus clean `tier_enchant` (e.g., `6.1`, `4.2`, `8.0`) and `quality` parameters without intrusive popup suggestions.
* **🕵️‍♂️ Bulk Black Market Category Scanner (`/bmsc`):** Scans an entire equipment category (`Bags & Capes`, `Swords & Axes`, `Bows/Daggers/Crossbows`, `Magic Staffs`, `Cloth/Leather/Plate Armor`) across all Tiers (`T4–T8`) and Enchantments (`.0–.2`) in one click, ranking the highest-profit flips into the **Caerleon Black Market**.
* **⚗️ T3 to T8 Refining, Crafting, Enchanting & Kitchen (`/refine`, `/craft`, `/enchant_flip`, `/kitchen`):**
  * **T3–T8 Refining (`/refine`):** Supports Tier 3 (`2x T3 Raw + 1x T2 Refined`) through Tier 8.4 with permanent **+40% Royal City bonus**, Island mode, Focus vs. No-Focus comparison, and Dual SPF.
  * **Artifact Foundry Enchanting (`/enchant_flip`):** Calculates `.0 ➔ .1` (Runes), `.1 ➔ .2` (Souls), and `.2 ➔ .3` (Relics) upgrade profit margins.
  * **Cooking & Alchemy (`/kitchen`):** Live ingredient & output profit calculator for Caerleon Food (+15%, 10x output) and Brecilien Potions (+15%, 5x output).
* **🏝️ Detailed Island Farming & Laborer Journal Engine (`/island`):** Calculates daily, 7-day, and 30-day profit for Farm/Herb/Pasture plots (with/without Focus and +10% city bonus) AND **Island Laborers** (factoring in Laborer Happiness yield multiplier e.g. `150%`, Empty vs. Full Journal cost, and 6.5% market tax).
* **🏦 Criteria-Based Guild Loot Split & Silver Balance Ledger (`/lootsplit`, `/balance`, `/balance_manage`):** Split guild loot using `Equal`, `Role-Weighted`, or `Repair Priority` presets, credit payouts directly to tagged `@members`' Silver balances with a single button click, and track unpaid guild payouts.
* **🕒 24/7 Cloud Hosting Ready:** Includes an optional built-in HTTP health-check server (`ENABLE_KEEP_ALIVE=true` or `PORT=8080`) for 24/7 cloud hosting on Render, Koyeb, Fly.io, Oracle Cloud, or UptimeRobot.

## 📋 Slash Commands Overview (13 Commands)

| Command | Category | Description |
| :--- | :--- | :--- |
| `/help` | General | Open the interactive command guide featuring highlights from all 4 categories. |
| `/set_server` | Market | Save your personal default Albion server (`Europe`, `Americas`, or `Asia`). |
| `/gold` | Market | View live Gold/Silver exchange rate, 24h Unicode sparkline chart, and bundle conversions. |
| `/price` | Market | Check live Buy & Sell orders for **any in-game item** (`item` + `tier_enchant` + `quality`). |
| `/bmsc` | Market | Bulk-scan an entire equipment category across all cities to find top **Black Market** flips. |
| `/arbitrage` | Market | Find profitable cross-city and Black Market flipping routes for any single item. |
| `/refine` | Crafting | Calculate **T3–T8** Refining profit, permanent city/island RRR, Dual SPF & Focus comparison. |
| `/craft` | Crafting | Calculate Crafting profit with permanent +15% city bonuses, Island mode & Crafting Journals. |
| `/enchant_flip` | Crafting | Calculate profit from enchanting equipment (`.0 ➔ .1/.2/.3`) with Runes, Souls, and Relics. |
| `/kitchen` | Crafting | Calculate Cooking (Food in Caerleon +15%) and Alchemy (Potions in Brecilien +15%) profit & SPF. |
| `/island` | Island | Detailed Island Farming (Crops/Herbs/Pastures) & **Laborer Journal** profit calculator. |
| `/lootsplit` | Guild | Calculate Guild Loot Split by criteria and credit payouts to member Silver balances. |
| `/balance` | Guild | Check your own or another `@member`'s accumulated Guild Silver balance. |
| `/balance_manage` | Guild | Add silver, record in-game payouts (`payout`), clear balances, or view the Server Leaderboard. |

## 🚀 Installation & 24/7 Hosting Guide

### 1. Local Setup
```bash
pip install -U discord.py aiohttp python-dotenv
```
Create a `.env` file in the root directory:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```
Run the bot:
```bash
python albion_multi_tool_bot.py
```

### 2. Running 24/7 (Cloud VPS or PaaS)
* **Cloud PaaS (Render / Koyeb / Fly.io):** Set environment variables `DISCORD_BOT_TOKEN` and `ENABLE_KEEP_ALIVE=true` (or `PORT=8080`). The bot automatically starts a lightweight HTTP health server at `/health` so web-service monitors keep it alive 24/7.
* **Linux VPS (Oracle Cloud / Ubuntu) with `systemd` or `pm2`:**
  ```bash
  pm2 start albion_multi_tool_bot.py --interpreter python3 --name albion-bot
  pm2 save
  ```

## 📄 License

This project is open-source and available under the **MIT License**. Market data is provided by [The Albion Online Data Project](https://www.albion-online-data.com/).