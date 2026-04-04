#
# This file contains the 'pristine' FF5-PR item, location, and region definitions. 
# In other words, the "pristine_items" list contains all items with their content IDs and various
#   groups and other metadata independent of any given Archipelago run.
# Other files like "Items", "Locations", and "Regions" will use the data structures in these files
#   to instantiate the "FF5PRItem" (and other) objects to put into the multiworld's Item Pool, etc.
#   The generate_output() function will then use the asset_paths and content_ids to prepare the patch for the client.
# A good example of this:
#   * pristine_items: contains a single "Elixir" entry, with an associate asset_path and content_id
#   * pristine_locations: describes several treasure chests that contain an "Elixir", and also have asset_paths and internal_paths
#   * Locations/Regions.py: Creates Locations for each treasure in the game, including those with an Elixir.
#     * User options can change this! If we do a "World 1 only" run, then pristine_locations in Worlds 2+3 won't generate Locations.
#   * Items.py: Adds an item to the item pool for each Elixir in each Location.
#     * Similarly, user options can change this. We could, for example, shuffle shop content into the item pool --or we could even 
#       completely ignore the original pool of chest contents and put a specific selection of items, weapon, and armor into the pool.
#   * generate_output() is given the set of FF5PRItems/Locations and looks up the original information in the pristine files.
#     It will then create a patch for each Location that tells our Client which assets and internal paths to patch (and which content IDs)
#     to write into those paths).
#   * Later, when running the game, our Client also uses the 'pristine' information to look up multiworld items that are received from
#     other players and then present a popup to the player. This is done in C#, but it's the same data.
#


import sys


# Note that our custom items start at 5000, and our job "items" start at 2000

# IDs for multiworld items
# We'll build a mapping of these later
PristineMultiworldItemStart = 3000000

# ID of the first "jumbo" Item; IDs will increase by 1 from here
JumboItemStartID = 5500

# ID of the first "Shop" Location (the client doesn't need to see this)
ShopLocationStart = 92000

# ID of the first "Remote" location+item TODO: should no longer need to be items at all; we are never "given" these by a peer
#RemoteIdStart = 80000

# What's the highest content_id the game knows about?
CurrMaxContentId = 1690

# Maximum current Product ID; anything above this will have to be created
MaxProductId = 341
MaxProductGroupId = 57




# Simple classes

class PristineItem:
  def __init__(self, content_id: int, classification: str, tags: list[str], optattrs: dict[str,str] = {}):
    self.content_id = content_id  # FF5 content_id; DO NOT USE as Archipelago id (use it only to *get* the item)
    self.classification = classification  # Filler, Progression, etc.
    self.tags = tags  # Ways to refer to this item. "Consumable", "Weapon", "Job"; also, "Priceless" (don't toss it)
    self.optattrs = optattrs  # Optional info necessary for patching the game. E.g., "call this sysCall to add this Job"

  def __repr__(self):
    return f"PristineItem({self.content_id}, {self.classification}, {self.tags})"



class PristineLocation:
  def __init__(self, loc_id: int, classification: str, orig_item: str, tags: list[str], asset_path: str, optattrs: dict[str,str] = {}):
    # Note about Location IDs: we create a set of (fake) "content" DB entries, 1 for each Location ID. Then, we hard-code all our 
    #   treasure chests, etc., to give the player the Location ID associated with that Chest. We intercet the "GetItem" call and
    #   instead give the player the randomized item. So with that in mind, we want our LocationIDs to be *somewhat* compact in their
    #   storage. I'm going to enforce that they all start at 90000.
    self.loc_id = loc_id

    self.classification = classification   # Default, Priority, Excluded
    self.orig_item = orig_item  # Original Item at this location (or "<num> Gil").
    self.tags = tags  # Ways to refer to this location. "Town", "Dungeon", etc. 
    self.asset_path = asset_path  # <path_to_asset>:<path_within_asset> ; used by our Resource Loader to patch the game
    self.optattrs = optattrs  # Optional info necessary for patching the game. E.g., the "Great Sword in the Water" message. 
                              # 'Label' is the expected 'Nop' label that we're planning to patch over; this keeps us honest rather than just stomping on memory (see Patches.py)

  def __repr__(self):
    return f"PristineLocation({self.loc_id}, {self.orig_item}, {self.tags})"



class PristineEvent:
  def __init__(self, event_item: str, tags: list[str]):
    self.event_item = event_item  # Name of the EventItem at this EventLocation
    self.tags = tags  # Ways to refer to this location. "Town", "Dungeon", etc. 
    self.loc_id = None  # As far as Locations go, this has no ID

  def __repr__(self):
    return f"PristineEvent({self.event_item}, {self.tags})"



# We specify Region/Entrance connections later
class PristineRegion:
  def __init__(self, tags: list[str], locations: dict[str, PristineLocation]):
    self.tags = tags  # These tags will be copied into the tag list for *all* Locations in this Region
    self.locations = locations  # { LocationName -> PristineLocation } ; used to group, e.g., all Floors in a Dungeon into the same logical space.

  def __repr__(self):
    return f"PristineRegion({self.tags}, {len(self.locations)} locations)"


# Shops have lists of items (Locations) that are in a given Region. They are *not* always added as Locations.
# If a product_group starts with '+', then we're adding it.
# shop_type lists the type of items sold here: Weapon, Armor, Item, Ability (anything mixed would be "Item")
class PristineShop:
  def __init__(self, region: str, product_group: str, pgroup_name: str, shop_type: str, asset_path: str, items: dict[str, int]):
    self.region = region
    self.product_group = product_group
    self.pgroup_name = pgroup_name
    self.shop_type = shop_type
    self.asset_path = asset_path
    self.items = items

  def __repr__(self):
    return f"PristineShop({self.region}, {self.pgroup_name}[{self.product_group}], {len(self.items)} items)"



# Helpers

# Retrieve an Asset path from a Map name + Entity_Default id
# If objectId is an array, assume [layerId, objectId]
def EntDefAsset(mapId, subMapId, objectId):
  layerId = 0
  if isinstance(objectId, list):
    layerId = objectId[0]
    objectId = objectId[1]
  subMapStr = '' if subMapId is None else f"_{subMapId}"
  return f"Assets/GameAssets/Serial/Res/Map/Map_{mapId}/Map_{mapId}{subMapStr}/entity_default:/layers/[{layerId}]/objects/[{objectId}]/properties"

# Retrieve an Asset path from a Map/Script Name + Mnemonic ID
def ScrMnemAsset(mapId, subMapId, scriptName, mnemonicId):
  subMapStr = '' if subMapId is None else f"_{subMapId}"
  return f"Assets/GameAssets/Serial/Res/Map/Map_{mapId}/Map_{mapId}{subMapStr}/{scriptName}:/Mnemonics/[{mnemonicId}]"

# Shops have their own Asset path
# If objectId is an array, assume [layerId, objectId]
# TODO: We could combine this with EntDefAsset; it's a kind of "ObjAsset"
def ShopAsset(mapId, subMapId, fileName, objectId):
  layerId = 0
  if isinstance(objectId, list):
    layerId = objectId[0]
    objectId = objectId[1]
  subMapStr = '' if subMapId is None else f"_{subMapId}"
  return f"Assets/GameAssets/Serial/Res/Map/Map_{mapId}/Map_{mapId}{subMapStr}/{fileName}:/layers/[{layerId}]/objects/[{objectId}]/properties"

# There's probably a cleaner way to specify this...
def make_pristine_locations(regions):
  res = {}
  for reg_data in regions.values():
    for loc_name, data in reg_data.locations.items():
      res[loc_name] = data
  return res



# Helper: Retrieve all item names that *might* be part of a randomizer.
# Note: This should be a superset of all possible items given through all possible options.
#       The 'item_name_to_id' and other variables in our World are instance variables, but I am not sure
#       if the AP code creates two FF5World instances (if there are 2 players) or just one. I'd also like to keep
#       item IDs consistent, so we'll enforce that using this function.
def get_all_item_names():
  res = set()

  # Add normal items
  for name in pristine_items.keys():
    res.add(name)

  # Scan for Location-specific Jumbos
  for entry in pristine_locations.values():
    if entry.loc_id is not None:  # Not an Event
      if entry.orig_item not in res:
        res.add(normalize_item_name(entry.orig_item))

  # Sorting is needed to preserve Jumbo item ID ordering
  return sorted(res)


# Turns a non-normalized (usually Jumbo) item name string into a list of [(item_number, item_name), ...]
def parse_jumbo_items(origNameStr):
  # The "+" is non-negotiable
  entries = origNameStr.split('+')

  # Build it as we go
  res = []
  for entry in entries:
    # Pull out the "5x" or "5" prefix
    parts = entry.strip().split(' ', 1)
    if len(parts) == 1:
      parts = ['1', parts[0]]   # "(1) Whip, the 1 is optional"
    count_str = parts[0]
    if count_str.endswith('x'):
      count_str = count_str[:-1]
    if count_str.isdigit():
      parts[0] = count_str
    else:
      parts = ['1', entry.strip()]   # "Power Drink" isn't a count of "Power", so we restore the item
    parts = [x.strip() for x in parts]  # Could be whitespace between "1x " and "Potion"

    # Now check the item; mostly we try to fix a trailing 's' or 'es'
    if parts[1] not in pristine_items:
      if parts[1].endswith('s') and parts[1][:-1] in pristine_items:
        parts[1] = parts[1][:-1]
      elif parts[1].endswith('es') and parts[1][:-2] in pristine_items:
        parts[1] = parts[1][:-2]
      else:
        raise Exception(f"Invalid Item Name: {parts[1]} in {origNameStr}")

    # Special-case verification for jumbos
    if origNameStr not in pristine_items:
      if pristine_items[parts[1]].classification.lower() != 'filler':
        raise Exception(f"Cannot make a Jumbo item containing a non-filler base item: {parts[1]}")
      tags = pristine_items[parts[1]].tags
      if 'KeyItem' in tags or 'WorldTeleport' in tags or 'Legendary' in tags or 'Job' in tags:
        raise Exception(f"Cannot make a Jumbo item containing a base item with special tags: {parts[1]}")

    # Good enough!
    item_num = int(parts[0])
    res.append((int(parts[0]), parts[1]))

  return res


# Mostly applies to Jumbo items, but turns "2x Potions + 1 Ether" into its canonical form (2x Potion + 1x Ether)
def normalize_item_name(origNameStr):
  # Special-case "1 <Pristine>" item
  if origNameStr in pristine_items:
    return origNameStr

  # Parse it into (id,count) pairs
  items = parse_jumbo_items(origNameStr)

  # Now just build it up!
  return ' + '.join([f"{entry[0]}x {entry[1]}" for entry in items])






# Helper: Validate Data
def validate_pristine():
  # Exit early on any error
  error = False

  # Confirm no duplicate item IDs
  seen_ids = set()
  for name, data in pristine_items.items():
    if data.content_id is not None and data.content_id in seen_ids:
      print(f"ERROR: Duplicate Item Id: {data.content_id}")
      error = True
    else:
      seen_ids.add(data.content_id)

  # Confirm no duplicate location IDs, and that they're within a valid range
  seen_ids = set()
  for name, data in pristine_locations.items():
    if isinstance(data, PristineLocation):
      if data.loc_id in seen_ids:
        print(f"ERROR: Duplicate Location Id: {data.loc_id}")
        error = True
      else:
        seen_ids.add(data.loc_id)

      if (data.loc_id < 90000) or (data.loc_id > 99999):
        print(f"ERROR: Location Id is out of range [90000,99999]: {data.loc_id}")
        error = True

  # Confirm that every Location names a valid Item (i.e., the item it gives/unlocks, not any Condition locking that Location)
  # (Skip Event Locations; they create the item they specify)
  for name, data in pristine_locations.items():
    if isinstance(data, PristineLocation):
      orig_name = data.orig_item
      if orig_name not in pristine_items:
        try:
          parse_jumbo_items(orig_name)
        except Exception:  # TODO: This never actually happens; the call to 'get_all_item_names()' in __init__ checks this first
          print(f"ERROR: Location refers to unknown (possibly jumbo) item: {orig_name}")
          error = True

  # Confirm that every Region Connection refers to regions that exist
  for regionA, regionB, connectRule in pristine_connections:
    if regionA not in pristine_regions:
      print(f"ERROR: Connection refers to unknown Region: {regionA}")
      error = True
    if regionB not in pristine_regions:
      print(f"ERROR: Connection refers to unknown Region: {regionB}")
      error = True

  # Check classification of Items/Locations
  for name, data in pristine_items.items():
    if data.classification not in ["Filler", "Progression", "Useful"]:  # We don't use the others yet...
      print(f"ERROR: Item refers to unknown Classification: {data.classification}")
      error = True
  #
  for name, data in pristine_locations.items():
    if isinstance(data, PristineLocation):
      if data.classification not in ["Default", "Priority", "Excluded"]:
        print(f"ERROR: Location refers to unknown Classification: {data.classification}")
        error = True

  # Check shops
  for name, data in pristine_shops.items():
    if data.region not in pristine_regions:
      print(f"ERROR: Shop refers to unknown Region: {data.region}")
      error = True
    for item in data.items.keys():
      if item not in pristine_items:
        print(f"ERROR: Shop refers to unknown Item: {item}")

  if error:
    raise Exception(f"Validation failed (see above).")



# List of patch filenames to apply, indexed by name
# At the moment, these are all required, but we might imagine a future where the player can turn some of them off
#   E.g., using the randomizer to *just* randomize every Job Crystal Shard, but without cutting the cutscenes short.
pristine_game_patches = {
  # Start a new game in Open World format
  "New Game Open World",

  # Cut out all the drama that happens in Crystal rooms; just give players their Jobs and set the appropriate Flags
  "Shorter Crystal Cutscenes",

  # Prepare our NPC + boss scripts that give us items; they need their own custom Message names, and they need to 
  #   have a 'marker' Nop put in place so that we can patch these confidently.
  "Prepare NPC and Boss Event Checks",
}


# Pristine items
# We index all of our Items by their name; the value is of type PristineItem
# Item tags are used similar to "groups" in Archipelago, to easy say things like "give me a Healing Consumable"
# Note that "classification" can be upgraded or downgraded; for example, the Jobs can be
#   downgraded from Progression to Useful if the Player chooses not to do a Job Fair run.
# TODO: Document how Gil is supposed to work... I think we can specify "1 Gil" in the Locations, but how does that translate to non-pristine?
pristine_items = {
  # These are first-class items per FF5

  # Consumables
  # TODO: Some of these should also be "Mix"
  "Gil":           PristineItem(1,    "Filler",      ["Gil"]),
  "Potion":        PristineItem(2,    "Filler",      ["Consumable", "HealHP"]),
  "Hi-Potion":     PristineItem(3,    "Filler",      ["Consumable", "HealHP"]),
  "Phoenix Down":  PristineItem(4,    "Filler",      ["Consumable", "Revive"]),
  "Ether":         PristineItem(5,    "Filler",      ["Consumable", "HealMP"]),
  "Antidote":      PristineItem(6,    "Filler",      ["Consumable", "HealStatus"]),
  "Eye Drops":     PristineItem(7,    "Filler",      ["Consumable", "HealStatus"]),
  "Gold Needle":   PristineItem(8,    "Filler",      ["Consumable", "HealStatus"]),
  "Maiden's Kiss": PristineItem(9,    "Filler",      ["Consumable", "HealStatus"]),
  "Mallet":        PristineItem(10,   "Filler",      ["Consumable", "HealStatus"]),
  "Holy Water":    PristineItem(11,   "Filler",      ["Consumable", "HealStatus"]),
  "Tent":          PristineItem(12,   "Filler",      ["FieldItem", "Revive","HealHP","HealMP"]),
  "Cottage":       PristineItem(13,   "Filler",      ["FieldItem", "Revive","HealHP","HealMP"]),
  "Elixir":        PristineItem(14,   "Filler",      ["Consumable", "HealMP","HealMP"]),

  # Drink/Mix
  "Goliath Tonic": PristineItem(15,   "Filler",      ["Drink"]),
  "Power Drink":   PristineItem(16,   "Filler",      ["Drink"]),
  "Speed Shake":   PristineItem(17,   "Filler",      ["Drink"]),
  "Iron Draft":    PristineItem(18,   "Filler",      ["Drink"]),
  "Hero Cocktail": PristineItem(19,   "Filler",      ["Drink"]),
  "Turtle Shell":  PristineItem(20,   "Filler",      ["Mix"]),
  "Dragon Fang":   PristineItem(21,   "Filler",      ["Mix"]),
  "Dark Matter":   PristineItem(22,   "Filler",      ["Mix"]),

  # Throw/Use in Battle
  "Magic Lamp":       PristineItem(23,   "Filler",      ["Bomb", "Infinite", "Priceless"]),
  "Flame Scroll":     PristineItem(24,   "Filler",      ["Bomb"]),
  "Water Scroll":     PristineItem(25,   "Filler",      ["Bomb"]),
  "Lightning Scroll": PristineItem(26,   "Filler",      ["Bomb"]),
  "Ash":              PristineItem(27,   "Filler",      ["Bomb", "Useless"]),
  "Shuriken":         PristineItem(28,   "Filler",      ["Bomb"]),
  "Fuma Shuriken":    PristineItem(29,   "Filler",      ["Bomb"]),

  # "Learn a Summon" (yes, the game skips from 29 to 33)
  # These currently drop from their respective combats
  "Ramuh":         PristineItem(33,   "Filler",      ["LearnSummon"]),
  "Catoblepas":    PristineItem(34,   "Filler",      ["LearnSummon"]),
  "Golem":         PristineItem(35,   "Filler",      ["LearnSummon"]),

  # Key Items (yes, id skips are expected)
  "Dragon Seal":     PristineItem(36,   "Filler",      ["KeyItem", "SuperBossDrop"]),
  "Omega Badge":     PristineItem(37,   "Filler",      ["KeyItem", "SuperBossDrop"]),
  "Galuf's Bangle":  PristineItem(39,   "Filler",      ["KeyItem"]),  # No idea what this does. Adds Krile to the party?
  "Memento":         PristineItem(40,   "Filler",      ["KeyItem"]),  # Nope, no clue
  "Pendant1":        PristineItem(42,   "Filler",      ["KeyItem"]),  # Not sure why there are two of these; Lenna's vs. Faris's perhaps?
  "Pendant2":        PristineItem(43,   "Filler",      ["KeyItem"]),  # Same
  "Canal Key":       PristineItem(44,   "Filler",      ["KeyItem","Unused"]),  # Access: Canal
  "Dragon Grass":    PristineItem(45,   "Filler",      ["KeyItem","Unused"]),
  "Adamantite":      PristineItem(47,   "Progression", ["KeyItem"]),
  "Whisperweed":     PristineItem(49,   "Filler",      ["KeyItem","Unused"]),
  "Guardian Branch": PristineItem(50,   "Progression", ["KeyItem"]),  # Access: Forest of Moore
  "Sealed Tome":     PristineItem(51,   "Progression", ["KeyItem"]),  # Access: Four Tablet Dungeons
  "First Tablet":    PristineItem(52,   "Progression", ["KeyItem", "StoneTablet"]),  # Allows access to Legendary weapons (3 each)
  "Second Tablet":   PristineItem(53,   "Progression", ["KeyItem", "StoneTablet"]),
  "Third Tablet":    PristineItem(54,   "Progression", ["KeyItem", "StoneTablet"]),
  "Fourth Tablet":   PristineItem(55,   "Progression", ["KeyItem", "StoneTablet"]),
  "World Map":       PristineItem(56,   "Filler",      ["KeyItem"]),
  "Splinter":        PristineItem(57,   "Filler",      ["KeyItem"]),
  "Dungeon Key":     PristineItem(58,   "Filler",      ["KeyItem"]),  # Which dungeon is this again?

  # Weapons
  "Knife":             PristineItem(60,  "Filler",      ["Weapon","Knife"]),
  "Dagger":            PristineItem(61,  "Filler",      ["Weapon","Knife"]),
  "Mythril Knife":     PristineItem(62,  "Filler",      ["Weapon","Knife"]),
  "Mage Masher":       PristineItem(63,  "Filler",      ["Weapon","Knife"]),
  "Main Gauche":       PristineItem(64,  "Filler",      ["Weapon","Knife"]),
  "Orichalcum Dirk":   PristineItem(65,  "Filler",      ["Weapon","Knife"]),
  "Dancing Dagger":    PristineItem(66,  "Filler",      ["Weapon","Knife"]),
  "Air Knife":         PristineItem(67,  "Filler",      ["Weapon","Knife"]),
  "Thief Knife":       PristineItem(68,  "Filler",      ["Weapon","Knife"]),
  "Assassin's Dagger": PristineItem(69,  "Filler",      ["Weapon","Knife","Legendary"]),
  "Man-Eater":         PristineItem(70,  "Filler",      ["Weapon","Knife"]),
  "Chicken Knife":     PristineItem(72,  "Filler",      ["Weapon","Knife","MooreChoice"]),
  #
  "Kunai":             PristineItem(73,  "Filler",      ["Weapon","ShortSword"]),
  "Kodachi":           PristineItem(74,  "Filler",      ["Weapon","ShortSword"]),
  "Sasuke's Katana":   PristineItem(75,  "Filler",      ["Weapon","ShortSword","Legendary"]),
  #
  "Broadsword":        PristineItem(77,  "Filler",      ["Weapon","Sword"]),
  "Long Sword":        PristineItem(78,  "Filler",      ["Weapon","Sword"]),
  "Mythril Sword":     PristineItem(79,  "Filler",      ["Weapon","Sword"]),
  "Coral Sword":       PristineItem(80,  "Filler",      ["Weapon","Sword"]),
  "Ancient Sword":     PristineItem(81,  "Filler",      ["Weapon","Sword"]),
  "Sleep Blade":       PristineItem(82,  "Filler",      ["Weapon","Sword"]),
  "Rune Blade":        PristineItem(83,  "Filler",      ["Weapon","Sword"]),
  "Great Sword":       PristineItem(84,  "Filler",      ["Weapon","Sword"]),
  "Excalipoor":        PristineItem(85,  "Filler",      ["Weapon","Sword","Useless"]),  # Yes, I know it has uses...
  "Enhancer":          PristineItem(86,  "Filler",      ["Weapon","Sword"]),
  #
  "Flametongue":       PristineItem(88,  "Filler",      ["Weapon","KnightSword"]),
  "Icebrand":          PristineItem(89,  "Filler",      ["Weapon","KnightSword"]),
  "Blood Sword":       PristineItem(90,  "Filler",      ["Weapon","KnightSword"]),
  "Defender":          PristineItem(91,  "Filler",      ["Weapon","KnightSword"]),
  "Excalibur":         PristineItem(92,  "Filler",      ["Weapon","KnightSword","Legendary"]),
  "Ragnarok":          PristineItem(93,  "Filler",      ["Weapon","KnightSword"]),
  "Brave Blade":       PristineItem(95,  "Filler",      ["Weapon","KnightSword","MooreChoice"]),
  #
  "Spear":             PristineItem(96,  "Filler",      ["Weapon","Spear"]),
  "Mythril Spear":     PristineItem(97,  "Filler",      ["Weapon","Spear"]),
  "Trident":           PristineItem(98,  "Filler",      ["Weapon","Spear"]),
  "Wind Spear":        PristineItem(99,  "Filler",      ["Weapon","Spear"]),
  "Heavy Lance":       PristineItem(100, "Filler",      ["Weapon","Spear"]),
  "Javelin":           PristineItem(101, "Filler",      ["Weapon","Spear"]),
  "Twin Lance":        PristineItem(102, "Filler",      ["Weapon","Spear","Boomerang"]),  # It's kind of both
  "Partisan":          PristineItem(103, "Filler",      ["Weapon","Spear"]),
  "Holy Lance":        PristineItem(104, "Filler",      ["Weapon","Spear","Legendary"]),
  "Dragon Lance":      PristineItem(105, "Filler",      ["Weapon","Spear"]),
  #
  "Battle Axe":        PristineItem(107, "Filler",      ["Weapon","Axe"]),
  "Mythril Hammer":    PristineItem(108, "Filler",      ["Weapon","Hammer"]),
  "Ogre Killer":       PristineItem(109, "Filler",      ["Weapon","Axe"]),
  "War Hammer":        PristineItem(110, "Filler",      ["Weapon","Hammer"]),
  "Death Sickle":      PristineItem(111, "Filler",      ["Weapon","Axe"]),
  "Poison Axe":        PristineItem(112, "Filler",      ["Weapon","Axe"]),
  "Gaia Hammer":       PristineItem(113, "Filler",      ["Weapon","Hammer"]),
  "Rune Axe":          PristineItem(114, "Filler",      ["Weapon","Axe","Legendary"]),
  "Thor's Hammer":     PristineItem(115, "Filler",      ["Weapon","Hammer"]),
  "Titan's Axe":       PristineItem(116, "Filler",      ["Weapon","Axe"]),
  #
  "Ashura":            PristineItem(118, "Filler",      ["Weapon","Katana"]),
  "Wind Slash":        PristineItem(119, "Filler",      ["Weapon","Katana"]),
  "Osafune":           PristineItem(120, "Filler",      ["Weapon","Katana"]),
  "Kotetsu":           PristineItem(121, "Filler",      ["Weapon","Katana"]),
  "Kikuichimonji":     PristineItem(122, "Filler",      ["Weapon","Katana"]),
  "Murasame":          PristineItem(123, "Filler",      ["Weapon","Katana"]),
  "Masamune":          PristineItem(124, "Filler",      ["Weapon","Katana","Legendary"]),
  "Murakumo":          PristineItem(125, "Filler",      ["Weapon","Katana"]),
  #
  "Rod":               PristineItem(127, "Filler",      ["Weapon","Rod"]), 
  "Flame Rod":         PristineItem(128, "Filler",      ["Weapon","Rod","Bomb"]), 
  "Frost Rod":         PristineItem(129, "Filler",      ["Weapon","Rod","Bomb"]), 
  "Thunder Rod":       PristineItem(130, "Filler",      ["Weapon","Rod","Bomb"]), 
  "Poison Rod":        PristineItem(131, "Filler",      ["Weapon","Rod","Bomb"]), 
  "Lilith Rod":        PristineItem(132, "Filler",      ["Weapon","Rod"]), 
  "Magus Rod":         PristineItem(133, "Filler",      ["Weapon","Rod","Legendary"]), 
  "Wonder Wand":       PristineItem(134, "Filler",      ["Weapon","Rod","Bomb","Infinite"]), 
  #
  "Staff":             PristineItem(136, "Filler",      ["Weapon","Staff"]), 
  "Healing Staff":     PristineItem(137, "Filler",      ["Weapon","Staff","HealHP","Infinite"]), 
  "Power Staff":       PristineItem(138, "Filler",      ["Weapon","Staff"]), 
  "Staff of Light":    PristineItem(139, "Filler",      ["Weapon","Staff","Bomb"]), 
  "Sage's Staff":      PristineItem(140, "Filler",      ["Weapon","Staff","Legendary"]), 
  "Judgment Staff":    PristineItem(141, "Filler",      ["Weapon","Staff"]), 
  "Flail":             PristineItem(143, "Filler",      ["Weapon","Staff"]), 
  "Morning Star":      PristineItem(144, "Filler",      ["Weapon","Staff"]), 
  #
  "Silver Bow":        PristineItem(145, "Filler",      ["Weapon","Bow"]), 
  "Flame Bow":         PristineItem(146, "Filler",      ["Weapon","Bow"]), 
  "Frost Bow":         PristineItem(147, "Filler",      ["Weapon","Bow"]), 
  "Thunder Bow":       PristineItem(148, "Filler",      ["Weapon","Bow"]), 
  "Dark Bow":          PristineItem(149, "Filler",      ["Weapon","Bow"]), 
  "Magic Bow":         PristineItem(150, "Filler",      ["Weapon","Bow"]), 
  "Killer Bow":        PristineItem(151, "Filler",      ["Weapon","Bow"]), 
  "Elven Bow":         PristineItem(152, "Filler",      ["Weapon","Bow"]), 
  "Hayate Bow":        PristineItem(153, "Filler",      ["Weapon","Bow"]), 
  "Aevis Killer":      PristineItem(154, "Filler",      ["Weapon","Bow"]), 
  "Yoichi's Bow":      PristineItem(155, "Filler",      ["Weapon","Bow","Legendary"]), 
  "Artemis's Bow":     PristineItem(156, "Filler",      ["Weapon","Bow"]), 
  #
  "Silver Harp":       PristineItem(158, "Filler",      ["Weapon","Harp"]), 
  "Dream Harp":        PristineItem(159, "Filler",      ["Weapon","Harp"]), 
  "Lamia's Harp":      PristineItem(160, "Filler",      ["Weapon","Harp"]), 
  "Apollo's Harp":     PristineItem(161, "Filler",      ["Weapon","Harp","Legendary"]), 
  #
  "Whip":              PristineItem(162, "Filler",      ["Weapon","Whip"]), 
  "Blitz Whip":        PristineItem(163, "Filler",      ["Weapon","Whip"]), 
  "Chain Whip":        PristineItem(164, "Filler",      ["Weapon","Whip"]), 
  "Beast Killer":      PristineItem(165, "Filler",      ["Weapon","Whip"]), 
  "Fire Lash":         PristineItem(166, "Filler",      ["Weapon","Whip","Legendary"]), 
  "Dragon's Whisker":  PristineItem(167, "Filler",      ["Weapon","Whip"]), 
  #
  "Diamond Bell":      PristineItem(168, "Filler",      ["Weapon","Bell"]), 
  "Gaia Bell":         PristineItem(169, "Filler",      ["Weapon","Bell"]), 
  "Rune Chime":        PristineItem(170, "Filler",      ["Weapon","Bell","Legendary"]), 
  "Tinklebell":        PristineItem(171, "Filler",      ["Weapon","Bell"]), 
  #
  "Moonring Blade":    PristineItem(172, "Filler",      ["Weapon","Boomerang"]), 
  "Rising Sun":        PristineItem(173, "Filler",      ["Weapon","Boomerang"]), 


  # Armor
  "Leather Shield":    PristineItem(178, "Filler",      ["Armor","Shield"]), 
  "Bronze Shield":     PristineItem(179, "Filler",      ["Armor","Shield"]), 
  "Iron Shield":       PristineItem(180, "Filler",      ["Armor","Shield"]), 
  "Mythril Shield":    PristineItem(181, "Filler",      ["Armor","Shield"]), 
  "Golden Shield":     PristineItem(182, "Filler",      ["Armor","Shield"]), 
  "Aegis Shield":      PristineItem(183, "Filler",      ["Armor","Shield"]), 
  "Diamond Shield":    PristineItem(184, "Filler",      ["Armor","Shield"]), 
  "Flame Shield":      PristineItem(185, "Filler",      ["Armor","Shield"]), 
  "Ice Shield":        PristineItem(186, "Filler",      ["Armor","Shield"]), 
  "Crystal Shield":    PristineItem(187, "Filler",      ["Armor","Shield"]), 
  "Genji Shield":      PristineItem(188, "Filler",      ["Armor","Shield"]), 
  #
  "Leather Cap":       PristineItem(190, "Filler",      ["Armor","Hat"]), 
  "Plumed Hat":        PristineItem(191, "Filler",      ["Armor","MageHat"]), 
  "Hypno Crown":       PristineItem(192, "Filler",      ["Armor","MageHat"]), 
  "Green Beret":       PristineItem(194, "Filler",      ["Armor","Hat"]), 
  "Headband":          PristineItem(195, "Filler",      ["Armor","Hat"]), 
  "Tiger Mask":        PristineItem(196, "Filler",      ["Armor","Hat"]), 
  "Black Cowl":        PristineItem(197, "Filler",      ["Armor","Hat"]), 
  "Lamia's Tiara":     PristineItem(198, "Filler",      ["Armor","MageHat"]), 
  "Wizard's Hat":      PristineItem(199, "Filler",      ["Armor","MageHat"]), 
  "Sage's Miter":      PristineItem(200, "Filler",      ["Armor","MageHat"]), 
  "Circlet":           PristineItem(201, "Filler",      ["Armor","MageHat"]), 
  "Gold Hairpin":      PristineItem(202, "Filler",      ["Armor","MageHat"]), 
  "Ribbon":            PristineItem(203, "Filler",      ["Armor","Ribbon"]), 
  "Bronze Helm":       PristineItem(204, "Filler",      ["Armor","Helmet"]), 
  "Iron Helm":         PristineItem(205, "Filler",      ["Armor","Helmet"]), 
  "Mythril Helm":      PristineItem(206, "Filler",      ["Armor","Helmet"]), 
  "Golden Helm":       PristineItem(207, "Filler",      ["Armor","Helmet"]), 
  "Diamond Helm":      PristineItem(208, "Filler",      ["Armor","Helmet"]), 
  "Crystal Helm":      PristineItem(209, "Filler",      ["Armor","Helmet"]), 
  "Genji Helm":        PristineItem(210, "Filler",      ["Armor","Helmet"]), 
  "Thornlet":          PristineItem(212, "Filler",      ["Armor","Helmet"]), 
  #
  "Leather Armor":     PristineItem(213, "Filler",      ["Armor","LightMail"]),
  "Angel Robe":        PristineItem(214, "Filler",      ["Armor","Robe"]),
  "Mirage Vest":       PristineItem(215, "Filler",      ["Armor","LightMail"]),
  "Rainbow Dress":     PristineItem(216, "Filler",      ["Armor","Robe"]),
  "Copper Cuirass":    PristineItem(218, "Filler",      ["Armor","LightMail"]),
  "Kenpo Gi":          PristineItem(219, "Filler",      ["Armor","LightMail"]),
  "Silver Plate":      PristineItem(220, "Filler",      ["Armor","LightMail"]),
  "Ninja Suit":        PristineItem(221, "Filler",      ["Armor","LightMail"]),
  "Power Sash":        PristineItem(222, "Filler",      ["Armor","LightMail"]),
  "Diamond Plate":     PristineItem(223, "Filler",      ["Armor","LightMail"]),
  "Black Garb":        PristineItem(224, "Filler",      ["Armor","LightMail"]),
  "Bone Mail":         PristineItem(225, "Filler",      ["Armor","LightMail"]),
  "Cotton Robe":       PristineItem(226, "Filler",      ["Armor","Robe"]),
  "Silk Robe":         PristineItem(227, "Filler",      ["Armor","Robe"]),
  "Sage's Surplice":   PristineItem(228, "Filler",      ["Armor","Robe"]),
  "Gaia Gear":         PristineItem(229, "Filler",      ["Armor","Robe"]),
  "Luminous Robe":     PristineItem(230, "Filler",      ["Armor","Robe"]),
  "Black Robe":        PristineItem(231, "Filler",      ["Armor","Robe"]),
  "White Robe":        PristineItem(232, "Filler",      ["Armor","Robe"]),
  "Bronze Armor":      PristineItem(234, "Filler",      ["Armor","HeavyMail"]),
  "Iron Armor":        PristineItem(235, "Filler",      ["Armor","HeavyMail"]),
  "Mythril Armor":     PristineItem(236, "Filler",      ["Armor","HeavyMail"]),
  "Golden Armor":      PristineItem(237, "Filler",      ["Armor","HeavyMail"]),
  "Diamond Armor":     PristineItem(238, "Filler",      ["Armor","HeavyMail"]),
  "Crystal Armor":     PristineItem(239, "Filler",      ["Armor","HeavyMail"]),
  "Genji Armor":       PristineItem(240, "Filler",      ["Armor","HeavyMail"]),
  #
  "Mythril Gloves":    PristineItem(242, "Filler",      ["Armor","Gauntlets"]),
  "Thief's Gloves":    PristineItem(243, "Filler",      ["Armor","Accessory"]),
  "Gauntlets":         PristineItem(244, "Filler",      ["Armor","Gauntlets"]),
  "Titan's Gloves":    PristineItem(245, "Filler",      ["Armor","Gauntlets"]),
  "Genji Gloves":      PristineItem(246, "Filler",      ["Armor","Gauntlets"]),
  "Silver Armlet":     PristineItem(247, "Filler",      ["Armor","Armlet"]),
  "Power Armlet":      PristineItem(248, "Filler",      ["Armor","Armlet"]),
  "Diamond Armlet":    PristineItem(249, "Filler",      ["Armor","Armlet"]),
  "Leather Shoes":     PristineItem(251, "Filler",      ["Armor","Accessory"]),
  "Hermes' Sandals":   PristineItem(252, "Filler",      ["Armor","Accessory","Priceless"]),
  "Red Slippers":      PristineItem(253, "Filler",      ["Armor","Accessory"]),
  "Angel Ring":        PristineItem(254, "Filler",      ["Armor","Accessory"]),
  "Flame Ring":        PristineItem(255, "Filler",      ["Armor","Accessory"]),
  "Coral Ring":        PristineItem(256, "Filler",      ["Armor","Accessory"]),
  "Reflect Ring":      PristineItem(257, "Filler",      ["Armor","Accessory"]),
  "Protect Ring":      PristineItem(258, "Filler",      ["Armor","Accessory"]),
  "Cursed Ring":       PristineItem(259, "Filler",      ["Armor","Accessory"]),
  "Kaiser Knuckles":   PristineItem(260, "Filler",      ["Armor","Accessory"]),
  "Silver Specs":      PristineItem(261, "Filler",      ["Armor","Accessory"]),
  "Elven Mantle":      PristineItem(262, "Filler",      ["Armor","Accessory"]),
  "Kornago Gourd":     PristineItem(266, "Filler",      ["Armor","Accessory"]),


  # Abilities that you learn (Magic, Summons, Songs)

  # White Magic
  "Cure":     PristineItem(374, "Filler",      ["Ability","WhiteMagic"]),
  "Libra":    PristineItem(375, "Filler",      ["Ability","WhiteMagic"]),
  "Poisona":  PristineItem(376, "Filler",      ["Ability","WhiteMagic"]),
  "Silence":  PristineItem(377, "Filler",      ["Ability","WhiteMagic"]),
  "Protect":  PristineItem(378, "Filler",      ["Ability","WhiteMagic"]),
  "Mini":     PristineItem(379, "Filler",      ["Ability","WhiteMagic"]),
  "Cura":     PristineItem(380, "Filler",      ["Ability","WhiteMagic"]),
  "Raise":    PristineItem(381, "Filler",      ["Ability","WhiteMagic"]),
  "Confuse":  PristineItem(382, "Filler",      ["Ability","WhiteMagic"]),
  "Blink":    PristineItem(383, "Filler",      ["Ability","WhiteMagic"]),
  "Shell":    PristineItem(384, "Filler",      ["Ability","WhiteMagic"]),
  "Esuna":    PristineItem(385, "Filler",      ["Ability","WhiteMagic"]),
  "Curaga":   PristineItem(386, "Filler",      ["Ability","WhiteMagic"]),
  "Reflect":  PristineItem(387, "Filler",      ["Ability","WhiteMagic"]),
  "Berserk":  PristineItem(388, "Filler",      ["Ability","WhiteMagic"]),
  "Arise":    PristineItem(389, "Filler",      ["Ability","WhiteMagic"]),
  "Holy":     PristineItem(390, "Filler",      ["Ability","WhiteMagic"]),
  "Dispel":   PristineItem(391, "Filler",      ["Ability","WhiteMagic"]),

  # Black Magic
  "Fire":       PristineItem(392, "Filler",      ["Ability","BlackMagic"]),
  "Blizzard":   PristineItem(393, "Filler",      ["Ability","BlackMagic"]),
  "Thunder":    PristineItem(394, "Filler",      ["Ability","BlackMagic"]),
  "Poison":     PristineItem(395, "Filler",      ["Ability","BlackMagic"]),
  "Sleep":      PristineItem(396, "Filler",      ["Ability","BlackMagic"]),
  "Toad":       PristineItem(397, "Filler",      ["Ability","BlackMagic"]),
  "Fira":       PristineItem(398, "Filler",      ["Ability","BlackMagic"]),
  "Blizzara":   PristineItem(399, "Filler",      ["Ability","BlackMagic"]),
  "Thundara":   PristineItem(400, "Filler",      ["Ability","BlackMagic"]),
  "Drain":      PristineItem(401, "Filler",      ["Ability","BlackMagic"]),
  "Break":      PristineItem(402, "Filler",      ["Ability","BlackMagic"]),
  "Bio":        PristineItem(403, "Filler",      ["Ability","BlackMagic"]),
  "Firaga":     PristineItem(404, "Filler",      ["Ability","BlackMagic"]),
  "Blizzaga":   PristineItem(405, "Filler",      ["Ability","BlackMagic"]),
  "Thundaga":   PristineItem(406, "Filler",      ["Ability","BlackMagic"]),
  "Flare":      PristineItem(407, "Filler",      ["Ability","BlackMagic"]),
  "Death":      PristineItem(408, "Filler",      ["Ability","BlackMagic"]),
  "Osmose":     PristineItem(409, "Filler",      ["Ability","BlackMagic"]),

  # Time Magic
  "Speed":    PristineItem(410, "Filler",      ["Ability","TimeMagic"]),
  "Slow":     PristineItem(411, "Filler",      ["Ability","TimeMagic"]),
  "Regen":    PristineItem(412, "Filler",      ["Ability","TimeMagic"]),
  "Mute":     PristineItem(413, "Filler",      ["Ability","TimeMagic"]),
  "Haste":    PristineItem(414, "Filler",      ["Ability","TimeMagic"]),
  "Float":    PristineItem(415, "Filler",      ["Ability","TimeMagic"]),
  "Gravity":  PristineItem(416, "Filler",      ["Ability","TimeMagic"]),
  "Stop":     PristineItem(417, "Filler",      ["Ability","TimeMagic"]),
  "Teleport": PristineItem(418, "Filler",      ["Ability","TimeMagic"]),
  "Comet":    PristineItem(419, "Filler",      ["Ability","TimeMagic"]),
  "Slowga":   PristineItem(420, "Filler",      ["Ability","TimeMagic"]),
  "Return":   PristineItem(421, "Filler",      ["Ability","TimeMagic"]),
  "Graviga":  PristineItem(422, "Filler",      ["Ability","TimeMagic"]),
  "Hastega":  PristineItem(423, "Filler",      ["Ability","TimeMagic"]),
  "Old":      PristineItem(424, "Filler",      ["Ability","TimeMagic"]),
  "Meteor":   PristineItem(425, "Filler",      ["Ability","TimeMagic"]),
  "Quick":    PristineItem(426, "Filler",      ["Ability","TimeMagic"]),
  "Banish":   PristineItem(427, "Filler",      ["Ability","TimeMagic"]),

  # Summon Magic
  "Chocobo":    PristineItem(428, "Filler",      ["Ability","SummonMagic"]),
  "Sylph":      PristineItem(429, "Filler",      ["Ability","SummonMagic"]),
  "Remora":     PristineItem(430, "Filler",      ["Ability","SummonMagic"]),
  "Shiva":      PristineItem(431, "Filler",      ["Ability","SummonMagic"]),
  "Ramuh":      PristineItem(432, "Filler",      ["Ability","SummonMagic"]),
  "Ifrit":      PristineItem(433, "Filler",      ["Ability","SummonMagic"]),
  "Titan":      PristineItem(434, "Filler",      ["Ability","SummonMagic"]),
  "Golem":      PristineItem(435, "Filler",      ["Ability","SummonMagic"]),
  "Catoblepas": PristineItem(436, "Filler",      ["Ability","SummonMagic"]),
  "Carbuncle":  PristineItem(437, "Filler",      ["Ability","SummonMagic"]),
  "Syldra":     PristineItem(438, "Filler",      ["Ability","SummonMagic"]),
  "Odin":       PristineItem(439, "Filler",      ["Ability","SummonMagic"]),
  "Phoenix":    PristineItem(440, "Filler",      ["Ability","SummonMagic"]),
  "Leviathan":  PristineItem(441, "Filler",      ["Ability","SummonMagic"]),
  "Bahamut":    PristineItem(442, "Filler",      ["Ability","SummonMagic"]),

  # Bard Songs... maybe?
  # TODO: These events are not hooked yet (pianos et al)
  "Sinewy Etude":    PristineItem(461, "Filler",      ["Ability","BardSong"]),
  "Swift Song":      PristineItem(462, "Filler",      ["Ability","BardSong"]),
  "Mighty March":    PristineItem(463, "Filler",      ["Ability","BardSong"]),
  "Mana's Paean":    PristineItem(464, "Filler",      ["Ability","BardSong"]),
  "Hero's Rime":     PristineItem(465, "Filler",      ["Ability","BardSong"]),
  "Requiem":         PristineItem(466, "Filler",      ["Ability","BardSong"]),
  "Romeo's Ballad":  PristineItem(467, "Filler",      ["Ability","BardSong"]),
  "Alluring Air":    PristineItem(468, "Filler",      ["Ability","BardSong"]),

  # Blue Magic... maybe?
  # TODO; We may also want to "bundle" Blue Magic (buy a bunch at once)
  "Doom":              PristineItem(649, "Filler",      ["Ability","BlueMagic"]),
  "Roulette":          PristineItem(650, "Filler",      ["Ability","BlueMagic"]),
  "Aqua Breath":       PristineItem(651, "Filler",      ["Ability","BlueMagic"]),
  "Level 5 Death":     PristineItem(652, "Filler",      ["Ability","BlueMagic"]),
  "Level 4 Graviga":   PristineItem(653, "Filler",      ["Ability","BlueMagic"]),
  "Level 2 Old":       PristineItem(654, "Filler",      ["Ability","BlueMagic"]),
  "Level 3 Flare":     PristineItem(655, "Filler",      ["Ability","BlueMagic"]),
  "Pond's Chorus":     PristineItem(656, "Filler",      ["Ability","BlueMagic"]),
  "Lilliputian Lyric": PristineItem(657, "Filler",      ["Ability","BlueMagic"]),
  "Flash":             PristineItem(658, "Filler",      ["Ability","BlueMagic"]),
  "Time Slip":         PristineItem(659, "Filler",      ["Ability","BlueMagic"]),
  "Moon Flute":        PristineItem(660, "Filler",      ["Ability","BlueMagic"]),
  "Death Claw":        PristineItem(661, "Filler",      ["Ability","BlueMagic"]),
  "Aero":              PristineItem(662, "Filler",      ["Ability","BlueMagic"]),
  "Aera":              PristineItem(663, "Filler",      ["Ability","BlueMagic"]),
  "Aeroga":            PristineItem(664, "Filler",      ["Ability","BlueMagic"]),
  "Flame Thrower":     PristineItem(665, "Filler",      ["Ability","BlueMagic"]),
  "Goblin Punch":      PristineItem(666, "Filler",      ["Ability","BlueMagic"]),
  "Dark Spark":        PristineItem(667, "Filler",      ["Ability","BlueMagic"]),
  "Off-Guard":         PristineItem(668, "Filler",      ["Ability","BlueMagic"]),
  "Transfusion":       PristineItem(669, "Filler",      ["Ability","BlueMagic"]),
  "Mind Blast":        PristineItem(670, "Filler",      ["Ability","BlueMagic"]),
  "Vampire":           PristineItem(671, "Filler",      ["Ability","BlueMagic"]),
  "Magic Hammer":      PristineItem(672, "Filler",      ["Ability","BlueMagic"]),
  "Mighty Guard":      PristineItem(673, "Filler",      ["Ability","BlueMagic"]),
  "Self-Destruct":     PristineItem(674, "Filler",      ["Ability","BlueMagic"]),
  "???":               PristineItem(675, "Filler",      ["Ability","BlueMagic"]),
  "1000 Needles":      PristineItem(676, "Filler",      ["Ability","BlueMagic"]),
  "White Wind":        PristineItem(677, "Filler",      ["Ability","BlueMagic"]),
  "Missile":           PristineItem(678, "Filler",      ["Ability","BlueMagic"]),



  # These have no content_ids, and FF5 doesn't treat them as items


  # Initial job (not yet randomized)
  #"Job: Freelancer":    PristineItem(2000, "Progression", ["KeyItem","Job"], {'JobId':1}),
  # First set of jobs
  "Job: Knight":        PristineItem(2001, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：ナイト', 'JobId':7}),
  "Job: Monk":          PristineItem(2002, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：モンク', 'JobId':3}),
  "Job: Thief":         PristineItem(2003, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：シーフ', 'JobId':2}),
  "Job: White Mage":    PristineItem(2004, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：白魔道士', 'JobId':5}),
  "Job: Black Mage":    PristineItem(2005, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：黒魔道士', 'JobId':6}),
  "Job: Blue Mage":     PristineItem(2006, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：青魔道士', 'JobId':19}),
  # Second set of jobs (minus Mime)
  "Job: Berserker":     PristineItem(2007, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：バーサーカー', 'JobId':14}),
  "Job: Red Mage":      PristineItem(2008, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：赤魔道士', 'JobId':4}),
  "Job: Summoner":      PristineItem(2009, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：召喚士', 'JobId':13}),
  "Job: Time Mage":     PristineItem(2010, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：時魔道士', 'JobId':16}),
  "Job: Mystic Knight": PristineItem(2011, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：魔法剣士', 'JobId':20}),
  # Third set of jobs (castle)
  "Job: Beastmaster":   PristineItem(2012, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：魔獣使い', 'JobId':21}),
  "Job: Geomancer":     PristineItem(2013, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：風水師', 'JobId':10}),
  "Job: Ninja":         PristineItem(2014, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：忍者', 'JobId':8}),
  # Third set of jobs (crescent)
  "Job: Bard":          PristineItem(2015, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：吟遊詩人', 'JobId':12}),
  "Job: Ranger":        PristineItem(2016, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：狩人', 'JobId':9}),
  # Fourth set of jobs
  "Job: Samurai":       PristineItem(2017, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：侍', 'JobId':15}),
  "Job: Dragoon":       PristineItem(2018, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：竜騎士', 'JobId':11}),
  "Job: Dancer":        PristineItem(2019, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：踊り子', 'JobId':18}),
  "Job: Chemist":       PristineItem(2020, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：薬師', 'JobId':17}),
  # Final job (Mime)
  "Job: Mimic":         PristineItem(2021, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：ものまね師', 'JobId':22}),

  
  # Custom Items: I plan to mod these in to the game for various purposes
  "W1Teleport":         PristineItem(5000, "Progression", ["KeyItem","WorldTeleport"]),  # Teleports player to World Map for World 1


}


# Pristine regions, and the locations in them
# The outer string in each of these is the "Region" name. All rooms are indexed by name later on.
# All Locations are indexed by name as well.
# We typically do not refer to Locations manually; rather, we'll say things like "get me every Town Interior in the Tule Region".
# Note that the asset_paths are post-patch (see: "Shorter Crystal Cutscenes") --if we ever want to make patches optional, 
#   we will need to somehow take that into account here.
# A Location may also be an EventLocation (PristineEvent), which is paired with its own EventItem, and possible tags.
#   For now, I'd suggest only putting "CompletionCondition" in the tags (or nothing)
# I've chosen to segment the IDs for these locations, so that I can expand locations without messing with existing numbers (with a 9x segment as well)
# Note: For now, I'm assuming an open-world randomizer where you start in World 1, 2, or 3 and unlock the other 2.
# Classifications:
#   Default = Most things
#   Priority = Not set directly (may be set via Options + Tags)
#   Excluded = Only set directly on chests that are in locations that cannot be freely re-entered (Walse Tower, Karnak Castle, etc.). May be set via Options + Tags
# Tags:
#   Chest = Item is retrieved from a Treasure chest, NPC, Pot/Bush, etc.. Will be dynamically set to Excluded unless (TODO) option is set
#   Trapped = Used with "Chest" to indicate that a fight occurs before getting the item. Currently not used for anything.
#   CrystalShard = Item is retrieved from a Crystal Shard. Can be dynamically set to Priority via (TODO) option
#   BossDrop = Item is retrieved after defeating a Boss. (Technically we leave the boss drop unmodified and give the player the item via an Event after)
# Note: Our rule with bosses is that they are Progression *unless* they're Crystal/Summon bosses. For now, that means Crystal/Summon bosses are just not listed.
#       We may change this eventually...
# TODO: Right now, Siren drops Bronze Armor/Shield depending on form; we don't capture that. I guess we could give both?
# TODO: Right now, we give an *extra* item in the pool for the boss's drop, but we don't modify the boss's drop at all (just the event).
#       We may want to set the boss drop to "nothing" in the game if it's used...
pristine_regions = {
  # Starting Region, typically called "Menu"
  # I don't plan on putting an Locations here, but it's good to reference (for connections, etc.)
  "Menu" : PristineRegion(["Start"], {
  }),

  # World Map (World 1)
  "World Map 1" : PristineRegion(["PossibleFirstMap"], {   # No treasures on the overworld *glares at FF9*
  }),

  # Tycoon Meteor Area
  "Tycoon Meteor" : PristineRegion([], {
    "Tycoon Meteor Treasure A":  PristineLocation(90001, "Default", "Phoenix Down",   ["Chest"], EntDefAsset(30010, None, [1,0])),
  }),

  # Pirate's Cave + Hideout
  "Pirate Hideout" : PristineRegion(["Dungeon"], { 
    # Pirate's Cave
    "Pirate Cave Treasure A":  PristineLocation(90002,  "Default", "Leather Cap",     ["Chest"], EntDefAsset(30021, 2, [1,7])),

    # Pirate's Hideout
    "Pirate Hideout Treasure A":  PristineLocation(90003,  "Default",  "Tent",       ["Chest"], EntDefAsset(30021, 5, 0)),
    "Pirate Hideout Treasure B":  PristineLocation(90004,  "Default",  "Ether",      ["Chest"], EntDefAsset(30021, 5, 1)),
    "Pirate Hideout Treasure C":  PristineLocation(90005,  "Default",  "300 Gil",    ["Chest"], EntDefAsset(30021, 5, 5)),
    "Pirate Hideout Pirate NPC":  PristineLocation(90006,  "Default",  "8 Potions",  ["Chest"], ScrMnemAsset(30021, 4, 'sc_npc_30021_4_1', 6), {'Label':'PiratePotions'}),
  }),

  # Town of Tule
  "Tule" : PristineRegion(["Town"], {
    # Tule Exterior
    "Town of Tule Treasure A":  PristineLocation(90007, "Default",  "Phoenix Down",    ["Chest"], EntDefAsset(20010, None, 14)),
    "Town of Tule Treasure B":  PristineLocation(90008, "Default",  "Leather Shoes",   ["Chest"], EntDefAsset(20010, None, 15)),
    "Town of Tule Treasure C":  PristineLocation(90009, "Default",  "Tent",            ["Chest"], EntDefAsset(20010, None, 16)),
    "Town of Tule Treasure D":  PristineLocation(90010, "Default",  "Potion",          ["Chest"], EntDefAsset(20010, None, 17)),
    "Town of Tule Treasure E":  PristineLocation(90011, "Default",  "150 Gil",         ["Chest"], EntDefAsset(20010, None, 18)),

    # SKIP: We don't care about the Canal Key for now

    # Tule Interior: Greenhorn's Club
    "Tule Greenhorns Club 1F Treasure A":  PristineLocation(90012, "Default",  "Ether",          ["Chest"], EntDefAsset(20011, 1, 0)),
    "Tule Greenhorns Club 1F Treasure B":  PristineLocation(90013, "Default",  "100 Gil",        ["Chest"], EntDefAsset(20011, 1, 1)),
    "Tule Greenhorns Club 1F Treasure C":  PristineLocation(90014, "Default",  "Potion",         ["Chest"], EntDefAsset(20011, 1, 2)),
    "Tule Greenhorns Club 1F Treasure D":  PristineLocation(90015, "Default",  "Phoenix Down",   ["Chest"], EntDefAsset(20011, 1, 3)),
    "Tule Greenhorns Club 1F Treasure E":  PristineLocation(90016, "Default",  "Tent",           ["Chest"], EntDefAsset(20011, 1, 4)),
    "Tule Greenhorns Club 2F Trapped Chest A":  PristineLocation(90017,  "Default",  "Leather Shoes",  ["Chest","Trapped"], EntDefAsset(20011, 2, 0), { 'battle_id':'todo' }),
  }),

  # Wind Shrine (Wind Crystal Jobs)
  "Wind Shrine" : PristineRegion(["Dungeon"], {
    # Wind Shrine First Floor
    # I've modified the Flags so that this NPC is always present (in World 1)  --no need to make him Excluded!
    "Wind Shrine Tycoon NPC":     PristineLocation(90018, "Default", "5x Potion",    ["Chest"], ScrMnemAsset(30041, 1, 'sc_npc_30041_1_1', 5), {'Label':'WindShrinePotions'}),

    # Wind Shrine Interior
    "Wind Shrine 2F Treasure A":  PristineLocation(90019, "Default",  "Tent",        ["Chest"], EntDefAsset(30041, 2, 0)),
    "Wind Shrine 3F Treasure A":  PristineLocation(90020, "Default",  "Leather Cap", ["Chest"], EntDefAsset(30041, 4, 5)),
    "Wind Shrine 3F Treasure B":  PristineLocation(90021, "Default",  "Broadsword",  ["Chest"], EntDefAsset(30041, 5, 0)),
    "Wind Shrine 4F Treasure A":  PristineLocation(90022, "Default",  "Staff",       ["Chest"], EntDefAsset(30041, 7, 2)),

    # Boss: Not Listed

    # Wind Shrine: Crystal Room
    "Wind Shrine Crystal Shard A":  PristineLocation(90023, "Default",  "Job: Knight",      ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 8), {'Label':'WindCrystalShard1'}),
    "Wind Shrine Crystal Shard B":  PristineLocation(90024, "Default",  "Job: Monk",        ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 9), {'Label':'WindCrystalShard2'}),
    "Wind Shrine Crystal Shard C":  PristineLocation(90025, "Default",  "Job: Thief",       ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 10), {'Label':'WindCrystalShard3'}),
    "Wind Shrine Crystal Shard D":  PristineLocation(90026, "Default",  "Job: White Mage",  ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 11), {'Label':'WindCrystalShard4'}),
    "Wind Shrine Crystal Shard E":  PristineLocation(90027, "Default",  "Job: Black Mage",  ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 12), {'Label':'WindCrystalShard5'}),
    "Wind Shrine Crystal Shard F":  PristineLocation(90028, "Default",  "Job: Blue Mage",   ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 13), {'Label':'WindCrystalShard6'}),
  }),

  # Torna Canal
  "Torna Canal" : PristineRegion(["Dungeon"], {
    # Boss: Karlabos
    # TODO: See notes in __init__::generate; there's some annoying issues with this...
    #"Torna Canal Boss: Karlabos":  PristineLocation(90029, "Default",  "Tent",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Ship Graveyard
  "Ship Graveyard" : PristineRegion(["Dungeon"], {
    # Exterior
    "Ship Graveyard Exterior Treasure A":  PristineLocation(90030, "Default",  "Flail",     ["Chest"], EntDefAsset(30060, None, 13)),

    # Sunken Shipwreck
    "Ship Graveyard Sunken Shipwreck Treasure A":  PristineLocation(90031, "Default",  "Antidote",     ["Chest"], EntDefAsset(30061, 14, 2)),
    "Ship Graveyard Sunken Shipwreck Treasure B":  PristineLocation(90032, "Default",  "Antidote",     ["Chest"], EntDefAsset(30061, 14, 4)),
    "Ship Graveyard Sunken Shipwreck Treasure C":  PristineLocation(90033, "Default",  "Phoenix Down", ["Chest"], EntDefAsset(30061, 14, 6)),
    "Ship Graveyard Sunken Shipwreck Treasure D":  PristineLocation(90034, "Default",  "Tent",         ["Chest"], EntDefAsset(30061, 3, 2)),
    "Ship Graveyard Sunken Shipwreck Treasure E":  PristineLocation(90035, "Default",  "990 Gil",      ["Chest"], EntDefAsset(30061, 4, 0)),
    "Ship Graveyard Sunken Shipwreck Treasure F":  PristineLocation(90036, "Default",  "Phoenix Down", ["Chest"], EntDefAsset(30061, 5, 1)),
    "Ship Graveyard Sunken Shipwreck Treasure G":  PristineLocation(90037, "Default",  "Potion",       ["Chest"], EntDefAsset(30061, 7, 0)),

    # We don't touch the map

    # Boss: Siren
    "Ship Graveyard Boss: Siren":  PristineLocation(90038, "Default",  "Bronze Armor",   ["BossDrop"], ScrMnemAsset(30060, None, 'sc_e_0030_1', 4), {'Label':'BossSirenItem'}),
  }),

  # Town of Carwen
  "Carwen" : PristineRegion(["Town"], {
    "Town of Carwen Treasure A":  PristineLocation(90039, "Default",  "Antidote",    ["Chest"], EntDefAsset(20020, None, 3)),
    "Town of Carwen Treasure B":  PristineLocation(90040, "Default",  "Frost Rod",   ["Chest"], EntDefAsset(20020, None, 4)),
    "Town of Carwen Treasure C":  PristineLocation(90041, "Default",  "1000 Gil",    ["Chest"], EntDefAsset(20021, 6, 6)),
  }),

  # North Mountain
  "North Mountain" : PristineRegion(["Dungeon"], {
    "North Mountain Treasure A":    PristineLocation(90042, "Default",  "Phoenix Down",   ["Chest"], EntDefAsset(30071, 1, 2)),
    "North Mountain Treasure B":    PristineLocation(90043, "Default",  "Gold Needle",    ["Chest"], EntDefAsset(30071, 1, 4)),
    
    # I'm ignoring this since I think people will forget that they got an item.
    #"North Mountain Cutscene Item": PristineLocation(90044,  "Mythril Helm",   [], ScrMnemAsset(-1, -1, '???', -1)),  # You get this right before the fight

    # Boss: Magissa and Forza
    "North Mountain Boss: Magissa and Forza":  PristineLocation(90045, "Default",  "Whip + Power Drink",   ["BossDrop"], ScrMnemAsset(30100, None, 'sc_e_0033_1', 4), {'Label':'BossMagissaItem'}),
  }),

  # Town of Walse
  "Walse" : PristineRegion(["Town"], {
    "Town of Walse Treasure A":  PristineLocation(90046, "Default",  "Silver Specs",    ["Chest"], EntDefAsset(20031, 1, 2)),
  }),

  # Castle Walse
  "Castle Walse" : PristineRegion(["Castle"], {
    # Basement 1 (Dangerous)
    "Castle Walse B1 Treasure A":  PristineLocation(90047, "Default",  "1000 Gil",     ["Chest"], EntDefAsset(20041, 10, 6)),
    "Castle Walse B1 Treasure B":  PristineLocation(90048, "Default",  "Speed",        ["Chest"], EntDefAsset(20041, 10, 7)),
    "Castle Walse B1 Treasure C":  PristineLocation(90049, "Default",  "1000 Gil",     ["Chest"], EntDefAsset(20041, 10, 8)),
    "Castle Walse B1 Treasure D":  PristineLocation(90050, "Default",  "Elven Mantle", ["Chest"], EntDefAsset(20041, 10, 9)),

    # Storehouse
    "Castle Walse Storehouse Treasure A":  PristineLocation(90051,  "Default",  "Tent",         ["Chest"], EntDefAsset(20041, 5, 2)),
    "Castle Walse Storehouse Treasure B":  PristineLocation(90052,  "Default",  "490 Gil",      ["Chest"], EntDefAsset(20041, 5, 3)),
    "Castle Walse Storehouse Treasure C":  PristineLocation(90053,  "Default",  "Phoenix Down", ["Chest"], EntDefAsset(20041, 5, 4)),

    # Boss: Shiva
    "Castle Walse Boss: Shiva":  PristineLocation(90054, "Default",  "Frost Rod",   ["BossDrop"], ScrMnemAsset(20041, 15, 'sc_e_0183_1', 8), {'Label':'BossShivaItem'}),
  }),

  # Tower of Walse (Water Crystal Jobs)
  "Tower of Walse" : PristineRegion(["Dungeon"], {
    # Dungeon Interior
    "Tower of Walse 5F Treasure A":  PristineLocation(90055,  "Excluded",  "Silk Robe",     ["Chest"], EntDefAsset(30121, 5, 5)),
    "Tower of Walse 5F Treasure B":  PristineLocation(90056,  "Excluded",  "Maiden's Kiss", ["Chest"], EntDefAsset(30121, 5, 6)),
    "Tower of Walse 9F Treasure A":  PristineLocation(90057,  "Excluded",  "Silver Armlet", ["Chest"], EntDefAsset(30121, 9, 4)),
    "Tower of Walse 9F Treasure B":  PristineLocation(90058,  "Excluded",  "Ether",         ["Chest"], EntDefAsset(30121, 9, 5)),

    # Boss: Skipping for now

    # Crystal Room
    "Tower of Walse Crystal Shard A":  PristineLocation(90059,  "Default",  "Job: Berserker",      ["CrystalShard"], ScrMnemAsset(30121, 10, 'sc_e_0039_1', 6), {'Label':'WaterCrystalShard1'}),
    "Tower of Walse Crystal Shard B":  PristineLocation(90060,  "Default",  "Job: Red Mage",       ["CrystalShard"], ScrMnemAsset(30121, 10, 'sc_e_0039_1', 7), {'Label':'WaterCrystalShard2'}),
    "Tower of Walse Crystal Shard C":  PristineLocation(90061,  "Default",  "Job: Summoner",       ["CrystalShard"], ScrMnemAsset(30121, 10, 'sc_e_0039_1', 8), {'Label':'WaterCrystalShard3'}),
    "Tower of Walse Crystal Shard D":  PristineLocation(90062,  "Default",  "Job: Time Mage",      ["CrystalShard"], ScrMnemAsset(30121, 10, 'sc_e_0039_1', 9), {'Label':'WaterCrystalShard4'}),
    "Tower of Walse Crystal Shard E":  PristineLocation(90063,  "Default",  "Job: Mystic Knight",  ["CrystalShard"], ScrMnemAsset(30121, 10, 'sc_e_0039_1', 10), {'Label':'WaterCrystalShard5'}),
  }),

  # Castle Tycoon
  # TODO: Seems like we might be missing 2 cottages; perhaps they're events?
  "Castle Tycoon" : PristineRegion(["Castle"], {
    # Exterior
    "Castle Tycoon Exterior Treasure A":  PristineLocation(90064,  "Default",  "Ether",        ["Chest"], EntDefAsset(20051, 10, 2)),
    "Castle Tycoon Exterior Treasure B":  PristineLocation(90065,  "Default",  "Cottage",      ["Chest"], EntDefAsset(20051, 10, 3)),
    "Castle Tycoon Exterior Treasure C":  PristineLocation(90066,  "Default",  "Phoenix Down", ["Chest"], EntDefAsset(20051, 10, 4)),
    "Castle Tycoon Exterior Treasure D":  PristineLocation(90067,  "Default",  "Elixir",       ["Chest"], EntDefAsset(20051, 10, 5)),

    # Interior: 4F
    "Castle Tycoon 4F Treasure A":  PristineLocation(90068,  "Default",  "Ether",         ["Chest"], EntDefAsset(20051, 14, 4)),
    "Castle Tycoon 4F Treasure B":  PristineLocation(90069,  "Default",  "Elixir",        ["Chest"], EntDefAsset(20051, 14, 5)),
    "Castle Tycoon 4F Treasure C":  PristineLocation(90070,  "Default",  "Phoenix Down",  ["Chest"], EntDefAsset(20051, 14, 6)),
    "Castle Tycoon 4F Treasure D":  PristineLocation(90071,  "Default",  "Maiden's Kiss", ["Chest"], EntDefAsset(20051, 14, 7)),

    # Storehouse
    "Castle Tycoon Storehouse Treasure A":  PristineLocation(90072,  "Default",  "Diamond Bell",  ["Chest"], EntDefAsset(20051, 5, [1,2])),
    "Castle Tycoon Storehouse Treasure B":  PristineLocation(90073,  "Default",  "Shuriken",      ["Chest"], EntDefAsset(20051, 5, [1,3])),
    "Castle Tycoon Storehouse Treasure C":  PristineLocation(90074,  "Default",  "Ashura",        ["Chest"], EntDefAsset(20051, 5, [1,4])),

    # Interior: 1F
    "Castle Tycoon 1F Treasure A":    PristineLocation(90075,  "Default",  "Hi-Potion",         ["Chest"], EntDefAsset(20051, 8, 4)),
    "Castle Tycoon Chancellor Gift":  PristineLocation(90076,  "Default",  "Healing Staff",     ["Chest"], ScrMnemAsset(20051, 5, 'sc_npc_20051_5_1', 10), {'Label':'ChancellorHealStaff'}),
  }),

  # Town of Karnak
  "Karnak" : PristineRegion(["Town"], {
    "Town of Karnak Treasure A":  PristineLocation(90077,  "Default",  "Flame Rod",    ["Chest","BlockedByFire"], EntDefAsset(20060, None, [1,2])),
  }),

  # Karnak Castle (Fire Crystal Jobs, First Half)
  "Karnak Castle" : PristineRegion(["Castle"], {
    # Interior: 1F
    "Karnak Castle 1F Trapped Chest A":  PristineLocation(90078,  "Default",    "Esuna",            ["Chest","Trapped"], EntDefAsset(20071, 1, 13)),
    "Karnak Castle 1F Trapped Chest B":  PristineLocation(90079,  "Excluded",   "Lightning Scroll", ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 1, 14)),

    # Interior: 2F
    "Karnak Castle 2F Treasure Chest A":  PristineLocation(90080,  "Excluded",   "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 10, 6)), 
    "Karnak Castle 2F Trapped Chest A":   PristineLocation(90081,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 7)), 
    "Karnak Castle 2F Trapped Chest B":   PristineLocation(90082,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 8)), 
    "Karnak Castle 2F Treasure Chest B":  PristineLocation(90083,  "Excluded",   "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 10, 9)), 
    "Karnak Castle 2F Trapped Chest C":   PristineLocation(90084,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 10)), 
    "Karnak Castle 2F Trapped Chest D":   PristineLocation(90085,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 11)), 
    "Karnak Castle 2F Trapped Chest E":   PristineLocation(90086,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 12)), 

    # Interior: B1
    "Karnak Castle B1 Trapped Chest A":   PristineLocation(90087,  "Excluded",   "Elven Mantle",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 13, 1)), 
    "Karnak Castle B1 Trapped Chest B":   PristineLocation(90088,  "Excluded",   "Main Gauche",    ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 16, 1)), 

    # Interior: B3
    "Karnak Castle B3 Trapped Chest A":   PristineLocation(90089,  "Excluded",   "Ribbon",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 5, 4)), 
    "Karnak Castle B3 Trapped Chest B":   PristineLocation(90090,  "Excluded",   "Shuriken", ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 5, 5)), 

    # Interior: B4
    "Karnak Castle B4 Treasure Chest A":  PristineLocation(90091,  "Excluded",  "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 6, 13)), 
    "Karnak Castle B4 Trapped Chest A":   PristineLocation(90092,  "Excluded",  "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 6, 14)), 

    # Iron Claw can't be added right now due to how the script chains (we'd have to show the reward before the combat). It's also 'Enc' instead of 'EncBoss' :P
    # 90093
  }),

  # Fire-Powered Ship
  # TODO: We should probably block this dungeon off from World 3 (Catapult) to prevent weird progression.
  #       If we keep it as part of World 3, we at least need to make sure you can't get to the Boss, since our patched event would warp you to World 1.
  "Fire Powered Ship" : PristineRegion(["Dungeon"], {
    "Fire Powered Ship Treasure Chest A":  PristineLocation(90094,  "Default",   "Thief's Gloves", ["Chest"], EntDefAsset(30151, 11, 25)), 
    "Fire Powered Ship Treasure Chest B":  PristineLocation(90095,  "Default",   "Green Beret",    ["Chest"], EntDefAsset(30151, 11, 26)), 
    "Fire Powered Ship Treasure Chest C":  PristineLocation(90096,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 20, [1,6])), 
    "Fire Powered Ship Treasure Chest D":  PristineLocation(90097,  "Default",   "Cottage",        ["Chest"], EntDefAsset(30151, 3, 0)), 
    "Fire Powered Ship Treasure Chest E":  PristineLocation(90098,  "Default",   "Mythril Gloves", ["Chest"], EntDefAsset(30151, 4, 2)), 
    "Fire Powered Ship Treasure Chest F":  PristineLocation(90099,  "Default",   "Phoenix Down",   ["Chest"], EntDefAsset(30151, 5, 6)), 
    "Fire Powered Ship Treasure Chest G":  PristineLocation(90100,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 6, 6)), 
    "Fire Powered Ship Treasure Chest H":  PristineLocation(90101,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 8, 2)), 
    "Fire Powered Ship Treasure Chest I":  PristineLocation(90102,  "Default",   "Moonring Blade", ["Chest"], EntDefAsset(30151, 9, 2)), 

    # Boss: Skipping, for now

    # Give them the Crystals here
    "Fire Powered Ship Crystal Shard A":  PristineLocation(90103,  "Default",  "Job: Beastmaster",  ["CrystalShard"], ScrMnemAsset(30151, 21, 'sc_e_0046_1', 6), {'Label':'FireCrystalShard1'}),
    "Fire Powered Ship Crystal Shard B":  PristineLocation(90104,  "Default",  "Job: Geomancer",    ["CrystalShard"], ScrMnemAsset(30151, 21, 'sc_e_0046_1', 7), {'Label':'FireCrystalShard2'}),
    "Fire Powered Ship Crystal Shard C":  PristineLocation(90105,  "Default",  "Job: Ninja",        ["CrystalShard"], ScrMnemAsset(30151, 21, 'sc_e_0046_1', 8), {'Label':'FireCrystalShard3'}),

    # ...and remove the fire from Karnak/Castle
    "RemoveKarnakFire": PristineEvent("FireBeGone", []),
  }),

  # Library of the Ancients
  "Library of the Ancients" : PristineRegion(["Dungeon"], {
    "Library of the Ancients Treasure Chest A":  PristineLocation(90106,  "Default",   "Ether",        ["Chest"], EntDefAsset(20221, 5, 3)), 
    "Library of the Ancients Treasure Chest B":  PristineLocation(90107,  "Default",   "Ninja Suit",   ["Chest"], EntDefAsset(20221, 6, 24)), 
    "Library of the Ancients Treasure Chest C":  PristineLocation(90108,  "Default",   "Phoenix Down", ["Chest"], EntDefAsset(20221, 9, 6)), 

    # Boss: Ifrit
    "Library of the Ancients Boss: Ifrit":  PristineLocation(90109, "Default",  "Flame Scroll",   ["BossDrop"], ScrMnemAsset(20221, 8, 'sc_e_0049_1', 10), {'Label':'BossIfritItem'}),

    # Boss: Byblos
    "Library of the Ancients Boss: Byblos":  PristineLocation(90110, "Default",  "Iron Draft",   ["BossDrop"], ScrMnemAsset(20221, 12, 'sc_e_0050_1', 3), {'Label':'BossByblosItem'}),
  }),

  # Istory (World Map Area)
  "Istory" : PristineRegion(["Town"], {
    # Boss: Ramuh
    # TODO: Ramuh is located in: Assets/GameAssets/Serial/Res/Battle/MonsterAI/sc_ai_040_Ramuh/sc_ai_040_Ramuh
    #       ...but the combat scripting is different. Looks like you can have pre-death messages, but only Items as drops.
    #       I'm not sure if it's save to unlock Jobs while in Combat --we could probably "pend" this item (if it's a job), but
    #       I'm not sure it's worth it. Will investigate with other summon+drops, later.
    #"Istory Forest Boss: Ramuh":  PristineLocation(90111, "Default",  "Lightning Scroll",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Jachol has shops
  "Jachol" : PristineRegion(["Town"], {
  }),

  # Jachol Cave
  # TODO: We need to make sure the player CAN'T free Lone Wolf, or the third item here disappears.
  "Jachol Cave" : PristineRegion(["Dungeon"], {
    "Jachol Cave Treasure Chest A":  PristineLocation(90112,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(30161, 2, 3)), 
    "Jachol Cave Treasure Chest B":  PristineLocation(90113,  "Default",   "Tent",        ["Chest"], EntDefAsset(30161, 2, 4)), 
    "Jachol Cave Treasure Chest C":  PristineLocation(90114,  "Default",   "Blitz Whip",  ["Chest"], ScrMnemAsset(30161, 2, 'sc_e_0362', 6), {'Label':'JacholCaveSpecialChestItem'}),
  }),

  # Town of Crescent (+ Black Chocobo Forest) (Fire Crystal Jobs, Second Half)
  "Crescent" : PristineRegion(["Town"], {
    "Black Chocobo Crystal Shard A":  PristineLocation(90115,  "Default",  "Job: Bard",        ["CrystalShard"], ScrMnemAsset(20110, None, 'sc_e_0056', 4), {'Label':'BlackChocoboShard1'}),
    "Black Chocobo Crystal Shard B":  PristineLocation(90116,  "Default",  "Job: Ranger",      ["CrystalShard"], ScrMnemAsset(20110, None, 'sc_e_0056', 5), {'Label':'BlackChocoboShard2'}),
  }),

  # Town of Lix - has shops
  "Lix" : PristineRegion(["Town"], {
  }),

  # Shifting Sands Desert
  "Shifting Sands Desert" : PristineRegion(["Dungeon"], {
    # Boss: Sandworm
    # TODO: We use "1 Gil" for "Nothing" boss drops. Might need a better option...
    "Shifting Sands Desert Boss: Sandworm":  PristineLocation(90117, "Default",  "1 Gil",   ["BossDrop"], ScrMnemAsset(30170, None, 'sc_e_0060_1', 5), {'Label':'BossSandwormItem'}),
  }),

  # Gohn; skipping (preserving number)

  # Catapult
  "Catapult" : PristineRegion([], {
    "Catapult Treasure Chest A":  PristineLocation(90118,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(20231, 4, 10)),
    "Catapult Treasure Chest B":  PristineLocation(90119,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(20231, 4, 11)),
    "Catapult Treasure Chest C":  PristineLocation(90120,  "Default",   "Mini",        ["Chest"], EntDefAsset(20231, 4, 12)),

    # Boss: Cray Claw
    # TODO: The real question is *where* to put him... I guess we could un-set Flag 67 and fight it when Cid/Mid meet you at the Catapult?
    #"Catapult Boss: Cray Claw":  PristineLocation(90121, "Default",  "Frost Bow",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Tycoon Meteor Interior (ID preserved)
  # Note: All Meteor + Adamant nonsense will be skipped; it will eventually just be the bosses (1 check each).
  "Tycoon Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Adamantoise
    "Tycoon Meteor Interior Boss: Adamantoise":  PristineLocation(90122, "Default",  "Adamantite",   ["BossDrop"], ScrMnemAsset(30011, 1, 'sc_e_0427_1', 4), {'Label':'BossAdamantoiseItem'}), 
  }),

  # Ronka Ruins (Earth Crystal Jobs)
  # TODO: Try to avoid making this area "Excluded" -- maybe we can keep Walse and Karnak open too?
  "Floating Ronka Ruins" : PristineRegion(["Dungeon"], {
    # Boss: Sol Cannon
    "High Altitude Boss: Sol Cannon":  PristineLocation(90123, "Default",  "Dark Matter",   ["BossDrop"], ScrMnemAsset(20260, None, 'sc_e_0073_2', 5), {'Label':'BossSolCannonItem'}),

    # Ronka Ruins Level 2
    "Ronka Ruins Level 2 Treasure Chest A":  PristineLocation(90124,  "Default",   "Golden Armor",   ["Chest"], EntDefAsset(30191, 2, 4)),   # TODO: This region needs to be checked by "Adamant"

    # Ronka Ruins Level 3
    "Ronka Ruins Level 3 Treasure Chest A":  PristineLocation(90125,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30191, 3, 14)),
    "Ronka Ruins Level 3 Treasure Chest B":  PristineLocation(90126,  "Default",   "Phoenix Down",   ["Chest"], EntDefAsset(30191, 3, 15)),
    "Ronka Ruins Level 3 Treasure Chest C":  PristineLocation(90127,  "Default",   "Golden Shield",  ["Chest"], EntDefAsset(30191, 3, 16)),

    # Ronka Ruins Level 4
    # NOTE: This is duplicated betwen sub-maps 5 and 11, so we must rewrite chests on both maps. I have no idea why.
    #       All item pickups appear to be on 5.
    "Ronka Ruins Level 4 Treasure Chest A":  PristineLocation(90128,  "Default",   "Hi-Potion",      ["Chest"], [EntDefAsset(30191, 5, 44), EntDefAsset(30191, 11, 44)]),
    "Ronka Ruins Level 4 Treasure Chest B":  PristineLocation(90129,  "Default",   "5000 Gil" ,      ["Chest"], [EntDefAsset(30191, 5, 45), EntDefAsset(30191, 11, 45)]),
    "Ronka Ruins Level 4 Treasure Chest C":  PristineLocation(90130,  "Default",   "Shuriken",       ["Chest"], [EntDefAsset(30191, 5, 46), EntDefAsset(30191, 11, 46)]),
    "Ronka Ruins Level 4 Treasure Chest D":  PristineLocation(90131,  "Default",   "Ancient Sword",  ["Chest"], [EntDefAsset(30191, 5, 47), EntDefAsset(30191, 11, 47)]),
    "Ronka Ruins Level 4 Treasure Chest E":  PristineLocation(90132,  "Default",   "Moonring Blade", ["Chest"], [EntDefAsset(30191, 5, 48), EntDefAsset(30191, 11, 48)]),
    "Ronka Ruins Level 4 Treasure Chest F":  PristineLocation(90133,  "Default",   "Power Armlet",   ["Chest"], [EntDefAsset(30191, 5, 49), EntDefAsset(30191, 11, 49)]),

    # Ronka Ruins Level 5
    # NOTE: This is duplicated betwen sub-maps 6 and 12, so we must rewrite chests on both maps. I have no idea why.
    #       All item pickups appear to be on 12.
    "Ronka Ruins Level 5 Treasure Chest A":  PristineLocation(90134,  "Default",   "Cottage",   ["Chest"], [EntDefAsset(30191, 6, 28), EntDefAsset(30191, 12, 28)]),
    "Ronka Ruins Level 5 Treasure Chest B":  PristineLocation(90135,  "Default",   "Ether",     ["Chest"], [EntDefAsset(30191, 6, 29), EntDefAsset(30191, 12, 29)]),

    # Skipping boss for now

    # Ronka Ruins Crystal Room
    "Ronka Ruins Crystal Shard A":  PristineLocation(90136,  "Default",  "Job: Samurai",      ["CrystalShard"], ScrMnemAsset(30191, 12, 'sc_e_0074_1', 4), {'Label':'EarthCrystalShard1'}),
    "Ronka Ruins Crystal Shard B":  PristineLocation(90137,  "Default",  "Job: Dragoon",      ["CrystalShard"], ScrMnemAsset(30191, 12, 'sc_e_0074_1', 5), {'Label':'EarthCrystalShard2'}),
    "Ronka Ruins Crystal Shard C":  PristineLocation(90138,  "Default",  "Job: Dancer",       ["CrystalShard"], ScrMnemAsset(30191, 12, 'sc_e_0074_1', 6), {'Label':'EarthCrystalShard3'}),
    "Ronka Ruins Crystal Shard D":  PristineLocation(90139,  "Default",  "Job: Chemist",      ["CrystalShard"], ScrMnemAsset(30191, 12, 'sc_e_0074_1', 7), {'Label':'EarthCrystalShard4'}),
  }),

  # Walse Meteor Interior  (ID preserved)
  "Walse Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Purobolos
    "Walse Meteor Interior Boss: Purobolos":  PristineLocation(90140, "Default",  "Potion",   ["BossDrop"], ScrMnemAsset(30130, None, 'sc_e_0079_1', 4), {'Label':'BossPurobolosItem'}),
  }),

  # Karnak Meteor Interior  (ID preserved)
  "Karnak Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Titan
    "Karnak Meteor Interior Boss: Titan":  PristineLocation(90141, "Default",  "Potion",   ["BossDrop"], ScrMnemAsset(30141, 2, 'sc_e_0081_1', 5), {'Label':'BossTitanItem'}),
  }),

  # Gohn Meteor Interior  (ID preserved)
  "Gohn Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Manticore
    "Gohn Meteor Interior Boss: Manticore":  PristineLocation(90142, "Default",  "Phoenix Down",   ["BossDrop"], ScrMnemAsset(30201, 2, 'sc_e_0083_1', 4), {'Label':'BossManticoreItem'}),
  }),

  # Transition: World 2 Teleport
  "World 1 to 2 Teleport" : PristineRegion([], {
    # For now, this is just the end
    "Unlock World 2": PristineEvent("Victory", ["CompletionCondition"]),
  }),


  # NOTE: Shops start at 92000

}


# Separate lookup of all locations, generated from pristine_regions
pristine_locations = make_pristine_locations(pristine_regions)



# Region Connections; Region A <-> Region B
# NOTE: These are 1-way connections!
# TODO: Do we like having our lambda rules here? I think we should identify them by string name and put them into .Rules to keep this "pristine".
# TODO: For now it's just an array, but we might use a 'make_pristine_connections()' type function
#       to do { Locaiton -> [List-of-connections] } or similar
pristine_connections = [
  # Menu Can hook up to either World 1, 2, or 3 randomly (or via options)
  ("Menu", "World Map 1", "require_world_1_teleport"),  # Option 3 is "connection rule" (for now)

  # World 1 Locations
  # TODO: Note that we need to lock all of these with "W1Teleport"; otherwise, the logic would allow using,
  #   say, Tule to access World 1 from World 3.
  ("World Map 1", "Tycoon Meteor", None),
  ("World Map 1", "Pirate Hideout", None),
  ("World Map 1", "Tule", None),
  ("World Map 1", "Wind Shrine", None),
  ("World Map 1", "Torna Canal", None),
  ("World Map 1", "Ship Graveyard", None),
  ("World Map 1", "Carwen", None),
  ("World Map 1", "North Mountain", None),
  ("World Map 1", "Walse", None),
  ("World Map 1", "Castle Walse", None),
  ("World Map 1", "Tower of Walse", None),
  ("World Map 1", "Castle Tycoon", None),
  ("World Map 1", "Karnak", None),
  ("World Map 1", "Karnak Castle", None),
  ("World Map 1", "Fire Powered Ship", None),
  ("World Map 1", "Library of the Ancients", None),
  ("World Map 1", "Istory", None),
  ("World Map 1", "Jachol", None),
  ("World Map 1", "Jachol Cave", None),
  ("World Map 1", "Crescent", None),
  ("World Map 1", "Lix", None),
  ("World Map 1", "Shifting Sands Desert", None),
  ("World Map 1", "Catapult", None),
  ("World Map 1", "Tycoon Meteor Interior", None),
  ("World Map 1", "Floating Ronka Ruins", "require_adamant"),
  ("World Map 1", "Walse Meteor Interior", None),
  ("World Map 1", "Karnak Meteor Interior", None),
  ("World Map 1", "Gohn Meteor Interior", None),

  # Transition between Worlds
  ("World Map 1", "World 1 to 2 Teleport", "require_10_jobs")  # Has 10 Jobs
]



# Shops are essentially groups of Locations (within Regions), but they are not always added to the pool.
# Because they often require some heavy modification, we list them specifically here.
# (If this becomes unwieldy, I'll move them to Locations somewhat...)
# Note: ItemName -> Id ; that's the "ID" in product.csv to overwrite. The actual Location's ID will be determined dynamically (starting at 92000)
# Note: All shop Locations will have the tag "Shop"
# Note: Locations formed from shops will be "<Shop Name>: <Original Item>"; e.g., "Tule Weapon Shop: Broadsword"
#       The Location ID will be different for each player that's playing the same game; I think this is fine
#       since each World gets its own object instance in Python. But it does make it harder to debug (hence keeping the name simple)
pristine_shops = {
  # Tule - Weapons
  "Tule Weapon Shop" : PristineShop('Tule', 1, 'Weapons', 'Weapon', ShopAsset(20011, 7, 'ev_e_0023', 0), {
    'Broadsword' : 1,
    'Rod' : 2,
    'Staff' : 3,
  }),

  # Carwen - Weapons
  "Carwen Weapon Shop" : PristineShop('Carwen', 2, 'Weapons', 'Weapon', ShopAsset(20021, 4, 'entity_default', 5), {
    'Dagger' : 4,
    'Long Sword' : 5,
    'Rod' : 6,
    'Staff' : 7,
  }),

  # Walse - Weapons
  "Walse Weapon Shop" : PristineShop('Walse', 3, 'Weapons', 'Weapon', ShopAsset(20031, 3, 'entity_default', 2), {
    'Battle Axe' : 8,
    'Long Sword' : 9,
    'Dagger' : 10,
  }),

  # Karnak - Weapons
  # NOTE: Produt Group 4 appears to be the discounted Karnak shop where you get arrested.
  # NOTE: Karnak's shop also has an entry for "ev_e_0042_ 1" on the same map (object 1) ---and yes, the space is part of the key.
  # In summary, don't try to change the Product Group of this shop; I expect something would break...
  "Karnak Weapon Shop" : PristineShop('Karnak', 5, 'Weapons', 'Weapon', ShopAsset(20061, 1, 'ev_e_0048', 2), {
    'Mythril Knife' : 18,
    'Mythril Sword' : 19,
    'Mythril Hammer' : 20,
    'Flame Rod' : 21,
    'Frost Rod' : 22,
    'Thunder Rod' : 23,
    'Flail' : 24,
  }),

  # Karnak - Weapons (NOTE: Appears to be World 3? Does it appear any earlier?)
  #"Karnak Weapon Shop Bonus" : PristineShop('Karnak', 6, 'Weapons', 'Weapon', ShopAsset(20061, 1, 'ev_e_0048', 0), {
  #  'Mythril Spear' : 25,
  #  'Kunai' : 26,
  #  'Whip' : 27,
  #  'Diamond Bell' : 28,
  #}),

  # Jachol - Weapons
  "Jachol Weapon Shop" : PristineShop('Jachol', 7, 'Weapons', 'Weapon', ShopAsset(20081, 5, 'entity_default', 5), {
    'Ogre Killer' : 29,
    'Coral Sword' : 30,
    'Mage Masher' : 31,
    'Trident' : 32,
    'Ashura' : 33,
    'Silver Bow' : 34,
  }),

  # Crescent - Weapons
  "Crescent Weapon Shop" : PristineShop('Crescent', 8, 'Weapons', 'Weapon', ShopAsset(20101, 3, 'entity_default', 2), {
    'Flame Bow' : 35,
    'Frost Bow' : 36,
    'Thunder Bow' : 37,
    'Silver Harp' : 38,
  }),

  # TODO: Regole, Moore, Quelb, Quelb+Bal, Surgate, Phantom Village (2?)
  # TODO: For World 3, some of these shops need to have a "World X accessible" check (most can rely on the Region)

  # Tule - Armor
  "Tule Armor Shop" : PristineShop('Tule', 16, 'Armor', 'Armor', ShopAsset(20011, 6, 'ev_e_0023', 0), {
    'Leather Shield' : 79,
    'Leather Cap' : 80,
    'Leather Armor' : 81,
  }),

  # Carwen - Armor
  "Carwen Armor Shop" : PristineShop('Carwen', 17, 'Armor', 'Armor', ShopAsset(20021, 4, 'entity_default', 4), {
    'Bronze Shield' : 82,
    'Bronze Helm' : 83,
    'Bronze Armor' : 84,
    'Copper Cuirass' : 85,
    'Cotton Robe' : 86,
  }),

  # Walse - Armor
  "Walse Armor Shop" : PristineShop('Walse', 18, 'Armor', 'Armor', ShopAsset(20031, 4, 'entity_default', 2), {
    'Iron Shield' : 87,
    'Iron Helm' : 88,
    'Iron Armor' : 89,
    'Kenpo Gi' : 90,
    'Cotton Robe' : 91,
  }),


  # Karnak - Armor
  # Note: This has the same "ev_e_0042_ 1" issue as the weapon shop. Something related to world 3 perhaps?
  # Note: Skip the shop with the sale prices (where you get arrested)
  "Karnak Armor Shop" : PristineShop('Karnak', 20, 'Armor', 'Armor', ShopAsset(20061, 1, 'ev_e_0048', 1), {
    'Mythril Shield' : 99,
    'Mythril Helm' : 100,
    'Plumed Hat' : 101,
    'Mythril Armor' : 102,
    'Silver Plate' : 103,
    'Silk Robe' : 104,
    'Mythril Gloves' : 105,
    'Silver Armlet' : 106,
  }),

  # Jachol - Armor
  "Jachol Armor Shop" : PristineShop('Jachol', 21, 'Armor', 'Armor', ShopAsset(20081, 5, 'entity_default', 4), {
    'Green Beret' : 107,
    'Ninja Suit' : 108,
    "Sage's Surplice" : 109,
  }),

  # Crescent - Armor
  "Crescent Armor Shop" : PristineShop('Crescent', 22, 'Armor', 'Armor', ShopAsset(20101, 4, 'entity_default', 2), {
    'Plumed Hat' : 110,
    "Sage's Surplice" : 111,
  }),

  # Lix - Armor
  "Lix Armor Shop" : PristineShop('Lix', 29, 'Armor', 'Armor', ShopAsset(20121, 5, 'entity_default', 3), {
    'Green Beret' : 154,
    'Ninja Suit' : 155,
  }),

  # TODO: Regole, Moore, Quelb, Quelb+Baal, Surgate, Phantom Village ( maybe 2?)

  # Tule - Items
  "Tule Item Shop" : PristineShop('Tule', 31, 'Items', 'Item', ShopAsset(20011, 5, 'entity_default', 0), {
    'Potion' : 164,
    'Tent' : 165,
  }),

  # Lix - Items
  # TODO: All Lix items have a discouint -- we may want to enforce this general discount when we add new items
  "Lix Item Shop" : PristineShop('Lix', 32, 'Items', 'Item', ShopAsset(20121, 4, 'entity_default', 4), {
    'Ether' : 166,
    'Potion' : 167,
    'Antidote' : 168,
    'Eye Drops' : 169,
    'Mallet' : 170,
    "Maiden's Kiss" : 171,
    'Gold Needle' : 172,
    'Tent' : 173,
  }),

  # Carwen - Items
  # NOTE: Cloned at Walse, Karnak, Jachol, Istory, Crescent (see "optional")
  "Carwen Item Shop" : PristineShop('Carwen', 33, 'Items', 'Item', ShopAsset(20021, 3, 'entity_default', 2), {
    'Potion' : 174,
    'Antidote' : 175,
    'Eye Drops' : 176,
    "Maiden's Kiss" : 177,
    'Mallet' : 178,
    'Gold Needle' : 179,
    'Phoenix Down' : 180,
    'Tent' : 181,
  }),

  # TODO: Weird shop with ID 34

  # TODO: Regole;Moore;Surgate Castle;Quelb;Castle of Bal

  # TODO: Regole;Moore;Surgate Castle;Quelb;Castle of Bal (second shop)

  # TODO: Phantom Village

  # Tule - Magic Shop
  "Tule Magic Shop" : PristineShop('Tule', 38, 'Magic', 'Magic', ShopAsset(20011, 8, 'entity_default', 0), {
    'Fire' : 214,
    'Blizzard' : 215,
    'Thunder' : 216,
    'Cure' : 217,
    'Libra' : 218,
    'Poisona' : 219,
  }),

  # Carwen - Magic Shop
  "Carwen Magic Shop" : PristineShop('Carwen', 39, 'Magic', 'Magic', ShopAsset(20021, 5, 'entity_default', 2), {
    'Fire' : 220,
    'Blizzard' : 221,
    'Thunder' : 222,
    'Sleep' : 223,
    'Cure' : 224,
    'Poisona' : 225,
    'Silence' : 226,
    'Protect' : 227,
  }),

  # Walse - Magic Shop
  "Walse Magic Shop" : PristineShop('Walse', 40, 'Magic', 'Magic', ShopAsset(20031, 5, 'entity_default', 2), {
    'Slow' : 228,
    'Regen' : 229,
    'Mute' : 230,
    'Haste' : 231,
    'Chocobo' : 232,
    'Sylph' : 233,
    'Remora' : 234,
  }),

  # Karnak - Magic Shop 1
  # NOTE: Cloned at Crescent (see "optional")
  "Karnak Black Magic Shop" : PristineShop('Karnak', 41, 'Magic', 'Magic', ShopAsset(20061, 4, 'entity_default', 3), {
    'Fira' : 235,
    'Blizzara' : 236,
    'Thundara' : 237,
    'Poison' : 238,
    'Sleep' : 239,
    'Fire' : 240,
    'Blizzard' : 241,
    'Thunder' : 242,
  }),

  # Karnak - Magic Shop 2
  # NOTE: Cloned at Jachol (see "optional")
  "Karnak White Magic Shop" : PristineShop('Karnak', 42, 'Magic', 'Magic', ShopAsset(20061, 4, 'entity_default', 2), {
    'Cura' : 243,
    'Raise' : 244,
    'Confuse' : 245,
    'Silence' : 246,
    'Protect' : 247,
    'Cure' : 248,
    'Libra' : 249,
    'Poisona' : 250,
  }),

  # Karnak - Magic Shop 3
  # NOTE: Cloned at Istory (see "optional")
  "Karnak Time Magic Shop" : PristineShop('Karnak', 43, 'Magic', 'Magic', ShopAsset(20061, 4, 'entity_default', 4), {
    'Gravity' : 251,
    'Stop' : 252,
    'Haste' : 253,
    'Mute' : 254,
    'Slow' : 255,
    'Regen' : 256,
  }),

  # TODO: Regole;Surgate Castle;Quelb;Castle of Bal 
  #       3 shops at each

  # TODO: Moore (various)

  # Lix - Magic Shop
  "Lix Magic Shop" : PristineShop('Lix', 50, 'Magic', 'Magic', ShopAsset(20121, 2, 'entity_default', 2), {
    'Esuna' : 284,
  }),

  # TODO: Phantom Village (several)

  # Istory - Accessories
  "Istory Accessory Shop" : PristineShop('Lix', 53, 'Accessories', 'Accessory', ShopAsset(20091, 4, 'entity_default', 2), {
    'Flame Ring' : 299,
    'Coral Ring' : 300,
    'Angel Ring' : 301,
  }),

  # TODO: Accessories, Phantom Village

  # Lix - Ninja Supplies
  "Lix Ninja Supplies" : PristineShop('Lix', 55, 'Ninja Supplies', 'Weapon', ShopAsset(20121, 5, 'entity_default', 2), {
    'Kunai' : 308,
    'Shuriken' : 309,
    'Flame Scroll' : 310,
    'Water Scroll' : 311,
    'Lightning Scroll' : 312,
  }),

  # TODO: Phantom Village, Ninja Supplies

  # TODO: Phantom Village, Apothecary

}

# Some Towns share the same shop.
# With the right flag set, we artificially create unique shop inventory for each duplicate.
# These shops' inventories will be the same as their clones to start (and then randomized separately).
# NOTE: We manually specify the inventories, since we need to add the product IDs manually...
optional_split_shops = {
  # TODO: Castle Bal Weapons

  # TODO: Castle Bal Armor

  #
  # Carwen Item Shop: Clones
  #

  # Walse - Items
  "Walse Item Shop" : PristineShop('Walse', 58, 'Items', 'Item', ShopAsset(20031, 2, 'entity_default', 4), {
    'Potion' : 342,
    'Antidote' : 343,
    'Eye Drops' : 344,
    "Maiden's Kiss" : 345,
    'Mallet' : 346,
    'Gold Needle' : 347,
    'Phoenix Down' : 348,
    'Tent' : 349,
  }),

  # Karnak - Items
  "Karnak Item Shop" : PristineShop('Karnak', 59, 'Items', 'Item', ShopAsset(20061, 2, 'entity_default', 6), {
    'Potion' : 350,
    'Antidote' : 351,
    'Eye Drops' : 352,
    "Maiden's Kiss" : 353,
    'Mallet' : 354,
    'Gold Needle' : 355,
    'Phoenix Down' : 356,
    'Tent' : 357,
  }),

  # Jachol - Items
  "Jachol Item Shop" : PristineShop('Jachol', 60, 'Items', 'Item', ShopAsset(20081, 2, 'entity_default', 4), {
    'Potion' : 358,
    'Antidote' : 359,
    'Eye Drops' : 360,
    "Maiden's Kiss" : 361,
    'Mallet' : 362,
    'Gold Needle' : 363,
    'Phoenix Down' : 364,
    'Tent' : 365,
  }),

  # Istory - Items
  "Istory Item Shop" : PristineShop('Istory', 61, 'Items', 'Item', ShopAsset(20091, 2, 'entity_default', 3), {
    'Potion' : 366,
    'Antidote' : 367,
    'Eye Drops' : 368,
    "Maiden's Kiss" : 369,
    'Mallet' : 370,
    'Gold Needle' : 371,
    'Phoenix Down' : 372,
    'Tent' : 373,
  }),

  # Crescent - Items
  "Crescent Item Shop" : PristineShop('Crescent', 62, 'Items', 'Item', ShopAsset(20101, 1, 'entity_default', 9), {
    'Potion' : 374,
    'Antidote' : 375,
    'Eye Drops' : 376,
    "Maiden's Kiss" : 377,
    'Mallet' : 378,
    'Gold Needle' : 379,
    'Phoenix Down' : 380,
    'Tent' : 381,
  }),

  # TODO: Regole Item shop clones (both item shops)

  #
  # Karnak Magic Shop (x3): Clones
  #

  # Crescent - Magic
  "Crescent Magic Shop" : PristineShop('Crescent', 63, 'Magic', 'Magic', ShopAsset(20101, 5, 'entity_default', 2), {
    'Fira' : 382,
    'Blizzara' : 383,
    'Thundara' : 384,
    'Poison' : 385,
    'Sleep' : 386,
    'Fire' : 387,
    'Blizzard' : 388,
    'Thunder' : 389,
  }),

  # Jachol - Magic
  "Jachol Magic Shop" : PristineShop('Jachol', 64, 'Magic', 'Magic', ShopAsset(20081, 4, 'entity_default', 2), {
    'Cura' : 390,
    'Raise' : 391,
    'Confuse' : 392,
    'Silence' : 393,
    'Protect' : 394,
    'Cure' : 395,
    'Libra' : 396,
    'Poisona' : 397,
  }),

  # Istory - Magic
  "Istory Magic Shop" : PristineShop('Istory', 65, 'Magic', 'Magic', ShopAsset(20091, 3, 'entity_default', 2), {
    'Gravity' : 398,
    'Stop' : 399,
    'Haste' : 400,
    'Mute' : 401,
    'Slow' : 402,
    'Regen' : 403,
  }),

  # TODO: Regole Magic Shop clones (all of them)

}








# TODO: Rules? Etc? Need more info to go on...

# TODO: Location Classification
#       Location Access Rules
#       LocationProgressType.DEFAULT, PRIORITY or EXCLUDED
#         Priority = force Progression items to appear here ; as a result, these locations will be more likely to be required
#         Excluded = never let Progression or Useful items appear here
#         Our strategy:
#           * Def. mark all Chests as Excluded
#           * Certain "missable" chests are "mega excluded" (areas we can't go back to) -- in case they turn off Excluded chests
#           * Piority: "Do we ever want them to get a Leather Hat from a Crystal Shard?" -- I think so? Alt: "Do we want there to be < 20 jobs?" -- sure?




# Custom messages; these will need to be modified based on what the game randomizes into that location.
# AssetPath -> { key -> [ Locations_We_Are_Reporting_On ] }
#             OR key -> value (to add/modify a string)
# Note: These message keys are assumed to be in place by our patches. If we don't add them, the game will hang.
custom_messages = {
  # Main story Message Boxes
  'Assets/GameAssets/Serial/Data/Message/story_mes_en' : {
    # Message to show when starting the randomizer
    'RANDO_WELCOME_1' : 'Welcome to the randomizer! Your seed is: <IC_ARMOR><IC_AX><IC_BAG><IC_BEL><IC_BMGC><IC_BOW><IC_CLTH><IC_DRAG><IC_FLL><IC_HEAD><IC_HMR><IC_HRP><IC_IOBJ><IC_KTN><IC_NIF><IC_NSRD><IC_RING><IC_ROD><IC_SHIELD><IC_SMGC><IC_SPR><IC_SRD><IC_SRK><IC_TENTO><IC_TMGC><IC_TRW><IC_WHP><IC_WMGC><IC_WND>',

    # Message shown when the Pirate NPC gives you potions
    'RANDO_PIRATE_POTION_MSG_1' : ['Pirate Hideout Pirate NPC'],

    # Message shown when the Wind Shrine NPC gives you potions
    'RANDO_WIND_SHRINE_POTION_MSG_1' : ['Wind Shrine Tycoon NPC'],

    # Message shown when the Chancellor gives you a Heal Staff
    'RANDO_CHANCELLOR_HEAL_STAFF_MSG_1' : ['Castle Tycoon Chancellor Gift'],

    # These messages are shown when you get the Wind Crystal shards
    'RANDO_WIND_CRYSTAL_MSG_1' : ['Wind Shrine Crystal Shard A', 'Wind Shrine Crystal Shard B', 'Wind Shrine Crystal Shard C', 'Wind Shrine Crystal Shard D', 'Wind Shrine Crystal Shard E', 'Wind Shrine Crystal Shard F'],
    'RANDO_WIND_CRYSTAL_MSG_2' : "Let's get out of here!",

    # Messages for various bosses and related stuff
    'RANDO_BOSS_MAGISSA_ITEM_MSG_1' : ['North Mountain Boss: Magissa and Forza'],
    'RANDO_BOSS_MAGISSA_POST_FIGHT_MSG_1' : "We should head back down...",
    'RANDO_BOSS_SIREN_ITEM_MSG_1' : ['Ship Graveyard Boss: Siren'],
    'RANDO_BOSS_SHIVA_ITEM_MSG_1' : ['Castle Walse Boss: Shiva'],
    'RANDO_BOSS_IFRIT_ITEM_MSG_1' : ['Library of the Ancients Boss: Ifrit'],
    'RANDO_BOSS_BYBLOS_ITEM_MSG_1' : ['Library of the Ancients Boss: Byblos'],
    'RANDO_BOSS_BYBLOS_ITEM_MSG_2' : "Looks like we just missed Mid. I'm getting out of these musty archives!",
    'RANDO_BOSS_SANDWORM_ITEM_MSG_1' : ['Shifting Sands Desert Boss: Sandworm'],
    'RANDO_BOSS_SANDWORM_ITEM_MSG_2' : "What a tough fight! Let's regroup and continue searching!",
    'RANDO_BOSS_ADAMANTOISE_ITEM_MSG_1' : ['Tycoon Meteor Interior Boss: Adamantoise'],
    'RANDO_BOSS_ADAMANTOISE_ITEM_MSG_2' : 'Great job everyone! Back to the World Map...',
    'RANDO_BOSS_PUROBOLOS_ITEM_MSG_1' : ['Walse Meteor Interior Boss: Purobolos'],
    'RANDO_BOSS_TITAN_ITEM_MSG_1' : ['Karnak Meteor Interior Boss: Titan'],
    'RANDO_BOSS_TITAN_ITEM_MSG_2' : "That's one more meteorite... let's get out of here.",
    'RANDO_BOSS_MANTICORE_ITEM_MSG_1' : ['Gohn Meteor Interior Boss: Manticore'],
    'RANDO_BOSS_MANTICORE_ITEM_MSG_2' : "What a tough fight! We should regroup.",
    'RANDO_JACHOL_CAVE_SPECIAL_CHEST_ITEM_MSG_1' : ['Jachol Cave Treasure Chest C'],
    'RANDO_NO_LONE_WOLF_MSG' : 'No.',
    'RANDO_BOSS_SOL_CANNON_ITEM_MSG_1' : ['High Altitude Boss: Sol Cannon'],

    # These messages are shown when you get the Water Crystal shards
    'RANDO_WATER_CRYSTAL_MSG_1' : ['Tower of Walse Crystal Shard A', 'Tower of Walse Crystal Shard B', 'Tower of Walse Crystal Shard C', 'Tower of Walse Crystal Shard D', 'Tower of Walse Crystal Shard E'],
    'RANDO_WATER_CRYSTAL_MSG_2' : "Whew, what a battle! Back to the World Map...",

    # These messages are shown when you get the Fire Crystal shards (first 3)
    'RANDO_FIRE_CRYSTAL_MSG_1' : ['Fire Powered Ship Crystal Shard A', 'Fire Powered Ship Crystal Shard B', 'Fire Powered Ship Crystal Shard C'],
    'RANDO_FIRE_CRYSTAL_MSG_2' : "The Flames have died down, now we can explore the Castle. Let's get moving!",
    # ...and second 2
    'RANDO_BLACK_CHOCOBO_CRYSTAL_MSG_1' : ['Black Chocobo Crystal Shard A', 'Black Chocobo Crystal Shard B'],
    'RANDO_BLACK_CHOCOBO_CRYSTAL_MSG_2' : "Oh, I guess it's not a chocobo after all...",

    # These messages are shown when you get the Earth Crystal shards
    'RANDO_EARTH_CRYSTAL_MSG_1' : ['Ronka Ruins Crystal Shard A', 'Ronka Ruins Crystal Shard B', 'Ronka Ruins Crystal Shard C', 'Ronka Ruins Crystal Shard D'],
    'RANDO_EARTH_CRYSTAL_MSG_2' : "We should get back to the airship...",
    'RANDO_EARTH_CRYSTAL_MSG_3' : "There's nothing for us to do in the Crystal Room.",
     

    # Some custom stuff - for fun!
    'N014_C00_271_01_01' : "Thank you for walking all the way back here to check on me. I've managed to crawl my way just far enough to block this door. Anyway, you should get back to the randomizer."
  },

  # The nameplates for a given message box. Anything not here will default to '' (empty string)
  # Note: Empty nameplates may not strictly be necessary, but I'd like to keep in sync with how the original game does it.
  'Assets/GameAssets/Serial/Data/Message/story_cha_en' : {
    # Nameplates for Wind Crystal Shards
    'RANDO_WIND_CRYSTAL_MSG_2' : "(BARTZ)",

    # Nameplates for various bosses and related stuff
    'RANDO_BOSS_MAGISSA_POST_FIGHT_MSG_1' : '(BARTZ)',
    'RANDO_BOSS_BYBLOS_ITEM_MSG_2' : '(BARTZ)',
    'RANDO_BOSS_SANDWORM_ITEM_MSG_2' : '(BARTZ)',
    'RANDO_BOSS_ADAMANTOISE_ITEM_MSG_2' : '(BARTZ)',
    'RANDO_BOSS_TITAN_ITEM_MSG_2' : '(BARTZ)',
    'RANDO_BOSS_MANTICORE_ITEM_MSG_2' : '(BARTZ)',
    'RANDO_NO_LONE_WOLF_MSG' : '(BARTZ)',

    # Nameplates for the Water Crystal shards
    'RANDO_WATER_CRYSTAL_MSG_2' : '(BARTZ)',

    # Nameplates for the Fire Crystal shards (first 3 + last 2)
    'RANDO_FIRE_CRYSTAL_MSG_2' : '(BARTZ)',
    'RANDO_BLACK_CHOCOBO_CRYSTAL_MSG_2' : '(BARTZ)',

    # These messages are shown when you get the Earth Crystal shards
    'RANDO_EARTH_CRYSTAL_MSG_2' : '(BARTZ)',
    'RANDO_EARTH_CRYSTAL_MSG_3' : '(BARTZ)',

    # We're just editing this; keep the nameplace as-is.
    'N014_C00_271_01_01' : 'Queen Karnak',

  },


}




