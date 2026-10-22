# ⚔️ Albion Multi Tool v3.0 — Open-Source Albion Online Economy Discord Bot

**Albion Multi Tool** is an open-source, AI-assisted Discord bot built for **Albion Online** refiners, crafters, traders, island managers, and guild officers. It integrates real-time market orders and historical price data from [**The Albion Online Data Project (AODP)**](https://www.albion-online-data.com/) across all three official servers (**Europe**, **Americas/West**, and **Asia/East**).

> **AI Open-Source Disclosure:** This repository was designed, architected, and developed as an AI-assisted open-source tool for the Albion Online community. Feel free to fork, customize, and self-host it for your own guild or trading server.

## ✨ What's New in v3.0 (Competitor Parity & Modern Discord UI/UX)

* **📊 Multi-Tier Refining Matrix Scanner (`/refine_matrix`):** Inspired by top web tools like Refinestation and Albion Free Market, scans all **16 Tier/Enchantment combinations (`T4.0` through `T8.3`)** in a single command and ranks the best tiers both **With Focus (by SPF)** and **Without Focus (by Net Profit)**.

* **✨ Artifact Foundry Enchanting Flipper (`/enchant_flip`):** Calculates exact profit margins for upgrading `.0` equipment to `.1` (Runes), `.2` (Souls), and `.3` (Relics) using live market prices (`384` mats for 2H weapons, `288` for 1H, `192` for Armor/Bags, `96` for Head/Shoes/Capes/Off-hands).

* **⚖️ Dual SPF & Side-by-Side Focus Comparison (`/refine`):** Displays both **Total Batch SPF (`Net Profit / Focus`)** and **Marginal Focus Gain (`(Focused Profit - Unfocused Profit) / Focus`)**, plus selectable **Tax Modes** (Premium 6.5%, Instant Sell 4%, Non-Premium 10.5%, Direct Trade 0%).

* **🎛️ Interactive Discord UI Components (`discord.ui.View`):** Includes interactive **Quality Switcher Dropdowns (`Normal` to `Masterpiece`)**, **Refresh Buttons**, **One-Click Watchlist Buttons** on `/price`, and an interactive **Category Dashboard** on `/help`.

* **⌨️ Real-Time Item Autocomplete & ANSI Visuals:** Suggests item names as you type in `/price`, `/arbitrage`, `/enchant_flip`, and `/alert_add`, and renders **ANSI color-coded profit blocks** and **24h Unicode Sparkline charts (`▁▂▃▄▅▆▇█`)**.

## 📋 Slash Commands Overview (14 Commands)

| Command | Description | 
| ----- | ----- | 
| `/help` | Open the interactive Albion Multi Tool command guide and feature dashboard. | 
| `/set_server` | Save your personal default Albion server (`Europe`, `Americas`, or `Asia`). | 
| `/gold` | View live Gold/Silver exchange rate, 24h Unicode sparkline chart, and bundle conversions. | 
| `/price` | Check live Buy & Sell orders across all cities with interactive Quality switcher & Bargain Detector. | 
| `/refine` | Calculate Refining profit, permanent city/island RRR, Dual SPF, and Focus vs. No-Focus comparison. | 
| `/refine_matrix` | Scan all 16 `T4.0–T8.3` refining tiers at once and rank the top money-makers by SPF & Net Profit. | 
| `/enchant_flip` | Calculate profit from enchanting equipment (`.0 ➔ .1/.2/.3`) with Runes, Souls, and Relics. | 
| `/craft` | Calculate Crafting profit with permanent +15% city bonuses, Island mode & Crafting Journals. | 
| `/island` | Calculate daily Island Farming (Crops/Herbs) and Island Laborer Journal profit. | 
| `/lootsplit` | Calculate Guild Loot Split using preset criteria (`Equal`, `Role-Weighted`, `Repair Priority`). | 
| `/arbitrage` | Find profitable cross-city and Black Market flipping routes for any item. | 
| `/alert_add` | Get notified automatically when an item drops 25%–30%+ below its average market price. | 
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

2. **Focus Cost Efficiency (FCE) & Dual SPF:**
   Specialization levels reduce Focus consumption rather than raising the RRR cap. Every $10,000\text{ FCE}$ halves the Focus cost:
   

   $$
   \text{Focus Cost} = \frac{\text{Base Focus}}{2^{\text{Total FCE} / 10000}}
   $$

   * **Total SPF:** $\text{Focused Net Profit} / \text{Focus Used}$

   * **Marginal SPF:** $(\text{Focused Net Profit} - \text{Unfocused Net Profit}) / \text{Focus Used}$

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

### 4. Run the Bot

```
python albion_multi_tool_bot.py

```

On startup, the bot automatically performs an **Instant Guild Sync** so all 14 `/` slash commands appear immediately in your Discord server.

## 📄 License

This project is open-source and available under the **MIT License**. Market data is provided by [The Albion Online Data Project](https://www.albion-online-data.com/) and item icons are provided by Sandbox Interactive's official Render API.