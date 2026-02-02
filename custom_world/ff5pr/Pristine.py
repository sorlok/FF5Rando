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


# Simple classes

class PristineItem:
  def __init__(self, content_id: int, classification: str, tags: list[str], optattrs: dict[str,str] = {}):
    self.content_id = content_id  # FF5 content_id; used as part of the Archipelago ID
    self.classification = classification  # Filler, Progression, etc.
    self.tags = tags  # Ways to refer to this item. "Consumable", "Weapon", "Job"; also, "Priceless" (don't toss it)
    self.optattrs = optattrs  # Optional info necessary for patching the game. E.g., "call this sysCall to add this Job"

  def __repr__(self):
    return f"PristineItem({self.content_id}, {self.classification}, {self.tags})"

  # The id reported to Archipelago has an offset added, to make debugging easier
  def id(self):
    return 7000000 + self.content_id


class PristineLocation:
  def __init__(self, loc_id: int, classification: str, orig_item: str, tags: list[str], asset_path: str, optattrs: dict[str,str] = {}):
    self.loc_id = loc_id  # Used to form the Archipelago ID only; FF5 has no notion of this
    self.classification = classification   # Default, Priority, Excluded
    self.orig_item = orig_item  # Original Item at this location (or "<num> Gil").
    self.tags = tags  # Ways to refer to this location. "Town", "Dungeon", etc. 
    self.asset_path = asset_path  # <path_to_asset>:<path_within_asset> ; used by our Resource Loader to patch the game
    self.optattrs = optattrs  # Optional info necessary for patching the game. E.g., the "Great Sword in the Water" message. 
                              # 'Label' is the expected 'Nop' label that we're planning to patch over; this keeps us honest rather than just stomping on memory (see Patches.py)

  def __repr__(self):
    return f"PristineLocation({self.loc_id}, {self.orig_item}, {self.tags})"

  # The id reported to Archipelago has an offset added, to make debugging easier
  def id(self):
    return 8000000 + self.loc_id

  # TODO: Remove this eventually...
  def orig_item_name(self):
    #if self.orig_item.startswith('!') or self.orig_item.startswith('#'):
    #  return self.orig_item[1:]
    return self.orig_item


class PristineEvent:
  def __init__(self, event_item: str, tags: list[str]):
    self.event_item = event_item  # Name of the EventItem at this EventLocation
    self.tags = tags  # Ways to refer to this location. "Town", "Dungeon", etc. 

  def __repr__(self):
    return f"PristineEvent({self.event_item}, {self.tags})"

  # Event Locations/Items do not have an ID
  def id(self):
    return None

  #def orig_item_name(self):
  #  return self.event_item


# TODO: Do we want to put Region connections here (and specialize their Entrance rules later?) Or is that just making our job later harder.
class PristineRegion:
  def __init__(self, tags: list[str], locations: dict[str, PristineLocation]):
    self.tags = tags  # These tags will be copied into the tag list for *all* Locations in this Region
    self.locations = locations  # { LocationName -> PristineLocation } ; used to group, e.g., all Floors in a Dungeon into the same logical space.

  def __repr__(self):
    return f"PristineRegion({self.tags}, {len(self.locations)} locations)"


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

# There's probably a cleaner way to specify this...
def make_pristine_locations(regions):
  res = {}
  for reg_data in regions.values():
    for loc_name, data in reg_data.locations.items():
      res[loc_name] = data
  return res
  

# Helper: Validate Data
def validate_pristine():
  # Exit early on any error
  error = False

  # Confirm no duplicate item IDs
  seen_ids = set()
  for name, data in pristine_items.items():
    if data.content_id in seen_ids:
      print(f"ERROR: Duplicate Item Id: {data.content_id}")
      error = True
    else:
      seen_ids.add(data.content_id)

  # Confirm no duplicat elocation IDs
  seen_ids = set()
  for name, data in pristine_locations.items():
    if isinstance(data, PristineLocation):
      if data.loc_id in seen_ids:
        print(f"ERROR: Duplicate Location Id: {data.loc_id}")
        error = True
      else:
        seen_ids.add(data.loc_id)

  # Confirm that every Location names a valid Item (i.e., the item it gives/unlocks, not any Condition locking that Location)
  # (Skip Event Locations; they create the item they specify)
  for name, data in pristine_locations.items():
    if isinstance(data, PristineLocation):
      orig_name = data.orig_item_name()
      if orig_name not in pristine_items: # and not orig_name.endswith('Gil'):
        print(f"ERROR: Location refers to unknown item: {orig_name}")
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
  "Leather Cap":       PristineItem(189, "Filler",      ["Armor","Hat"]), 
  "Plumed Hat":        PristineItem(190, "Filler",      ["Armor","MageHat"]), 
  "Hypno Crown":       PristineItem(191, "Filler",      ["Armor","MageHat"]), 
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


  # These have made up content_ids, and FF5 doesn't treat them as items

  # First set of jobs
  "Job: Knight":        PristineItem(2000, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：ナイト'}),
  "Job: Monk":          PristineItem(2001, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：モンク'}),
  "Job: Thief":         PristineItem(2002, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：シーフ'}),
  "Job: White Mage":    PristineItem(2003, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：白魔道士'}),
  "Job: Black Mage":    PristineItem(2004, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：黒魔道士'}),
  "Job: Blue Mage":     PristineItem(2005, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：青魔道士'}),
  # Second set of jobs (minus Mime)
  "Job: Berserker":     PristineItem(2006, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：バーサーカー'}),
  "Job: Red Mage":      PristineItem(2007, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：赤魔道士'}),
  "Job: Summoner":      PristineItem(2008, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：召喚士'}),
  "Job: Time Mage":     PristineItem(2009, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：時魔道士'}),
  "Job: Mystic Knight": PristineItem(2010, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：魔法剣士'}),
  # Third set of jobs (castle)
  "Job: Beastmaster":   PristineItem(2011, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：魔獣使い'}),
  "Job: Geomancer":     PristineItem(2012, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：風水師'}),
  "Job: Ninja":         PristineItem(2013, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：忍者'}),
  # Third set of jobs (crescent)
  "Job: Bard":          PristineItem(2014, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：吟遊詩人'}),
  "Job: Ranger":        PristineItem(2015, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：狩人'}),
  # Fourth set of jobs
  "Job: Samurai":       PristineItem(2016, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：侍'}),
  "Job: Dragoon":       PristineItem(2017, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：竜騎士'}),
  "Job: Dancer":        PristineItem(2018, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：踊り子'}),
  "Job: Chemist":       PristineItem(2019, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：薬師'}),
  # Final job (Mime)
  "Job: Mimic":         PristineItem(2020, "Progression", ["KeyItem","Job"], {'SysCall':'ジョブ開放：ものまね師'}),

  
  # Custom Items: I plan to mod these in to the game for various purposes
  "W1Teleport":         PristineItem(5000, "Progression", ["KeyItem","WorldTeleport"]),  # Teleports player to World Map for World 1


  # TODO: TEMP: I think we need to auto-generate these? Not sure how to handle "500 Gil" or "8 Potions", so we do it this way for now...
  "1 Gil":              PristineItem(9000, "Filler", ["Gil"]),
  "100 Gil":            PristineItem(9001, "Filler", ["Gil"]),
  "150 Gil":            PristineItem(9002, "Filler", ["Gil"]),
  "300 Gil":            PristineItem(9003, "Filler", ["Gil"]),
  "490 Gil":            PristineItem(9004, "Filler", ["Gil"]),
  "990 Gil":            PristineItem(9005, "Filler", ["Gil"]),
  "1000 Gil":           PristineItem(9006, "Filler", ["Gil"]),
  "2000 Gil":           PristineItem(9007, "Filler", ["Gil"]),
  "5000 Gil":           PristineItem(9008, "Filler", ["Gil"]),
  #
  "5 Potions":          PristineItem(9009, "Filler", ["Consumable", "HealHP"]),
  "8 Potions":          PristineItem(9010, "Filler", ["Consumable", "HealHP"]),



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
    "Tycoon Meteor Treasure A":  PristineLocation(1000, "Default", "Phoenix Down",   ["Chest"], EntDefAsset(30010, None, [1,0])),
  }),

  # Pirate's Cave + Hideout
  "Pirate Hideout" : PristineRegion(["Dungeon"], { 
    # Pirate's Cave
    "Pirate Cave Treasure A":  PristineLocation(1100,  "Default", "Leather Cap",     ["Chest"], EntDefAsset(30021, 2, [1,7])),

    # Pirate's Hideout
    "Pirate Hideout Treasure A":  PristineLocation(1200,  "Default",  "Tent",       ["Chest"], EntDefAsset(30021, 5, 0)),
    "Pirate Hideout Treasure B":  PristineLocation(1201,  "Default",  "Ether",      ["Chest"], EntDefAsset(30021, 5, 1)),
    "Pirate Hideout Treasure C":  PristineLocation(1202,  "Default",  "300 Gil",    ["Chest"], EntDefAsset(30021, 5, 5)),
    "Pirate Hideout Pirate NPC":  PristineLocation(1203,  "Default",  "8 Potions",  ["Chest"], ScrMnemAsset(30021, 4, 'sc_npc_30021_4_1', 6), {'Label':'PiratePotions'}),
  }),

  # Town of Tule
  "Tule" : PristineRegion(["Town"], {
    # Tule Exterior
    "Town of Tule Treasure A":  PristineLocation(1300, "Default",  "Phoenix Down",    ["Chest"], EntDefAsset(20010, None, 14)),
    "Town of Tule Treasure B":  PristineLocation(1301, "Default",  "Leather Shoes",   ["Chest"], EntDefAsset(20010, None, 15)),
    "Town of Tule Treasure C":  PristineLocation(1302, "Default",  "Tent",            ["Chest"], EntDefAsset(20010, None, 16)),
    "Town of Tule Treasure D":  PristineLocation(1303, "Default",  "Potion",          ["Chest"], EntDefAsset(20010, None, 17)),
    "Town of Tule Treasure E":  PristineLocation(1304, "Default",  "150 Gil",         ["Chest"], EntDefAsset(20010, None, 18)),

    # SKIP: We don't care about the Canal Key for now

    # Tule Interior: Greenhorn's Club
    "Tule Greenhorns Club 1F Treasure A":  PristineLocation(1400, "Default",  "Ether",          ["Chest"], EntDefAsset(20011, 1, 0)),
    "Tule Greenhorns Club 1F Treasure B":  PristineLocation(1401, "Default",  "100 Gil",        ["Chest"], EntDefAsset(20011, 1, 1)),
    "Tule Greenhorns Club 1F Treasure C":  PristineLocation(1402, "Default",  "Potion",         ["Chest"], EntDefAsset(20011, 1, 2)),
    "Tule Greenhorns Club 1F Treasure D":  PristineLocation(1403, "Default",  "Phoenix Down",   ["Chest"], EntDefAsset(20011, 1, 3)),
    "Tule Greenhorns Club 1F Treasure E":  PristineLocation(1404, "Default",  "Tent",           ["Chest"], EntDefAsset(20011, 1, 4)),
    "Tule Greenhorns Club 2F Trapped Chest A":  PristineLocation(1405,  "Default",  "Leather Shoes",  ["Chest","Trapped"], EntDefAsset(20011, 2, 0), { 'battle_id':'todo' }),
  }),

  # Wind Shrine (Wind Crystal Jobs)
  "Wind Shrine" : PristineRegion(["Dungeon"], {
    # Wind Shrine First Floor
    # This check goes away after you get the first crystal shards, so it's Excluded.
    # TODO: Probably some way to always spawn this NPC, but I'd have to dig for it...
    "Wind Shrine Tycoon NPC":     PristineLocation(1500, "Excluded", "5 Potions",   ["Chest"], ScrMnemAsset(30041, 1, 'sc_npc_30041_1_1', 5), {'Label':'WindShrinePotions'}),

    # Wind Shrine Interior
    "Wind Shrine 2F Treasure A":  PristineLocation(1501, "Default",  "Tent",        ["Chest"], EntDefAsset(30041, 2, 0)),
    "Wind Shrine 3F Treasure A":  PristineLocation(1502, "Default",  "Leather Cap", ["Chest"], EntDefAsset(30041, 4, 5)),
    "Wind Shrine 3F Treasure B":  PristineLocation(1503, "Default",  "Broadsword",  ["Chest"], EntDefAsset(30041, 5, 0)),
    "Wind Shrine 4F Treasure A":  PristineLocation(1504, "Default",  "Staff",       ["Chest"], EntDefAsset(30041, 7, 2)),

    # Boss: Not Listed

    # Wind Shrine: Crystal Room
    "Wind Shrine Crystal Shard A":  PristineLocation(9000, "Default",  "Job: Knight",      ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 8), {'Label':'WindCrystalShard1'}),
    "Wind Shrine Crystal Shard B":  PristineLocation(9001, "Default",  "Job: Monk",        ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 9), {'Label':'WindCrystalShard2'}),
    "Wind Shrine Crystal Shard C":  PristineLocation(9002, "Default",  "Job: Thief",       ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 10), {'Label':'WindCrystalShard3'}),
    "Wind Shrine Crystal Shard D":  PristineLocation(9003, "Default",  "Job: White Mage",  ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 11), {'Label':'WindCrystalShard4'}),
    "Wind Shrine Crystal Shard E":  PristineLocation(9004, "Default",  "Job: Black Mage",  ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 12), {'Label':'WindCrystalShard5'}),
    "Wind Shrine Crystal Shard F":  PristineLocation(9005, "Default",  "Job: Blue Mage",   ["CrystalShard"], ScrMnemAsset(30041, 8, 'sc_e_0017', 13), {'Label':'WindCrystalShard6'}),
  }),

  # Torna Canal
  "Torna Canal" : PristineRegion(["Dungeon"], {
    # Boss: Karlabos
    # TODO: See notes in __init__::generate; there's some annoying issues with this...
    #"Torna Canal Boss: Karlabos":  PristineLocation(1600, "Default",  "Tent",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Ship Graveyard
  "Ship Graveyard" : PristineRegion(["Dungeon"], {
    # Exterior
    "Ship Graveyard Exterior Treasure A":  PristineLocation(1700, "Default",  "Flail",     ["Chest"], EntDefAsset(30060, None, 13)),

    # Sunken Shipwreck
    "Ship Graveyard Sunken Shipwreck Treasure A":  PristineLocation(1701, "Default",  "Antidote",     ["Chest"], EntDefAsset(30061, 14, 2)),
    "Ship Graveyard Sunken Shipwreck Treasure B":  PristineLocation(1702, "Default",  "Antidote",     ["Chest"], EntDefAsset(30061, 14, 4)),
    "Ship Graveyard Sunken Shipwreck Treasure C":  PristineLocation(1703, "Default",  "Phoenix Down", ["Chest"], EntDefAsset(30061, 14, 6)),
    "Ship Graveyard Sunken Shipwreck Treasure D":  PristineLocation(1704, "Default",  "Tent",         ["Chest"], EntDefAsset(30061, 3, 2)),
    "Ship Graveyard Sunken Shipwreck Treasure E":  PristineLocation(1705, "Default",  "990 Gil",      ["Chest"], EntDefAsset(30061, 4, 0)),
    "Ship Graveyard Sunken Shipwreck Treasure F":  PristineLocation(1706, "Default",  "Phoenix Down", ["Chest"], EntDefAsset(30061, 5, 1)),
    "Ship Graveyard Sunken Shipwreck Treasure G":  PristineLocation(1707, "Default",  "Potion",       ["Chest"], EntDefAsset(30061, 7, 0)),

    # We don't touch the map

    # Boss: Siren
    "Ship Graveyard Boss: Siren":  PristineLocation(1708, "Default",  "Bronze Armor",   ["BossDrop"], ScrMnemAsset(30060, None, 'sc_e_0030_1', 4), {'Label':'BossSirenItem'}),
  }),

  # Town of Carwen
  "Carwen" : PristineRegion(["Town"], {
    "Town of Carwen Treasure A":  PristineLocation(1800, "Default",  "Antidote",    ["Chest"], EntDefAsset(20020, None, 4)),
    "Town of Carwen Treasure B":  PristineLocation(1801, "Default",  "Frost Rod",   ["Chest"], EntDefAsset(20020, None, 4)),
    "Town of Carwen Treasure C":  PristineLocation(1802, "Default",  "1000 Gil",    ["Chest"], EntDefAsset(20021, 6, 6)),
  }),

  # North Mountain
  "North Mountain" : PristineRegion(["Dungeon"], {
    "North Mountain Treasure A":    PristineLocation(1900, "Default",  "Phoenix Down",   ["Chest"], EntDefAsset(30071, 1, 2)),
    "North Mountain Treasure B":    PristineLocation(1901, "Default",  "Gold Needle",    ["Chest"], EntDefAsset(30071, 1, 4)),
    
    # I'm ignoring this since I think people will forget that they got an item.
    #"North Mountain Cutscene Item": PristineLocation(1902,  "Mythril Helm",   [], ScrMnemAsset(-1, -1, '???', -1)),  # You get this right before the fight

    # Boss: Magissa and Forza
    "North Mountain Boss: Magissa and Forza":  PristineLocation(1903, "Default",  "Whip",   ["BossDrop"], ScrMnemAsset(30100, None, 'sc_e_0033_1', 4), {'Label':'BossMagissaItem'}),  # TODO: Also give: Power Drink -- as a bundle?
  }),

  # Town of Walse
  "Walse" : PristineRegion(["Town"], {
    "Town of Walse Treasure A":  PristineLocation(2000, "Default",  "Silver Specs",    ["Chest"], EntDefAsset(20031, 1, 2)),
  }),

  # Castle Walse
  "Castle Walse" : PristineRegion(["Castle"], {
    # Basement 1 (Dangerous)
    "Castle Walse B1 Treasure A":  PristineLocation(2100, "Default",  "1000 Gil",     ["Chest"], EntDefAsset(20041, 10, 6)),
    #"Castle Walse B1 Treasure B":  PristineLocation(2101, "Default",  "Speed",       ["Chest"], EntDefAsset(20041, 10, 7)),   # TODO: I haven't mapped this item yet...
    "Castle Walse B1 Treasure C":  PristineLocation(2102, "Default",  "1000 Gil",     ["Chest"], EntDefAsset(20041, 10, 8)),
    "Castle Walse B1 Treasure D":  PristineLocation(2103, "Default",  "Elven Mantle", ["Chest"], EntDefAsset(20041, 10, 9)),

    # Storehouse
    "Castle Walse Storehouse Treasure A":  PristineLocation(2104,  "Default",  "Tent",         ["Chest"], EntDefAsset(20041, 5, 2)),
    "Castle Walse Storehouse Treasure B":  PristineLocation(2105,  "Default",  "490 Gil",      ["Chest"], EntDefAsset(20041, 5, 3)),
    "Castle Walse Storehouse Treasure C":  PristineLocation(2106,  "Default",  "Phoenix Down", ["Chest"], EntDefAsset(20041, 5, 4)),

    # Boss: Shiva
    "Castle Walse Boss: Shiva":  PristineLocation(2107, "Default",  "Frost Rod",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Tower of Walse (Water Crystal Jobs)
  "Tower of Walse" : PristineRegion(["Dungeon"], {
    # Dungeon Interior
    "Tower of Walse 5F Treasure A":  PristineLocation(2200,  "Excluded",  "Silk Robe",     ["Chest"], EntDefAsset(30121, 5, 5)),
    "Tower of Walse 5F Treasure B":  PristineLocation(2201,  "Excluded",  "Maiden's Kiss", ["Chest"], EntDefAsset(30121, 5, 6)),
    "Tower of Walse 9F Treasure A":  PristineLocation(2202,  "Excluded",  "Silver Armlet", ["Chest"], EntDefAsset(30121, 9, 4)),
    "Tower of Walse 9F Treasure B":  PristineLocation(2203,  "Excluded",  "Ether",         ["Chest"], EntDefAsset(30121, 9, 5)),

    # Boss: Skipping for now

    # Crystal Room
    "Tower of Walse Crystal Shard A":  PristineLocation(9006,  "Default",  "Job: Berserker",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Tower of Walse Crystal Shard B":  PristineLocation(9007,  "Default",  "Job: Red Mage",       ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Tower of Walse Crystal Shard C":  PristineLocation(9008,  "Default",  "Job: Summoner",       ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Tower of Walse Crystal Shard D":  PristineLocation(9009,  "Default",  "Job: Time Mage",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Tower of Walse Crystal Shard E":  PristineLocation(9010,  "Default",  "Job: Mystic Knight",  ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Castle Tycoon
  # TODO: Seems like we might be missing 2 cottages; perhaps they're events?
  "Castle Tycoon" : PristineRegion(["Castle"], {
    # Exterior
    "Castle Tycoon Exterior Treasure A":  PristineLocation(2300,  "Default",  "Ether",        ["Chest"], EntDefAsset(20051, 10, 2)),
    "Castle Tycoon Exterior Treasure B":  PristineLocation(2301,  "Default",  "Cottage",      ["Chest"], EntDefAsset(20051, 10, 3)),
    "Castle Tycoon Exterior Treasure C":  PristineLocation(2302,  "Default",  "Phoenix Down", ["Chest"], EntDefAsset(20051, 10, 4)),
    "Castle Tycoon Exterior Treasure D":  PristineLocation(2303,  "Default",  "Elixir",       ["Chest"], EntDefAsset(20051, 10, 5)),

    # Interior: 4F
    "Castle Tycoon 4F Treasure A":  PristineLocation(2304,  "Default",  "Ether",         ["Chest"], EntDefAsset(20051, 14, 4)),
    "Castle Tycoon 4F Treasure B":  PristineLocation(2305,  "Default",  "Elixir",        ["Chest"], EntDefAsset(20051, 14, 5)),
    "Castle Tycoon 4F Treasure C":  PristineLocation(2306,  "Default",  "Phoenix Down",  ["Chest"], EntDefAsset(20051, 14, 6)),
    "Castle Tycoon 4F Treasure D":  PristineLocation(2307,  "Default",  "Maiden's Kiss", ["Chest"], EntDefAsset(20051, 14, 7)),

    # Storehouse
    "Castle Tycoon Storehouse Treasure A":  PristineLocation(2308,  "Default",  "Diamond Bell",  ["Chest"], EntDefAsset(20051, 5, [1,2])),
    "Castle Tycoon Storehouse Treasure B":  PristineLocation(2309,  "Default",  "Shuriken",      ["Chest"], EntDefAsset(20051, 5, [1,3])),
    "Castle Tycoon Storehouse Treasure C":  PristineLocation(2310,  "Default",  "Ashura",        ["Chest"], EntDefAsset(20051, 5, [1,4])),

    # Interior: 1F
    "Castle Tycoon 1F Treasure A":    PristineLocation(2311,  "Default",  "Hi-Potion",         ["Chest"], EntDefAsset(20051, 8, 4)),
    "Castle Tycoon Chancellor Gift":  PristineLocation(2312,  "Default",  "Healing Staff",     ["Chest"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Town of Karnak
  "Karnak" : PristineRegion(["Town"], {
    "Town of Karnak Treasure A":  PristineLocation(2400,  "Default",  "Flame Rod",    ["Chest","BlockedByFire"], EntDefAsset(20060, None, [1,2])),  # TODO: Needs "FlamesGone"
  }),

  # Karnak Castle (Fire Crystal Jobs, First Half)
  "Karnak Castle" : PristineRegion(["Castle"], {
    # Interior: 1F
    #"Karnak Castle 1F Trapped Chest A":  PristineLocation(2500,  "Default",  "Esuna",            ["Chest","Trapped"], EntDefAsset(20071, 1, 13)),  # TODO: Haven't called out this spell yet...
    "Karnak Castle 1F Trapped Chest B":  PristineLocation(2501,  "Excluded",   "Lightning Scroll", ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 1, 14)),  # TODO: All of these need "FlamesGone"

    # Interior: 2F
    "Karnak Castle 2F Treasure Chest A":  PristineLocation(2502,  "Excluded",   "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 10, 6)), 
    "Karnak Castle 2F Trapped Chest A":   PristineLocation(2503,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 7)), 
    "Karnak Castle 2F Trapped Chest B":   PristineLocation(2504,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 8)), 
    "Karnak Castle 2F Treasure Chest B":  PristineLocation(2505,  "Excluded",   "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 10, 9)), 
    "Karnak Castle 2F Trapped Chest C":   PristineLocation(2506,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 10)), 
    "Karnak Castle 2F Trapped Chest D":   PristineLocation(2507,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 11)), 
    "Karnak Castle 2F Trapped Chest E":   PristineLocation(2508,  "Excluded",   "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 10, 12)), 

    # Interior: B1
    "Karnak Castle B1 Trapped Chest A":   PristineLocation(2509,  "Excluded",   "Elven Mantle",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 13, 1)), 
    "Karnak Castle B1 Trapped Chest B":   PristineLocation(2510,  "Excluded",   "Main Gauche",    ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 16, 1)), 

    # Interior: B3
    "Karnak Castle B3 Trapped Chest A":   PristineLocation(2511,  "Excluded",   "Ribbon",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 5, 4)), 
    "Karnak Castle B3 Trapped Chest B":   PristineLocation(2512,  "Excluded",   "Shuriken", ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 5, 5)), 

    # Interior: B4
    "Karnak Castle B4 Treasure Chest A":  PristineLocation(2513,  "Excluded",  "2000 Gil", ["Chest","BlockedByFire"], EntDefAsset(20071, 6, 13)), 
    "Karnak Castle B4 Trapped Chest A":   PristineLocation(2514,  "Excluded",  "Elixir",   ["Chest","Trapped","BlockedByFire"], EntDefAsset(20071, 6, 14)), 

    # Iron Claw is not really a Boss, so skipping
  }),

  # Fire-Powered Ship
  "Fire Powered Ship" : PristineRegion(["Dungeon"], {
    "Fire Powered Ship Treasure Chest A":  PristineLocation(2600,  "Default",   "Thief's Gloves", ["Chest"], EntDefAsset(30151, 11, 25)), 
    "Fire Powered Ship Treasure Chest B":  PristineLocation(2601,  "Default",   "Green Beret",    ["Chest"], EntDefAsset(30151, 11, 26)), 
    "Fire Powered Ship Treasure Chest C":  PristineLocation(2602,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 20, [1,6])), 
    "Fire Powered Ship Treasure Chest D":  PristineLocation(2603,  "Default",   "Cottage",        ["Chest"], EntDefAsset(30151, 3, 0)), 
    "Fire Powered Ship Treasure Chest E":  PristineLocation(2604,  "Default",   "Mythril Gloves", ["Chest"], EntDefAsset(30151, 4, 2)), 
    "Fire Powered Ship Treasure Chest F":  PristineLocation(2605,  "Default",   "Phoenix Down",   ["Chest"], EntDefAsset(30151, 5, 6)), 
    "Fire Powered Ship Treasure Chest G":  PristineLocation(2606,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 6, 6)), 
    "Fire Powered Ship Treasure Chest H":  PristineLocation(2607,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30151, 8, 2)), 
    "Fire Powered Ship Treasure Chest I":  PristineLocation(2608,  "Default",   "Moonring Blade", ["Chest"], EntDefAsset(30151, 9, 2)), 

    # Boss: Skipping, for now

    # Give them the Crystals here
    "Fire Powered Ship Crystal Shard A":  PristineLocation(9011,  "Default",  "Job: Beastmaster",  ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Fire Powered Ship Crystal Shard B":  PristineLocation(9012,  "Default",  "Job: Geomancer",    ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Fire Powered Ship Crystal Shard C":  PristineLocation(9013,  "Default",  "Job: Ninja",        ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find

    # ...and remove the fire from Karnak/Castle
    "RemoveKarnakFire": PristineEvent("FireBeGone", []),
  }),

  # Library of the Ancients
  "Library of the Ancients" : PristineRegion(["Dungeon"], {
    "Library of the Ancients Treasure Chest A":  PristineLocation(2700,  "Default",   "Ether",        ["Chest"], EntDefAsset(20221, 5, 3)), 
    "Library of the Ancients Treasure Chest B":  PristineLocation(2701,  "Default",   "Ninja Suit",   ["Chest"], EntDefAsset(20221, 6, 24)), 
    "Library of the Ancients Treasure Chest C":  PristineLocation(2702,  "Default",   "Phoenix Down", ["Chest"], EntDefAsset(20221, 9, 6)), 

    # Boss: Ifrit
    "Library of the Ancients Boss: Ifrit":  PristineLocation(2703, "Default",  "Flame Scroll",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 

    # Boss: Byblos
    "Library of the Ancients Boss: Byblos":  PristineLocation(2704, "Default",  "Iron Draft",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Istory (World Map Area)
  "Istory" : PristineRegion(["Town"], {
    # Boss: Ramuh
    "Istory Forest Boss: Ramuh":  PristineLocation(2800, "Default",  "Lightning Scroll",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Jachol  has nothing; skipping (keeping number)

  # Jachol Cave
  "Jachol Cave" : PristineRegion(["Dungeon"], {
    "Jachol Cave Treasure Chest A":  PristineLocation(3000,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(30161, 2, 3)), 
    "Jachol Cave Treasure Chest B":  PristineLocation(3001,  "Default",   "Tent",        ["Chest"], EntDefAsset(30161, 2, 4)), 
    "Jachol Cave Treasure Chest C":  PristineLocation(3002,  "Default",   "Blitz Whip",  ["Chest"], ScrMnemAsset(-1, -1, '???', -1)),  # It's an Event because Lone Wolf can steal it...
  }),

  # Town of Crescent (+ Black Chocobo Forest) (Fire Crystal Jobs, Second Half)
  "Crescent" : PristineRegion(["Town"], {
    "Black Chocobo Crystal Shard A":  PristineLocation(9014,  "Default",  "Job: Bard",        ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Black Chocobo Crystal Shard B":  PristineLocation(9015,  "Default",  "Job: Ranger",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Town of Lix; skipping (preserving number)

  # Shifting Sands Desert
  "Shifting Sands Desert" : PristineRegion(["Dungeon"], {
    # Boss: Sandworm
    # TODO: We use "1 Gil" for "Nothing" boss drops. Might need a better option...
    "Shifting Sands Desert Boss: Sandworm":  PristineLocation(3200, "Default",  "1 Gil",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Gohn; skipping (preserving number)

  # Catapult
  "Catapult" : PristineRegion([], {
    "Catapult Treasure Chest A":  PristineLocation(3400,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(20231, 4, 10)),
    "Catapult Treasure Chest B":  PristineLocation(3401,  "Default",   "Shuriken",    ["Chest"], EntDefAsset(20231, 4, 11)),
    #"Catapult Treasure Chest C":  PristineLocation(3402,  "Default",   "Mini",        ["Chest"], EntDefAsset(20231, 4, 12)),  # TODO: need to call out item

    # Boss: Cray Claw
    "Catapult Boss: Cray Claw":  PristineLocation(3403, "Default",  "Frost Bow",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Tycoon Meteor Interior (ID preserved)
  # Note: All Meteor + Adamant nonsense will be skipped; it will eventually just be the bosses (1 check each).
  "Tycoon Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Adamantoise
    "Tycoon Meteor Interior Boss: Adamantoise":  PristineLocation(3500, "Default",  "Adamantite",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Ronka Ruins (Earth Crystal Jobs)
  # TODO: Try to avoid making this area "Excluded" -- maybe we can keep Walse and Karnak open too?
  "Floating Ronka Ruins" : PristineRegion(["Dungeon"], {
    # Boss: Sol Cannon
    "High Altitude Boss: Sol Cannon":  PristineLocation(3600, "Default",  "Dark Matter",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 

    # TODO: There's a duplicate set of 4F/5F chests I need to figure out; I'm putting the SECOND (non-red) set for now

    # Ronka Ruins Level 2
    "Ronka Ruins Level 2 Treasure Chest A":  PristineLocation(3601,  "Default",   "Golden Armor",   ["Chest"], EntDefAsset(30191, 2, 4)),   # TODO: This region needs to be checked by "Adamant"

    # Ronka Ruins Level 3
    "Ronka Ruins Level 3 Treasure Chest A":  PristineLocation(3602,  "Default",   "Elixir",         ["Chest"], EntDefAsset(30191, 3, 14)),
    "Ronka Ruins Level 3 Treasure Chest B":  PristineLocation(3603,  "Default",   "Phoenix Down",   ["Chest"], EntDefAsset(30191, 3, 15)),
    "Ronka Ruins Level 3 Treasure Chest C":  PristineLocation(3604,  "Default",   "Golden Shield",  ["Chest"], EntDefAsset(30191, 3, 16)),

    # Ronka Ruins Level 4
    "Ronka Ruins Level 4 Treasure Chest A":  PristineLocation(3605,  "Default",   "Hi-Potion",      ["Chest"], EntDefAsset(30191, 5, 44)),
    "Ronka Ruins Level 4 Treasure Chest B":  PristineLocation(3606,  "Default",   "5000 Gil" ,      ["Chest"], EntDefAsset(30191, 5, 45)),
    "Ronka Ruins Level 4 Treasure Chest C":  PristineLocation(3607,  "Default",   "Shuriken",       ["Chest"], EntDefAsset(30191, 5, 46)),
    "Ronka Ruins Level 4 Treasure Chest D":  PristineLocation(3608,  "Default",   "Ancient Sword",  ["Chest"], EntDefAsset(30191, 5, 47)),
    "Ronka Ruins Level 4 Treasure Chest E":  PristineLocation(3609,  "Default",   "Moonring Blade", ["Chest"], EntDefAsset(30191, 5, 48)),
    "Ronka Ruins Level 4 Treasure Chest F":  PristineLocation(3610,  "Default",   "Power Armlet",   ["Chest"], EntDefAsset(30191, 5, 49)),

    # Ronka Ruins Level 5
    "Ronka Ruins Level 5 Treasure Chest A":  PristineLocation(3611,  "Default",   "Cottage",   ["Chest"], EntDefAsset(30191, 6, 28)),
    "Ronka Ruins Level 5 Treasure Chest B":  PristineLocation(3612,  "Default",   "Ether",     ["Chest"], EntDefAsset(30191, 6, 29)),

    # Skipping boss for now

    # Ronka Ruins Crystal Room
    "Ronka Ruins Crystal Shard A":  PristineLocation(9016,  "Default",  "Job: Samurai",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Ronka Ruins Crystal Shard B":  PristineLocation(9017,  "Default",  "Job: Dragoon",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Ronka Ruins Crystal Shard C":  PristineLocation(9018,  "Default",  "Job: Dancer",       ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
    "Ronka Ruins Crystal Shard D":  PristineLocation(9019,  "Default",  "Job: Chemist",      ["CrystalShard"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find
  }),

  # Walse Meteor Interior  (ID preserved)
  "Walse Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Purobolos
    "Walse Meteor Interior Boss: Purobolos":  PristineLocation(3700, "Default",  "Potion",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Karnak Meteor Interior  (ID preserved)
  "Karnak Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Titan
    "Karnak Meteor Interior Boss: Titan":  PristineLocation(3800, "Default",  "Potion",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Gohn Meteor Interior  (ID preserved)
  "Gohn Meteor Interior" : PristineRegion(["BossRoom"], {
    # Boss: Manticore
    "Gohn Meteor Interior Boss: Manticore":  PristineLocation(3900, "Default",  "Phoenix Down",   ["BossDrop"], ScrMnemAsset(-1, -1, '???', -1)),  # TODO: Find. 
  }),

  # Transition: World 2 Teleport
  "World 1 to 2 Teleport" : PristineRegion([], {
    # For now, this is just the end
    "Unlock World 2": PristineEvent("Victory", ["CompletionCondition"]),
  }),

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
  ("World Map 1", "Jachol Cave", None),
  ("World Map 1", "Crescent", None),
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

    # These messages are shown when you get the Wind Crystal shards
    'RANDO_WIND_CRYSTAL_MSG_1' : ['Wind Shrine Crystal Shard A', 'Wind Shrine Crystal Shard B', 'Wind Shrine Crystal Shard C', 'Wind Shrine Crystal Shard D', 'Wind Shrine Crystal Shard E', 'Wind Shrine Crystal Shard F'],
    'RANDO_WIND_CRYSTAL_MSG_2' : "Let's get out of here!",

    # Messages for various bosses and related stuff
    'RANDO_BOSS_MAGISSA_ITEM_MSG_1' : ['North Mountain Boss: Magissa and Forza'],
    'RANDO_BOSS_MAGISSA_POST_FIGHT_MSG_1' : "We should head back down...",
    'RANDO_BOSS_SIREN_TEM_MSG_1' : ['Ship Graveyard Boss: Siren'],
  },

  # The nameplates for a given message box
  # Note: Empty nameplates may not strictly be necessary, but I'd like to keep in sync with how the original game does it.
  'Assets/GameAssets/Serial/Data/Message/story_cha_en' : {
    # Nameplace, rando starting
    'RANDO_WELCOME_1' : '',

    # Nameplate for the Pirate NPC that gives you potions
    'RANDO_PIRATE_POTION_MSG_1' : '',

    # Nameplate for Wind Shrine NPC gives you potions
    'RANDO_WIND_SHRINE_POTION_MSG_1' : '',

    # Nameplates for Wind Crystal Shards
    'RANDO_WIND_CRYSTAL_MSG_1' : '',
    'RANDO_WIND_CRYSTAL_MSG_2' : "(BARTZ)",

    # Nameplates for various bosses and related stuff
    'RANDO_BOSS_MAGISSA_ITEM_MSG_1' : '',
    'RANDO_BOSS_MAGISSA_POST_FIGHT_MSG_1' : '(BARTZ)',
    'RANDO_BOSS_SIREN_TEM_MSG_1' : '',


  },





  
}




