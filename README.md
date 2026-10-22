# ⚔️ Albion Multi Tool — Open-Source Albion Online Economy Discord Bot

**Albion Multi Tool** is an open-source, AI-assisted Discord bot built for **Albion Online** refiners, crafters, traders, island managers, and guild officers. It integrates real-time market orders and historical price data from [**The Albion Online Data Project (AODP)**](https://www.albion-online-data.com/) across all three official servers (**Europe**, **Americas/West**, and **Asia/East**).

> **AI Open-Source Disclosure:** This repository was designed, architected, and developed as an AI-assisted open-source tool for the Albion Online community. Feel free to fork, customize, and self-host it for your own guild or trading server.

## ✨ Key Features

* **🌍 Per-User Server Memory (`/set_server`):** Each Discord user can save their preferred server (`Europe`, `Americas`, or `Asia`) once, and all subsequent commands automatically query that server.

* **🪙 Live Gold Exchange Rate (`/gold`):** Fetches real-time Gold/Silver prices, 24-hour trends, highs/lows, and instant Silver conversions for 500, 3,000 (30-Day Premium), and 10,000 Gold bundles.

* **🏪 Cross-City Market Orders & Bargain Detector (`/price`):** Displays live minimum Sell Orders and maximum Buy Orders across Bridgewatch, Fort Sterling, Lymhurst, Martlock, Thetford, Caerleon, Brecilien, and the Black Market. Automatically flags items selling **25%+ below** their historical market average.

* **⚗️ Refining Profit & Focus Calculator (`/refine`):** Automatically applies the permanent **+40% Royal City refining bonus** (or **Personal Island 0% station fee** mode), computes exact **Resource Return Rate (RRR)**, station nutrition fees, market taxes, net profit, ROI, and **Silver Per Focus (SPF)** based on your Mastery and Specialization levels.

* **🔨 Equipment Crafting Calculator (`/craft`):** Built-in mapping for all permanent **+15% Royal City, Caerleon, and Brecilien crafting bonuses**, Personal Island mode, non-returnable Artifact/Heart/Crest costs, and Crafting Journal profit contributions.

* **🏝️ Personal Island Farming & Laborer Calculator (`/island`):** Calculates daily and 30-day projected net profit for island crop/herb plots (with or without Focus watering and +10% local city yield bonus) alongside **Island Laborer** journal turn-ins.

* **⚔️ Criteria-Based Guild Loot Split (`/lootsplit`):** Supports three customizable rule presets (**Equal Split**, **Role-Weighted Split** for Shotcallers/Tanks/Healers/Scouts, and **Repair & Regear Priority**) while exempting raw silver bags from market sales taxes.

* **🚚 Cross-City & Black Market Flipper (`/arbitrage`):** Scans all cities to find the cheapest buy location and ranks the most profitable transport routes via Sell Orders (6.5% tax) or instant Buy Orders / Black Market (4% tax).

* **🔔 Automated 25%–30%+ Price Drop Alerts (`/alert_add`, `/alert_list`, `/alert_remove`):** Background task checks AODP prices every 10 minutes and pings you in Discord whenever a watched item drops below its historical average price by your target percentage.

## 📋 Slash Commands Overview

| Command | Description | 
| ----- | ----- | 
| `/set_server` | Save your personal default Albion server (`Europe`, `Americas`, or `Asia`). | 
| `/gold` | View live Gold/Silver exchange rate, 24h change, and bundle conversions. | 
| `/price` | Check live Buy & Sell orders across all cities and Black Market with bargain detection. | 
| `/refine` | Calculate Refining profit, permanent city/island RRR, and Silver Per Focus (SPF). | 
| `/craft` | Calculate Crafting profit with permanent +15% city bonuses, Island mode & Journals. | 
| `/island` | Calculate daily Island Farming (Crops/Herbs) and Island Laborer Journal profit. | 
| `/lootsplit` | Calculate Guild Loot Split using preset criteria (`Equal`, `Role-Weighted`, `Repair Priority`). | 
| `/arbitrage` | Find profitable cross-city and Black Market flipping routes for any item. | 
| `/alert_add` | Get notified when an item drops 25%–30%+ below its average market price. | 
| `/alert_list` | View all active market price drop alerts registered by you. | 
| `/alert_remove` | Remove a specific item (or `all`) from your active price drop alerts. | 

## 🧮 Economic Formulas Used

1. **Resource Return Rate (RRR):**
   All production bonuses stack additively before converting through:
   

   $$
   \text{RRR} = \frac{\text{Total Bonus}}{1 + \text{Total Bonus}}
   $$

   * **City Base Bonus:** $+18\%$ ($\approx 15.25\%$ RRR)

   * **Refining Bonus City Specialty:** $+40\%$ ($36.71\%$ RRR unfocused, $53.92\%$ RRR with $+59\%$ Focus)

   * **Crafting Bonus City Specialty:** $+15\%$ ($24.81\%$ RRR unfocused, $47.92\%$ RRR with $+59\%$ Focus)

   * **Personal Island Station:** $0\%$ City Base, $0$ Silver station fee ($37.11\%$ RRR with $+59\%$ Focus)

2. **Focus Cost Efficiency (FCE):**
   Specialization levels reduce Focus consumption rather than raising the RRR cap. Every $10,000\text{ FCE}$ halves the Focus cost:
   

   $$
   \text{Focus Cost} = \frac{\text{Base Focus}}{2^{\text{Total FCE} / 10000}}
   $$

3. **Crafting Station Usage Fee:**
   

   $$
   \text{Nutrition Consumed} = \text{Item Value} \times 0.1125 \times \text{Quantity}
   $$

   $$
   \text{Station Fee} = \frac{\text{Nutrition Consumed} \times \text{Station Rate}}{100}
   $$

## 🚀 Installation & Self-Hosting Guide

### 1. Prerequisites

* **Python 3.10** or newer installed on your machine.

* A Discord Bot application created in the [Discord Developer Portal](https://discord.com/developers/applications).

### 2. Install Dependencies

```
pip install -U discord.py aiohttp python-dotenv

```

### 3. Configure Your Bot Token

Create a file named `.env` in the same folder as `albion_multi_tool_bot.py` and add your bot token:

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here

```

*(Security Warning: Never share your `.env` file or commit your `DISCORD_BOT_TOKEN` to GitHub!)*

### 4. Invite the Bot to Your Server

In the [Discord Developer Portal](https://discord.com/developers/applications), open **OAuth2 -> URL Generator**:

1. Check **both** `bot` and `applications.commands` under **Scopes**.

2. Check `Send Messages`, `Embed Links`, and `Use Slash Commands` under **Bot Permissions**.

3. Open the generated URL in your browser and authorize the bot into your Discord server.

### 5. Run the Bot

```
python albion_multi_tool_bot.py

```

On startup, the bot automatically performs an **Instant Guild Sync** so all 11 `/` slash commands appear immediately in your Discord server.

## 📄 License

This project is open-source and available under the **MIT License**. Market data is provided by [The Albion Online Data Project](https://www.albion-online-data.com/) and item icons are provided by Sandbox Interactive's official Render API.