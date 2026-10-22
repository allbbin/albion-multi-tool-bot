"""
============================================================================================
ALBION MULTI TOOL — Open-Source Albion Online Economy, Crafting, Island & Guild Discord Bot
============================================================================================
Notice       : This project is an AI-generated / AI-assisted open-source Discord bot built
               for the Albion Online community. Released under the MIT License.
Data Sources : The Albion Online Data Project (AODP) REST API v2 & Official Albion Render API
Servers      : Europe (EU), Americas (West), Asia (East)
Dependencies : discord.py >= 2.3.0, aiohttp >= 3.9.0, python-dotenv >= 1.0.0

Quick Setup:
1. pip install -U discord.py aiohttp python-dotenv
2. Create a `.env` file in the project root with: DISCORD_BOT_TOKEN=your_secret_token_here
   (NEVER commit your `.env` file or token to GitHub!)
3. Run: python albion_multi_tool_bot.py
============================================================================================
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    # Load standard .env first; also support .env.txt on Windows if Notepad added a .txt extension
    load_dotenv(BASE_DIR / ".env")
    if not os.getenv("DISCORD_BOT_TOKEN") and (BASE_DIR / ".env.txt").exists():
        load_dotenv(BASE_DIR / ".env.txt")
except ImportError:
    pass


def load_bot_token() -> Optional[str]:
    """
    Reads DISCORD_BOT_TOKEN from environment variables, `.env`, or `.env.txt`
    (in case Windows Notepad saved `.env` as `.env.txt`).
    """
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        return token.strip().strip('"').strip("'")

    for candidate in (BASE_DIR / ".env", BASE_DIR / ".env.txt"):
        if candidate.exists():
            try:
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("DISCORD_BOT_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return None


# ============================================================================
# 1. CONSTANTS, SERVER ENDPOINTS & PERMANENT CITY BONUS DATABASE
# ============================================================================

AODP_SERVERS: Dict[str, str] = {
    "eu": "https://europe.albion-online-data.com",
    "west": "https://west.albion-online-data.com",
    "east": "https://east.albion-online-data.com",
}

SERVER_LABELS: Dict[str, str] = {
    "eu": "🌍 Europe (EU)",
    "west": "🌎 Americas (West)",
    "east": "🌏 Asia (East)",
}

DEFAULT_LOCATIONS: List[str] = [
    "Bridgewatch",
    "Fort Sterling",
    "Lymhurst",
    "Martlock",
    "Thetford",
    "Caerleon",
    "Brecilien",
    "Black Market",
]

QUALITY_NAMES: Dict[int, str] = {
    1: "Normal",
    2: "Good",
    3: "Outstanding",
    4: "Excellent",
    5: "Masterpiece",
}

# Permanent Royal City Refining Specialty Bonuses (+40% Production Bonus)
REFINING_BONUS_CITIES: Dict[str, Dict[str, str]] = {
    "ore": {
        "name": "Metal Bar (Ore -> Bar)",
        "raw_key": "ORE",
        "refined_key": "METALBAR",
        "city": "Thetford",
        "bonus": "+40%",
    },
    "fiber": {
        "name": "Cloth (Fiber -> Cloth)",
        "raw_key": "FIBER",
        "refined_key": "CLOTH",
        "city": "Lymhurst",
        "bonus": "+40%",
    },
    "hide": {
        "name": "Leather (Hide -> Leather)",
        "raw_key": "HIDE",
        "refined_key": "LEATHER",
        "city": "Martlock",
        "bonus": "+40%",
    },
    "wood": {
        "name": "Planks (Wood -> Planks)",
        "raw_key": "WOOD",
        "refined_key": "PLANKS",
        "city": "Fort Sterling",
        "bonus": "+40%",
    },
    "rock": {
        "name": "Stone Block (Rock -> Stone Block)",
        "raw_key": "ROCK",
        "refined_key": "STONEBLOCK",
        "city": "Bridgewatch",
        "bonus": "+40%",
    },
}

# Permanent City Crafting Specialty Bonuses (+15% Production Bonus)
CRAFTING_CATEGORY_CITIES: Dict[str, Tuple[str, str]] = {
    "cloth_robe": ("Cloth Robe (Chest)", "Fort Sterling"),
    "plate_helmet": ("Plate Helmet (Head)", "Fort Sterling"),
    "hammer": ("Hammer", "Fort Sterling"),
    "spear": ("Spear", "Fort Sterling"),
    "holy_staff": ("Holy Staff", "Fort Sterling"),
    "sword": ("Sword", "Lymhurst"),
    "bow": ("Bow", "Lymhurst"),
    "arcane_staff": ("Arcane Staff", "Lymhurst"),
    "leather_hood": ("Leather Hood (Head)", "Lymhurst"),
    "leather_shoes": ("Leather Shoes (Feet)", "Lymhurst"),
    "plate_armor": ("Plate Armor (Chest)", "Bridgewatch"),
    "cloth_sandals": ("Cloth Sandals (Feet)", "Bridgewatch"),
    "crossbow": ("Crossbow", "Bridgewatch"),
    "dagger": ("Dagger", "Bridgewatch"),
    "cursed_staff": ("Cursed Staff", "Bridgewatch"),
    "axe": ("Axe", "Martlock"),
    "quarterstaff": ("Quarterstaff", "Martlock"),
    "frost_staff": ("Frost Staff", "Martlock"),
    "plate_boots": ("Plate Boots (Feet)", "Martlock"),
    "offhand": ("Off-Hand (Shield/Tome/Torch/Horn)", "Martlock"),
    "mace": ("Mace", "Thetford"),
    "fire_staff": ("Fire Staff", "Thetford"),
    "nature_staff": ("Nature Staff", "Thetford"),
    "leather_jacket": ("Leather Jacket (Chest)", "Thetford"),
    "cloth_cowl": ("Cloth Cowl (Head)", "Thetford"),
    "war_gloves": ("War Gloves", "Caerleon"),
    "shapeshifter": ("Shapeshifter Staff", "Caerleon"),
    "gathering_gear": ("Gathering Gear & Tools", "Caerleon"),
    "food": ("Cooked Food", "Caerleon"),
    "cape": ("Cape", "Brecilien"),
    "bag": ("Bag", "Brecilien"),
    "potion": ("Potion", "Brecilien"),
}

# Tier-based Refining Recipe Ratios: (Current Tier Raw Qty, Lower Tier Refined Qty)
REFINING_RECIPE_RATIOS: Dict[int, Tuple[int, int]] = {
    2: (1, 0),
    3: (2, 1),
    4: (2, 1),
    5: (3, 1),
    6: (4, 1),
    7: (5, 1),
    8: (5, 1),
}

# Base Refining Focus Cost per unit at 0 Mastery / 0 Spec
BASE_REFINING_FOCUS: Dict[Tuple[int, int], int] = {
    (4, 0): 54,   (4, 1): 94,   (4, 2): 164,  (4, 3): 287,  (4, 4): 503,
    (5, 0): 94,   (5, 1): 164,  (5, 2): 287,  (5, 3): 503,  (5, 4): 880,
    (6, 0): 164,  (6, 1): 287,  (6, 2): 503,  (6, 3): 880,  (6, 4): 1539,
    (7, 0): 287,  (7, 1): 503,  (7, 2): 880,  (7, 3): 1539, (7, 4): 2694,
    (8, 0): 503,  (8, 1): 880,  (8, 2): 1539, (8, 3): 2694, (8, 4): 4714,
}

# Common Item Shortcuts for Natural Language Search
COMMON_ITEM_ALIASES: Dict[str, str] = {
    "bag": "BAG",
    "cape": "CAPE",
    "broadsword": "MAIN_SWORD",
    "claymore": "2H_CLAYMORE",
    "dual swords": "2H_DUALSWORD",
    "dualsword": "2H_DUALSWORD",
    "carving": "2H_CLEAVER_HELL",
    "carving sword": "2H_CLEAVER_HELL",
    "greataxe": "2H_AXE",
    "halberd": "2H_HALBERD",
    "realmbreaker": "2H_AXE_AVALON",
    "bearpaws": "2H_DUALAXE_KEEPER",
    "bow": "2H_BOW",
    "longbow": "2H_LONGBOW",
    "warbow": "2H_WARBOW",
    "badon": "2H_BOW_HELL",
    "mistpiercer": "2H_BOW_AVALON",
    "light crossbow": "MAIN_1HCROSSBOW",
    "boltcaster": "2H_DUALCROSSBOW_HELL",
    "dagger": "MAIN_DAGGER",
    "bloodletter": "MAIN_RAPIER_MORGANA",
    "deathgivers": "2H_DUALSICKLE_UNDEAD",
    "1h spear": "MAIN_SPEAR",
    "spirithunter": "2H_HARPOON_HELL",
    "fire staff": "MAIN_FIRESTAFF",
    "great fire": "2H_FIRESTAFF",
    "blazing": "2H_INFERNOSTAFF_MORGANA",
    "holy staff": "MAIN_HOLYSTAFF",
    "fallen": "2H_HOLYSTAFF_HELL",
    "hallowfall": "MAIN_HOLYSTAFF_AVALON",
    "nature staff": "MAIN_NATURESTAFF",
    "druidic": "MAIN_NATURESTAFF_KEEPER",
    "blight": "2H_NATURESTAFF_HELL",
    "frost staff": "MAIN_FROSTSTAFF",
    "permafrost": "2H_ICECRYSTAL_UNDEAD",
    "chillhowl": "MAIN_FROSTSTAFF_AVALON",
    "cursed staff": "MAIN_CURSEDSTAFF",
    "shadowcaller": "MAIN_CURSEDSTAFF_AVALON",
    "cleric robe": "ARMOR_CLOTH_SET2",
    "mage robe": "ARMOR_CLOTH_SET3",
    "scholar robe": "ARMOR_CLOTH_SET1",
    "mercenary jacket": "ARMOR_LEATHER_SET1",
    "hunter jacket": "ARMOR_LEATHER_SET2",
    "assassin jacket": "ARMOR_LEATHER_SET3",
    "hellion jacket": "ARMOR_LEATHER_HELL",
    "mistwalker jacket": "ARMOR_LEATHER_FEY",
    "soldier armor": "ARMOR_PLATE_SET1",
    "knight armor": "ARMOR_PLATE_SET2",
    "guardian armor": "ARMOR_PLATE_SET3",
    "judicator armor": "ARMOR_PLATE_KEEPER",
    "soldier boots": "SHOES_PLATE_SET1",
    "scholar sandals": "SHOES_CLOTH_SET1",
    "hunter shoes": "SHOES_LEATHER_SET2",
    "guardian helmet": "HEAD_PLATE_SET3",
    "fiend cowl": "HEAD_CLOTH_HELL",
    "mage cowl": "HEAD_CLOTH_SET3",
    "pork omelette": "MEAL_OMELETTE",
    "omelette": "MEAL_OMELETTE",
    "beef stew": "MEAL_STEW",
    "stew": "MEAL_STEW",
    "healing potion": "POTION_HEAL",
    "poison potion": "POTION_COOLDOWN",
    "riding horse": "MOUNT_HORSE",
    "armored horse": "MOUNT_ARMORED_HORSE",
    "stag": "MOUNT_GIANTSTAG",
    "swiftclaw": "MOUNT_COUGAR_KEEPER",
    "direwolf": "MOUNT_DIREWOLF",
    "mammoth": "MOUNT_MAMMOTH_TRANSPORT",
    "ore": "ORE",
    "bar": "METALBAR",
    "metalbar": "METALBAR",
    "hide": "HIDE",
    "leather": "LEATHER",
    "fiber": "FIBER",
    "cloth": "CLOTH",
    "wood": "WOOD",
    "plank": "PLANKS",
    "planks": "PLANKS",
    "rock": "ROCK",
    "stone": "ROCK",
    "stoneblock": "STONEBLOCK",
}

USER_PREFS_FILE = BASE_DIR / "user_preferences.json"
PRICE_ALERTS_FILE = BASE_DIR / "price_alerts.json"


# ============================================================================
# 2. PERSISTENT STORAGE HELPERS (USER SERVER PREFERENCES & PRICE ALERTS)
# ============================================================================

def load_json_file(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user_server(user_id: int, explicit_server: Optional[str] = None) -> str:
    """Returns explicit server if provided; otherwise looks up user's saved default server (fallback: 'eu')."""
    if explicit_server in AODP_SERVERS:
        return explicit_server
    prefs: Dict[str, str] = load_json_file(USER_PREFS_FILE, {})
    return prefs.get(str(user_id), "eu")


def set_user_server(user_id: int, server: str) -> None:
    prefs: Dict[str, str] = load_json_file(USER_PREFS_FILE, {})
    prefs[str(user_id)] = server
    save_json_file(USER_PREFS_FILE, prefs)


# ============================================================================
# 3. CORE MATH & ECONOMY ENGINE (REFINING, CRAFTING, ISLAND, LOOT SPLIT)
# ============================================================================

def calculate_rrr(
    location_mode: str = "bonus_city",
    activity: str = "refining",
    use_focus: bool = False,
) -> Tuple[float, float]:
    """
    Converts Albion Online production bonuses into Resource Return Rate (RRR).
    Formula: RRR = Total_Bonus / (1 + Total_Bonus)
    Location modes:
      - 'bonus_city'     : +18% City Base + Specialty Bonus (+40% Refining or +15% Crafting)
      - 'non_bonus_city' : +18% City Base only
      - 'island'         : 0% City Base, 0% Specialty (Personal/Guild Island stations grant no base bonus;
                           however, they charge 0 silver nutrition usage fee, and Focus (+59%) yields ~37.1% RRR)
    """
    if location_mode == "island":
        city_base = 0.0
        specialty = 0.0
    elif location_mode == "non_bonus_city":
        city_base = 0.18
        specialty = 0.0
    else:  # bonus_city
        city_base = 0.18
        specialty = 0.40 if activity == "refining" else 0.15

    focus_bonus = 0.59 if use_focus else 0.0
    total_bonus = city_base + specialty + focus_bonus
    if total_bonus <= 0:
        return 0.0, 0.0
    rrr = total_bonus / (1.0 + total_bonus)
    return total_bonus, rrr


def calculate_focus_cost(
    base_focus: int,
    mastery_level: int = 0,
    target_spec_level: int = 0,
    other_specs_sum: int = 0,
) -> float:
    """
    Calculates Focus cost per action using Focus Cost Efficiency (FCE).
    - Mastery level: +30 FCE to all tiers
    - Target Spec level: +250 FCE (specific tier) + 30 FCE (all tiers) = +280 FCE
    - Sum of other 4 tier specs: +30 FCE per level
    Formula: Focus = Base_Focus / (2 ** (Total_FCE / 10000))
    """
    total_fce = (mastery_level * 30) + (target_spec_level * 280) + (other_specs_sum * 30)
    return base_focus / (2.0 ** (total_fce / 10000.0))


def calculate_station_fee(
    item_value: float,
    station_rate_per_100_nutrition: float,
    quantity: int = 1,
    is_island: bool = False,
) -> float:
    """
    Calculates crafting/refining station fee based on Item Value.
    Island stations consume player food rather than silver fees, so station silver fee is 0 when is_island=True.
    Formula:
      Nutrition = Item_Value * 0.1125 * Quantity
      Usage_Fee = Nutrition * Station_Rate / 100
    """
    if is_island or station_rate_per_100_nutrition <= 0:
        return 0.0
    nutrition = item_value * 0.1125 * quantity
    return (nutrition * station_rate_per_100_nutrition) / 100.0


@dataclass
class RefiningResult:
    resource_type: str
    tier: int
    enchant: int
    quantity: int
    location_label: str
    total_bonus_pct: float
    rrr_pct: float
    raw_unit_price: float
    lower_refined_unit_price: float
    output_unit_sell_price: float
    gross_material_cost: float
    returned_material_value: float
    net_material_cost: float
    station_fee_total: float
    market_tax_total: float
    gross_revenue: float
    net_profit: float
    roi_pct: float
    focus_per_unit: float
    total_focus_used: float
    silver_per_focus: float


def compute_refining_profit(
    resource_type: str,
    tier: int,
    enchant: int,
    quantity: int,
    raw_unit_price: float,
    lower_refined_unit_price: float,
    output_unit_sell_price: float,
    location_mode: str = "bonus_city",
    use_focus: bool = True,
    station_fee_rate: float = 400.0,
    has_premium: bool = True,
    sell_via_order: bool = True,
    mastery_lvl: int = 100,
    target_spec_lvl: int = 100,
    other_specs_sum: int = 400,
) -> RefiningResult:
    """Computes full refining revenue, RRR return, station fee, taxes, net profit, and Silver Per Focus (SPF)."""
    raw_qty_needed, lower_qty_needed = REFINING_RECIPE_RATIOS.get(tier, (2, 1))
    is_island = location_mode == "island"

    total_bonus, rrr = calculate_rrr(
        location_mode=location_mode,
        activity="refining",
        use_focus=use_focus,
    )

    unit_gross_mat_cost = (raw_qty_needed * raw_unit_price) + (lower_qty_needed * lower_refined_unit_price)
    gross_material_cost = unit_gross_mat_cost * quantity

    returned_material_value = gross_material_cost * rrr
    net_material_cost = gross_material_cost - returned_material_value

    estimated_item_value = (2 ** (tier - 2 + enchant)) * 4.0 if tier >= 3 else 0.0
    station_fee_total = calculate_station_fee(
        estimated_item_value,
        station_fee_rate,
        quantity,
        is_island=is_island,
    )

    sales_tax_rate = 0.04 if has_premium else 0.08
    setup_fee_rate = 0.025 if sell_via_order else 0.0
    total_tax_rate = sales_tax_rate + setup_fee_rate

    gross_revenue = output_unit_sell_price * quantity
    market_tax_total = gross_revenue * total_tax_rate

    net_profit = gross_revenue - net_material_cost - station_fee_total - market_tax_total
    total_cost = net_material_cost + station_fee_total + market_tax_total
    roi_pct = (net_profit / total_cost * 100.0) if total_cost > 0 else 0.0

    base_focus = BASE_REFINING_FOCUS.get((tier, enchant), 150)
    focus_per_unit = calculate_focus_cost(base_focus, mastery_lvl, target_spec_lvl, other_specs_sum) if use_focus else 0.0
    total_focus_used = focus_per_unit * quantity
    silver_per_focus = (net_profit / total_focus_used) if (use_focus and total_focus_used > 0) else 0.0

    bonus_city = REFINING_BONUS_CITIES.get(resource_type, {}).get("city", "Unknown")
    if location_mode == "bonus_city":
        location_label = f"{bonus_city} (Bonus City +40%)"
    elif location_mode == "island":
        location_label = "Personal/Guild Island (0% Base, 0 Station Fee)"
    else:
        location_label = "Non-Bonus Royal City (+18% Base Only)"

    return RefiningResult(
        resource_type=resource_type,
        tier=tier,
        enchant=enchant,
        quantity=quantity,
        location_label=location_label,
        total_bonus_pct=total_bonus * 100.0,
        rrr_pct=rrr * 100.0,
        raw_unit_price=raw_unit_price,
        lower_refined_unit_price=lower_refined_unit_price,
        output_unit_sell_price=output_unit_sell_price,
        gross_material_cost=gross_material_cost,
        returned_material_value=returned_material_value,
        net_material_cost=net_material_cost,
        station_fee_total=station_fee_total,
        market_tax_total=market_tax_total,
        gross_revenue=gross_revenue,
        net_profit=net_profit,
        roi_pct=roi_pct,
        focus_per_unit=focus_per_unit,
        total_focus_used=total_focus_used,
        silver_per_focus=silver_per_focus,
    )


@dataclass
class IslandFarmingResult:
    plots_count: int
    total_tiles: int
    use_focus: bool
    city_bonus_active: bool
    total_seed_cost: float
    seed_return_value: float
    net_seed_expense: float
    total_crop_yield: float
    gross_crop_revenue: float
    market_tax: float
    net_Farming_profit: float
    laborer_profit_total: float
    combined_daily_profit: float
    focus_used: float
    silver_per_focus: float


def compute_island_economy(
    plots_count: int,
    seed_unit_price: float,
    crop_unit_sell_price: float,
    base_seed_return_no_focus: float = 0.733,
    seed_return_with_focus: float = 1.067,
    use_focus: bool = True,
    city_farming_bonus: bool = True,
    farming_fce: int = 10000,
    laborer_count: int = 0,
    empty_journal_price: float = 0.0,
    full_journal_price: float = 0.0,
    laborer_yield_value: float = 0.0,
) -> IslandFarmingResult:
    """
    Calculates daily Personal Island Farming (Crops/Herbs) + Island Laborer House net profit.
    """
    total_tiles = plots_count * 9
    total_seed_cost = total_tiles * seed_unit_price

    effective_seed_return = seed_return_with_focus if use_focus else base_seed_return_no_focus
    seed_return_value = total_tiles * effective_seed_return * seed_unit_price
    net_seed_expense = total_seed_cost - seed_return_value

    avg_yield_per_tile = 9.0 * (1.10 if city_farming_bonus else 1.0)
    total_crop_yield = total_tiles * avg_yield_per_tile
    gross_crop_revenue = total_crop_yield * crop_unit_sell_price
    market_tax = gross_crop_revenue * 0.065

    net_farming_profit = gross_crop_revenue - market_tax - net_seed_expense

    focus_per_tile = 1000.0 / (2.0 ** (farming_fce / 10000.0)) if use_focus else 0.0
    focus_used = total_tiles * focus_per_tile
    spf = (net_farming_profit / focus_used) if (use_focus and focus_used > 0) else 0.0

    unit_journal_cost = max(0.0, full_journal_price - empty_journal_price)
    unit_laborer_net = (laborer_yield_value * 0.935) - unit_journal_cost
    laborer_profit_total = laborer_count * unit_laborer_net

    combined_daily_profit = net_farming_profit + laborer_profit_total

    return IslandFarmingResult(
        plots_count=plots_count,
        total_tiles=total_tiles,
        use_focus=use_focus,
        city_bonus_active=city_farming_bonus,
        total_seed_cost=total_seed_cost,
        seed_return_value=seed_return_value,
        net_seed_expense=net_seed_expense,
        total_crop_yield=total_crop_yield,
        gross_crop_revenue=gross_crop_revenue,
        market_tax=market_tax,
        net_Farming_profit=net_farming_profit,
        laborer_profit_total=laborer_profit_total,
        combined_daily_profit=combined_daily_profit,
        focus_used=focus_used,
        silver_per_focus=spf,
    )


@dataclass
class LootSplitResult:
    rule_preset: str
    gross_loot_value: int
    silver_bags: int
    repair_cost: int
    regear_reserve: int
    market_tax_pct: float
    market_tax_amount: int
    net_after_deductions: int
    guild_cut_pct: float
    guild_cut_amount: int
    caller_bonus_pct: float
    caller_bonus_amount: int
    distributable_pool: int
    total_participants: int
    special_roles_count: int
    special_role_weight: float
    regular_members_count: int
    regular_member_payout: int
    special_role_payout: int


def compute_loot_split(
    estimated_loot_value: int,
    total_participants: int,
    rule_preset: str = "equal",
    silver_bags: int = 0,
    repair_cost: int = 0,
    regear_reserve: int = 0,
    market_tax_pct: float = 6.5,
    guild_cut_pct: float = 10.0,
    caller_bonus_pct: float = 0.0,
    special_roles_count: int = 0,
    special_role_weight: float = 1.5,
) -> LootSplitResult:
    """Criteria-based & player-customizable Guild Loot Split calculator."""
    if total_participants < 1:
        raise ValueError("Total participants must be at least 1.")

    special_roles_count = max(0, min(special_roles_count, total_participants))
    regular_members_count = total_participants - special_roles_count

    market_tax_amount = int(round(estimated_loot_value * (market_tax_pct / 100.0)))
    net_loot = max(0, estimated_loot_value - market_tax_amount)

    effective_regear = regear_reserve if rule_preset == "repair_priority" else 0
    net_after_deductions = max(0, net_loot + silver_bags - repair_cost - effective_regear)

    guild_cut_amount = int(round(net_after_deductions * (guild_cut_pct / 100.0)))
    caller_bonus_amount = int(round(net_after_deductions * (caller_bonus_pct / 100.0)))

    distributable_pool = max(0, net_after_deductions - guild_cut_amount - caller_bonus_amount)

    if rule_preset == "role_weighted" and special_roles_count > 0:
        total_weight_shares = (regular_members_count * 1.0) + (special_roles_count * special_role_weight)
        base_share = distributable_pool / total_weight_shares if total_weight_shares > 0 else 0.0
        regular_member_payout = int(base_share)
        special_role_payout = int(round(base_share * special_role_weight))
    else:
        regular_member_payout = distributable_pool // total_participants
        special_role_payout = regular_member_payout

    return LootSplitResult(
        rule_preset=rule_preset,
        gross_loot_value=estimated_loot_value,
        silver_bags=silver_bags,
        repair_cost=repair_cost,
        regear_reserve=effective_regear,
        market_tax_pct=market_tax_pct,
        market_tax_amount=market_tax_amount,
        net_after_deductions=net_after_deductions,
        guild_cut_pct=guild_cut_pct,
        guild_cut_amount=guild_cut_amount,
        caller_bonus_pct=caller_bonus_pct,
        caller_bonus_amount=caller_bonus_amount,
        distributable_pool=distributable_pool,
        total_participants=total_participants,
        special_roles_count=special_roles_count,
        special_role_weight=special_role_weight,
        regular_members_count=regular_members_count,
        regular_member_payout=regular_member_payout,
        special_role_payout=special_role_payout,
    )


# ============================================================================
# 4. NATURAL LANGUAGE ITEM ID RESOLVER & PRICE DISCOUNT ANALYZER
# ============================================================================

def resolve_item_id(user_query: str) -> str:
    """
    Converts natural player queries (e.g., '6.1 plank', 't4.2 bag', 't7 carving sword')
    into canonical Albion Online Data Project Item IDs (e.g., 'T6_PLANKS_LEVEL1@1').
    """
    q = user_query.strip()
    if q.upper().startswith(("T1_", "T2_", "T3_", "T4_", "T5_", "T6_", "T7_", "T8_", "UNIQUE_")):
        return q.upper()

    q_lower = q.lower()
    tokens = q_lower.split()

    tier = 4
    enchant = 0
    remaining_tokens: List[str] = []

    for token in tokens:
        clean_tok = token.lstrip("t")
        if "." in clean_tok:
            parts = clean_tok.split(".", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                tier = int(parts[0])
                enchant = int(parts[1])
                continue
        elif clean_tok.isdigit() and 1 <= int(clean_tok) <= 8 and token.startswith("t"):
            tier = int(clean_tok)
            continue
        remaining_tokens.append(token)

    item_phrase = " ".join(remaining_tokens).strip()
    base_id = COMMON_ITEM_ALIASES.get(item_phrase)

    if not base_id:
        for alias_key, alias_val in COMMON_ITEM_ALIASES.items():
            if alias_key in item_phrase or item_phrase in alias_key:
                base_id = alias_val
                break

    if not base_id:
        base_id = item_phrase.upper().replace(" ", "_")

    resource_bases = {"ORE", "HIDE", "FIBER", "WOOD", "ROCK", "METALBAR", "LEATHER", "CLOTH", "PLANKS", "STONEBLOCK"}
    if base_id in resource_bases:
        if enchant > 0:
            return f"T{tier}_{base_id}_LEVEL{enchant}@{enchant}"
        return f"T{tier}_{base_id}"

    if enchant > 0:
        return f"T{tier}_{base_id}@{enchant}"
    return f"T{tier}_{base_id}"


def build_resource_item_id(base_key: str, tier: int, enchant: int) -> str:
    if tier <= 3 or enchant == 0:
        return f"T{tier}_{base_key}"
    return f"T{tier}_{base_key}_LEVEL{enchant}@{enchant}"


def evaluate_price_drop_alert(
    current_prices: List[Dict[str, Any]],
    history_records: List[Dict[str, Any]],
    drop_threshold_pct: float = 25.0,
) -> Optional[Dict[str, Any]]:
    """
    Checks if any city's current minimum sell price (`sell_price_min`) has dropped
    by at least `drop_threshold_pct` (e.g., 25%-30%) below the historical/market average price.
    """
    active_sells = [
        (r.get("city", "Unknown"), float(r.get("sell_price_min", 0)), r.get("sell_price_min_date", ""))
        for r in current_prices
        if r.get("sell_price_min", 0) > 0
    ]
    if not active_sells:
        return None

    total_weighted_val = 0.0
    total_count = 0
    for h_loc in history_records:
        for point in h_loc.get("data", []):
            cnt = int(point.get("item_count", 0))
            avg_p = float(point.get("avg_price", 0))
            if cnt > 0 and avg_p > 0:
                total_weighted_val += cnt * avg_p
                total_count += cnt

    if total_count > 0:
        baseline_avg = total_weighted_val / total_count
    else:
        baseline_avg = sum(p for _, p, _ in active_sells) / len(active_sells)

    if baseline_avg <= 0:
        return None

    active_sells.sort(key=lambda x: x[1])
    cheapest_city, cheapest_price, cheapest_date = active_sells[0]
    discount_pct = ((baseline_avg - cheapest_price) / baseline_avg) * 100.0

    if discount_pct >= drop_threshold_pct:
        return {
            "city": cheapest_city,
            "current_price": cheapest_price,
            "average_price": baseline_avg,
            "discount_pct": discount_pct,
            "updated_at": cheapest_date,
        }
    return None


# ============================================================================
# 5. DISCORD BOT CLASS, BACKGROUND PRICE ALERT LOOP & SLASH COMMANDS
# ============================================================================
# Note: Using discord.Client + app_commands.CommandTree avoids the unnecessary
# "Privileged message content intent is missing" warning since this bot uses Slash Commands.

class AlbionMultiToolBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={"User-Agent": "AlbionMultiTool-OpenSource-AIBot/2.1"},
        )
        self.check_price_alerts_task.start()
        synced = await self.tree.sync()
        print(f"[Albion Multi Tool] Synchronized {len(synced)} slash commands with Discord.")

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Albion Market | /price /refine",
            ),
        )
        print(f"[Albion Multi Tool] Logged in as {self.user} — Bot is now ONLINE!")

    async def close(self) -> None:
        self.check_price_alerts_task.cancel()
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()

    async def fetch_gold_prices(self, server: str = "eu", count: int = 24) -> List[Dict[str, Any]]:
        base_url = AODP_SERVERS.get(server, AODP_SERVERS["eu"])
        url = f"{base_url}/api/v2/stats/gold?count={count}"
        assert self.http_session is not None
        async with self.http_session.get(url) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

    async def fetch_market_prices(
        self,
        item_ids: List[str],
        server: str = "eu",
        locations: Optional[List[str]] = None,
        qualities: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        base_url = AODP_SERVERS.get(server, AODP_SERVERS["eu"])
        items_str = ",".join(item_ids)
        loc_list = locations or DEFAULT_LOCATIONS
        params: Dict[str, str] = {"locations": ",".join(loc_list)}
        if qualities:
            params["qualities"] = ",".join(str(q) for q in qualities)
        url = f"{base_url}/api/v2/stats/prices/{items_str}.json"
        assert self.http_session is not None
        async with self.http_session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

    async def fetch_market_history(
        self,
        item_id: str,
        server: str = "eu",
        quality: int = 1,
    ) -> List[Dict[str, Any]]:
        base_url = AODP_SERVERS.get(server, AODP_SERVERS["eu"])
        url = f"{base_url}/api/v2/stats/history/{item_id}.json"
        params = {
            "locations": ",".join(DEFAULT_LOCATIONS),
            "qualities": str(quality),
            "time-scale": "24",
        }
        assert self.http_session is not None
        async with self.http_session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

    @tasks.loop(minutes=10)
    async def check_price_alerts_task(self) -> None:
        """Background task that checks tracked items every 10 minutes for 25-30%+ drops below average."""
        alerts: List[Dict[str, Any]] = load_json_file(PRICE_ALERTS_FILE, [])
        if not alerts:
            return

        for alert in alerts:
            try:
                item_id = alert["item_id"]
                server = alert.get("server", "eu")
                quality = int(alert.get("quality", 1))
                threshold = float(alert.get("threshold_pct", 25.0))
                channel_id = int(alert["channel_id"])
                user_id = int(alert["user_id"])

                current_prices, history_records = await asyncio.gather(
                    self.fetch_market_prices([item_id], server=server, qualities=[quality]),
                    self.fetch_market_history(item_id, server=server, quality=quality),
                )
                deal = evaluate_price_drop_alert(current_prices, history_records, drop_threshold_pct=threshold)
                if deal:
                    channel = self.get_channel(channel_id)
                    if channel and hasattr(channel, "send"):
                        embed = discord.Embed(
                            title=f"🚨 Market Bargain Alert: {item_id} (-{deal['discount_pct']:.1f}%)",
                            description=(
                                f"<@{user_id}>, **{item_id}** dropped significantly below its market average on "
                                f"**{SERVER_LABELS.get(server, server)}**!"
                            ),
                            color=discord.Color.red(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc),
                        )
                        embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{item_id}.png?quality={quality}")
                        embed.add_field(name="📍 Cheapest City", value=f"**{deal['city']}**", inline=True)
                        embed.add_field(name="🏷️ Current Sell Price", value=f"**{format_silver(deal['current_price'])} Silver**", inline=True)
                        embed.add_field(name="📊 Market Average", value=f"{format_silver(deal['average_price'])} Silver", inline=True)
                        embed.set_footer(text="Albion Multi Tool • AI-Built Open-Source Economy Bot")
                        await channel.send(content=f"<@{user_id}>", embed=embed)
            except Exception as exc:
                print(f"[Alert Check Warning] {exc}")

    @check_price_alerts_task.before_loop
    async def before_alert_loop(self) -> None:
        await self.wait_until_ready()


bot = AlbionMultiToolBot()

SERVER_CHOICES = [
    app_commands.Choice(name="🌍 Europe (EU)", value="eu"),
    app_commands.Choice(name="🌎 Americas (West)", value="west"),
    app_commands.Choice(name="🌏 Asia (East)", value="east"),
]

LOCATION_MODE_CHOICES = [
    app_commands.Choice(name="🏰 Bonus Royal City (+18% Base & +40%/+15% Specialty)", value="bonus_city"),
    app_commands.Choice(name="🏝️ Personal / Guild Island (0% Base, 0 Silver Fee)", value="island"),
    app_commands.Choice(name="🏙️ Non-Bonus City (+18% Base Only)", value="non_bonus_city"),
]


def format_silver(amount: float) -> str:
    return f"{int(round(amount)):,}"


def format_timestamp_age(iso_str: str) -> str:
    if not iso_str or iso_str.startswith("0001-01-01"):
        return "No Data"
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt
        mins = int(diff.total_seconds() // 60)
        if mins < 1:
            return "Just now"
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h {mins % 60}m ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return iso_str


# ----------------------------------------------------------------------------
# COMMAND 1: /set_server - Per-User Default Server Preference
# ----------------------------------------------------------------------------
@bot.tree.command(name="set_server", description="Save your default Albion Online server (Europe, Americas, or Asia).")
@app_commands.describe(server="Choose your primary Albion Online server")
@app_commands.choices(server=SERVER_CHOICES)
async def cmd_set_server(interaction: discord.Interaction, server: str) -> None:
    set_user_server(interaction.user.id, server)
    await interaction.response.send_message(
        f"✅ Your default server has been saved as **{SERVER_LABELS.get(server, server)}**. "
        f"All market and calculator commands will now automatically use this server unless you specify another one!",
        ephemeral=True,
    )


# ----------------------------------------------------------------------------
# COMMAND 2: /gold - Real-Time Gold Price & 24h Trend
# ----------------------------------------------------------------------------
@bot.tree.command(name="gold", description="Display real-time Gold/Silver exchange rate and 24-hour trend.")
@app_commands.describe(server="Optional server override (uses /set_server preference by default)")
@app_commands.choices(server=SERVER_CHOICES)
async def cmd_gold(interaction: discord.Interaction, server: Optional[str] = None) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    data = await bot.fetch_gold_prices(server=active_server, count=24)

    if not data:
        await interaction.followup.send("⚠️ Could not fetch Gold price data from AODP API right now. Please try again shortly.")
        return

    latest = data[0]
    current_price = latest.get("price", 0)
    latest_time = format_timestamp_age(latest.get("timestamp", ""))

    prices = [row.get("price", 0) for row in data if row.get("price", 0) > 0]
    min_24h = min(prices) if prices else current_price
    max_24h = max(prices) if prices else current_price
    avg_24h = sum(prices) / len(prices) if prices else current_price
    oldest_price = prices[-1] if prices else current_price
    diff = current_price - oldest_price
    diff_pct = (diff / oldest_price * 100.0) if oldest_price > 0 else 0.0
    trend_emoji = "📈" if diff >= 0 else "📉"

    embed = discord.Embed(
        title=f"🪙 Live Gold Exchange Rate — {SERVER_LABELS.get(active_server, active_server)}",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(
        name="💰 Current 1 Gold",
        value=f"**{format_silver(current_price)} Silver**\n*(Updated: {latest_time})*",
        inline=False,
    )
    embed.add_field(name=f"{trend_emoji} 24h Change", value=f"{diff:+d} Silver ({diff_pct:+.2f}%)", inline=True)
    embed.add_field(name="📊 24h Average", value=f"{format_silver(avg_24h)} Silver", inline=True)
    embed.add_field(name="↕️ 24h Low / High", value=f"{format_silver(min_24h)} / {format_silver(max_24h)}", inline=True)
    embed.add_field(
        name="📦 Bundle Conversions",
        value=(
            f"• **500 Gold:** {format_silver(current_price * 500)} Silver\n"
            f"• **3,000 Gold (30d Premium):** {format_silver(current_price * 3000)} Silver\n"
            f"• **10,000 Gold:** {format_silver(current_price * 10000)} Silver"
        ),
        inline=False,
    )
    embed.set_footer(text="Albion Multi Tool • AI-Built Open-Source Project • Data: AODP")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 3: /price - Live Buy & Sell Orders Across All Cities
# ----------------------------------------------------------------------------
@bot.tree.command(name="price", description="Check live Buy & Sell orders across all cities and Black Market.")
@app_commands.describe(
    item="Item name or ID (e.g., '6.1 plank', 't4.2 bag', 't6 cleric robe', 'T4_BAG')",
    quality="Item quality (1: Normal, 2: Good, 3: Outstanding, 4: Excellent, 5: Masterpiece)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(server=SERVER_CHOICES)
async def cmd_price(
    interaction: discord.Interaction,
    item: str,
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    item_id = resolve_item_id(item)
    qualities = [quality] if 1 <= quality <= 5 else [1, 2, 3, 4, 5]

    records, history_records = await asyncio.gather(
        bot.fetch_market_prices([item_id], server=active_server, qualities=qualities),
        bot.fetch_market_history(item_id, server=active_server, quality=quality),
    )

    if not records:
        await interaction.followup.send(
            f"⚠️ No market data found for `{item_id}` on **{SERVER_LABELS.get(active_server)}**.\n"
            f"💡 **Tip:** Try typing shortcuts like `6.1 plank`, `t4.2 bag`, `t6 mercenary jacket`, or an exact ID like `T6_PLANKS_LEVEL1@1`."
        )
        return

    embed = discord.Embed(
        title=f"🏪 Cross-City Market Orders: {item_id}",
        description=f"**Server:** {SERVER_LABELS.get(active_server)} | **Quality:** {QUALITY_NAMES.get(quality, 'All')}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{item_id}.png?quality={quality}")

    best_sell_city = None
    best_sell_price = float("inf")
    best_buy_city = None
    best_buy_price = 0

    lines: List[str] = []
    for row in records:
        city = row.get("city", "Unknown")
        sell_min = row.get("sell_price_min", 0)
        sell_date = format_timestamp_age(row.get("sell_price_min_date", ""))
        buy_max = row.get("buy_price_max", 0)
        buy_date = format_timestamp_age(row.get("buy_price_max_date", ""))

        if sell_min > 0 and sell_min < best_sell_price:
            best_sell_price = sell_min
            best_sell_city = city
        if buy_max > best_buy_price:
            best_buy_price = buy_max
            best_buy_city = city

        sell_str = f"**{format_silver(sell_min)}** *({sell_date})*" if sell_min > 0 else "—"
        buy_str = f"**{format_silver(buy_max)}** *({buy_date})*" if buy_max > 0 else "—"
        lines.append(f"📍 **{city}**\n┗ 🏷️ Min Sell: {sell_str} | 📥 Max Buy: {buy_str}")

    embed.description += "\n\n" + "\n".join(lines[:10])

    deal = evaluate_price_drop_alert(records, history_records, drop_threshold_pct=25.0)
    if deal:
        embed.add_field(
            name="🔥 BARGAIN DETECTED (25%+ Below Average!)",
            value=(
                f"**{deal['city']}** is currently selling at **{format_silver(deal['current_price'])} Silver**, which is "
                f"**`-{deal['discount_pct']:.1f}%`** below the market average (`{format_silver(deal['average_price'])} Silver`)!"
            ),
            inline=False,
        )

    if best_sell_city and best_buy_city and best_sell_price < float("inf") and best_buy_price > 0:
        spread = (best_buy_price * 0.96) - best_sell_price
        embed.add_field(
            name="💡 Quick Trader Summary",
            value=(
                f"• **Lowest Sell Order (Buy Here):** {best_sell_city} — **{format_silver(best_sell_price)}** Silver\n"
                f"• **Highest Buy Order (Instant Sell):** {best_buy_city} — **{format_silver(best_buy_price)}** Silver\n"
                f"• **Instant Flip Margin (After 4% Tax):** {format_silver(spread)} Silver"
            ),
            inline=False,
        )

    embed.set_footer(text="Albion Multi Tool • AI-Built Open-Source Project • Icons: render.albiononline.com")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 4: /refine - Refining Profit, Permanent City Bonus, Island & SPF Calculator
# ----------------------------------------------------------------------------
RESOURCE_CHOICES = [
    app_commands.Choice(name="⛏️ Ore -> Metal Bar (Thetford +40%)", value="ore"),
    app_commands.Choice(name="🌿 Fiber -> Cloth (Lymhurst +40%)", value="fiber"),
    app_commands.Choice(name="🦌 Hide -> Leather (Martlock +40%)", value="hide"),
    app_commands.Choice(name="🪵 Wood -> Planks (Fort Sterling +40%)", value="wood"),
    app_commands.Choice(name="🪨 Rock -> Stone Block (Bridgewatch +40%)", value="rock"),
]


@bot.tree.command(name="refine", description="Calculate Refining profit, city/island RRR, and Silver Per Focus (SPF).")
@app_commands.describe(
    resource="Resource type to refine (auto-applies permanent +40% Royal City bonus)",
    tier="Resource tier (4 to 8)",
    enchant="Enchantment level (0 to 4, e.g., 6.1 -> tier=6, enchant=1)",
    quantity="Batch quantity to refine (Default: 100)",
    location_mode="Refining location: Bonus City (+40%), Island (0% Fee), or Non-Bonus City",
    use_focus="Spend Focus points? (+59% production bonus)",
    station_fee="Station fee per 100 nutrition (Default: 400; 0 on Island)",
    mastery_level="Your Refining Mastery level (0-100, for Focus cost calculation)",
    target_spec="Your Specialization level in this exact Tier (0-100)",
    other_specs_sum="Sum of your Specialization levels in the other 4 Tiers (0-400)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(resource=RESOURCE_CHOICES, location_mode=LOCATION_MODE_CHOICES, server=SERVER_CHOICES)
async def cmd_refine(
    interaction: discord.Interaction,
    resource: str,
    tier: app_commands.Range[int, 4, 8] = 6,
    enchant: app_commands.Range[int, 0, 4] = 1,
    quantity: app_commands.Range[int, 1, 100000] = 100,
    location_mode: str = "bonus_city",
    use_focus: bool = True,
    station_fee: float = 400.0,
    mastery_level: app_commands.Range[int, 0, 100] = 100,
    target_spec: app_commands.Range[int, 0, 100] = 100,
    other_specs_sum: app_commands.Range[int, 0, 400] = 400,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)

    res_info = REFINING_BONUS_CITIES[resource]
    bonus_city = res_info["city"]
    raw_id = build_resource_item_id(res_info["raw_key"], tier, enchant)
    lower_refined_id = build_resource_item_id(res_info["refined_key"], tier - 1, enchant)
    output_refined_id = build_resource_item_id(res_info["refined_key"], tier, enchant)

    records = await bot.fetch_market_prices(
        [raw_id, lower_refined_id, output_refined_id],
        server=active_server,
        locations=[bonus_city, "Caerleon", "Thetford", "Lymhurst", "Martlock", "Bridgewatch", "Fort Sterling"],
    )

    def get_best_price(target_id: str, preferred_city: str) -> Tuple[float, str]:
        city_price = 0
        fallback_price = float("inf")
        fallback_city = preferred_city
        for r in records:
            if r.get("item_id") == target_id:
                p = r.get("sell_price_min", 0)
                if p > 0:
                    if r.get("city") == preferred_city:
                        city_price = p
                    if p < fallback_price:
                        fallback_price = p
                        fallback_city = r.get("city", preferred_city)
        if city_price > 0:
            return float(city_price), preferred_city
        if fallback_price < float("inf"):
            return float(fallback_price), fallback_city
        return 0.0, "No Data"

    raw_price, raw_city = get_best_price(raw_id, bonus_city)
    lower_price, lower_city = get_best_price(lower_refined_id, bonus_city)
    out_price, out_city = get_best_price(output_refined_id, bonus_city)

    if raw_price == 0 or lower_price == 0 or out_price == 0:
        await interaction.followup.send(
            f"⚠️ Missing live price data on AODP for `{raw_id}`, `{lower_refined_id}`, or `{output_refined_id}`.\n"
            f"Found: Raw={format_silver(raw_price)}, Lower Refined={format_silver(lower_price)}, Output={format_silver(out_price)}"
        )
        return

    res = compute_refining_profit(
        resource_type=resource,
        tier=tier,
        enchant=enchant,
        quantity=quantity,
        raw_unit_price=raw_price,
        lower_refined_unit_price=lower_price,
        output_unit_sell_price=out_price,
        location_mode=location_mode,
        use_focus=use_focus,
        station_fee_rate=station_fee,
        has_premium=True,
        sell_via_order=True,
        mastery_lvl=mastery_level,
        target_spec_lvl=target_spec,
        other_specs_sum=other_specs_sum,
    )

    raw_qty_ratio, lower_qty_ratio = REFINING_RECIPE_RATIOS[tier]
    profit_color = discord.Color.green() if res.net_profit >= 0 else discord.Color.red()
    status_emoji = "✅ PROFITABLE" if res.net_profit >= 0 else "❌ LOSS"

    embed = discord.Embed(
        title=f"⚗️ Refining Profit Calculator: {quantity}x T{tier}.{enchant} {res_info['name']}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Location:** {res.location_label}\n"
            f"**Effective RRR:** `{res.rrr_pct:.2f}%` *(Total Production Bonus: +{res.total_bonus_pct:.0f}%)*"
        ),
        color=profit_color,
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{output_refined_id}.png")

    embed.add_field(
        name="📥 Unit Input & Output Prices",
        value=(
            f"• **{raw_qty_ratio}x {raw_id}:** {format_silver(raw_price)} Silver *({raw_city})*\n"
            f"• **{lower_qty_ratio}x {lower_refined_id}:** {format_silver(lower_price)} Silver *({lower_city})*\n"
            f"• **1x Output ({output_refined_id}):** {format_silver(out_price)} Silver *({out_city})*"
        ),
        inline=False,
    )
    embed.add_field(
        name="💸 Cost & Return Breakdown",
        value=(
            f"• **Gross Materials:** {format_silver(res.gross_material_cost)} Silver\n"
            f"• **RRR Refund ({res.rrr_pct:.1f}%):** +{format_silver(res.returned_material_value)} Silver\n"
            f"• **Net Material Cost:** {format_silver(res.net_material_cost)} Silver\n"
            f"• **Station Fee:** {format_silver(res.station_fee_total)} Silver\n"
            f"• **Market Tax (6.5%):** {format_silver(res.market_tax_total)} Silver"
        ),
        inline=True,
    )
    embed.add_field(
        name=f"💰 Net Outcome ({status_emoji})",
        value=(
            f"• **Gross Revenue:** {format_silver(res.gross_revenue)} Silver\n"
            f"• **Net Profit/Loss:** **{format_silver(res.net_profit)} Silver**\n"
            f"• **ROI:** `{res.roi_pct:+.2f}%`\n"
            f"• **Profit per Unit:** {format_silver(res.net_profit / quantity)} Silver"
        ),
        inline=True,
    )

    if use_focus:
        daily_10k_profit = res.silver_per_focus * 10000
        embed.add_field(
            name="⚡ Focus Efficiency (Silver Per Focus - SPF)",
            value=(
                f"• **Focus per Unit:** {res.focus_per_unit:.1f} Focus\n"
                f"• **Total Focus Used:** {format_silver(res.total_focus_used)} Focus\n"
                f"• **Silver / Focus (SPF):** **{format_silver(res.silver_per_focus)} Silver/Focus**\n"
                f"• **Daily 10,000 Focus Value:** **{format_silver(daily_10k_profit)} Silver/Day**"
            ),
            inline=False,
        )

    embed.set_footer(text="Albion Multi Tool • Permanent City Bonuses Auto-Applied • RRR = Bonus / (1 + Bonus)")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 5: /craft - Equipment Crafting Calculator (Permanent City Bonus, Island & Journals)
# ----------------------------------------------------------------------------
CRAFT_CATEGORY_CHOICES = [
    app_commands.Choice(name="🔨 Fort Sterling (+15%: Hammer, Spear, Holy, Plate Helm, Cloth Robe)", value="cloth_robe"),
    app_commands.Choice(name="🏹 Lymhurst (+15%: Sword, Bow, Arcane, Leather Hood, Leather Shoes)", value="sword"),
    app_commands.Choice(name="🗡️ Bridgewatch (+15%: Crossbow, Dagger, Cursed, Plate Armor, Sandals)", value="plate_armor"),
    app_commands.Choice(name="🪓 Martlock (+15%: Axe, Quarterstaff, Frost, Plate Boots, Off-Hand)", value="axe"),
    app_commands.Choice(name="🔥 Thetford (+15%: Mace, Fire/Nature Staff, Leather Jacket, Cowl)", value="leather_jacket"),
    app_commands.Choice(name="🥊 Caerleon (+15%: War Gloves, Shapeshifter, Gathering Gear, Food)", value="war_gloves"),
    app_commands.Choice(name="🧪 Brecilien (+15%: Cape, Bag, Potion)", value="bag"),
]


@bot.tree.command(name="craft", description="Calculate Crafting profit with permanent city bonus, Island mode & Journals.")
@app_commands.describe(
    item_name="Item name being crafted (e.g., 'T6.1 Cleric Robe' or 'T7.2 Carving Sword')",
    category_city="Select item's permanent +15% bonus city group",
    location_mode="Crafting location: Bonus City (+15%), Island (0% Fee), or Non-Bonus City",
    primary_mat_qty="Primary material quantity per craft (e.g., 16 for armor/1H, 20 for 2H)",
    primary_mat_price="Unit price of primary material (Silver)",
    sell_price="Market sell price per crafted item (Silver)",
    secondary_mat_qty="Secondary material quantity per craft (e.g., 12 for 2H, 0 if none)",
    secondary_mat_price="Unit price of secondary material (Silver)",
    artifact_cost="Non-returnable Artifact / Heart / Crest cost per unit (Silver, 0 if none)",
    journal_profit_per_craft="Estimated net profit from Crafting Journals per item crafted (Silver)",
    quantity="Number of items to craft (Default: 10)",
    use_focus="Spend Focus points? (+59% production bonus)",
    station_fee="Station fee per 100 nutrition (Default: 500; 0 on Island)",
)
@app_commands.choices(category_city=CRAFT_CATEGORY_CHOICES, location_mode=LOCATION_MODE_CHOICES)
async def cmd_craft(
    interaction: discord.Interaction,
    item_name: str,
    category_city: str,
    primary_mat_qty: int,
    primary_mat_price: int,
    sell_price: int,
    location_mode: str = "bonus_city",
    secondary_mat_qty: int = 0,
    secondary_mat_price: int = 0,
    artifact_cost: int = 0,
    journal_profit_per_craft: int = 0,
    quantity: int = 10,
    use_focus: bool = False,
    station_fee: float = 500.0,
) -> None:
    cat_label, best_city_name = CRAFTING_CATEGORY_CITIES.get(category_city, ("Equipment", "Royal City"))
    is_island = location_mode == "island"

    total_bonus, rrr = calculate_rrr(
        location_mode=location_mode,
        activity="crafting",
        use_focus=use_focus,
    )

    returnable_unit_cost = (primary_mat_qty * primary_mat_price) + (secondary_mat_qty * secondary_mat_price)
    net_returnable_unit_cost = returnable_unit_cost * (1.0 - rrr)

    total_mats_count = primary_mat_qty + secondary_mat_qty
    approx_item_value = total_mats_count * 16.0
    unit_station_fee = calculate_station_fee(approx_item_value, station_fee, quantity=1, is_island=is_island)

    unit_total_cost = net_returnable_unit_cost + artifact_cost + unit_station_fee
    unit_tax = sell_price * 0.065
    unit_net_profit = (sell_price - unit_total_cost - unit_tax) + journal_profit_per_craft

    batch_cost = (unit_total_cost + unit_tax) * quantity
    batch_profit = unit_net_profit * quantity
    roi_pct = (batch_profit / batch_cost * 100.0) if batch_cost > 0 else 0.0

    loc_desc = (
        f"{best_city_name} (Permanent +15% Bonus)"
        if location_mode == "bonus_city"
        else ("Personal Island (0% Base, 0 Station Fee)" if is_island else "Non-Bonus City (+18% Base Only)")
    )

    embed = discord.Embed(
        title=f"🔨 Crafting Profit Analysis: {quantity}x {item_name}",
        description=(
            f"**Recommended Bonus City:** `{best_city_name}` | **Selected Mode:** `{loc_desc}`\n"
            f"**Effective RRR:** `{rrr * 100:.2f}%` *(Total Bonus: +{total_bonus * 100:.0f}%, Focus: {'Yes' if use_focus else 'No'})*"
        ),
        color=discord.Color.green() if batch_profit >= 0 else discord.Color.red(),
    )
    embed.add_field(
        name="🧱 Per-Item Cost & Return Breakdown",
        value=(
            f"• **Gross Returnable Mats:** {format_silver(returnable_unit_cost)} Silver\n"
            f"• **Net Mats After RRR ({rrr * 100:.1f}%):** {format_silver(net_returnable_unit_cost)} Silver\n"
            f"• **Non-Returnable Artifact/Crest:** {format_silver(artifact_cost)} Silver\n"
            f"• **Station Fee + Market Tax (6.5%):** {format_silver(unit_station_fee + unit_tax)} Silver\n"
            f"• **Crafting Journal Bonus:** +{format_silver(journal_profit_per_craft)} Silver"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"📊 Batch Summary ({quantity} Units)",
        value=(
            f"• **Unit Sell Price:** {format_silver(sell_price)} Silver\n"
            f"• **Net Profit per Item:** **{format_silver(unit_net_profit)} Silver**\n"
            f"• **Total Batch Net Profit:** **{format_silver(batch_profit)} Silver**\n"
            f"• **Return on Investment (ROI):** `{roi_pct:+.2f}%`"
        ),
        inline=False,
    )
    embed.set_footer(text="Albion Multi Tool • Artifacts/Hearts/Crests are exempt from RRR • AI-Built Open-Source Bot")
    await interaction.response.send_message(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 6: /island - Personal/Guild Island Farming & Laborer Journal Calculator
# ----------------------------------------------------------------------------
@bot.tree.command(name="island", description="Calculate daily Island Farming (Crops/Herbs) and Laborer Journal profit.")
@app_commands.describe(
    plots_count="Total number of farming/herb plots across your islands (e.g., 16 plots = 144 tiles)",
    seed_price="Unit price of 1 seed / herb seed (Silver)",
    crop_sell_price="Market sell price of 1 harvested crop / herb (Silver)",
    use_focus="Water plots with Focus? (Boosts seed return rate above 100%)",
    city_farming_bonus="Is this crop grown in its +10% Local Royal City bonus location?",
    base_seed_return_pct="Base seed return % without Focus (Default: 73.3 for T6-T8 crops)",
    focus_seed_return_pct="Total seed return % when watered with Focus (Default: 106.7)",
    farming_fce="Your Farming Focus Cost Efficiency points (Default: 10000 -> 500 Focus/tile)",
    laborer_count="Number of Island Laborers fed daily (0 if none)",
    empty_journal_price="Price of 1 Empty Crafting/Gathering Journal (Silver)",
    full_journal_price="Price of 1 Full Crafting/Gathering Journal (Silver)",
    laborer_yield_value="Estimated market value of materials returned by 1 Laborer (Silver)",
)
async def cmd_island(
    interaction: discord.Interaction,
    plots_count: app_commands.Range[int, 1, 200],
    seed_price: int,
    crop_sell_price: int,
    use_focus: bool = True,
    city_farming_bonus: bool = True,
    base_seed_return_pct: float = 73.3,
    focus_seed_return_pct: float = 106.7,
    farming_fce: int = 10000,
    laborer_count: int = 0,
    empty_journal_price: int = 0,
    full_journal_price: int = 0,
    laborer_yield_value: int = 0,
) -> None:
    res = compute_island_economy(
        plots_count=plots_count,
        seed_unit_price=float(seed_price),
        crop_unit_sell_price=float(crop_sell_price),
        base_seed_return_no_focus=base_seed_return_pct / 100.0,
        seed_return_with_focus=focus_seed_return_pct / 100.0,
        use_focus=use_focus,
        city_farming_bonus=city_farming_bonus,
        farming_fce=farming_fce,
        laborer_count=laborer_count,
        empty_journal_price=float(empty_journal_price),
        full_journal_price=float(full_journal_price),
        laborer_yield_value=float(laborer_yield_value),
    )

    embed = discord.Embed(
        title=f"🏝️ Personal Island Daily Economy ({res.plots_count} Plots / {res.total_tiles} Tiles)",
        description=(
            f"**Watering with Focus:** `{'Yes' if use_focus else 'No'}` | "
            f"**City +10% Yield Bonus:** `{'Active' if city_farming_bonus else 'Inactive'}`"
        ),
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="🌾 Farming / Herb Plot Breakdown",
        value=(
            f"• **Initial Seed Value:** {format_silver(res.total_seed_cost)} Silver\n"
            f"• **Returned Seeds Value:** +{format_silver(res.seed_return_value)} Silver\n"
            f"• **Net Seed Cost / Surplus:** {format_silver(-res.net_seed_expense)} Silver\n"
            f"• **Harvested Yield (~{res.total_crop_yield:.0f} units):** {format_silver(res.gross_crop_revenue)} Silver\n"
            f"• **Market Tax (6.5%):** -{format_silver(res.market_tax)} Silver\n"
            f"• **Net Daily Farming Profit:** **{format_silver(res.net_Farming_profit)} Silver**"
        ),
        inline=False,
    )

    if laborer_count > 0:
        embed.add_field(
            name=f"🏠 Island Laborers ({laborer_count} Laborers)",
            value=(
                f"• **Journal Turn-In Cost (Full - Empty):** {format_silver(max(0, full_journal_price - empty_journal_price))} Silver/ea\n"
                f"• **Net Laborer Profit (After 6.5% Tax):** **{format_silver(res.laborer_profit_total)} Silver/Day**"
            ),
            inline=False,
        )

    summary_lines = [
        f"• **Combined Daily Profit:** **{format_silver(res.combined_daily_profit)} Silver / Day**",
        f"• **Monthly Projection (30d):** **{format_silver(res.combined_daily_profit * 30)} Silver / Month**",
    ]
    if use_focus:
        summary_lines.append(f"• **Focus Used & SPF:** `{format_silver(res.focus_used)} Focus` (`{format_silver(res.silver_per_focus)} Silver/Focus`)")

    embed.add_field(name="💰 Total Island Income Summary", value="\n".join(summary_lines), inline=False)
    embed.set_footer(text="Albion Multi Tool • Island Calculator • AI-Built Open-Source Bot")
    await interaction.response.send_message(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 7: /lootsplit - Criteria-Based & Customizable Guild Loot Split
# ----------------------------------------------------------------------------
LOOT_RULE_CHOICES = [
    app_commands.Choice(name="⚖️ Equal Split (Everyone gets an equal 1.0x share)", value="equal"),
    app_commands.Choice(name="🛡️ Role-Weighted Split (Priority roles get higher weight)", value="role_weighted"),
    app_commands.Choice(name="🔧 Repair & Regear Priority (Deducts Repair + Regear first)", value="repair_priority"),
]


@bot.tree.command(name="lootsplit", description="Calculate Guild Loot Split using preset criteria and player-defined rules.")
@app_commands.describe(
    estimated_loot="Estimated Market Value (EMV) of all looted items in chest (Silver)",
    participants="Total number of participating players",
    rule_preset="Select loot split rule criteria (Equal, Role-Weighted, or Repair Priority)",
    silver_bags="Raw silver bags collected (Exempt from market tax, Default: 0)",
    repair_cost="Total party repair cost to deduct first (Default: 0)",
    regear_reserve="Extra silver reserved for regears before splitting (Default: 0)",
    market_tax_pct="Market sales + setup tax percentage (Default: 6.5%)",
    guild_cut_pct="Guild treasury tax percentage (Default: 10%)",
    caller_bonus_pct="Shotcaller flat bonus percentage from net pool (Default: 0%)",
    special_roles_count="Number of Priority Roles (Tanks/Healers/Scouts) in Role-Weighted mode",
    special_role_weight="Share multiplier for Priority Roles (e.g., 1.5 = +50% share)",
    session_name="Event title or party notes (e.g., '20:00 UTC Ava Raid / ZvZ Roam')",
)
@app_commands.choices(rule_preset=LOOT_RULE_CHOICES)
async def cmd_lootsplit(
    interaction: discord.Interaction,
    estimated_loot: int,
    participants: app_commands.Range[int, 1, 200],
    rule_preset: str = "equal",
    silver_bags: int = 0,
    repair_cost: int = 0,
    regear_reserve: int = 0,
    market_tax_pct: float = 6.5,
    guild_cut_pct: float = 10.0,
    caller_bonus_pct: float = 0.0,
    special_roles_count: int = 0,
    special_role_weight: float = 1.5,
    session_name: str = "Guild Content Session",
) -> None:
    res = compute_loot_split(
        estimated_loot_value=estimated_loot,
        total_participants=participants,
        rule_preset=rule_preset,
        silver_bags=silver_bags,
        repair_cost=repair_cost,
        regear_reserve=regear_reserve,
        market_tax_pct=market_tax_pct,
        guild_cut_pct=guild_cut_pct,
        caller_bonus_pct=caller_bonus_pct,
        special_roles_count=special_roles_count,
        special_role_weight=special_role_weight,
    )

    preset_titles = {
        "equal": "Equal Split (1.0x All Members)",
        "role_weighted": f"Role-Weighted ({res.special_role_weight}x Priority Roles / 1.0x Standard)",
        "repair_priority": "Repair & Regear Reserve Priority",
    }

    embed = discord.Embed(
        title=f"⚔️ Guild Loot Split Report — {session_name}",
        description=f"**Active Rule Criteria:** `{preset_titles.get(rule_preset, rule_preset)}`",
        color=discord.Color.purple(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(
        name="📦 Gross Pool & Deductions",
        value=(
            f"• **Estimated Item Loot (EMV):** {format_silver(res.gross_loot_value)} Silver\n"
            f"• **Silver Bags (Tax-Free):** +{format_silver(res.silver_bags)} Silver\n"
            f"• **Market Tax ({res.market_tax_pct}%):** -{format_silver(res.market_tax_amount)} Silver\n"
            f"• **Repair Cost:** -{format_silver(res.repair_cost)} Silver\n"
            f"• **Regear Reserve:** -{format_silver(res.regear_reserve)} Silver\n"
            f"• **Net Pool After Expenses:** **{format_silver(res.net_after_deductions)} Silver**"
        ),
        inline=False,
    )
    embed.add_field(
        name="🏦 Guild & Shotcaller Allocations",
        value=(
            f"• **Guild Cut ({res.guild_cut_pct}%):** {format_silver(res.guild_cut_amount)} Silver\n"
            f"• **Shotcaller Bonus ({res.caller_bonus_pct}%):** {format_silver(res.caller_bonus_amount)} Silver\n"
            f"• **Distributable Member Pool:** **{format_silver(res.distributable_pool)} Silver**"
        ),
        inline=False,
    )

    if rule_preset == "role_weighted" and res.special_roles_count > 0:
        payout_text = (
            f"🛡️ **Priority Roles ({res.special_roles_count}x @ {res.special_role_weight}x Weight):** "
            f"**`{format_silver(res.special_role_payout)} Silver` / each**\n"
            f"⚔️ **Standard Members ({res.regular_members_count}x @ 1.0x Weight):** "
            f"**`{format_silver(res.regular_member_payout)} Silver` / each**"
        )
    else:
        payout_text = f"🎉 **Payout per Member ({res.total_participants} Players):** **`{format_silver(res.regular_member_payout)} Silver`**"

    embed.add_field(name="👥 Final Player Payouts", value=payout_text, inline=False)
    embed.set_footer(text=f"Calculated by {interaction.user.display_name} • Albion Multi Tool")
    await interaction.response.send_message(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 8: /arbitrage - Cross-City & Black Market Flipper
# ----------------------------------------------------------------------------
@bot.tree.command(name="arbitrage", description="Find profitable cross-city and Black Market flipping routes for an item.")
@app_commands.describe(
    item="Item name or ID (e.g., 't6 cleric robe', '6.1 bag', 't7 broadsword')",
    quality="Item quality (1-5)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(server=SERVER_CHOICES)
async def cmd_arbitrage(
    interaction: discord.Interaction,
    item: str,
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    item_id = resolve_item_id(item)
    records = await bot.fetch_market_prices([item_id], server=active_server, qualities=[quality])

    if not records:
        await interaction.followup.send(f"⚠️ No price data found for `{item_id}`.")
        return

    sell_offers = [(r["city"], r["sell_price_min"], r["sell_price_min_date"]) for r in records if r.get("sell_price_min", 0) > 0]
    buy_orders = [(r["city"], r["buy_price_max"], r["buy_price_max_date"]) for r in records if r.get("buy_price_max", 0) > 0]

    if not sell_offers:
        await interaction.followup.send(f"⚠️ No active Sell Orders found for `{item_id}`.")
        return

    sell_offers.sort(key=lambda x: x[1])
    cheapest_city, cheapest_price, cheapest_date = sell_offers[0]

    embed = discord.Embed(
        title=f"🚚 Cross-City & Black Market Arbitrage: {item_id}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Cheapest Buy Location:** **{cheapest_city}** — "
            f"`{format_silver(cheapest_price)} Silver` *({format_timestamp_age(cheapest_date)})*"
        ),
        color=discord.Color.orange(),
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{item_id}.png?quality={quality}")

    routes: List[str] = []
    for city, price, dt_str in sorted(sell_offers, key=lambda x: x[1], reverse=True):
        if city == cheapest_city:
            continue
        net_after_tax = price * 0.935
        profit = net_after_tax - cheapest_price
        roi = (profit / cheapest_price * 100.0) if cheapest_price > 0 else 0.0
        if profit > 0:
            routes.append(
                f"• **{cheapest_city} ➔ {city} (Sell Order):** List `{format_silver(price)}` | "
                f"Net: **`+{format_silver(profit)}`** (`+{roi:.1f}%`) *({format_timestamp_age(dt_str)})*"
            )

    instant_routes: List[str] = []
    for city, b_price, dt_str in sorted(buy_orders, key=lambda x: x[1], reverse=True):
        net_instant = b_price * 0.96
        profit = net_instant - cheapest_price
        roi = (profit / cheapest_price * 100.0) if cheapest_price > 0 else 0.0
        if profit > 0:
            instant_routes.append(
                f"• **{cheapest_city} ➔ {city} (Instant Buy Order):** `{format_silver(b_price)}` | "
                f"Net: **`+{format_silver(profit)}`** (`+{roi:.1f}%`) *({format_timestamp_age(dt_str)})*"
            )

    embed.add_field(
        name="📈 Sell Order Transport Routes (6.5% Tax Deducted)",
        value="\n".join(routes[:5]) if routes else "No profitable Sell Order routes found right now.",
        inline=False,
    )
    embed.add_field(
        name="⚡ Instant Cash Routes (Buy Orders / Black Market - 4% Tax Deducted)",
        value="\n".join(instant_routes[:5]) if instant_routes else "No profitable instant Buy Order routes found right now.",
        inline=False,
    )
    embed.set_footer(text="Albion Multi Tool • Account for Red Zone transport risk when hauling to Caerleon/Black Market!")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMANDS 9, 10, 11: /alert_add, /alert_list, /alert_remove (25-30%+ Price Drop Alerts)
# ----------------------------------------------------------------------------
@bot.tree.command(name="alert_add", description="Get notified when an item drops 25-30%+ below its average market price.")
@app_commands.describe(
    item="Item name or ID to watch (e.g., '6.1 plank', 't7 carving sword', 'T6_BAG')",
    drop_threshold_pct="Alert when price is this % below market average (Default: 25%)",
    quality="Item quality (1-5)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(server=SERVER_CHOICES)
async def cmd_alert_add(
    interaction: discord.Interaction,
    item: str,
    drop_threshold_pct: app_commands.Range[float, 10.0, 80.0] = 25.0,
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    active_server = get_user_server(interaction.user.id, server)
    item_id = resolve_item_id(item)

    alerts: List[Dict[str, Any]] = load_json_file(PRICE_ALERTS_FILE, [])
    new_alert = {
        "user_id": interaction.user.id,
        "channel_id": interaction.channel_id,
        "item_id": item_id,
        "quality": quality,
        "server": active_server,
        "threshold_pct": drop_threshold_pct,
        "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    alerts.append(new_alert)
    save_json_file(PRICE_ALERTS_FILE, alerts)

    await interaction.response.send_message(
        f"🔔 **Price Drop Alert Activated!**\n"
        f"• **Item:** `{item_id}` (Quality: {QUALITY_NAMES.get(quality, 'Normal')})\n"
        f"• **Server:** {SERVER_LABELS.get(active_server)}\n"
        f"• **Trigger Condition:** At least **`-{drop_threshold_pct:.1f}%`** below market average price.\n"
        f"*(The bot checks live AODP prices every 10 minutes and will ping you in this channel.)*"
    )


@bot.tree.command(name="alert_list", description="View all active market price drop alerts registered by you.")
async def cmd_alert_list(interaction: discord.Interaction) -> None:
    alerts: List[Dict[str, Any]] = load_json_file(PRICE_ALERTS_FILE, [])
    user_alerts = [a for a in alerts if int(a.get("user_id", 0)) == interaction.user.id]

    if not user_alerts:
        await interaction.response.send_message("🔕 You currently have no active price drop alerts. Use `/alert_add` to create one!", ephemeral=True)
        return

    lines = [
        f"**{idx + 1}.** `{a['item_id']}` (Q{a.get('quality', 1)}) — **{SERVER_LABELS.get(a.get('server', 'eu'))}** "
        f"| Trigger: `-{a.get('threshold_pct', 25)}%` below avg"
        for idx, a in enumerate(user_alerts)
    ]
    embed = discord.Embed(
        title="🔔 Your Active Market Price Drop Alerts",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Use /alert_remove <item> to delete an alert • Albion Multi Tool")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="alert_remove", description="Remove an item from your active price drop alerts.")
@app_commands.describe(item="Item name or ID to remove (or type 'all' to clear all your alerts)")
async def cmd_alert_remove(interaction: discord.Interaction, item: str) -> None:
    alerts: List[Dict[str, Any]] = load_json_file(PRICE_ALERTS_FILE, [])
    if item.strip().lower() == "all":
        remaining = [a for a in alerts if int(a.get("user_id", 0)) != interaction.user.id]
        save_json_file(PRICE_ALERTS_FILE, remaining)
        await interaction.response.send_message("🗑️ All of your price drop alerts have been cleared.", ephemeral=True)
        return

    target_id = resolve_item_id(item)
    remaining = [
        a for a in alerts
        if not (int(a.get("user_id", 0)) == interaction.user.id and a.get("item_id") == target_id)
    ]
    save_json_file(PRICE_ALERTS_FILE, remaining)
    await interaction.response.send_message(f"🗑️ Removed price alerts matching `{target_id}`.", ephemeral=True)


if __name__ == "__main__":
    token = load_bot_token()
    if not token:
        print(
            "ERROR: DISCORD_BOT_TOKEN not found!\n"
            "Please create a .env (or .env.txt) file with DISCORD_BOT_TOKEN=your_token_here or export it in your environment."
        )
    else:
        bot.run(token)