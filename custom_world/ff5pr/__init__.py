import Utils
import settings
import base64
import threading
import requests
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import add_rule
from BaseClasses import Tutorial, MultiWorld, ItemClassification, LocationProgressType, Item, Location, Region, CollectionState

from .Pristine import pristine_items, pristine_locations, pristine_regions, pristine_connections, validate_pristine

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






# Helper: Classification string to ItemClassification type
#         TODO: Put into its own file
def ParseItemClassification(classStr):
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
    print("WARNING: Unknown Item classification type: {classStr}")
    return ItemClassification.filler


# Helper: Classification string to LocationClassification type
def ParseLocationClassification(classStr):
  classStr = classStr.lower()
  if classStr == 'default':
    return LocationProgressType.DEFAULT
  elif classStr == 'priority':
    return LocationProgressType.PRIORITY
  elif classStr == 'excluded':
    return LocationProgressType.EXCLUDED
  else:
    print("WARNING: Unknown Location classification type: {classStr}")
    return LocationProgressType.DEFAULT


# Helper: Retrieve the Pristine object associated with the given Archipelago item
def GetPristine(obj):
    if isinstance(obj, Region):
        return pristine_regions[obj.name]
    elif isinstance(obj, Location):
        return pristine_locations[obj.name]
    elif isinstance(obj, Item):
        return pristine_items[obj.name]
    else:
        print(f"WARNING: Object has no known Pristine type: {type(obj)} => {obj}")
        return obj  # Hope for the best



# completion_items is an output parameter; it stores any Location with CompletionCondition as a tag
def create_region(world: World, name: str, locations, completion_items):
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

            # Set Classification
            location.progress_type = ParseLocationClassification(data.classification)
            # TODO: Where to put these rules? Pristine? Or...?
            if "Chest" in data.tags:
                location.progress_type = LocationProgressType.EXCLUDED

            # Lock via fire?
            if "BlockedByFire" in data.tags:
                ruleFn = lambda state: world.require_fire_be_gone(state)
                add_rule(location, ruleFn)

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


# One world is created for each Player. The world has a reference to the broader "multiworld" object.
class FF5PRWorld(World):
    """Final Fantasy V Pixel Remaster stuff..."""

    game = "Final Fantasy V PR"

    options_dataclass = FF5PROptions
    options: FF5PROptions
    #settings: typing.ClassVar[FF5PRSettings]  # I don't think we need this yet?

    # Does this world have any meaningful layout or pathing?
    # If so, set this to True, and the paths to various checks will be shown in the spoiler log
    # The way I currently lay out items doesn't really give useful pathing; it would just be "World 1 -> Dungeon X", etc.
    # This might be useful in theory, but right now it's just a bunch of clutter.
    topology_present = True  # TODO: Needs to be on for now for debugging...

    # TODO: Set both from Pristine (and make sure Regions propagate to their children)
    item_name_groups = {}
    for name, data in pristine_items.items():
        if data.id() is not None:
            for tag in data.tags:
                item_name_groups.setdefault(tag, set()).add(name)

    # TODO: Set from Pristine (and make sure Regions propagate to their children, if we still want that...)
    location_name_groups = {}

    # Make a mapping from item 'name' to item 'id', so that we can look up 'Elixir' and get 14
    item_name_to_id = { name: data.id() for name, data in pristine_items.items() if data.id() is not None }

    # Make a mapping from location 'name' to 'id', so that we can look up 'Greenhorns_Club_1F_Treasure1' and get 1234
    location_name_to_id = { name: data.id() for name, data in pristine_locations.items() if data.id() is not None }
    
    web = FF5PRWebWorld()
 
    def __init__(self, world: MultiWorld, player: int):
        super().__init__(world, player)

        # Useful when developing
        validate_pristine()


    # Some rules
    # TODO: Move to the .Rules file... but how to get playerID in that case?
    def require_world_1_teleport(self, state: CollectionState) -> bool:
        return state.has("W1Teleport", self.player)
    def require_10_jobs(self, state: CollectionState) -> bool:
        return state.has_group("Job", self.player, 10)
    def require_fire_be_gone(self, state: CollectionState) -> bool:
        return state.has("FireBeGone", self.player)


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
        for region_name, region_data in pristine_regions.items():
            create_region(self, region_name, region_data.locations, completion_items)

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
        for regA, regB, connectRule in pristine_connections:
            # Deal with our rule
            ruleFn = None
            if connectRule == "require_world_1_teleport":
                ruleFn = lambda state: self.require_world_1_teleport(state)
            elif connectRule == "require_10_jobs":
                ruleFn = lambda state: self.require_10_jobs(state)
            elif connectRule is not None:
                raise Exception(f"BAD RULE: {connectRule}")

            self.getRegion(regA).connect(self.getRegion(regB), None, ruleFn)  # Third param is "name"
        

        # Rule for getting into the final area
        # TODO: I'd like to abstract this somewhere in Pristine or similar...
        # TODO: Better searching through regions...
        #for region in self.multiworld.regions:
        #    if region.player == self.player and region.name == "World 1 to 2 Teleport":
        #        for location in region.locations:
        #            if location.name == "Unlock World 2":
        #                add_rule(location, lambda state: state.has_group("Job", self.player, 10))  # Has 10 Crystals


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
                for location in region.locations:
                    pristine_location = GetPristine(location)
                    if pristine_location.id() is not None:
                        pristine_item_name = pristine_location.orig_item_name()
                        new_item = self.create_item(pristine_item_name)
                        items.append(new_item)
        
        # TODO: Here is where we balance the Item-to-Location ratio; i.e., make 'Junk' items if we're short

        # Update
        self.multiworld.itempool += items

        # Collect our first unlock; right now only World 1 is available
        firstTeleport = None
        for name, data in pristine_items.items():
            # TODO: Make a list and randomly select one of them (when we have multiple worlds).
            if "WorldTeleport" in data.tags:
                firstTeleport = self.create_item(name)
        #
        self.multiworld.push_precollected(firstTeleport)


    # Create an item on demand
    def create_item(self, fullName: str) -> FF5PRItem:
        # Doing this for now; we can figure out the "right" way later.
        return FF5PRItem(fullName, ParseItemClassification(pristine_items[fullName].classification), pristine_items[fullName].id(), self.player)

        # TODO: This doesn't work right; it won't catch "5 Potion(S)", and it doesn't handle IDs correctly.
        # The only exception here is that we allow specifying '100 Gil', which refers to the 'Gil' item (x100, naturally)
        #name = fullName
        #count = 1
        #
        # This is hard-coded for gil; we *may* eventually allow multiples of other items (10 Potions) if it seems useful.
        #if name not in pristine_items and name.endswith('Gil'):
        #    parts = name.split(' ', 1)
        #    if parts[0].isdigit() and parts[1] == 'Gil':  # Note: isdigit doesn't work with negatives
        #        name = parts[1]
        #        count = int(parts[0])
        #
        #return FF5PRItem(name, ParseItemClassification(pristine_items[name].classification), pristine_items[name].id(), self.player)




