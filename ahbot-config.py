#!/usr/bin/env python3
import mysql.connector
import random

# =========================
# Configuration Variables
# =========================

# Database connection settings
DB_HOST = 'localhost'
DB_USER = 'mangos'
DB_PASSWORD = 'mangos'
DB_DATABASE = 'mangos'

# General multipliers for bid and buyout prices (applied to the sell_price field)
bid_multiplier = 0.5    # Base multiplier for bid price (for non-weapon/armor items)
buyout_multiplier = 2.5  # Base multiplier for buyout price (for non-weapon/armor items)

# Additional multipliers for weapons (class 2) and armor (class 4)
weapon_armor_bid_multiplier = 4    # Bid multiplier for weapons and armor
weapon_armor_buyout_multiplier = 10  # Buyout multiplier for weapons and armor

# Randomness ranges for price adjustments (e.g., ±5% variation)
bid_variance = (0.75, 1.25)
buyout_variance = (0.75, 1.25)

# =========================
# Variation Range Settings
# =========================
# For weapons (class 2) and armor (class 4), generate a random number of variations between these values. Unfortunately some items (e.g. Cenarion Bracers) appear multiple times in the source table so you will get multiple copies even with this limit in place. 
# Use the follow query to see this - yyou can remove them if desired
# SELECT entry, name FROM item_template WHERE entry = 16830;

min_variations_weapon_armor = 1  # Minimum variations for weapons/armor
max_variations_weapon_armor = 3  # Maximum variations for weapons/armor

# For other allowed classes, generate a random number of variations between these values.
min_variations_other = 2         # Minimum variations for other items
max_variations_other = 6         # Maximum variations for other items

# =========================
# Optional Filter Settings
# =========================

# Quality filter: Define allowed quality levels.
# Quality levels:
#   0 = Grey (Poor), 1 = White (Common), 2 = Green (Uncommon),
#   3 = Blue (Rare), 4 = Purple (Epic), 5 = Orange (Legendary),
#   6 = Red (Artifact), 7 = Gold (Bind to Account)

use_filter_quality = True
allowed_qualities = [1, 2, 3, 4, 5]  # Adjust as desired

use_filter_required_honor = True      # Only include items with required_honor_rank = 0
use_filter_required_reputation = True # Only include items with required_reputation_faction = 0 AND required_reputation_rank = 0
use_filter_item_level = False         # Optionally filter by item_level range
min_item_level = 0                    # Minimum item level (inclusive)
max_item_level = 100                  # Maximum item level (inclusive)

# Exclude Certain classes. See below for classes
# 0 Consumable
# 1 Container
# 2 Weapon
# 3 Gem
# 4 Armor
# 5 Reagent
# 6 Projectile
# 7 Trade Goods
# 8 Generic(OBSOLETE)
# 9 Recipe
# 10 Money(OBSOLETE)
# 11 Quiver
# 12 Quest
# 13 Key
# 14 Permanent(OBSOLETE)
# 15 Miscellaneous
# 16 Glyph

exclude_classes = [8, 10, 12, 13, 14]

# Exclude any item with "Deprecated" in its name
exclude_deprecated = True

# Exclude Test Items
exclude_test = True

# === Manual Item Code Overrides ===
include_items = []  # e.g., [12345, 67890]
exclude_items = []  # e.g., [18948, 23456]

# =========================
# Bonding Rules (unchanged)
# =========================
# 0 No bounds
# 1 Bind on Pickup
# 2 BoE
# 3 Bind on Use
# 4 Quest Item
# 5 Quest Item1

def bonding_allowed(item_class, bonding):
    return bonding in (0, 2, 3)


# =========================
# END OF USER CONFIG
# =========================


# =========================
# Class Labels for Comments
# =========================
class_labels = {
    0: 'Consumable',
    1: 'Container',
    2: 'Weapon',
    3: 'Gem',
    4: 'Armor',
    5: 'Reagent',
    6: 'Projectile',
    7: 'Trade Goods',
    9: 'Recipe',
    11: 'Quiver',
    12: 'Quest',
    13: 'Key',
    15: 'Miscellaneous',
    16: 'Glyph'
}

# =========================
# Build the WHERE Clause
# =========================
where_clauses = []

if use_filter_quality:
    allowed_qualities_str = ", ".join(str(q) for q in allowed_qualities)
    where_clauses.append(f"quality IN ({allowed_qualities_str})")
if use_filter_required_honor:
    where_clauses.append("required_honor_rank = 0")
if use_filter_required_reputation:
    where_clauses.append("required_reputation_faction = 0 AND required_reputation_rank = 0")
if use_filter_item_level:
    where_clauses.append(f"item_level BETWEEN {min_item_level} AND {max_item_level}")

# Exclude quest items and keys (classes 12 and 13)
where_clauses.append("class NOT IN (12, 13)")

# Exclude items with "Deprecated" in the name if desired
if exclude_deprecated:
    where_clauses.append("name NOT LIKE '%Deprecated%'")

# Exclude items with "Test" in the name if desired
if exclude_test:
    where_clauses.append("name NOT LIKE '%Test%'")

if where_clauses:
    base_filter = " AND ".join(where_clauses)
else:
    base_filter = "1"  # No filtering

# If include_items is set, force include those items using OR.
if include_items:
    include_clause = "entry IN (" + ", ".join(str(x) for x in include_items) + ")"
    combined_filter = f"(({base_filter}) OR ({include_clause}))"
else:
    combined_filter = base_filter

# Always exclude items listed in exclude_items.
if exclude_items:
    exclude_clause = "entry NOT IN (" + ", ".join(str(x) for x in exclude_items) + ")"
    final_where_clause = f"({combined_filter}) AND ({exclude_clause})"
else:
    final_where_clause = combined_filter

# =========================
# Connect to the Database
# =========================
cnx = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_DATABASE
)
cursor = cnx.cursor(dictionary=True)

# Query the item_template table for eligible items.
# Now we also retrieve the "stackable" field, which is the maximum stack size.
query = f"""
SELECT entry, class, buy_count, sell_price, bonding, name, stackable
FROM item_template
WHERE {final_where_clause}
ORDER BY class, entry;
"""
cursor.execute(query)
rows = cursor.fetchall()

# =========================
# Process Results & Generate Output
# =========================
output_lines = []
current_class = None
total_inserts = 0

for row in rows:
    item_class = row['class']
    bonding = row['bonding']
    # Apply bonding rules based on item class.
    if not bonding_allowed(item_class, bonding):
        continue  # Skip items that don't meet bonding criteria

    # When the item class changes, add a comment header.
    if item_class != current_class:
        current_class = item_class
        class_name = class_labels.get(item_class, f"Class {item_class}")
        output_lines.append(f"-- {class_name}")
    entry = row['entry']
    sell_price = row['sell_price']
    item_name = row['name']
    # Use the "stackable" field for max stack size.
    max_stack = row['stackable']

    # Determine number of variations based on item class.
    if item_class in (2, 4):  # Weapon or Armor
        n_variations_this = random.randint(min_variations_weapon_armor, max_variations_weapon_armor)
    else:
        n_variations_this = random.randint(min_variations_other, max_variations_other)
    
    for i in range(n_variations_this):
        # Determine the stack based on item class:
        # For Consumable (0), Reagent (5), Projectile (6), and Trade Goods (7):
        # 80% of the time, use the max stack; 20% choose a random value between 1 and max_stack.
        # For all other classes, stack should be 1.
        if item_class in (0, 5, 6, 7):
            if random.random() < 0.8:
                stack = max_stack
            else:
                stack = random.randint(1, max_stack)
        else:
            stack = 1

        # Calculate price per unit with multipliers and variance.
        if item_class in (2, 4):
            unit_bid = sell_price * weapon_armor_bid_multiplier * random.uniform(*bid_variance)
            unit_buyout = sell_price * weapon_armor_buyout_multiplier * random.uniform(*buyout_variance)
        else:
            unit_bid = sell_price * bid_multiplier * random.uniform(*bid_variance)
            unit_buyout = sell_price * buyout_multiplier * random.uniform(*buyout_variance)
        
        # Multiply the unit price by the stack amount.
        bid = round(unit_bid * stack)
        buyout = round(unit_buyout * stack)
        
        # Append the item name as a comment after the INSERT statement.
        insert_stmt = (f"INSERT INTO `mangos`.`auctionhousebot` (`item`, `stack`, `bid`, `buyout`) "
                       f"VALUES({entry}, {stack}, {bid}, {buyout}); -- {item_name}")
        output_lines.append(insert_stmt)
        total_inserts += 1

# =========================
# Write Output to a File
# =========================
output_filename = "ahbot_inserts.txt"
with open(output_filename, "w") as f:
    for line in output_lines:
        f.write(line + "\n")

print(f"Total items processed: {len(rows)}")
print(f"Total INSERT statements generated: {total_inserts}")
print(f"Output written to {output_filename}")

cursor.close()
cnx.close()

