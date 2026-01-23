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
  def __init__(self, loc_id: int, orig_item: str, tags: list[str], asset_path: str, optattrs: dict[str,str] = {}):
    self.loc_id = loc_id  # Used to form the Archipelago ID only; FF5 has no notion of this
    self.orig_item = orig_item  # Original Item at this location (or "<num> Gil"). Start with "!/#" to mark this location "Priority"/"Excluded"
    self.tags = tags  # Ways to refer to this location. "Town", "Dungeon", etc. 
    self.asset_path = asset_path  # <path_to_asset>:<path_within_asset> ; used by our Resource Loader to patch the game
    self.optattrs = optattrs  # Optional info necessary for patching the game. E.g., the "Great Sword in the Water" message.

  def __repr__(self):
    return f"PristineLocation({self.loc_id}, {self.orig_item}, {self.tags})"

  # The id reported to Archipelago has an offset added, to make debugging easier
  def id(self):
    return 8000000 + self.loc_id

  # Return the name, minus modifiers
  def orig_item_name(self):
    if self.orig_item.startswith('!') or self.orig_item.startswith('#'):
      return self.orig_item[1:]
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
def EntDefAsset(mapId, subMapId, objectId):
  return f"Assets/GameAssets/Serial/Res/Map/Map_{mapId}/Map_{mapId}_{subMapId}/entity_default:/layers/[0]/objects/[{objectId}]/properties"

# Retrieve an Asset path from a Map/Script Name + Mnemonic ID
def ScrMnemAsset(mapId, subMapId, scriptName, mnemonicId):
  return f"Assets/GameAssets/Serial/Res/Map/Map_{mapId}/Map_{mapId}_{subMapId}/{scriptName}:/Mnemonics/[{mnemonicId}]"

# There's probably a cleaner way to specify this...
def make_pristine_locations(regions):
  res = {}
  for reg_data in regions.values():
    for loc_name, data in reg_data.locations.items():
      res[loc_name] = data
  return res
  



# List of patch filenames to apply, indexed by name
# At the moment, these are all required, but we might imagine a future where the player can turn some of them off
#   E.g., using the randomizer to *just* randomize every Job Crystal Shard, but without cutting the cutscenes short.
all_patches = {
  # Cut out all the drama that happens in Crystal rooms; just give players their Jobs and set the appropriate Flags
  "Shorter Crystal Cutscenes" : "short_crystal_cutscenes.csv",
}


# Pristine items
# We index all of our Items by their name; the value is of type PristineItem
# Item tags are used similar to "groups" in Archipelago, to easy say things like "give me a Healing Consumable"
# Note that "classification" can be upgraded or downgraded; for example, the Jobs can be
#   downgraded from Progression to Useful if the Player chooses not to do a Job Fair run.
# TODO: Document how Gil is supposed to work... I think we can specify "1 Gil" in the Locations, but how does that translate to non-pristine?
pristine_items = {
  # These are first-class items per FF5
  "Gil":           PristineItem(1,    "Filler",      ["Gil"]),
  "Potion":        PristineItem(2,    "Filler",      ["Consumable", "HealHP"]),
  "Phoenix Down":  PristineItem(4,    "Filler",      ["Consumable", "Revive"]),
  "Ether":         PristineItem(5,    "Filler",      ["Consumable", "HealMP"]),
  "Tent":          PristineItem(12,   "Filler",      ["FieldItem", "Revive","HealHP","HealMP"]),
  "Leather Shoes": PristineItem(251,  "Filler",      ["Armor","Shoes"]),

  # These have made up content_ids, and FF5 doesn't treat them as items
  "Job: Knight":     PristineItem(2000, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：ナイト'}),
  "Job: Monk":       PristineItem(2001, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：モンク'}),
  "Job: Thief":      PristineItem(2002, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：シーフ'}),
  "Job: White Mage": PristineItem(2003, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：白魔道士'}),
  "Job: Black Mage": PristineItem(2004, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：黒魔道士'}),
  "Job: Blue Mage":  PristineItem(2005, "Progression", ["KeyItem", "Job"], {'SysCall':'ジョブ開放：青魔道士'}),
}


# Pristine regions, and the locations in them
# The outer string in each of these is the "Region" name. All rooms are indexed by name later on.
# All Locations are indexed by name as well.
# We typically do not refer to Locations manually; rather, we'll say things like "get me every Town Interior in the Tule Region".
# Note that the asset_paths are post-patch (see: "Shorter Crystal Cutscenes") --if we ever want to make patches optional, 
#   we will need to somehow take that into account here.
# A Location may also be an EventLocation (PristineEvent), which is paired with its own EventItem, and possible tags.
#   For now, I'd suggest only putting "CompletionCondition" in the tags (or nothing)
pristine_regions = {
  # Starting Region, typically called "Menu"
  # I don't plan on putting an Locations here, but it's good to reference (for connections, etc.)
  "Menu" : PristineRegion(["Start"], {
  }),

  # Town of Tule
  "Tule" : PristineRegion(["Town"], {
    # Tule Interior: Greenhorn's Club
    "Tule Greenhorns Club 1F Treasure A":  PristineLocation(6,   "Ether",          ["Interior"], EntDefAsset(20011, 1, 0)),
    "Tule Greenhorns Club 1F Treasure B":  PristineLocation(7,   "100 Gil",        ["Interior"], EntDefAsset(20011, 1, 1)),
    "Tule Greenhorns Club 1F Treasure C":  PristineLocation(8,   "Potion",         ["Interior"], EntDefAsset(20011, 1, 2)),
    "Tule Greenhorns Club 1F Treasure D":  PristineLocation(9,   "Phoenix Down",   ["Interior"], EntDefAsset(20011, 1, 3)),
    "Tule Greenhorns Club 1F Treasure E":  PristineLocation(10,  "Tent",           ["Interior"], EntDefAsset(20011, 1, 4)),
    "Tule Greenhorns Club 2F Treasure A":  PristineLocation(11,  "Leather Shoes",  ["Interior", "Battle"], EntDefAsset(20011, 2, 0), { 'battle_id':'todo' }),
  }),

  # Wind Temple
  "Wind Temple" : PristineRegion(["Dungeon"], {
    # Wind Temple: Crystal Room
    "Wind Temple Crystal Shard A":  PristineLocation(2000,  "!Job: Knight",      ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 8)),
    "Wind Temple Crystal Shard B":  PristineLocation(2001,  "!Job: Monk",        ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 9)),
    "Wind Temple Crystal Shard C":  PristineLocation(2002,  "!Job: Thief",       ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 10)),
    "Wind Temple Crystal Shard D":  PristineLocation(2003,  "!Job: White Mage",  ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 11)),
    "Wind Temple Crystal Shard E":  PristineLocation(2004,  "!Job: Black Mage",  ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 12)),
    "Wind Temple Crystal Shard F":  PristineLocation(2005,  "!Job: Blue Mage",   ["BossRoom"], ScrMnemAsset(30041, 8, 'sc_e_0017', 13)),
  }),

  # Ending Region (might not be needed)
  "Final Boss Fight" : PristineRegion(["End"], {
    "Defeat Neo Ex-Death": PristineEvent("Victory", ["CompletionCondition"]),
  }),

}


# Separate lookup of all locations, generated from pristine_regions
pristine_locations = make_pristine_locations(pristine_regions)



# Region Connections; Region A <-> Region B
# TODO: Figure out if we want specific exit/entrance hookups
pristine_connections = {
  "Menu" : "Tule",
  "Menu" : "Wind Temple",
  "Wind Temple" : "Final Boss Fight",
}



# TODO: Rules? Etc? Need more info to go on...














