"""
============================================================================================
ALBION MULTI TOOL v4.0 — Open-Source Albion Online Economy, Crafting, Island & Guild Bot
============================================================================================
Notice       : This project is an AI-generated / AI-assisted open-source Discord bot built
               for the Albion Online community. Released under the MIT License.
Data Sources : The Albion Online Data Project (AODP) REST API v2, Official Albion Render API,
               and ao-bin-dumps full in-game item index (12,000+ items).
Servers      : Europe (EU), Americas (West), Asia (East)
Dependencies : discord.py >= 2.3.0, aiohttp >= 3.9.0, python-dotenv >= 1.0.0

v4.0 Highlights:
- T3 to T8 Refining support (including T3.0 refining with T2 refined input)
- Universal Item Resolver: Accepts ANY valid Albion Online item name/ID (downloads & caches
  the full ao-bin-dumps item catalog on startup + rich offline fallback dictionary) with
  clean Tier.Enchant (e.g. '6.1', '4.2', '8.0') and Quality inputs (no forced popup clutter)
- /bmsc          : Bulk Black Market Flipper scanning entire equipment categories
- /kitchen       : Live Food (Caerleon +15%) & Potion (Brecilien +15%) cooking/alchemy calculator
- /island        : Detailed Farming/Herbs/Pasture + Laborer Happiness & Journal turn-in engine
- /lootsplit + /balance + /balance_manage : Full Guild Loot Split & Member Silver Balance Ledger
- 24/7 Keep-Alive HTTP Health Server (for Render, Koyeb, UptimeRobot, Fly.io & Cloud VPS)
============================================================================================
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from aiohttp import web
import discord
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
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

ROYAL_CITIES: List[str] = [
    "Bridgewatch",
    "Fort Sterling",
    "Lymhurst",
    "Martlock",
    "Thetford",
    "Caerleon",
    "Brecilien",
]

QUALITY_NAMES: Dict[int, str] = {
    1: "Normal",
    2: "Good",
    3: "Outstanding",
    4: "Excellent",
    5: "Masterpiece",
}

TAX_MODES: Dict[str, Tuple[str, float]] = {
    "premium_order": ("Premium Sell Order (6.5% Tax)", 0.065),
    "premium_instant": ("Premium Instant Sell (4.0% Tax)", 0.040),
    "no_premium_order": ("Standard Sell Order (10.5% Tax)", 0.105),
    "direct_trade": ("Direct Trade / Discord (0% Tax)", 0.000),
}

ENCHANT_MATERIAL_COUNTS: Dict[str, int] = {
    "2h_weapon": 384,
    "1h_weapon": 288,
    "armor_bag": 192,
    "head_shoes_cape_offhand": 96,
}

BM_SCANNER_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "bags_capes": {
        "label": "🎒 Bags & Capes",
        "items": ["BAG", "BAG_INSIGHT", "CAPE"],
    },
    "swords_axes": {
        "label": "⚔️ Swords & Axes",
        "items": ["MAIN_SWORD", "2H_CLAYMORE", "2H_DUALSWORD", "MAIN_AXE", "2H_AXE", "2H_HALBERD"],
    },
    "bows_daggers_xbow": {
        "label": "🏹 Bows, Daggers & Crossbows",
        "items": ["2H_BOW", "2H_WARBOW", "2H_LONGBOW", "MAIN_DAGGER", "2H_DAGGERPAIR", "MAIN_1HCROSSBOW", "2H_CROSSBOW"],
    },
    "magic_staffs": {
        "label": "🪄 Fire, Holy, Nature, Frost & Cursed Staffs",
        "items": ["MAIN_FIRESTAFF", "2H_FIRESTAFF", "MAIN_HOLYSTAFF", "2H_HOLYSTAFF", "MAIN_NATURESTAFF", "MAIN_FROSTSTAFF", "MAIN_CURSEDSTAFF"],
    },
    "cloth_armor": {
        "label": "🧙‍♂️ Cloth Robes, Cowls & Sandals",
        "items": [
            "ARMOR_CLOTH_SET1", "ARMOR_CLOTH_SET2", "ARMOR_CLOTH_SET3",
            "HEAD_CLOTH_SET1", "HEAD_CLOTH_SET2", "HEAD_CLOTH_SET3",
            "SHOES_CLOTH_SET1", "SHOES_CLOTH_SET2", "SHOES_CLOTH_SET3",
        ],
    },
    "leather_armor": {
        "label": "🦌 Leather Jackets, Hoods & Shoes",
        "items": [
            "ARMOR_LEATHER_SET1", "ARMOR_LEATHER_SET2", "ARMOR_LEATHER_SET3",
            "HEAD_LEATHER_SET1", "HEAD_LEATHER_SET2", "HEAD_LEATHER_SET3",
            "SHOES_LEATHER_SET1", "SHOES_LEATHER_SET2", "SHOES_LEATHER_SET3",
        ],
    },
    "plate_armor": {
        "label": "🛡️ Plate Armors, Helmets & Boots",
        "items": [
            "ARMOR_PLATE_SET1", "ARMOR_PLATE_SET2", "ARMOR_PLATE_SET3",
            "HEAD_PLATE_SET1", "HEAD_PLATE_SET2", "HEAD_PLATE_SET3",
            "SHOES_PLATE_SET1", "SHOES_PLATE_SET2", "SHOES_PLATE_SET3",
        ],
    },
}

KITCHEN_RECIPES: Dict[str, Dict[str, Any]] = {
    "t8_beef_stew": {
        "name": "T8 Beef Stew (DPS Meal)",
        "output_id": "T8_MEAL_STEW",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 1022,
        "item_value": 648,
        "ingredients": [("T8_PUMPKIN", 36), ("T4_BREAD", 36), ("T8_MEAT", 72)],
    },
    "t7_pork_omelette": {
        "name": "T7 Pork Omelette (Cooldown Meal)",
        "output_id": "T7_MEAL_OMELETTE",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 584,
        "item_value": 468,
        "ingredients": [("T7_CORN", 36), ("T7_MEAT", 72), ("T5_EGG", 18)],
    },
    "t7_pork_pie": {
        "name": "T7 Pork Pie (Gathering & Carry Weight Meal)",
        "output_id": "T7_MEAL_PIE",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 584,
        "item_value": 468,
        "ingredients": [("T7_CORN", 18), ("T4_FLOUR", 36), ("T7_MEAT", 72), ("T6_MILK", 18)],
    },
    "t8_beef_sandwich": {
        "name": "T8 Beef Sandwich (Tank Max HP Meal)",
        "output_id": "T8_MEAL_SANDWICH",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 1022,
        "item_value": 648,
        "ingredients": [("T8_PUMPKIN", 18), ("T4_BREAD", 36), ("T8_MEAT", 72), ("T8_BUTTER", 18)],
    },
    "t6_potato_salad": {
        "name": "T6 Potato Salad (Crafting Quality Meal)",
        "output_id": "T6_MEAL_SALAD",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 334,
        "item_value": 288,
        "ingredients": [("T6_POTATO", 72), ("T6_AGARIC", 72)],
    },
    "t7_roast_pork": {
        "name": "T7 Roast Pork (Lifesteal PvE Meal)",
        "output_id": "T7_MEAL_ROAST",
        "output_per_craft": 10,
        "bonus_city": "Caerleon",
        "base_focus": 584,
        "item_value": 468,
        "ingredients": [("T7_MEAT", 72), ("T7_CORN", 36), ("T6_MILK", 36)],
    },
    "t6_healing_potion": {
        "name": "T6 Major Healing Potion",
        "output_id": "T6_POTION_HEAL",
        "output_per_craft": 5,
        "bonus_city": "Brecilien",
        "base_focus": 334,
        "item_value": 216,
        "ingredients": [("T6_FOXGLOVE", 72), ("T5_EGG", 18), ("T6_ALCOHOL", 18)],
    },
    "t8_poison_potion": {
        "name": "T8 Major Poison Potion",
        "output_id": "T8_POTION_COOLDOWN",
        "output_per_craft": 5,
        "bonus_city": "Brecilien",
        "base_focus": 1022,
        "item_value": 504,
        "ingredients": [("T8_YARROW", 72), ("T7_MULLEIN", 36), ("T5_MILK", 18), ("T8_ALCOHOL", 18)],
    },
    "t7_gigantify_potion": {
        "name": "T7 Major Gigantify Potion",
        "output_id": "T7_POTION_REVIVE",
        "output_per_craft": 5,
        "bonus_city": "Brecilien",
        "base_focus": 584,
        "item_value": 360,
        "ingredients": [("T7_MULLEIN", 72), ("T4_BURDOCK", 36), ("T5_EGG", 18), ("T7_ALCOHOL", 18)],
    },
    "t7_resistance_potion": {
        "name": "T7 Major Resistance Potion",
        "output_id": "T7_POTION_STONESKIN",
        "output_per_craft": 5,
        "bonus_city": "Brecilien",
        "base_focus": 584,
        "item_value": 360,
        "ingredients": [("T7_MULLEIN", 72), ("T6_FOXGLOVE", 36), ("T4_MILK", 18), ("T7_ALCOHOL", 18)],
    },
}

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
# T3 requires 2x T3 Raw + 1x T2 Refined!
REFINING_RECIPE_RATIOS: Dict[int, Tuple[int, int]] = {
    2: (1, 0),
    3: (2, 1),
    4: (2, 1),
    5: (3, 1),
    6: (4, 1),
    7: (5, 1),
    8: (5, 1),
}

# Base Refining Focus Cost per unit at 0 Mastery / 0 Spec (Includes T3.0 = 31)
BASE_REFINING_FOCUS: Dict[Tuple[int, int], int] = {
    (3, 0): 31,   (3, 1): 31,   (3, 2): 31,   (3, 3): 31,   (3, 4): 31,
    (4, 0): 54,   (4, 1): 94,   (4, 2): 164,  (4, 3): 287,  (4, 4): 503,
    (5, 0): 94,   (5, 1): 164,  (5, 2): 287,  (5, 3): 503,  (5, 4): 880,
    (6, 0): 164,  (6, 1): 287,  (6, 2): 503,  (6, 3): 880,  (6, 4): 1539,
    (7, 0): 287,  (7, 1): 503,  (7, 2): 880,  (7, 3): 1539, (7, 4): 2694,
    (8, 0): 503,  (8, 1): 880,  (8, 2): 1539, (8, 3): 2694, (8, 4): 4714,
}

# Comprehensive Built-in Item Dictionary (Fallback + Instant Lookup alongside ao-bin-dumps)
COMMON_ITEM_ALIASES: Dict[str, str] = {
    # Bags & Capes
    "bag": "BAG",
    "satchel": "BAG_INSIGHT",
    "satchel of insight": "BAG_INSIGHT",
    "cape": "CAPE",
    "bridgewatch cape": "CAPEITEM_FW_BRIDGEWATCH",
    "fort sterling cape": "CAPEITEM_FW_FORTSTERLING",
    "lymhurst cape": "CAPEITEM_FW_LYMHURST",
    "martlock cape": "CAPEITEM_FW_MARTLOCK",
    "thetford cape": "CAPEITEM_FW_THETFORD",
    "caerleon cape": "CAPEITEM_FW_CAERLEON",
    "brecilien cape": "CAPEITEM_FW_BRECILIEN",
    "heretic cape": "CAPEITEM_HERETIC",
    "undead cape": "CAPEITEM_UNDEAD",
    "keeper cape": "CAPEITEM_KEEPER",
    "morgana cape": "CAPEITEM_MORGANA",
    "demon cape": "CAPEITEM_DEMON",
    "avalonian cape": "CAPEITEM_AVALON",
    # Swords
    "broadsword": "MAIN_SWORD",
    "claymore": "2H_CLAYMORE",
    "dual swords": "2H_DUALSWORD",
    "dualsword": "2H_DUALSWORD",
    "clarent blade": "MAIN_SCIMITAR_MORGANA",
    "carving": "2H_CLEAVER_HELL",
    "carving sword": "2H_CLEAVER_HELL",
    "galatine pair": "2H_DUALSCIMITAR_UNDEAD",
    "kingmaker": "2H_CLAYMORE_AVALON",
    "infinity blade": "MAIN_SWORD_CRYSTAL",
    # Axes
    "battleaxe": "MAIN_AXE",
    "greataxe": "2H_AXE",
    "halberd": "2H_HALBERD",
    "carrioncaller": "2H_HALBERD_MORGANA",
    "infernal scythe": "2H_SCYTHE_HELL",
    "bearpaws": "2H_DUALAXE_KEEPER",
    "bear paws": "2H_DUALAXE_KEEPER",
    "realmbreaker": "2H_AXE_AVALON",
    "crystal reaper": "2H_SCYTHE_CRYSTAL",
    # Maces & Hammers
    "mace": "MAIN_MACE",
    "heavy mace": "2H_MACE",
    "morning star": "2H_FLAIL",
    "bedrock mace": "MAIN_ROCKMACE_KEEPER",
    "incubus mace": "MAIN_MACE_HELL",
    "camlann mace": "2H_MACE_MORGANA",
    "oathkeepers": "2H_DUALMACE_AVALON",
    "hammer": "MAIN_HAMMER",
    "polehammer": "2H_POLEHAMMER",
    "great hammer": "2H_HAMMER",
    "tombhammer": "2H_HAMMER_UNDEAD",
    "forge hammers": "2H_DUALHAMMER_HELL",
    "grovekeeper": "2H_RAM_KEEPER",
    "hand of justice": "2H_HAMMER_AVALON",
    # Bows, Crossbows, Daggers, Spears
    "bow": "2H_BOW",
    "warbow": "2H_WARBOW",
    "longbow": "2H_LONGBOW",
    "whispering bow": "2H_LONGBOW_UNDEAD",
    "wailing bow": "2H_BOW_KEEPER",
    "bow of badon": "2H_BOW_HELL",
    "badon": "2H_BOW_HELL",
    "mistpiercer": "2H_BOW_AVALON",
    "skystrider bow": "2H_BOW_CRYSTAL",
    "crossbow": "2H_CROSSBOW",
    "heavy crossbow": "2H_CROSSBOWLARGE",
    "light crossbow": "MAIN_1HCROSSBOW",
    "weeping repeater": "2H_REPEATINGCROSSBOW_UNDEAD",
    "boltcasters": "2H_DUALCROSSBOW_HELL",
    "boltcaster": "2H_DUALCROSSBOW_HELL",
    "siegebow": "2H_CROSSBOWLARGE_MORGANA",
    "energy shaper": "2H_CROSSBOW_CANNON_AVALON",
    "dagger": "MAIN_DAGGER",
    "dagger pair": "2H_DAGGERPAIR",
    "claws": "2H_CLAWPAIR",
    "bloodletter": "MAIN_RAPIER_MORGANA",
    "demonfang": "MAIN_DAGGER_HELL",
    "black hands": "2H_IRONGAUNTLETS_HELL",
    "deathgivers": "2H_DUALSICKLE_UNDEAD",
    "bridled fury": "2H_DAGGER_KATAR_AVALON",
    "spear": "MAIN_SPEAR",
    "1h spear": "MAIN_SPEAR",
    "pike": "2H_SPEAR",
    "glaive": "2H_GLAIVE",
    "heron spear": "MAIN_SPEAR_KEEPER",
    "spirithunter": "2H_HARPOON_HELL",
    "trinity spear": "2H_TRIDENT_UNDEAD",
    "daybreaker": "MAIN_SPEAR_LANCE_AVALON",
    # Quarterstaffs, War Gloves, Shapeshifter
    "quarterstaff": "2H_QUARTERSTAFF",
    "iron-clad staff": "2H_IRONCLADEDSTAFF",
    "double bladed staff": "2H_DOUBLEBLADEDSTAFF",
    "black monk stave": "2H_COMBATSTAFF_MORGANA",
    "soulscythe": "2H_TWINSCYTHE_HELL",
    "staff of balance": "2H_ROCKSTAFF_KEEPER",
    "grailseeker": "2H_QUARTERSTAFF_AVALON",
    "brawler gloves": "2H_KNUCKLES_SET1",
    "battle bracers": "2H_KNUCKLES_SET2",
    "spiked gauntlets": "2H_KNUCKLES_SET3",
    "ursine maulers": "2H_KNUCKLES_KEEPER",
    "hellfire hands": "2H_KNUCKLES_HELL",
    "ravenstrike cestus": "2H_KNUCKLES_MORGANA",
    "fists of avalon": "2H_KNUCKLES_AVALON",
    "prowling staff": "2H_SHAPESHIFTER_SET1",
    "rootbound staff": "2H_SHAPESHIFTER_SET2",
    "primal staff": "2H_SHAPESHIFTER_SET3",
    "bloodmoon staff": "2H_SHAPESHIFTER_MORGANA",
    "hellspawn staff": "2H_SHAPESHIFTER_HELL",
    "earthrune staff": "2H_SHAPESHIFTER_KEEPER",
    "lightcaller": "2H_SHAPESHIFTER_AVALON",
    # Magic Staffs
    "fire staff": "MAIN_FIRESTAFF",
    "great fire staff": "2H_FIRESTAFF",
    "infernal staff": "2H_INFERNOSTAFF",
    "wildfire staff": "MAIN_FIRESTAFF_KEEPER",
    "brimstone staff": "2H_FIRESTAFF_HELL",
    "blazing staff": "2H_INFERNOSTAFF_MORGANA",
    "blazing": "2H_INFERNOSTAFF_MORGANA",
    "dawnsong": "2H_FIRE_RINGPAIR_AVALON",
    "holy staff": "MAIN_HOLYSTAFF",
    "great holy staff": "2H_HOLYSTAFF",
    "divine staff": "2H_DIVINESTAFF",
    "lifetouch staff": "MAIN_HOLYSTAFF_MORGANA",
    "fallen staff": "2H_HOLYSTAFF_HELL",
    "fallen": "2H_HOLYSTAFF_HELL",
    "redemption staff": "2H_HOLYSTAFF_UNDEAD",
    "hallowfall": "MAIN_HOLYSTAFF_AVALON",
    "nature staff": "MAIN_NATURESTAFF",
    "great nature staff": "2H_NATURESTAFF",
    "wild staff": "2H_WILDSTAFF",
    "druidic staff": "MAIN_NATURESTAFF_KEEPER",
    "druidic": "MAIN_NATURESTAFF_KEEPER",
    "blight staff": "2H_NATURESTAFF_HELL",
    "blight": "2H_NATURESTAFF_HELL",
    "rampant staff": "2H_NATURESTAFF_KEEPER",
    "ironroot staff": "MAIN_NATURESTAFF_AVALON",
    "frost staff": "MAIN_FROSTSTAFF",
    "great frost staff": "2H_FROSTSTAFF",
    "glacial staff": "2H_GLACIALSTAFF",
    "hoarfrost staff": "MAIN_FROSTSTAFF_KEEPER",
    "icicle staff": "2H_ICEGAUNTLETS_HELL",
    "permafrost prism": "2H_ICECRYSTAL_UNDEAD",
    "permafrost": "2H_ICECRYSTAL_UNDEAD",
    "chillhowl": "MAIN_FROSTSTAFF_AVALON",
    "cursed staff": "MAIN_CURSEDSTAFF",
    "great cursed staff": "2H_CURSEDSTAFF",
    "demonic staff": "2H_DEMONICSTAFF",
    "lifecurse staff": "MAIN_CURSEDSTAFF_UNDEAD",
    "cursed skull": "2H_SKULLORB_HELL",
    "damnation staff": "2H_CURSEDSTAFF_MORGANA",
    "shadowcaller": "MAIN_CURSEDSTAFF_AVALON",
    "arcane staff": "MAIN_ARCANESTAFF",
    "great arcane staff": "2H_ARCANESTAFF",
    "enigmatic staff": "2H_ENIGMATICSTAFF",
    "witchwork staff": "MAIN_ARCANESTAFF_UNDEAD",
    "occult staff": "2H_ARCANESTAFF_HELL",
    "malevolent locus": "2H_ENIGMATICORB_MORGANA",
    "evensong": "2H_ARCANE_RINGPAIR_AVALON",
    # Armors, Helmets, Shoes
    "scholar robe": "ARMOR_CLOTH_SET1",
    "cleric robe": "ARMOR_CLOTH_SET2",
    "mage robe": "ARMOR_CLOTH_SET3",
    "druid robe": "ARMOR_CLOTH_KEEPER",
    "fiend robe": "ARMOR_CLOTH_HELL",
    "cultist robe": "ARMOR_CLOTH_MORGANA",
    "robe of purity": "ARMOR_CLOTH_AVALON",
    "feyscale robe": "ARMOR_CLOTH_FEY",
    "mercenary jacket": "ARMOR_LEATHER_SET1",
    "hunter jacket": "ARMOR_LEATHER_SET2",
    "assassin jacket": "ARMOR_LEATHER_SET3",
    "stalker jacket": "ARMOR_LEATHER_MORGANA",
    "hellion jacket": "ARMOR_LEATHER_HELL",
    "specter jacket": "ARMOR_LEATHER_UNDEAD",
    "jacket of tenacity": "ARMOR_LEATHER_AVALON",
    "mistwalker jacket": "ARMOR_LEATHER_FEY",
    "soldier armor": "ARMOR_PLATE_SET1",
    "knight armor": "ARMOR_PLATE_SET2",
    "guardian armor": "ARMOR_PLATE_SET3",
    "graveguard armor": "ARMOR_PLATE_UNDEAD",
    "demon armor": "ARMOR_PLATE_HELL",
    "judicator armor": "ARMOR_PLATE_KEEPER",
    "armor of valor": "ARMOR_PLATE_AVALON",
    "duskweaver armor": "ARMOR_PLATE_FEY",
    "scholar cowl": "HEAD_CLOTH_SET1",
    "cleric cowl": "HEAD_CLOTH_SET2",
    "mage cowl": "HEAD_CLOTH_SET3",
    "druid cowl": "HEAD_CLOTH_KEEPER",
    "fiend cowl": "HEAD_CLOTH_HELL",
    "cultist cowl": "HEAD_CLOTH_MORGANA",
    "cowl of purity": "HEAD_CLOTH_AVALON",
    "feyscale hat": "HEAD_CLOTH_FEY",
    "mercenary hood": "HEAD_LEATHER_SET1",
    "hunter hood": "HEAD_LEATHER_SET2",
    "assassin hood": "HEAD_LEATHER_SET3",
    "stalker hood": "HEAD_LEATHER_MORGANA",
    "hellion hood": "HEAD_LEATHER_HELL",
    "specter hood": "HEAD_LEATHER_UNDEAD",
    "hood of tenacity": "HEAD_LEATHER_AVALON",
    "mistwalker hood": "HEAD_LEATHER_FEY",
    "soldier helmet": "HEAD_PLATE_SET1",
    "knight helmet": "HEAD_PLATE_SET2",
    "guardian helmet": "HEAD_PLATE_SET3",
    "graveguard helmet": "HEAD_PLATE_UNDEAD",
    "demon helmet": "HEAD_PLATE_HELL",
    "judicator helmet": "HEAD_PLATE_KEEPER",
    "helmet of valor": "HEAD_PLATE_AVALON",
    "duskweaver helmet": "HEAD_PLATE_FEY",
    "scholar sandals": "SHOES_CLOTH_SET1",
    "cleric sandals": "SHOES_CLOTH_SET2",
    "mage sandals": "SHOES_CLOTH_SET3",
    "druid sandals": "SHOES_CLOTH_KEEPER",
    "fiend sandals": "SHOES_CLOTH_HELL",
    "cultist sandals": "SHOES_CLOTH_MORGANA",
    "sandals of purity": "SHOES_CLOTH_AVALON",
    "feyscale sandals": "SHOES_CLOTH_FEY",
    "mercenary shoes": "SHOES_LEATHER_SET1",
    "hunter shoes": "SHOES_LEATHER_SET2",
    "assassin shoes": "SHOES_LEATHER_SET3",
    "stalker shoes": "SHOES_LEATHER_MORGANA",
    "hellion shoes": "SHOES_LEATHER_HELL",
    "specter shoes": "SHOES_LEATHER_UNDEAD",
    "shoes of tenacity": "SHOES_LEATHER_AVALON",
    "mistwalker shoes": "SHOES_LEATHER_FEY",
    "soldier boots": "SHOES_PLATE_SET1",
    "knight boots": "SHOES_PLATE_SET2",
    "guardian boots": "SHOES_PLATE_SET3",
    "graveguard boots": "SHOES_PLATE_UNDEAD",
    "demon boots": "SHOES_PLATE_HELL",
    "judicator boots": "SHOES_PLATE_KEEPER",
    "boots of valor": "SHOES_PLATE_AVALON",
    "duskweaver boots": "SHOES_PLATE_FEY",
    # Off-hands
    "shield": "OFF_SHIELD",
    "sarcophagus": "OFF_TOWERSHIELD_UNDEAD",
    "caitiff shield": "OFF_SHIELD_HELL",
    "facebreaker": "OFF_SPIKEDSHIELD_MORGANA",
    "astral aegis": "OFF_SHIELD_AVALON",
    "tome of spells": "OFF_BOOK",
    "eye of secrets": "OFF_ORB_MORGANA",
    "muisak": "OFF_DEMONSKULL_HELL",
    "taproot": "OFF_TOTEM_KEEPER",
    "celestial censer": "OFF_CENSER_AVALON",
    "torch": "OFF_TORCH",
    "mistcaller": "OFF_HORN_KEEPER",
    "leering cane": "OFF_JESTERCANE_HELL",
    "cryptcandle": "OFF_LAMP_UNDEAD",
    "sacred scepter": "OFF_TALISMAN_AVALON",
    # Consumables & Mounts & Materials
    "pork omelette": "MEAL_OMELETTE",
    "omelette": "MEAL_OMELETTE",
    "beef stew": "MEAL_STEW",
    "stew": "MEAL_STEW",
    "pork pie": "MEAL_PIE",
    "beef sandwich": "MEAL_SANDWICH",
    "potato salad": "MEAL_SALAD",
    "roast pork": "MEAL_ROAST",
    "healing potion": "POTION_HEAL",
    "poison potion": "POTION_COOLDOWN",
    "gigantify potion": "POTION_REVIVE",
    "resistance potion": "POTION_STONESKIN",
    "riding horse": "MOUNT_HORSE",
    "armored horse": "MOUNT_ARMORED_HORSE",
    "ox": "MOUNT_OX",
    "transport ox": "MOUNT_OX",
    "stag": "MOUNT_GIANTSTAG",
    "swiftclaw": "MOUNT_COUGAR_KEEPER",
    "direwolf": "MOUNT_DIREWOLF",
    "direboar": "MOUNT_DIREBOAR",
    "mammoth": "MOUNT_MAMMOTH_TRANSPORT",
    "ore": "ORE",
    "bar": "METALBAR",
    "metal bar": "METALBAR",
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
    "stone block": "STONEBLOCK",
    "stoneblock": "STONEBLOCK",
    "rune": "RUNE",
    "soul": "SOUL",
    "relic": "RELIC",
}

TIER_PREFIX_WORDS = {
    "beginner's", "beginners",
    "novice's", "novices",
    "journeyman's", "journeymans",
    "adept's", "adepts",
    "expert's", "experts",
    "master's", "masters",
    "grandmaster's", "grandmasters",
    "elder's", "elders",
}

USER_PREFS_FILE = BASE_DIR / "user_preferences.json"
GUILD_BALANCES_FILE = BASE_DIR / "guild_balances.json"
ITEMS_CACHE_FILE = BASE_DIR / "items_index_cache.json"

# Global dynamic lookup map populated on startup from ao-bin-dumps (maps lowercase English base name -> base UniqueName)
DYNAMIC_ITEM_INDEX: Dict[str, str] = {}


# ============================================================================
# 2. PERSISTENT STORAGE, GUILD BALANCE LEDGER & FORMATTING HELPERS
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
    if explicit_server in AODP_SERVERS:
        return explicit_server
    prefs: Dict[str, str] = load_json_file(USER_PREFS_FILE, {})
    return prefs.get(str(user_id), "eu")


def set_user_server(user_id: int, server: str) -> None:
    prefs: Dict[str, str] = load_json_file(USER_PREFS_FILE, {})
    prefs[str(user_id)] = server
    save_json_file(USER_PREFS_FILE, prefs)


def update_member_balance(
    guild_id: int,
    user_id: int,
    user_name: str,
    delta_silver: int,
    is_payout: bool = False,
) -> Dict[str, int]:
    """
    Updates a member's Guild Loot Split Silver balance in `guild_balances.json`.
    Returns {"balance": current_balance, "total_earned": ..., "total_paid": ...}.
    """
    db: Dict[str, Dict[str, Any]] = load_json_file(GUILD_BALANCES_FILE, {})
    g_key = str(guild_id)
    u_key = str(user_id)
    guild_map = db.setdefault(g_key, {})
    rec = guild_map.get(u_key, {"name": user_name, "balance": 0, "total_earned": 0, "total_paid": 0})
    rec["name"] = user_name

    if is_payout:
        paid_amt = abs(delta_silver)
        rec["balance"] = max(0, int(rec.get("balance", 0)) - paid_amt)
        rec["total_paid"] = int(rec.get("total_paid", 0)) + paid_amt
    else:
        rec["balance"] = max(0, int(rec.get("balance", 0)) + delta_silver)
        if delta_silver > 0:
            rec["total_earned"] = int(rec.get("total_earned", 0)) + delta_silver

    guild_map[u_key] = rec
    save_json_file(GUILD_BALANCES_FILE, db)
    return rec


def get_member_balance(guild_id: int, user_id: int, user_name: str) -> Dict[str, Any]:
    db: Dict[str, Dict[str, Any]] = load_json_file(GUILD_BALANCES_FILE, {})
    return db.get(str(guild_id), {}).get(
        str(user_id),
        {"name": user_name, "balance": 0, "total_earned": 0, "total_paid": 0},
    )


def get_guild_leaderboard(guild_id: int) -> List[Tuple[str, Dict[str, Any]]]:
    db: Dict[str, Dict[str, Any]] = load_json_file(GUILD_BALANCES_FILE, {})
    g_map = db.get(str(guild_id), {})
    items = list(g_map.items())
    items.sort(key=lambda kv: int(kv[1].get("balance", 0)), reverse=True)
    return items


def format_silver(amount: float) -> str:
    return f"{int(round(amount)):,}"


def format_ansi_profit(amount: float, suffix: str = " Silver") -> str:
    val_str = f"{int(round(amount)):+,}{suffix}"
    if amount >= 0:
        return f"\u001b[1;32m{val_str}\u001b[0m"
    return f"\u001b[1;31m{val_str}\u001b[0m"


def build_sparkline(values: List[float]) -> str:
    if not values:
        return "—"
    bars = "▁▂▃▄▅▆▇█"
    low = min(values)
    high = max(values)
    if high == low:
        return bars[3] * min(len(values), 16)
    sampled = values[:16]
    return "".join(bars[min(7, int((v - low) / (high - low) * 7))] for v in sampled)


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


# ============================================================================
# 3. UNIVERSAL IN-GAME ITEM RESOLVER (12,000+ ITEMS SUPPORT)
# ============================================================================

def parse_tier_enchant_str(tier_enchant_str: str, default_tier: int = 6, default_enchant: int = 0) -> Tuple[int, int]:
    """Parses '6.1', 'T4.2', '8', '5.0' into (tier, enchant)."""
    s = tier_enchant_str.strip().lower().lstrip("t")
    if not s:
        return default_tier, default_enchant
    if "." in s:
        parts = s.split(".", 1)
        t = int(parts[0]) if parts[0].isdigit() else default_tier
        e = int(parts[1]) if parts[1].isdigit() else default_enchant
        return max(1, min(8, t)), max(0, min(4, e))
    if s.isdigit():
        return max(1, min(8, int(s))), default_enchant
    return default_tier, default_enchant


def strip_tier_prefix(name_lower: str) -> str:
    words = name_lower.split()
    if words and words[0] in TIER_PREFIX_WORDS:
        return " ".join(words[1:]).strip()
    return name_lower


def resolve_item_id(user_query: str, tier_enchant: Optional[str] = None) -> str:
    """
    Resolves ANY valid Albion Online item name or ID into its canonical AODP Item ID.
    Supports:
      - Exact IDs (e.g., 'T6_2H_CLEAVER_HELL@1', 'T4_BAG')
      - Separate `tier_enchant` parameter (e.g., item='Cleric Robe', tier_enchant='6.1')
      - Combined string (e.g., '6.1 cleric robe', 't7.2 carving sword', 'Adept's Cleric Robe')
      - Full 12,000+ item lookup from DYNAMIC_ITEM_INDEX (loaded from ao-bin-dumps) + COMMON_ITEM_ALIASES
    """
    q = user_query.strip()
    # 1. If already a canonical ID (T1_.. to T8_.. or UNIQUE_..)
    if re.match(r"^(T[1-8]_|UNIQUE_)", q.upper()):
        raw_id = q.upper()
        if tier_enchant:
            t, e = parse_tier_enchant_str(tier_enchant)
            # Replace T{x}_ prefix if present
            raw_id = re.sub(r"^T[1-8]_", f"T{t}_", raw_id)
            raw_id = raw_id.split("@")[0]
            raw_id = re.sub(r"_LEVEL[1-4]$", "", raw_id)
            base_part = raw_id[3:]
            if base_part in {"ORE", "HIDE", "FIBER", "WOOD", "ROCK", "METALBAR", "LEATHER", "CLOTH", "PLANKS", "STONEBLOCK"}:
                return f"T{t}_{base_part}_LEVEL{e}@{e}" if (e > 0 and t >= 4) else f"T{t}_{base_part}"
            return f"{raw_id}@{e}" if e > 0 else raw_id
        return raw_id

    # 2. Extract embedded tier/enchant from user_query if present
    q_lower = q.lower()
    tokens = q_lower.split()
    inferred_tier = 6
    inferred_enchant = 0
    has_embedded_tier = False
    remaining_tokens: List[str] = []

    for token in tokens:
        clean_tok = token.lstrip("t")
        if "." in clean_tok:
            parts = clean_tok.split(".", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                inferred_tier = int(parts[0])
                inferred_enchant = int(parts[1])
                has_embedded_tier = True
                continue
        elif clean_tok.isdigit() and 1 <= int(clean_tok) <= 8 and token.startswith("t"):
            inferred_tier = int(clean_tok)
            has_embedded_tier = True
            continue
        remaining_tokens.append(token)

    if tier_enchant and tier_enchant.strip():
        tier, enchant = parse_tier_enchant_str(tier_enchant, default_tier=inferred_tier, default_enchant=inferred_enchant)
    elif has_embedded_tier:
        tier, enchant = inferred_tier, inferred_enchant
    else:
        tier, enchant = 6, 0

    item_phrase = strip_tier_prefix(" ".join(remaining_tokens).strip())

    # 3. Look up in DYNAMIC_ITEM_INDEX (full ao-bin-dumps) or COMMON_ITEM_ALIASES
    base_id = COMMON_ITEM_ALIASES.get(item_phrase) or DYNAMIC_ITEM_INDEX.get(item_phrase)

    if not base_id:
        for alias_key, alias_val in COMMON_ITEM_ALIASES.items():
            if alias_key == item_phrase or alias_key in item_phrase:
                base_id = alias_val
                break

    if not base_id and DYNAMIC_ITEM_INDEX:
        for dyn_name, dyn_base in DYNAMIC_ITEM_INDEX.items():
            if item_phrase in dyn_name:
                base_id = dyn_base
                break

    if not base_id:
        base_id = item_phrase.upper().replace(" ", "_")

    # If base_id already starts with T1_..T8_ (e.g., non-tiered specific item from index), adjust tier
    if re.match(r"^T[1-8]_", base_id):
        base_id = base_id[3:]

    resource_bases = {"ORE", "HIDE", "FIBER", "WOOD", "ROCK", "METALBAR", "LEATHER", "CLOTH", "PLANKS", "STONEBLOCK"}
    if base_id in resource_bases:
        if enchant > 0 and tier >= 4:
            return f"T{tier}_{base_id}_LEVEL{enchant}@{enchant}"
        return f"T{tier}_{base_id}"

    if enchant > 0 and tier >= 4:
        return f"T{tier}_{base_id}@{enchant}"
    return f"T{tier}_{base_id}"


def build_resource_item_id(base_key: str, tier: int, enchant: int) -> str:
    if tier <= 3 or enchant == 0:
        return f"T{tier}_{base_key}"
    return f"T{tier}_{base_key}_LEVEL{enchant}@{enchant}"


# ============================================================================
# 4. CORE MATH & ECONOMY ENGINE (T3-T8 REFINING, CRAFTING, ISLAND + JOURNALS)
# ============================================================================

def calculate_rrr(
    location_mode: str = "bonus_city",
    activity: str = "refining",
    use_focus: bool = False,
) -> Tuple[float, float]:
    if location_mode == "island":
        city_base = 0.0
        specialty = 0.0
    elif location_mode == "non_bonus_city":
        city_base = 0.18
        specialty = 0.0
    else:
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
    total_fce = (mastery_level * 30) + (target_spec_level * 280) + (other_specs_sum * 30)
    return base_focus / (2.0 ** (total_fce / 10000.0))


def calculate_station_fee(
    item_value: float,
    station_rate_per_100_nutrition: float,
    quantity: int = 1,
    is_island: bool = False,
) -> float:
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
    tax_label: str
    total_bonus_pct: float
    rrr_pct: float
    unfocused_rrr_pct: float
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
    unfocused_net_profit: float
    roi_pct: float
    focus_per_unit: float
    total_focus_used: float
    silver_per_focus: float
    marginal_spf: float


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
    tax_mode: str = "premium_order",
    mastery_lvl: int = 100,
    target_spec_lvl: int = 100,
    other_specs_sum: int = 400,
) -> RefiningResult:
    """Computes T3 to T8 refining breakdown including Total SPF and Marginal Focus Gain."""
    if tier <= 3:
        enchant = 0
    raw_qty_needed, lower_qty_needed = REFINING_RECIPE_RATIOS.get(tier, (2, 1))
    is_island = location_mode == "island"

    total_bonus, rrr = calculate_rrr(location_mode=location_mode, activity="refining", use_focus=use_focus)
    _, unfocused_rrr = calculate_rrr(location_mode=location_mode, activity="refining", use_focus=False)

    unit_gross_mat_cost = (raw_qty_needed * raw_unit_price) + (lower_qty_needed * lower_refined_unit_price)
    gross_material_cost = unit_gross_mat_cost * quantity

    returned_material_value = gross_material_cost * rrr
    net_material_cost = gross_material_cost - returned_material_value

    unfocused_net_mat_cost = gross_material_cost * (1.0 - unfocused_rrr)

    estimated_item_value = (2 ** (tier - 2 + enchant)) * 4.0 if tier >= 3 else 0.0
    station_fee_total = calculate_station_fee(
        estimated_item_value,
        station_fee_rate,
        quantity,
        is_island=is_island,
    )

    tax_label, total_tax_rate = TAX_MODES.get(tax_mode, TAX_MODES["premium_order"])

    gross_revenue = output_unit_sell_price * quantity
    market_tax_total = gross_revenue * total_tax_rate

    net_profit = gross_revenue - net_material_cost - station_fee_total - market_tax_total
    unfocused_net_profit = gross_revenue - unfocused_net_mat_cost - station_fee_total - market_tax_total

    total_cost = net_material_cost + station_fee_total + market_tax_total
    roi_pct = (net_profit / total_cost * 100.0) if total_cost > 0 else 0.0

    base_focus = BASE_REFINING_FOCUS.get((tier, enchant), 31 if tier == 3 else 150)
    focus_per_unit = calculate_focus_cost(base_focus, mastery_lvl, target_spec_lvl, other_specs_sum)
    total_focus_used = (focus_per_unit * quantity) if use_focus else 0.0
    silver_per_focus = (net_profit / total_focus_used) if (use_focus and total_focus_used > 0) else 0.0
    marginal_spf = ((net_profit - unfocused_net_profit) / (focus_per_unit * quantity)) if (focus_per_unit * quantity) > 0 else 0.0

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
        tax_label=tax_label,
        total_bonus_pct=total_bonus * 100.0,
        rrr_pct=rrr * 100.0,
        unfocused_rrr_pct=unfocused_rrr * 100.0,
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
        unfocused_net_profit=unfocused_net_profit,
        roi_pct=roi_pct,
        focus_per_unit=focus_per_unit,
        total_focus_used=total_focus_used,
        silver_per_focus=silver_per_focus,
        marginal_spf=marginal_spf,
    )


@dataclass
class EnchantFlipStep:
    step_label: str
    from_id: str
    to_id: str
    mat_id: str
    mat_qty: int
    base_item_price: float
    mat_unit_price: float
    total_upgrade_cost: float
    target_sell_price: float
    net_profit_after_tax: float
    roi_pct: float


def compute_enchant_flips(
    base_item_id: str,
    tier: int,
    slot_type: str,
    price_map: Dict[str, float],
    tax_rate: float = 0.065,
) -> List[EnchantFlipStep]:
    mat_qty = ENCHANT_MATERIAL_COUNTS.get(slot_type, 192)
    clean_base = base_item_id.split("@")[0]

    steps_cfg = [
        ("0 ➔ .1 (Runes)", clean_base, f"{clean_base}@1", f"T{tier}_RUNE"),
        (".1 ➔ .2 (Souls)", f"{clean_base}@1", f"{clean_base}@2", f"T{tier}_SOUL"),
        (".2 ➔ .3 (Relics)", f"{clean_base}@2", f"{clean_base}@3", f"T{tier}_RELIC"),
    ]

    results: List[EnchantFlipStep] = []
    for label, src_id, dst_id, mat_id in steps_cfg:
        base_p = price_map.get(src_id, 0.0)
        dst_p = price_map.get(dst_id, 0.0)
        mat_p = price_map.get(mat_id, 0.0)
        if base_p <= 0 or dst_p <= 0 or mat_p <= 0:
            continue
        upgrade_cost = base_p + (mat_qty * mat_p)
        net_revenue = dst_p * (1.0 - tax_rate)
        net_profit = net_revenue - upgrade_cost
        roi = (net_profit / upgrade_cost * 100.0) if upgrade_cost > 0 else 0.0
        results.append(
            EnchantFlipStep(
                step_label=label,
                from_id=src_id,
                to_id=dst_id,
                mat_id=mat_id,
                mat_qty=mat_qty,
                base_item_price=base_p,
                mat_unit_price=mat_p,
                total_upgrade_cost=upgrade_cost,
                target_sell_price=dst_p,
                net_profit_after_tax=net_profit,
                roi_pct=roi,
            )
        )
    return results


@dataclass
class BMFlipCandidate:
    item_id: str
    buy_city: str
    buy_price: float
    bm_sell_order_price: float
    bm_buy_order_price: float
    instant_profit: float
    instant_roi_pct: float
    order_profit: float
    order_roi_pct: float
    updated_age: str


def evaluate_bm_scanner_candidates(records: List[Dict[str, Any]]) -> Tuple[List[BMFlipCandidate], List[BMFlipCandidate]]:
    by_item: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        iid = r.get("item_id", "")
        if iid:
            by_item.setdefault(iid, []).append(r)

    instant_list: List[BMFlipCandidate] = []
    order_list: List[BMFlipCandidate] = []

    for iid, rows in by_item.items():
        bm_sell_min = 0.0
        bm_buy_max = 0.0
        bm_date = ""
        cheapest_royal_city = ""
        cheapest_royal_price = float("inf")

        for row in rows:
            city = row.get("city", "")
            s_min = float(row.get("sell_price_min", 0))
            b_max = float(row.get("buy_price_max", 0))
            if city == "Black Market":
                if s_min > 0:
                    bm_sell_min = s_min
                if b_max > 0:
                    bm_buy_max = b_max
                    bm_date = row.get("buy_price_max_date", "") or row.get("sell_price_min_date", "")
            else:
                if 0 < s_min < cheapest_royal_price:
                    cheapest_royal_price = s_min
                    cheapest_royal_city = city

        if cheapest_royal_price == float("inf") or cheapest_royal_price <= 0:
            continue

        inst_profit = (bm_buy_max * 0.96) - cheapest_royal_price if bm_buy_max > 0 else -1.0
        inst_roi = (inst_profit / cheapest_royal_price * 100.0) if inst_profit > 0 else 0.0

        ord_profit = (bm_sell_min * 0.935) - cheapest_royal_price if bm_sell_min > 0 else -1.0
        ord_roi = (ord_profit / cheapest_royal_price * 100.0) if ord_profit > 0 else 0.0

        cand = BMFlipCandidate(
            item_id=iid,
            buy_city=cheapest_royal_city,
            buy_price=cheapest_royal_price,
            bm_sell_order_price=bm_sell_min,
            bm_buy_order_price=bm_buy_max,
            instant_profit=inst_profit,
            instant_roi_pct=inst_roi,
            order_profit=ord_profit,
            order_roi_pct=ord_roi,
            updated_age=format_timestamp_age(bm_date),
        )
        if inst_profit > 0:
            instant_list.append(cand)
        if ord_profit > 0:
            order_list.append(cand)

    instant_list.sort(key=lambda x: x.instant_profit, reverse=True)
    order_list.sort(key=lambda x: x.order_profit, reverse=True)
    return instant_list, order_list


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
    net_farming_profit: float
    unfocused_farming_profit: float
    laborer_count: int
    laborer_happiness_pct: float
    journal_net_cost_per_laborer: float
    gross_yield_per_laborer: float
    net_profit_per_laborer: float
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
    laborer_happiness_pct: float = 150.0,
    empty_journal_price: float = 0.0,
    full_journal_price: float = 0.0,
    base_100pct_journal_yield_value: float = 0.0,
) -> IslandFarmingResult:
    """
    Detailed Personal/Guild Island Farming (Crops/Herbs/Pastures) + Laborer Journal Calculator.
    - Calculates Farming with & without Focus side-by-side.
    - Calculates Laborer Journal turn-in profit factoring in Laborer Happiness Yield Multiplier
      (e.g., 150% return rate in matching tier house with trophies), Empty vs Full Journal cost, and 6.5% tax.
    """
    total_tiles = plots_count * 9
    total_seed_cost = total_tiles * seed_unit_price

    effective_seed_return = seed_return_with_focus if use_focus else base_seed_return_no_focus
    seed_return_value = total_tiles * effective_seed_return * seed_unit_price
    net_seed_expense = total_seed_cost - seed_return_value

    unfocused_seed_return_val = total_tiles * base_seed_return_no_focus * seed_unit_price
    unfocused_seed_expense = total_seed_cost - unfocused_seed_return_val

    avg_yield_per_tile = 9.0 * (1.10 if city_farming_bonus else 1.0)
    total_crop_yield = total_tiles * avg_yield_per_tile
    gross_crop_revenue = total_crop_yield * crop_unit_sell_price
    market_tax = gross_crop_revenue * 0.065

    net_farming_profit = gross_crop_revenue - market_tax - net_seed_expense
    unfocused_farming_profit = gross_crop_revenue - market_tax - unfocused_seed_expense

    focus_per_tile = 1000.0 / (2.0 ** (farming_fce / 10000.0)) if use_focus else 0.0
    focus_used = total_tiles * focus_per_tile
    spf = (net_farming_profit / focus_used) if (use_focus and focus_used > 0) else 0.0

    # Detailed Laborer & Journal Math:
    # A laborer consumes 1 Full Journal, returns 1 Empty Journal + (Base_Yield * Happiness_Multiplier)
    journal_net_cost = max(0.0, full_journal_price - empty_journal_price)
    gross_yield_per_laborer = base_100pct_journal_yield_value * (laborer_happiness_pct / 100.0)
    net_yield_after_tax = gross_yield_per_laborer * 0.935  # 6.5% market tax on sold materials
    net_profit_per_laborer = net_yield_after_tax - journal_net_cost
    laborer_profit_total = laborer_count * net_profit_per_laborer

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
        net_farming_profit=net_farming_profit,
        unfocused_farming_profit=unfocused_farming_profit,
        laborer_count=laborer_count,
        laborer_happiness_pct=laborer_happiness_pct,
        journal_net_cost_per_laborer=journal_net_cost,
        gross_yield_per_laborer=gross_yield_per_laborer,
        net_profit_per_laborer=net_profit_per_laborer,
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
# 5. DISCORD BOT CLASS, FULL ITEM INDEX LOADER & 24/7 KEEP-ALIVE SERVER
# ============================================================================

class AlbionMultiToolBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._initial_sync_done: bool = False
        self._base_commands: List[app_commands.Command[Any, ..., Any]] = []
        self._web_runner: Optional[web.AppRunner] = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=18),
            headers={"User-Agent": "AlbionMultiTool-OpenSource-AIBot/4.0"},
        )
        self._base_commands = list(self.tree.get_commands())
        asyncio.create_task(self.load_full_item_catalog())
        asyncio.create_task(self.start_keep_alive_server())

    async def load_full_item_catalog(self) -> None:
        """
        Loads the complete Albion Online item index (12,000+ items) from local cache
        or downloads it once from ao-bin-dumps so every valid item in the game works in /price!
        """
        global DYNAMIC_ITEM_INDEX
        if ITEMS_CACHE_FILE.exists():
            try:
                DYNAMIC_ITEM_INDEX = json.loads(ITEMS_CACHE_FILE.read_text(encoding="utf-8"))
                print(f"[Albion Multi Tool] Loaded {len(DYNAMIC_ITEM_INDEX)} item names from local cache.")
                return
            except Exception:
                pass

        urls = [
            "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json",
            "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/formatted/items.json",
        ]
        assert self.http_session is not None
        for url in urls:
            try:
                async with self.http_session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        raw_text = await resp.text()
                        items_list = json.loads(raw_text)
                        idx_map: Dict[str, str] = {}
                        for entry in items_list:
                            uniq = entry.get("UniqueName", "")
                            loc = entry.get("LocalizedNames") or {}
                            en_name = loc.get("EN-US", "") if isinstance(loc, dict) else ""
                            if not uniq or not en_name:
                                continue
                            clean_en = strip_tier_prefix(en_name.strip().lower())
                            # Strip @enchant and _LEVELx so we store the clean base ID
                            clean_uniq = uniq.split("@")[0]
                            clean_uniq = re.sub(r"_LEVEL[1-4]$", "", clean_uniq)
                            if re.match(r"^T[1-8]_", clean_uniq):
                                clean_uniq = clean_uniq[3:]
                            if clean_en and clean_en not in idx_map:
                                idx_map[clean_en] = clean_uniq
                            idx_map[en_name.strip().lower()] = uniq
                        DYNAMIC_ITEM_INDEX = idx_map
                        save_json_file(ITEMS_CACHE_FILE, DYNAMIC_ITEM_INDEX)
                        print(f"[Albion Multi Tool] Downloaded & cached {len(DYNAMIC_ITEM_INDEX)} in-game items from ao-bin-dumps!")
                        return
            except Exception as exc:
                print(f"[Albion Multi Tool] Note: Could not fetch remote item dump ({exc}); using built-in item index.")

    async def start_keep_alive_server(self) -> None:
        """
        Starts a lightweight 24/7 HTTP health-check endpoint if PORT or ENABLE_KEEP_ALIVE is set.
        Ideal for 24/7 cloud hosting (Render, Koyeb, Fly.io, UptimeRobot).
        """
        port_str = os.getenv("PORT")
        enable_ka = os.getenv("ENABLE_KEEP_ALIVE", "false").lower() in ("1", "true", "yes")
        if not port_str and not enable_ka:
            return
        port = int(port_str) if (port_str and port_str.isdigit()) else 8080
        try:
            app = web.Application()
            app.router.add_get("/", lambda req: web.Response(text="Albion Multi Tool v4.0 Bot is Alive & Running 24/7!"))
            app.router.add_get("/health", lambda req: web.json_response({"status": "ok", "bot": str(self.user)}))
            self._web_runner = web.AppRunner(app)
            await self._web_runner.setup()
            site = web.TCPSite(self._web_runner, "0.0.0.0", port)
            await site.start()
            print(f"[Albion Multi Tool] 24/7 Keep-Alive HTTP server listening on port {port}.")
        except Exception as exc:
            print(f"[Albion Multi Tool] Keep-Alive server note: {exc}")

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Albion Market | /help /bmsc /kitchen",
            ),
        )
        print(f"[Albion Multi Tool] Logged in as {self.user} — Bot is now ONLINE!")

        if not self._initial_sync_done:
            self._initial_sync_done = True
            for guild in self.guilds:
                try:
                    self.tree.clear_commands(guild=guild)
                    for cmd in self._base_commands:
                        self.tree.add_command(cmd, guild=guild)
                    synced_guild = await self.tree.sync(guild=guild)
                    print(
                        f"[Albion Multi Tool] Instant-synced {len(synced_guild)} unique commands "
                        f"to server: '{guild.name}' (ID: {guild.id})"
                    )
                except Exception as exc:
                    print(f"[Albion Multi Tool] WARNING: Could not sync commands to '{guild.name}'. Error: {exc}")

            try:
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                print("[Albion Multi Tool] Cleared duplicate global commands from Discord cache.")
            except Exception as exc:
                print(f"[Albion Multi Tool] Note while clearing global commands: {exc}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            self.tree.clear_commands(guild=guild)
            for cmd in self._base_commands:
                self.tree.add_command(cmd, guild=guild)
            await self.tree.sync(guild=guild)
            print(f"[Albion Multi Tool] Instant-synced commands to newly joined server: '{guild.name}'")
        except Exception as exc:
            print(f"[Albion Multi Tool] Guild join sync error in '{guild.name}': {exc}")

    async def close(self) -> None:
        if self._web_runner:
            await self._web_runner.cleanup()
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

TAX_MODE_CHOICES = [
    app_commands.Choice(name="👑 Premium Sell Order (6.5% Tax)", value="premium_order"),
    app_commands.Choice(name="⚡ Premium Instant Sell to Buy Order (4.0% Tax)", value="premium_instant"),
    app_commands.Choice(name="🧾 Non-Premium Sell Order (10.5% Tax)", value="no_premium_order"),
    app_commands.Choice(name="🤝 Direct Player Trade / Discord Market (0% Tax)", value="direct_trade"),
]

RESOURCE_CHOICES = [
    app_commands.Choice(name="⛏️ Ore -> Metal Bar (Thetford +40%)", value="ore"),
    app_commands.Choice(name="🌿 Fiber -> Cloth (Lymhurst +40%)", value="fiber"),
    app_commands.Choice(name="🦌 Hide -> Leather (Martlock +40%)", value="hide"),
    app_commands.Choice(name="🪵 Wood -> Planks (Fort Sterling +40%)", value="wood"),
    app_commands.Choice(name="🪨 Rock -> Stone Block (Bridgewatch +40%)", value="rock"),
]

QUALITY_CHOICES = [
    app_commands.Choice(name="1 - Normal", value=1),
    app_commands.Choice(name="2 - Good", value=2),
    app_commands.Choice(name="3 - Outstanding", value=3),
    app_commands.Choice(name="4 - Excellent", value=4),
    app_commands.Choice(name="5 - Masterpiece", value=5),
]


# ============================================================================
# 6. MODERN DISCORD UI VIEWS (INTERACTIVE BUTTONS & SELECT DROPDOWNS)
# ============================================================================

async def build_price_embed(item_id: str, quality: int, active_server: str) -> discord.Embed:
    """Fetches live market orders and builds a clean Embed with ANSI spread."""
    qualities = [quality] if 1 <= quality <= 5 else [1, 2, 3, 4, 5]
    records = await bot.fetch_market_prices([item_id], server=active_server, qualities=qualities)

    embed = discord.Embed(
        title=f"🏪 Cross-City Market Orders: {item_id}",
        description=f"**Server:** {SERVER_LABELS.get(active_server)} | **Quality:** `{QUALITY_NAMES.get(quality, 'Normal')}`",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{item_id}.png?quality={quality}")

    if not records:
        embed.description += (
            f"\n\n⚠️ No active price data found for `{item_id}` on **{SERVER_LABELS.get(active_server)}**.\n"
            f"💡 **Tip:** Enter the item name (e.g. `Cleric Robe`, `Carving Sword`, `Bag`) and `tier_enchant` (e.g. `6.1`)."
        )
        return embed

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

    if best_sell_city and best_buy_city and best_sell_price < float("inf") and best_buy_price > 0:
        spread = (best_buy_price * 0.96) - best_sell_price
        ansi_block = (
            f"```ansi\n"
            f"\u001b[1;36mLowest Sell Order :\u001b[0m {best_sell_city} ({format_silver(best_sell_price)} Silver)\n"
            f"\u001b[1;33mHighest Buy Order :\u001b[0m {best_buy_city} ({format_silver(best_buy_price)} Silver)\n"
            f"\u001b[1;37mInstant Flip (4%):\u001b[0m {format_ansi_profit(spread)}\n"
            f"```"
        )
        embed.add_field(name="💡 Trader Spread & Instant Flip", value=ansi_block, inline=False)

    embed.set_footer(text="Albion Multi Tool v4.0 • Use the dropdown below to switch Quality or click Refresh!")
    return embed


class PriceInteractiveView(discord.ui.View):
    """Interactive quality dropdown and refresh button attached to /price embeds."""

    def __init__(self, item_id: str, quality: int, server: str) -> None:
        super().__init__(timeout=300)
        self.item_id = item_id
        self.quality = quality
        self.server = server

    @discord.ui.select(
        placeholder="🎨 Switch Item Quality (Normal -> Masterpiece)...",
        options=[
            discord.SelectOption(label="1 - Normal", value="1", emoji="⚪"),
            discord.SelectOption(label="2 - Good", value="2", emoji="🟢"),
            discord.SelectOption(label="3 - Outstanding", value="3", emoji="🔵"),
            discord.SelectOption(label="4 - Excellent", value="4", emoji="🟣"),
            discord.SelectOption(label="5 - Masterpiece", value="5", emoji="🟡"),
        ],
    )
    async def select_quality(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        self.quality = int(select.values[0])
        await interaction.response.defer()
        embed = await build_price_embed(self.item_id, self.quality, self.server)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="🔄 Refresh Prices", style=discord.ButtonStyle.primary)
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        embed = await build_price_embed(self.item_id, self.quality, self.server)
        await interaction.edit_original_response(embed=embed, view=self)


class LootSplitDepositView(discord.ui.View):
    """Allows the caller/officer to credit the calculated payout directly to mentioned members' Guild Balances."""

    def __init__(
        self,
        guild_id: int,
        author_id: int,
        mentioned_members: List[discord.Member],
        payout_per_member: int,
        session_name: str,
    ) -> None:
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.author_id = author_id
        self.mentioned_members = mentioned_members
        self.payout_per_member = payout_per_member
        self.session_name = session_name
        self.deposited = False

    @discord.ui.button(label="💳 Credit Payout to Mentioned Members' Balances", style=discord.ButtonStyle.success)
    async def btn_deposit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⚠️ Only the person who ran `/lootsplit` can deposit this split.", ephemeral=True)
            return
        if self.deposited:
            await interaction.response.send_message("ℹ️ This loot split has already been credited to member balances!", ephemeral=True)
            return
        if not self.mentioned_members:
            await interaction.response.send_message(
                "ℹ️ No `@members` were tagged in `members_to_credit`. Use `/balance_manage` or include `@mentions` in `/lootsplit`!",
                ephemeral=True,
            )
            return

        self.deposited = True
        button.disabled = True
        lines: List[str] = []
        for m in self.mentioned_members:
            rec = update_member_balance(self.guild_id, m.id, m.display_name, self.payout_per_member)
            lines.append(f"• <@{m.id}>: `+{format_silver(self.payout_per_member)}` ➔ **New Balance:** `{format_silver(rec['balance'])} Silver`")

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"✅ **Credited `{format_silver(self.payout_per_member)} Silver` each for `{self.session_name}`:**\n" + "\n".join(lines[:20])
        )


class HelpDashboardView(discord.ui.View):
    """Interactive category dropdown for the /help command."""

    def __init__(self) -> None:
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="📂 Select a feature category to explore commands...",
        options=[
            discord.SelectOption(label="🏪 1. Market, Gold & Black Market (/bmsc)", value="market", emoji="🪙"),
            discord.SelectOption(label="⚗️ 2. Refining, Crafting, Enchant & Kitchen", value="crafting", emoji="🔨"),
            discord.SelectOption(label="🏝️ 3. Island Farming & Laborer Journals", value="island", emoji="🏝️"),
            discord.SelectOption(label="⚔️ 4. Guild Loot Split & Balance System", value="guild", emoji="🏦"),
        ],
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        cat = select.values[0]
        embed = discord.Embed(color=discord.Color.blurple(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        if cat == "market":
            embed.title = "🏪 Category 1: Market, Gold & Black Market Scanner"
            embed.description = (
                "• **`/set_server`** — Save your default Albion server (`Europe`, `Americas`, or `Asia`).\n"
                "• **`/gold`** — Live Gold/Silver exchange rate, 24h Unicode sparkline chart & bundle values.\n"
                "• **`/price`** — Live Buy & Sell orders for **any valid item in Albion Online** (`item` + `tier_enchant` + `quality`).\n"
                "• **`/bmsc`** — Bulk-scans an entire equipment category (`Bags`, `Swords`, `Armor`, etc.) for top **Black Market** flips!\n"
                "• **`/arbitrage`** — Ranks the most profitable Cross-City & Black Market transport routes for a single item."
            )
        elif cat == "crafting":
            embed.title = "⚗️ Category 2: Refining (T3–T8), Crafting, Enchant & Kitchen"
            embed.description = (
                "• **`/refine`** — Live **T3 to T8** refining calculator with permanent **+40% Royal City bonus**, Island mode, "
                "side-by-side **Focus vs. No-Focus comparison**, Total SPF, and Marginal Focus Gain.\n"
                "• **`/craft`** — Equipment crafting calculator with permanent **+15% city bonuses**, Island mode, Artifact exemption, and Journal profits.\n"
                "• **`/enchant_flip`** — Calculates Artifact Foundry upgrade flipping (`.0 ➔ .1` Runes, `.1 ➔ .2` Souls, `.2 ➔ .3` Relics) using live market prices.\n"
                "• **`/kitchen`** — Live Food (**Caerleon +15%**) & Potion (**Brecilien +15%**) cooking/alchemy profit and Focus SPF calculator."
            )
        elif cat == "island":
            embed.title = "🏝️ Category 3: Island Farming & Laborer Journals"
            embed.description = (
                "• **`/island`** — Comprehensive Personal/Guild Island calculator:\n"
                "  ┗ **Farming / Herbs / Pastures:** Seed cost, Focus watering return, +10% city yield bonus, Focus vs. No-Focus profit.\n"
                "  ┗ **Island Laborers & Journals:** Models Laborer count, Happiness Return Rate (e.g. `150%`), Empty vs. Full Journal cost, and 7-day / 30-day projections."
            )
        else:
            embed.title = "⚔️ Category 4: Guild Loot Split & Member Balance Ledger"
            embed.description = (
                "• **`/lootsplit`** — Criteria-based Guild Loot Split (`Equal`, `Role-Weighted`, `Repair Priority`) with one-click **Balance Deposit** button.\n"
                "• **`/balance`** — Check your own or another `@member`'s unpaid Guild Silver balance and lifetime earnings.\n"
                "• **`/balance_manage`** — Add silver, record in-game payouts (`payout`), clear balances, or view the Server Unpaid Leaderboard."
            )
        embed.set_footer(text="Albion Multi Tool v4.0 • AI-Built Open-Source Economy Bot")
        await interaction.response.edit_message(embed=embed, view=self)


# ============================================================================
# 7. SLASH COMMANDS (13 UNIQUE COMMANDS)
# ============================================================================

# ----------------------------------------------------------------------------
# COMMAND 1: /help - Interactive Help Dashboard (1 Featured Tool per Category on Main Page)
# ----------------------------------------------------------------------------
@bot.tree.command(name="help", description="Open the interactive Albion Multi Tool command guide and feature dashboard.")
async def cmd_help(interaction: discord.Interaction) -> None:
    user_srv = get_user_server(interaction.user.id)
    embed = discord.Embed(
        title="⚔️ Albion Multi Tool v4.0 — Interactive Command Center",
        description=(
            f"Welcome to **Albion Multi Tool**, an open-source AI-built economy, refining, crafting, island, and guild bot!\n"
            f"🌍 **Your Active Server:** **{SERVER_LABELS.get(user_srv)}** *(Change anytime via `/set_server`)*\n\n"
            f"👇 **Use the dropdown menu below** to explore all commands by category:"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="🌟 Featured Highlights (1 From Each Category)",
        value=(
            "🏪 **1. Market & Black Market:** `/bmsc` & `/price` — Scan categories for Black Market flips or check any item's live orders.\n"
            "⚗️ **2. Refining, Crafting & Enchant:** `/refine` & `/enchant_flip` — T3–T8 Refining SPF, Crafting & Rune/Soul/Relic upgrades.\n"
            "🏝️ **3. Island & Laborer Journals:** `/island` — Detailed Crop/Herb plots + Laborer Happiness & Journal profit.\n"
            "⚔️ **4. Guild Loot Split & Balances:** `/lootsplit` & `/balance` — Split loot by role criteria and track member Silver balances."
        ),
        inline=False,
    )
    embed.set_footer(text="Albion Multi Tool v4.0 • Data: The Albion Online Data Project (AODP)")
    await interaction.response.send_message(embed=embed, view=HelpDashboardView())


# ----------------------------------------------------------------------------
# COMMAND 2: /set_server - Per-User Default Server Preference
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
# COMMAND 3: /gold - Real-Time Gold Price, Sparkline & 24h Trend
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
    chronological_prices = list(reversed(prices))
    sparkline = build_sparkline(chronological_prices)

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
        value=f"**{format_silver(current_price)} Silver** *({latest_time})*\n**24h Trend Chart:** `{sparkline}`",
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
    embed.set_footer(text="Albion Multi Tool v4.0 • AI-Built Open-Source Project • Data: AODP")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 4: /price - Accepts ANY Valid Item + Separate Tier.Enchant & Quality
# ----------------------------------------------------------------------------
@bot.tree.command(name="price", description="Check live Buy & Sell orders for any in-game item across all cities.")
@app_commands.describe(
    item="Any in-game item name or ID (e.g., 'Cleric Robe', 'Carving Sword', 'Mistwalker Jacket', 'Planks')",
    tier_enchant="Tier and Enchantment (e.g., '6.1', '4.2', '8.0', '5.3', Default: '6.0')",
    quality="Item quality (1: Normal to 5: Masterpiece)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(quality=QUALITY_CHOICES, server=SERVER_CHOICES)
async def cmd_price(
    interaction: discord.Interaction,
    item: str,
    tier_enchant: str = "6.0",
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    item_id = resolve_item_id(item, tier_enchant=tier_enchant)
    embed = await build_price_embed(item_id, quality, active_server)
    view = PriceInteractiveView(item_id=item_id, quality=quality, server=active_server)
    await interaction.followup.send(embed=embed, view=view)


# ----------------------------------------------------------------------------
# COMMAND 5: /refine - T3 to T8 Refining Profit, Dual SPF & Focus Comparison
# ----------------------------------------------------------------------------
@bot.tree.command(name="refine", description="Calculate T3–T8 Refining profit, city/island RRR, and Silver Per Focus (SPF).")
@app_commands.describe(
    resource="Resource type to refine (auto-applies permanent +40% Royal City bonus)",
    tier="Resource tier (3 to 8 — T3 uses 2x T3 Raw + 1x T2 Refined)",
    enchant="Enchantment level (0 to 4; automatically 0 for T3)",
    quantity="Batch quantity to refine (Default: 100)",
    location_mode="Refining location: Bonus City (+40%), Island (0% Fee), or Non-Bonus City",
    tax_mode="Market tax mode (Premium 6.5%, Instant 4%, Non-Premium 10.5%, Trade 0%)",
    use_focus="Spend Focus points? (+59% production bonus)",
    station_fee="Station fee per 100 nutrition (Default: 400; 0 on Island)",
    mastery_level="Your Refining Mastery level (0-100, for Focus cost calculation)",
    target_spec="Your Specialization level in this exact Tier (0-100)",
    other_specs_sum="Sum of your Specialization levels in the other Tiers (0-400)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(
    resource=RESOURCE_CHOICES,
    location_mode=LOCATION_MODE_CHOICES,
    tax_mode=TAX_MODE_CHOICES,
    server=SERVER_CHOICES,
)
async def cmd_refine(
    interaction: discord.Interaction,
    resource: str,
    tier: app_commands.Range[int, 3, 8] = 6,
    enchant: app_commands.Range[int, 0, 4] = 0,
    quantity: app_commands.Range[int, 1, 100000] = 100,
    location_mode: str = "bonus_city",
    tax_mode: str = "premium_order",
    use_focus: bool = True,
    station_fee: float = 400.0,
    mastery_level: app_commands.Range[int, 0, 100] = 100,
    target_spec: app_commands.Range[int, 0, 100] = 100,
    other_specs_sum: app_commands.Range[int, 0, 400] = 400,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)

    effective_enchant = 0 if tier <= 3 else enchant
    res_info = REFINING_BONUS_CITIES[resource]
    bonus_city = res_info["city"]
    raw_id = build_resource_item_id(res_info["raw_key"], tier, effective_enchant)
    lower_refined_id = build_resource_item_id(res_info["refined_key"], tier - 1, effective_enchant)
    output_refined_id = build_resource_item_id(res_info["refined_key"], tier, effective_enchant)

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
        enchant=effective_enchant,
        quantity=quantity,
        raw_unit_price=raw_price,
        lower_refined_unit_price=lower_price,
        output_unit_sell_price=out_price,
        location_mode=location_mode,
        use_focus=use_focus,
        station_fee_rate=station_fee,
        tax_mode=tax_mode,
        mastery_lvl=mastery_level,
        target_spec_lvl=target_spec,
        other_specs_sum=other_specs_sum,
    )

    raw_qty_ratio, lower_qty_ratio = REFINING_RECIPE_RATIOS[tier]
    profit_color = discord.Color.green() if res.net_profit >= 0 else discord.Color.red()

    embed = discord.Embed(
        title=f"⚗️ Refining Profit Calculator: {quantity}x T{tier}.{effective_enchant} {res_info['name']}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Location:** `{res.location_label}`\n"
            f"**Tax Mode:** `{res.tax_label}` | **Active RRR:** `{res.rrr_pct:.2f}%`"
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
            f"• **Market Tax:** {format_silver(res.market_tax_total)} Silver"
        ),
        inline=True,
    )
    embed.add_field(
        name="⚖️ Focus vs. No-Focus Comparison",
        value=(
            f"• **Without Focus ({res.unfocused_rrr_pct:.1f}% RRR):** `{format_silver(res.unfocused_net_profit)} Silver`\n"
            f"• **Active Mode ({res.rrr_pct:.1f}% RRR):** **`{format_silver(res.net_profit)} Silver`**\n"
            f"• **ROI:** `{res.roi_pct:+.2f}%`\n"
            f"• **Focus / Unit:** `{res.focus_per_unit:.1f} Focus`"
        ),
        inline=True,
    )

    ansi_summary = (
        f"```ansi\n"
        f"\u001b[1;37mNet Batch Profit     :\u001b[0m {format_ansi_profit(res.net_profit)}\n"
        f"\u001b[1;36mTotal Batch SPF      :\u001b[0m {format_ansi_profit(res.silver_per_focus, ' Silver/Focus')}\n"
        f"\u001b[1;33mMarginal Focus Gain  :\u001b[0m {format_ansi_profit(res.marginal_spf, ' Silver/Focus')}\n"
        f"\u001b[1;32m10k Daily Focus Value:\u001b[0m {format_ansi_profit(res.silver_per_focus * 10000, ' Silver/Day')}\n"
        f"```"
    )
    embed.add_field(name="⚡ Financial & Focus Efficiency Summary", value=ansi_summary, inline=False)
    embed.set_footer(text="Albion Multi Tool v4.0 • Supports T3–T8 Refining • RRR = Bonus / (1 + Bonus)")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 6: /bmsc - Bulk Black Market Flipper & Category Scanner (Renamed to /bmsc)
# ----------------------------------------------------------------------------
BM_CATEGORY_CHOICES = [
    app_commands.Choice(name="🎒 Bags & Capes (T4–T8)", value="bags_capes"),
    app_commands.Choice(name="⚔️ Swords & Axes (T4–T8)", value="swords_axes"),
    app_commands.Choice(name="🏹 Bows, Daggers & Crossbows (T4–T8)", value="bows_daggers_xbow"),
    app_commands.Choice(name="🪄 Fire, Holy, Nature, Frost & Cursed Staffs (T4–T8)", value="magic_staffs"),
    app_commands.Choice(name="🧙‍♂️ Cloth Robes, Cowls & Sandals (T4–T8)", value="cloth_armor"),
    app_commands.Choice(name="🦌 Leather Jackets, Hoods & Shoes (T4–T8)", value="leather_armor"),
    app_commands.Choice(name="🛡️ Plate Armors, Helmets & Boots (T4–T8)", value="plate_armor"),
]


@bot.tree.command(name="bmsc", description="Scan an entire equipment category across all cities to find top Black Market flips.")
@app_commands.describe(
    category="Equipment category to scan against the Caerleon Black Market",
    tier="Filter by specific Tier (4 to 8, or 0 to scan all Tiers T4-T8)",
    quality="Item quality (1: Normal to 5: Masterpiece)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(category=BM_CATEGORY_CHOICES, quality=QUALITY_CHOICES, server=SERVER_CHOICES)
async def cmd_bmsc(
    interaction: discord.Interaction,
    category: str,
    tier: app_commands.Range[int, 0, 8] = 0,
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    cat_info = BM_SCANNER_CATEGORIES[category]
    base_items: List[str] = cat_info["items"]

    tiers_to_scan = [tier] if 4 <= tier <= 8 else [4, 5, 6, 7, 8]
    enchants_to_scan = [0, 1, 2]

    query_ids: List[str] = []
    for t in tiers_to_scan:
        for base in base_items:
            for e in enchants_to_scan:
                if e == 0:
                    query_ids.append(f"T{t}_{base}")
                else:
                    query_ids.append(f"T{t}_{base}@{e}")

    all_records: List[Dict[str, Any]] = []
    chunk_size = 45
    for idx in range(0, len(query_ids), chunk_size):
        chunk = query_ids[idx : idx + chunk_size]
        recs = await bot.fetch_market_prices(chunk, server=active_server, qualities=[quality])
        all_records.extend(recs)

    instant_flips, order_flips = evaluate_bm_scanner_candidates(all_records)

    embed = discord.Embed(
        title=f"🕵️‍♂️ Black Market Bulk Scanner (/bmsc): {cat_info['label']}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Quality:** `{QUALITY_NAMES.get(quality, 'Normal')}` "
            f"| **Scanned Items:** `{len(query_ids)}`\n"
            f"Compares the cheapest Royal City Sell Orders against **Caerleon Black Market** Buy & Sell Orders."
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )

    inst_lines: List[str] = []
    for idx, f in enumerate(instant_flips[:6], start=1):
        inst_lines.append(
            f"**{idx}. `{f.item_id}`** — Buy **{f.buy_city}** (`{format_silver(f.buy_price)}`) ➔ "
            f"BM Instant (`{format_silver(f.bm_buy_order_price)}`)\n"
            f"┗ 💰 Net Profit: **`+{format_silver(f.instant_profit)} Silver`** (`+{f.instant_roi_pct:.1f}%`) *({f.updated_age})*"
        )
    embed.add_field(
        name="⚡ Top Instant Black Market Flips (Sell to BM Buy Order — 4% Tax)",
        value="\n".join(inst_lines) if inst_lines else "No instant Black Market flips found for this filter right now.",
        inline=False,
    )

    ord_lines: List[str] = []
    for idx, f in enumerate(order_flips[:6], start=1):
        ord_lines.append(
            f"**{idx}. `{f.item_id}`** — Buy **{f.buy_city}** (`{format_silver(f.buy_price)}`) ➔ "
            f"BM Sell Order (`{format_silver(f.bm_sell_order_price)}`)\n"
            f"┗ 📈 Net Profit: **`+{format_silver(f.order_profit)} Silver`** (`+{f.order_roi_pct:.1f}%`)"
        )
    embed.add_field(
        name="📦 Top Black Market Sell-Order Flips (List on BM — 6.5% Tax)",
        value="\n".join(ord_lines) if ord_lines else "No Sell-Order Black Market flips found for this filter right now.",
        inline=False,
    )

    embed.set_footer(text="Albion Multi Tool v4.0 • Always verify in-game Black Market volume before transporting large batches!")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 7: /kitchen - Cooking (Food) & Alchemy (Potion) Profit Calculator
# ----------------------------------------------------------------------------
KITCHEN_RECIPE_CHOICES = [
    app_commands.Choice(name="🍲 T8 Beef Stew (Caerleon +15%, 10x Output)", value="t8_beef_stew"),
    app_commands.Choice(name="🍳 T7 Pork Omelette (Caerleon +15%, 10x Output)", value="t7_pork_omelette"),
    app_commands.Choice(name="🥧 T7 Pork Pie (Caerleon +15%, 10x Output)", value="t7_pork_pie"),
    app_commands.Choice(name="🥪 T8 Beef Sandwich (Caerleon +15%, 10x Output)", value="t8_beef_sandwich"),
    app_commands.Choice(name="🥗 T6 Potato Salad (Caerleon +15%, 10x Output)", value="t6_potato_salad"),
    app_commands.Choice(name="🍖 T7 Roast Pork (Caerleon +15%, 10x Output)", value="t7_roast_pork"),
    app_commands.Choice(name="🧪 T6 Major Healing Potion (Brecilien +15%, 5x Output)", value="t6_healing_potion"),
    app_commands.Choice(name="☠️ T8 Major Poison Potion (Brecilien +15%, 5x Output)", value="t8_poison_potion"),
    app_commands.Choice(name="🛡️ T7 Major Gigantify Potion (Brecilien +15%, 5x Output)", value="t7_gigantify_potion"),
    app_commands.Choice(name="✨ T7 Major Resistance Potion (Brecilien +15%, 5x Output)", value="t7_resistance_potion"),
]


@bot.tree.command(name="kitchen", description="Calculate Cooking (Food) and Alchemy (Potion) profit & SPF with live AODP prices.")
@app_commands.describe(
    recipe="Select the Food (Caerleon +15%) or Potion (Brecilien +15%) recipe",
    crafts_count="Number of recipe crafts to run (Default: 10 crafts = 100 meals or 50 potions)",
    location_mode="Cooking/Brewing location: Bonus City (+15%), Island (0% Fee), or Non-Bonus City",
    tax_mode="Market tax mode (Premium 6.5%, Instant 4%, Non-Premium 10.5%, Trade 0%)",
    use_focus="Spend Focus points? (+59% production bonus)",
    station_fee="Station fee per 100 nutrition (Default: 450; 0 on Island)",
    chef_alchemist_fce="Your total Focus Cost Efficiency (FCE) in this recipe (Default: 20000 -> 1/4 Focus)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(
    recipe=KITCHEN_RECIPE_CHOICES,
    location_mode=LOCATION_MODE_CHOICES,
    tax_mode=TAX_MODE_CHOICES,
    server=SERVER_CHOICES,
)
async def cmd_kitchen(
    interaction: discord.Interaction,
    recipe: str,
    crafts_count: app_commands.Range[int, 1, 10000] = 10,
    location_mode: str = "bonus_city",
    tax_mode: str = "premium_order",
    use_focus: bool = True,
    station_fee: float = 450.0,
    chef_alchemist_fce: app_commands.Range[int, 0, 50000] = 20000,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    rec = KITCHEN_RECIPES[recipe]
    bonus_city = rec["bonus_city"]
    output_id = rec["output_id"]
    out_per_craft = int(rec["output_per_craft"])
    total_output_units = crafts_count * out_per_craft

    ing_list: List[Tuple[str, int]] = rec["ingredients"]
    query_ids = [output_id] + [ing_id for ing_id, _ in ing_list]
    records = await bot.fetch_market_prices(query_ids, server=active_server, locations=ROYAL_CITIES)

    def get_best_price(target_id: str, preferred_city: str) -> Tuple[float, str]:
        city_price = 0.0
        fallback_price = float("inf")
        fallback_city = preferred_city
        for r in records:
            if r.get("item_id") == target_id:
                p = float(r.get("sell_price_min", 0))
                if p > 0:
                    if r.get("city") == preferred_city:
                        city_price = p
                    if p < fallback_price:
                        fallback_price = p
                        fallback_city = r.get("city", preferred_city)
        if city_price > 0:
            return city_price, preferred_city
        if fallback_price < float("inf"):
            return fallback_price, fallback_city
        return 0.0, "No Data"

    out_unit_price, out_city = get_best_price(output_id, bonus_city)
    ing_lines: List[str] = []
    unit_craft_gross_cost = 0.0
    missing_ids: List[str] = []

    for ing_id, qty_per_craft in ing_list:
        p, c_name = get_best_price(ing_id, bonus_city)
        if p <= 0:
            missing_ids.append(ing_id)
        line_cost = p * qty_per_craft
        unit_craft_gross_cost += line_cost
        ing_lines.append(
            f"• **{qty_per_craft * crafts_count}x `{ing_id}`:** {format_silver(p)} Silver/ea *({c_name})*"
        )

    if out_unit_price <= 0 or missing_ids:
        await interaction.followup.send(
            f"⚠️ Missing live price data on AODP for `{output_id}` or ingredients: `{', '.join(missing_ids)}`."
        )
        return

    is_island = location_mode == "island"
    total_bonus, rrr = calculate_rrr(location_mode=location_mode, activity="crafting", use_focus=use_focus)
    _, unfocused_rrr = calculate_rrr(location_mode=location_mode, activity="crafting", use_focus=False)

    gross_batch_cost = unit_craft_gross_cost * crafts_count
    returned_mat_value = gross_batch_cost * rrr
    net_mat_cost = gross_batch_cost - returned_mat_value
    unfocused_net_mat_cost = gross_batch_cost * (1.0 - unfocused_rrr)

    station_fee_total = calculate_station_fee(float(rec["item_value"]), station_fee, quantity=crafts_count, is_island=is_island)
    tax_label, tax_rate = TAX_MODES.get(tax_mode, TAX_MODES["premium_order"])

    gross_revenue = total_output_units * out_unit_price
    market_tax_total = gross_revenue * tax_rate

    net_profit = gross_revenue - net_mat_cost - station_fee_total - market_tax_total
    unfocused_profit = gross_revenue - unfocused_net_mat_cost - station_fee_total - market_tax_total
    total_cost = net_mat_cost + station_fee_total + market_tax_total
    roi_pct = (net_profit / total_cost * 100.0) if total_cost > 0 else 0.0

    focus_per_craft = float(rec["base_focus"]) / (2.0 ** (chef_alchemist_fce / 10000.0))
    total_focus = (focus_per_craft * crafts_count) if use_focus else 0.0
    spf = (net_profit / total_focus) if (use_focus and total_focus > 0) else 0.0
    marginal_spf = ((net_profit - unfocused_profit) / (focus_per_craft * crafts_count)) if (focus_per_craft * crafts_count) > 0 else 0.0

    embed = discord.Embed(
        title=f"🍲 Kitchen & Alchemy Calculator: {total_output_units}x {rec['name']}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Bonus City:** `{bonus_city} (+15%)` | **RRR:** `{rrr * 100:.2f}%`\n"
            f"**Batch:** `{crafts_count} Crafts` ➔ Produces **`{total_output_units} Units`** ({out_per_craft} per craft)"
        ),
        color=discord.Color.green() if net_profit >= 0 else discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{output_id}.png")

    embed.add_field(
        name="🧺 Live Ingredient & Output Prices",
        value="\n".join(ing_lines) + f"\n• **Output (`{output_id}`):** **{format_silver(out_unit_price)} Silver/ea** *({out_city})*",
        inline=False,
    )
    embed.add_field(
        name="💸 Batch Cost Breakdown",
        value=(
            f"• **Gross Ingredients:** {format_silver(gross_batch_cost)} Silver\n"
            f"• **RRR Refund ({rrr * 100:.1f}%):** +{format_silver(returned_mat_value)} Silver\n"
            f"• **Net Ingredients:** {format_silver(net_mat_cost)} Silver\n"
            f"• **Station Fee + Tax:** {format_silver(station_fee_total + market_tax_total)} Silver"
        ),
        inline=True,
    )
    embed.add_field(
        name="⚖️ Focus vs. No-Focus",
        value=(
            f"• **No Focus ({unfocused_rrr * 100:.1f}% RRR):** `{format_silver(unfocused_profit)} Silver`\n"
            f"• **Active ({rrr * 100:.1f}% RRR):** **`{format_silver(net_profit)} Silver`**\n"
            f"• **ROI:** `{roi_pct:+.2f}%`\n"
            f"• **Total Focus:** `{format_silver(total_focus)} Focus`"
        ),
        inline=True,
    )

    ansi_box = (
        f"```ansi\n"
        f"\u001b[1;37mNet Kitchen Profit   :\u001b[0m {format_ansi_profit(net_profit)}\n"
        f"\u001b[1;36mTotal Batch SPF      :\u001b[0m {format_ansi_profit(spf, ' Silver/Focus')}\n"
        f"\u001b[1;33mMarginal Focus Gain  :\u001b[0m {format_ansi_profit(marginal_spf, ' Silver/Focus')}\n"
        f"```"
    )
    embed.add_field(name="⚡ Kitchen Profit & Focus Summary", value=ansi_box, inline=False)
    embed.set_footer(text="Albion Multi Tool v4.0 • Food bonuses in Caerleon (+15%), Potions bonus in Brecilien (+15%)")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 8: /enchant_flip - Rune / Soul / Relic Upgrade Flipper
# ----------------------------------------------------------------------------
SLOT_TYPE_CHOICES = [
    app_commands.Choice(name="⚔️ Two-Handed Weapon (384 Runes/Souls/Relics per step)", value="2h_weapon"),
    app_commands.Choice(name="🗡️ One-Handed Weapon (288 Runes/Souls/Relics per step)", value="1h_weapon"),
    app_commands.Choice(name="🛡️ Armor (Chest) or Bag (192 Runes/Souls/Relics per step)", value="armor_bag"),
    app_commands.Choice(name="🪖 Helmet, Boots, Cape or Off-Hand (96 per step)", value="head_shoes_cape_offhand"),
]


@bot.tree.command(name="enchant_flip", description="Calculate profit from enchanting items (.0 -> .1/.2/.3) with Runes, Souls & Relics.")
@app_commands.describe(
    item="Any in-game equipment name or ID (e.g., 'Carving Sword', 'Cleric Robe', 'Bag')",
    tier="Equipment Tier (4 to 8, Default: 6)",
    slot_type="Equipment slot type (determines whether 96, 192, 288, or 384 materials are required)",
    quality="Item quality (1: Normal to 5: Masterpiece)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(slot_type=SLOT_TYPE_CHOICES, quality=QUALITY_CHOICES, server=SERVER_CHOICES)
async def cmd_enchant_flip(
    interaction: discord.Interaction,
    item: str,
    tier: app_commands.Range[int, 4, 8] = 6,
    slot_type: str = "2h_weapon",
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    resolved_id = resolve_item_id(item, tier_enchant=f"{tier}.0")
    clean_base = resolved_id.split("@")[0]

    query_ids = [
        clean_base,
        f"{clean_base}@1",
        f"{clean_base}@2",
        f"{clean_base}@3",
        f"T{tier}_RUNE",
        f"T{tier}_SOUL",
        f"T{tier}_RELIC",
    ]
    records = await bot.fetch_market_prices(query_ids, server=active_server, qualities=[quality, 1])

    price_map: Dict[str, float] = {}
    for r in records:
        iid = r.get("item_id", "")
        p = float(r.get("sell_price_min", 0))
        if p > 0 and (iid not in price_map or p < price_map[iid]):
            price_map[iid] = p

    flips = compute_enchant_flips(clean_base, tier=tier, slot_type=slot_type, price_map=price_map)

    embed = discord.Embed(
        title=f"✨ Artifact Foundry Enchanting Flipper: {clean_base}",
        description=(
            f"**Server:** {SERVER_LABELS.get(active_server)} | **Slot Cost:** `{ENCHANT_MATERIAL_COUNTS[slot_type]} Mats/Step` "
            f"| **Quality:** `{QUALITY_NAMES.get(quality, 'Normal')}`"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_thumbnail(url=f"https://render.albiononline.com/v1/item/{clean_base}@1.png?quality={quality}")

    if not flips:
        embed.description += "\n\n⚠️ Not enough live market orders found for all enchantment steps (`.0`, `.1`, `.2`, `.3`) and Runes/Souls/Relics."
        await interaction.followup.send(embed=embed)
        return

    for step in flips:
        status_icon = "✅ PROFITABLE FLIP" if step.net_profit_after_tax >= 0 else "❌ UNPROFITABLE"
        embed.add_field(
            name=f"🔮 {step.step_label} — {status_icon}",
            value=(
                f"• **Buy Base (`{step.from_id}`):** {format_silver(step.base_item_price)} Silver\n"
                f"• **Materials ({step.mat_qty}x `{step.mat_id}` @ {format_silver(step.mat_unit_price)}):** "
                f"{format_silver(step.mat_qty * step.mat_unit_price)} Silver\n"
                f"• **Total Upgrade Cost:** {format_silver(step.total_upgrade_cost)} Silver\n"
                f"• **Target Sell (`{step.to_id}`):** {format_silver(step.target_sell_price)} Silver\n"
                f"• **Net Profit (After 6.5% Tax):** **`{step.net_profit_after_tax:+,.0f} Silver`** (`{step.roi_pct:+.1f}%`)"
            ),
            inline=False,
        )

    embed.set_footer(text="Albion Multi Tool v4.0 • Tip: Buy Runes/Souls/Relics via Buy Orders to boost your margin!")
    await interaction.followup.send(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 9: /craft - Equipment Crafting Calculator
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
    embed.set_footer(text="Albion Multi Tool v4.0 • Artifacts/Hearts/Crests are exempt from RRR • AI-Built Open-Source Bot")
    await interaction.response.send_message(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 10: /island - Detailed Personal Island Farming & Laborer Journal Calculator
# ----------------------------------------------------------------------------
@bot.tree.command(name="island", description="Detailed Island Farming (Crops/Herbs/Pastures) & Laborer Journal profit calculator.")
@app_commands.describe(
    plots_count="Total number of farming/herb/pasture plots across your islands (e.g., 16 plots = 144 tiles)",
    seed_price="Unit price of 1 seed / herb seed / baby animal (Silver)",
    crop_sell_price="Market sell price of 1 harvested crop / herb / product (Silver)",
    use_focus="Water/Nurture plots with Focus? (Boosts seed/offspring return rate above 100%)",
    city_farming_bonus="Is this grown in its +10% Local Royal City bonus location?",
    base_seed_return_pct="Base seed return % without Focus (Default: 73.3 for T6-T8 crops)",
    focus_seed_return_pct="Total seed return % when watered with Focus (Default: 106.7)",
    farming_fce="Your Farming Focus Cost Efficiency points (Default: 10000 -> 500 Focus/tile)",
    laborer_count="Number of Island Laborers fed daily (e.g., 15, 30, 60; 0 if none)",
    laborer_happiness_pct="Laborer yield return rate % based on House/Furniture/Trophies (Default: 150%)",
    empty_journal_price="Market price of 1 Empty Crafting/Gathering Journal (Silver)",
    full_journal_price="Market price of 1 Full Journal (or 0 if you fill journals yourself!)",
    base_journal_yield_value="Base (100% happiness) market value of materials returned per journal (Silver)",
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
    laborer_happiness_pct: float = 150.0,
    empty_journal_price: int = 3000,
    full_journal_price: int = 18000,
    base_journal_yield_value: int = 16000,
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
        laborer_happiness_pct=laborer_happiness_pct,
        empty_journal_price=float(empty_journal_price),
        full_journal_price=float(full_journal_price),
        base_100pct_journal_yield_value=float(base_journal_yield_value),
    )

    embed = discord.Embed(
        title=f"🏝️ Detailed Island & Laborer Journal Economy ({res.plots_count} Plots / {res.total_tiles} Tiles)",
        description=(
            f"**Watering with Focus:** `{'Yes' if use_focus else 'No'}` | "
            f"**City +10% Yield Bonus:** `{'Active' if city_farming_bonus else 'Inactive'}` | "
            f"**Active Laborers:** `{res.laborer_count}`"
        ),
        color=discord.Color.teal(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(
        name="🌾 1. Farming / Herb / Pasture Plot Breakdown",
        value=(
            f"• **Initial Seed/Animal Cost:** {format_silver(res.total_seed_cost)} Silver\n"
            f"• **Returned Seeds Value:** +{format_silver(res.seed_return_value)} Silver\n"
            f"• **Net Seed Balance:** {format_silver(-res.net_seed_expense)} Silver\n"
            f"• **Harvested Yield (~{res.total_crop_yield:.0f} units):** {format_silver(res.gross_crop_revenue)} Silver\n"
            f"• **Market Tax (6.5%):** -{format_silver(res.market_tax)} Silver\n"
            f"• **Profit Without Focus:** `{format_silver(res.unfocused_farming_profit)} Silver`\n"
            f"• **Net Daily Farming Profit:** **`{format_silver(res.net_farming_profit)} Silver`**"
        ),
        inline=False,
    )

    if laborer_count > 0:
        embed.add_field(
            name=f"📘 2. Island Laborer & Journal Breakdown ({res.laborer_count} Laborers @ {res.laborer_happiness_pct:.0f}% Yield)",
            value=(
                f"• **Journal Turn-In Cost (`Full - Empty`):** {format_silver(res.journal_net_cost_per_laborer)} Silver / journal\n"
                f"• **Gross Material Yield (`{res.laborer_happiness_pct:.0f}%` Happiness):** {format_silver(res.gross_yield_per_laborer)} Silver / journal\n"
                f"• **Net Profit per Laborer (After 6.5% Tax):** `{format_silver(res.net_profit_per_laborer)} Silver`\n"
                f"• **Total Daily Laborer Profit ({res.laborer_count}x):** **`{format_silver(res.laborer_profit_total)} Silver / Day`**"
            ),
            inline=False,
        )

    ansi_island = (
        f"```ansi\n"
        f"\u001b[1;37mCombined Daily Profit :\u001b[0m {format_ansi_profit(res.combined_daily_profit, ' Silver/Day')}\n"
        f"\u001b[1;36mWeekly Projection (7d):\u001b[0m {format_ansi_profit(res.combined_daily_profit * 7, ' Silver/Week')}\n"
        f"\u001b[1;32mMonthly Income (30d)  :\u001b[0m {format_ansi_profit(res.combined_daily_profit * 30, ' Silver/Month')}\n"
    )
    if use_focus:
        ansi_island += f"\u001b[1;33mFarming Focus & SPF   :\u001b[0m {format_silver(res.focus_used)} Focus ({format_silver(res.silver_per_focus)} Silver/Focus)\n"
    ansi_island += "```"

    embed.add_field(name="💰 3. Total Island Portfolio Projection", value=ansi_island, inline=False)
    embed.set_footer(text="Albion Multi Tool v4.0 • Tip: Set full_journal_price=0 if you self-fill journals while crafting!")
    await interaction.response.send_message(embed=embed)


# ----------------------------------------------------------------------------
# COMMAND 11: /lootsplit - Criteria-Based Guild Loot Split + Balance Ledger Integration
# ----------------------------------------------------------------------------
LOOT_RULE_CHOICES = [
    app_commands.Choice(name="⚖️ Equal Split (Everyone gets an equal 1.0x share)", value="equal"),
    app_commands.Choice(name="🛡️ Role-Weighted Split (Priority roles get higher weight)", value="role_weighted"),
    app_commands.Choice(name="🔧 Repair & Regear Priority (Deducts Repair + Regear first)", value="repair_priority"),
]


@bot.tree.command(name="lootsplit", description="Calculate Guild Loot Split and optionally credit payouts to member balances.")
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
    members_to_credit="Optional: Mention members (@user1 @user2...) to credit their balance with 1 click!",
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
    members_to_credit: str = "",
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

    # Parse any @mentions inside `members_to_credit`
    mentioned_members: List[discord.Member] = []
    if interaction.guild and members_to_credit:
        found_ids = [int(uid) for uid in re.findall(r"<@!?(\d+)>", members_to_credit)]
        for uid in dict.fromkeys(found_ids):
            member_obj = interaction.guild.get_member(uid)
            if member_obj:
                mentioned_members.append(member_obj)

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

    if mentioned_members:
        payout_text += f"\n\n👥 **Tagged for Balance Credit ({len(mentioned_members)}):** " + ", ".join(m.mention for m in mentioned_members[:15])

    embed.add_field(name="👥 Final Player Payouts", value=payout_text, inline=False)
    embed.set_footer(text=f"Calculated by {interaction.user.display_name} • Click the button below to credit balances!")

    view = LootSplitDepositView(
        guild_id=interaction.guild_id or 0,
        author_id=interaction.user.id,
        mentioned_members=mentioned_members,
        payout_per_member=res.regular_member_payout,
        session_name=session_name,
    )
    await interaction.response.send_message(embed=embed, view=view)


# ----------------------------------------------------------------------------
# COMMANDS 12 & 13 (NEW): /balance & /balance_manage - Guild Silver Balance Ledger
# ----------------------------------------------------------------------------
@bot.tree.command(name="balance", description="Check your own or another guild member's accumulated Silver balance from loot splits.")
@app_commands.describe(member="Optional: Select a server member to check their Silver balance (defaults to yourself)")
async def cmd_balance(interaction: discord.Interaction, member: Optional[discord.Member] = None) -> None:
    target = member or interaction.user
    guild_id = interaction.guild_id or 0
    rec = get_member_balance(guild_id, target.id, target.display_name)

    embed = discord.Embed(
        title=f"🏦 Guild Silver Wallet — {target.display_name}",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="💰 Current Unpaid Balance", value=f"**`{format_silver(rec['balance'])} Silver`**", inline=False)
    embed.add_field(name="📈 Total Lifetime Earned", value=f"{format_silver(rec['total_earned'])} Silver", inline=True)
    embed.add_field(name="💸 Total Paid Out", value=f"{format_silver(rec['total_paid'])} Silver", inline=True)
    embed.set_footer(text="Albion Multi Tool v4.0 • Guild Loot Split Balance System")
    await interaction.response.send_message(embed=embed)


BALANCE_ACTION_CHOICES = [
    app_commands.Choice(name="➕ Add Silver to Member Balance", value="add"),
    app_commands.Choice(name="💸 Record Payout (Deduct Paid Silver from Balance)", value="payout"),
    app_commands.Choice(name="🧹 Clear Member Balance to 0 (Full Payout)", value="clear"),
    app_commands.Choice(name="🏆 View Server Unpaid Balance Leaderboard", value="leaderboard"),
]


@bot.tree.command(name="balance_manage", description="Add silver, record payouts, clear balances, or view the Guild Silver Leaderboard.")
@app_commands.describe(
    action="Choose whether to add silver, record a payout, clear a balance, or view the leaderboard",
    member="Target guild member (not required when viewing leaderboard)",
    amount="Silver amount to add or deduct (not required for 'clear' or 'leaderboard')",
)
@app_commands.choices(action=BALANCE_ACTION_CHOICES)
async def cmd_balance_manage(
    interaction: discord.Interaction,
    action: str,
    member: Optional[discord.Member] = None,
    amount: int = 0,
) -> None:
    guild_id = interaction.guild_id or 0

    if action == "leaderboard":
        board = get_guild_leaderboard(guild_id)
        active_board = [(uid, data) for uid, data in board if int(data.get("balance", 0)) > 0]
        if not active_board:
            await interaction.response.send_message("🏦 All guild members currently have `0 Silver` unpaid balance!")
            return

        total_owed = sum(int(d.get("balance", 0)) for _, d in active_board)
        lines = [
            f"**{idx}.** <@{uid}> (`{d.get('name', 'Member')}`) — **`{format_silver(d['balance'])} Silver`**"
            for idx, (uid, d) in enumerate(active_board[:20], start=1)
        ]
        embed = discord.Embed(
            title="🏆 Guild Unpaid Silver Balance Leaderboard",
            description=f"**Total Guild Silver Owed to Members:** **`{format_silver(total_owed)} Silver`**\n\n" + "\n".join(lines),
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_footer(text="Albion Multi Tool v4.0 • Use /balance_manage action:payout when you trade Silver in-game!")
        await interaction.response.send_message(embed=embed)
        return

    if not member:
        await interaction.response.send_message("⚠️ Please select a `member` for this balance action.", ephemeral=True)
        return

    if action == "add":
        if amount <= 0:
            await interaction.response.send_message("⚠️ Please enter a positive `amount` of Silver to add.", ephemeral=True)
            return
        rec = update_member_balance(guild_id, member.id, member.display_name, amount, is_payout=False)
        await interaction.response.send_message(
            f"✅ Added **`+{format_silver(amount)} Silver`** to {member.mention}'s guild balance.\n"
            f"🏦 **New Unpaid Balance:** **`{format_silver(rec['balance'])} Silver`**"
        )
    elif action == "payout":
        if amount <= 0:
            await interaction.response.send_message("⚠️ Please enter a positive `amount` of Silver paid out.", ephemeral=True)
            return
        rec = update_member_balance(guild_id, member.id, member.display_name, amount, is_payout=True)
        await interaction.response.send_message(
            f"💸 Recorded in-game payout of **`-{format_silver(amount)} Silver`** to {member.mention}.\n"
            f"🏦 **Remaining Unpaid Balance:** **`{format_silver(rec['balance'])} Silver`**"
        )
    elif action == "clear":
        cur = get_member_balance(guild_id, member.id, member.display_name)
        cleared_amt = int(cur.get("balance", 0))
        rec = update_member_balance(guild_id, member.id, member.display_name, cleared_amt, is_payout=True)
        await interaction.response.send_message(
            f"🧹 Cleared {member.mention}'s full balance (**`{format_silver(cleared_amt)} Silver`** marked as paid out).\n"
            f"🏦 **Current Balance:** `{format_silver(rec['balance'])} Silver`"
        )


# ----------------------------------------------------------------------------
# COMMAND 14: /arbitrage - Cross-City & Black Market Flipper (Any Valid Item)
# ----------------------------------------------------------------------------
@bot.tree.command(name="arbitrage", description="Find profitable cross-city and Black Market flipping routes for any item.")
@app_commands.describe(
    item="Any in-game item name or ID (e.g., 'Cleric Robe', 'Carving Sword', 'Bag')",
    tier_enchant="Tier and Enchantment (e.g., '6.1', '4.2', '8.0', Default: '6.0')",
    quality="Item quality (1: Normal to 5: Masterpiece)",
    server="Optional server override (uses /set_server preference by default)",
)
@app_commands.choices(quality=QUALITY_CHOICES, server=SERVER_CHOICES)
async def cmd_arbitrage(
    interaction: discord.Interaction,
    item: str,
    tier_enchant: str = "6.0",
    quality: int = 1,
    server: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    active_server = get_user_server(interaction.user.id, server)
    item_id = resolve_item_id(item, tier_enchant=tier_enchant)
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
    embed.set_footer(text="Albion Multi Tool v4.0 • Account for Red Zone transport risk when hauling to Caerleon/Black Market!")
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    token = load_bot_token()
    if not token:
        print(
            "ERROR: DISCORD_BOT_TOKEN not found!\n"
            "Please create a .env (or .env.txt) file with DISCORD_BOT_TOKEN=your_token_here or export it in your environment."
        )
    else:
        bot.run(token, reconnect=True)