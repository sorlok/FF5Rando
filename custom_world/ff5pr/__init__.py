import Utils
import settings
import base64
import threading
import requests
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import add_rule
from BaseClasses import Tutorial, MultiWorld, ItemClassification, Item, Location, Region
#from .Regions import create_regions, location_table, set_rules, stage_set_rules, rooms, non_dead_end_crest_rooms,non_dead_end_crest_warps
#from .Items import item_table, item_groups, create_items, FFMQItem, fillers
#from .Output import generate_output
#from .Options import FFMQOptions
#from .Client import FFMQClient


from .Pristine import pristine_items, pristine_locations, pristine_connections



# TODO: Put Options in its own file
from Options import Choice, FreeText, ItemsAccessibility, Toggle, Range, PerGameCommonOptions
from dataclasses import dataclass


# TODO: these go into their own classes too

# This represents a "FF5 Item" from the game server's point of view.
# The 'game' name will be used to hook it up with the relevant world,
#   at which point the id ('code' in the base class, I think) is used
#   to identify the item to the local Client.
class FF5PRItem(Item):
    game: str = "Final Fantasy V PR"


# Sort of similar?
class FF5PRLocation(Location):
    game: str = "Final Fantasy V PR"


# Contains everything custom that we'd need to know for making an item work in our game
class ItemData:
    # item_id will be added to 0x10000 to get the final id
    # classification would be something like 'progression', etc.
    # groups = groups to add this item to, if any
    # data_name = ???
    # TODO: Do we want the 'content_id' here? Or maybe use the content_id as the actual item ID?
    def __init__(self, item_id, classification, groups=(), data_name=None):
        self.groups = groups
        self.classification = classification
        self.id = None   # TODO: When would this happen?
        if item_id is not None:
            self.id = item_id + 10000
        self.data_name = data_name


# Helper: Classification string to ItemClassification type
#         TODO: Put into its own file
def ParseClassification(classStr):
  classStr = classStr.lower()
  if classStr == 'filler':
    return ItemClassification.filler
  elif classStr == 'progression':
    return ItemClassification.progression
  elif classStr == 'useful':
    return ItemClassification.useful
  elif classStr == 'trap':
    return ItemClassification.trap
  elif classStr == 'skipbalancing':
    return ItemClassification.skip_balancing
  elif classStr == 'deprioritized':
    return ItemClassification.deprioritized
  elif classStr == 'progression_deprioritized_skip_balancing':
    return ItemClassification.progression_deprioritized_skip_balancing
  elif classStr == 'progression_skip_balancing':
    return ItemClassification.progression_skip_balancing
  elif classStr == 'progression_deprioritized':
    return ItemClassification.progression_deprioritized
  else:
    print("WARNING: Unknown classification type: {classStr}")
    return ItemClassification.filler




# Our list of items
# TODO: Need to do this *WAY* better
#item_table = {
#    "Ether": ItemData(0, ItemClassification.filler, ["Consumables"]),
#    "100 Gil": ItemData(1, ItemClassification.filler, ["Gil"]),
#    "Potion": ItemData(2, ItemClassification.filler, ["Consumables"]),
#    "Phoenix Down": ItemData(3, ItemClassification.filler, ["Consumables"]),
#    "Tent": ItemData(4, ItemClassification.filler, ["Consumables"]),
#    "Leather Shoes": ItemData(5, ItemClassification.filler, ["Armor"]),
#    "Job: Knight": ItemData(6, ItemClassification.progression, ["Key Items"]),
#    "Job: Thief": ItemData(7, ItemClassification.useful, ["Key Items"]),
#}



# TODO: This also goes somewhere...
#       Not sure how we want to generate location IDs for this game
#location_table = {
#    'tule_greenhorns_club_1f_treasure_1': 0,
#    'tule_greenhorns_club_1f_treasure_2': 1,
#    'tule_greenhorns_club_1f_treasure_3': 2,
#    'tule_greenhorns_club_1f_treasure_4': 3,
#    'tule_greenhorns_club_1f_treasure_5': 4,
#    'tule_greenhorns_club_2f_treasure_1': 5,
#
#    'wind_temple_crystal_shard_1': 6,
#    'wind_temple_crystal_shard_2': 7,
#}




# completion_items is an output parameter; it stores any Location with CompletionCondition as a tag
def create_region(world: World, pristine_locations, name: str, locations, completion_items):
    # Make this location in this world
    res = Region(name, world.player, world.multiworld)

    # Add all locations, and reference them back to the parent
    EventId = None  # Event Items/Locations don't have an ID
    EventClassification = ItemClassification.progression # By definition, an Event Item will always be for progression
    for name, data in locations.items():
        # Handle events differently
        if data.id() is None:
            location = FF5PRLocation(world.player, name, EventId, res)
            location.place_locked_item(FF5PRItem(data.event_item, EventClassification, EventId, world.player))
            if 'CompletionCondition' in data.tags:
                completion_items.append(data.event_item)
        else:
            location = FF5PRLocation(world.player, name, data.id(), res)
        res.locations.append(location)

    # Append it to the multiworld's list of regions
    world.multiworld.regions.append(res)

    return res


class FF5PRWebWorld(WebWorld):
    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing Final Fantasy 5 PR with Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["???"]
    )
    
    tutorials = [setup_en]
    game_info_languages = ["en"]


@dataclass
class FF5PROptions(PerGameCommonOptions):
    pass


class FF5PRWorld(World):
    """Final Fantasy V Pixel Remaster stuff..."""

    game = "Final Fantasy V PR"

    options_dataclass = FF5PROptions
    options: FF5PROptions
    #settings: typing.ClassVar[FF5PRSettings]  # I don't think we need this yet?

    # Does this world have any meaningful layout or pathing?
    # If so, set this to True, and the paths to various checks will be shown in the spoiler log
    topology_present = True

    # TODO: Set both from Pristine (and make sure Regions propagate to their children)
    item_name_groups = {}
    location_name_groups = {}

    # Make a mapping from item 'name' to item 'id', so that we can look up 'Elixir' and get 14
    item_name_to_id = { name: data.id() for name, data in pristine_items.items() if data.id() is not None }

    # Make a mapping from location 'name' to 'id', so that we can look up 'Greenhorns_Club_1F_Treasure1' and get 1234
    location_name_to_id = {}
    for region_data in pristine_locations.values():
        for name, data in region_data.locations.items():
            if data.id() is not None:
                location_name_to_id[name] = data.id()

    
    web = FF5PRWebWorld()
 
    def __init__(self, world: MultiWorld, player: int):
        #self.rom_name_available_event = threading.Event()
        #self.rom_name = None
        #self.rooms = None
        super().__init__(world, player)

    # Helper: Retrieve a region object
    def getRegion(self, regionName):
        for region in self.multiworld.regions:
            if region.player == self.player and region.name == regionName:
                return region
        return None

    # Place this world's Regions and their Locations in the multiworld regions list
    # TODO: Dispatch to .Region.create_regions()
    def create_regions(self):
        # Create all regions, and their child locations
        completion_items = []
        for region_name, region_data in pristine_locations.items():
            create_region(self, pristine_locations, region_name, region_data.locations, completion_items)

        # TODO: Need to separate the item "IDs" and whatnot (the ".csv" equivalent) from the actual creation.
        #       In other words, building the ItemPool will depend on player options (eventually), and will NOT
        #       just be copying the .csv file into the create_items() code.
        # TODO: We also, I guess, might want to represent what item *was* at a given location by default.
        #       I.e., we have 1 Elixir at Tule X and 1 Elixir at Lix Y, and thus we add 2 Elixirs to the initial Item Pool
        #       (and this allows us to only add 1 if we set the flag that says "Only do World 3").
        # TODO: Some of this stuff goes into set_rules() if we're being pedantic...

        # Add completion condition
        # TODO: Need to check the logic; I think there's a 'has_any" for checking all the completion_items
        if len(completion_items) > 0:
            self.multiworld.completion_condition[self.player] = lambda state: state.has(completion_items[0], self.player)   # If you won, release all items
        else:
            print("ERROR: No completion condition in events...")

        # Hook up basic connections
        for regA, regB in pristine_connections.items():        
          self.getRegion(regA).connect(self.getRegion(regB))
        

        # Rule for getting into the final area
        # TODO: TEMP: For now, you need the Knight class to get into the final boss area
        # TODO: A better rule would be something like "You need a special key to get the chest in Location"; but the 
        #       rule "you need a Knight to access the Rift" is better as a Region Access Rule
        #add_rule(victoryEventLocation, lambda state: state.has("Job: Knight", self.player))
        # TODO: Seems like we need this?
        #final_boss_fight_region.locations.append(victoryEventLocation)





    # Create this world's items and add them to the item pool
    # After this function call, all Items, Regions, and Locations are fixed (this includes Events).
    def create_items(self):
        # TODO: Items should be deferred (?? what did I mean by this ??)
        items = []

        # By default, we add the original set of items to the item pool.
        # In other words, if Chest X contains a Potion and Chest Y contains an Ether, add a Potion then an Ether
        for region in self.multiworld.regions:
            if region.player == self.player:  # I think this is right?
                pristine_region = pristine_locations[region.name]
                for location in region.locations:
                    pristine_location = pristine_region.locations[location.name]
                    if pristine_location.id() is not None:
                        pristine_item_name = pristine_location.orig_item_name()
                        print("BLAH:",location,pristine_item_name)
                        items.append(self.create_item(pristine_item_name))

        # Update
        self.multiworld.itempool += items

        # TODO: Here is where we balance the Item-to-Location ratio; i.e., make 'Junk' items if we're short


    # Create an item on demand
    def create_item(self, fullName: str) -> FF5PRItem:
        # The only exception here is that we allow specifying '100 Gil', which refers to the 'Gil' item (x100, naturally)
        name = fullName
        count = 1

        # This is hard-coded for gil; we *may* eventually allow multiples of other items (10 Potions) if it seems useful.
        if name not in pristine_items and name.endswith('Gil'):
            parts = name.split(' ', 1)
            if parts[0].isdigit() and parts[1] == 'Gil':  # Note: isdigit doesn't work with negatives
                name = parts[1]
                count = int(parts[0])

        # TODO: Right now, this will give 1 gil -- I need to figure out how to do multiples of currency
        return FF5PRItem(name, ParseClassification(pristine_items[name].classification), pristine_items[name].id(), self.player)




