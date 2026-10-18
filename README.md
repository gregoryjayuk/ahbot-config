# ahbot-config

A Python script that stocks the [vMaNGOS](https://github.com/vmangos/core) auction house. Instead of the AHBot's tiny default item list, it reads `item_template` from the world database and writes `auctionhousebot` rows for every sensible item, with bid and buyout prices derived from each item's vendor price, extra multipliers for weapons and armour, random variation so the house doesn't look machine-made, and several stack and variation rules per item class.

The full write-up, with everything I learned about configuring AHBot: [VMangos AHBot: The Lost Config](https://facedragons.com/foss/vmangos-ahbot-config/).

## Use

```bash
pip install mysql-connector-python
# edit the settings at the top of ahbot-config.py: DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE, multipliers
python3 ahbot-config.py          # writes the INSERT statements for review
```

Review the generated SQL, import it into the world database, and restart `mangosd`. `ahbot_inserts.txt` is an example of the output.

## Version 2

This is the original March 2025 version. Its successor models real item scarcity from the loot tables and spawn counts, with four economy profiles, and lives in [vmangos-toolkit](https://github.com/gregoryjayuk/vmangos-toolkit/tree/main/ahbot/v2).
