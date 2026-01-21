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


# Our list of items
# TODO: Need to do this *WAY* better
item_table = {
    "Ether": ItemData(0, ItemClassification.filler, ["Consumables"]),
    "100 Gil": ItemData(1, ItemClassification.filler, ["Gil"]),
    "Potion": ItemData(2, ItemClassification.filler, ["Consumables"]),
    "Phoenix Down": ItemData(3, ItemClassification.filler, ["Consumables"]),
    "Tent": ItemData(4, ItemClassification.filler, ["Consumables"]),
    "Leather Shoes": ItemData(5, ItemClassification.filler, ["Armor"]),
    "Job: Knight": ItemData(6, ItemClassification.progression, ["Key Items"]),
    "Job: Thief": ItemData(7, ItemClassification.useful, ["Key Items"]),
}



# TODO: This also goes somewhere...
#       Not sure how we want to generate location IDs for this game
location_table = {
    'tule_greenhorns_club_1f_treasure_1': 0,
    'tule_greenhorns_club_1f_treasure_2': 1,
    'tule_greenhorns_club_1f_treasure_3': 2,
    'tule_greenhorns_club_1f_treasure_4': 3,
    'tule_greenhorns_club_1f_treasure_5': 4,
    'tule_greenhorns_club_2f_treasure_1': 5,

    'wind_temple_crystal_shard_1': 6,
    'wind_temple_crystal_shard_2': 7,
}




def create_region(world: World, active_locations, name: str, locations=[]):
    # Make this location in this world
    res = Region(name, world.player, world.multiworld)

    # Add all locations, and reference them back to the parent
    for locationName in locations:
        locId = active_locations.get(locationName, None)
        if locId is not None:
            location = FF5PRLocation(world.player, locationName, locId, res)
            res.locations.append(location)

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

    # I guess we don't need these yet?
    item_name_groups = {}

    # Make a mapping from item 'name' to item 'id', so that we can look up 'Elixir' and get 14
    item_name_to_id = { name: data.id for name, data in item_table.items() if data.id is not None }

    # Make a mapping from location 'name' to 'id', so that we can look up 'Greenhorns_Club_1F_Treasure1' and get 1234
    location_name_to_id = location_table

    
    web = FF5PRWebWorld()
 
    def __init__(self, world: MultiWorld, player: int):
        #self.rom_name_available_event = threading.Event()
        #self.rom_name = None
        #self.rooms = None
        super().__init__(world, player)


    # Place this world's Regions and their Locations in the multiworld regions list
    # TODO: Dispatch to .Region.create_regions()
    def create_regions(self):
        # Start region
        menu_region = create_region(self, location_table, 'Menu', [])

        # TODO: There is a better Region().add_locations(location_mapping, FF5PRLocation)
        tule_greenhorns_club_region = create_region(self, location_table, 'Tule_Greenhorns_Club', [
            'tule_greenhorns_club_1f_treasure_1', 'tule_greenhorns_club_1f_treasure_2', 'tule_greenhorns_club_1f_treasure_3',
            'tule_greenhorns_club_1f_treasure_4', 'tule_greenhorns_club_1f_treasure_5', 'tule_greenhorns_club_2f_treasure_1',
        ])

        wind_temple_region = create_region(self, location_table, 'Wind_Temple', [
            'wind_temple_crystal_shard_1', 'wind_temple_crystal_shard_2'
        ])

        final_boss_fight_region = create_region(self, location_table, 'Final Boss Fight', [])


        # Append all created regions
        self.multiworld.regions += [
            menu_region,
            tule_greenhorns_club_region,
            wind_temple_region,
            final_boss_fight_region,
        ]

        # TODO: Need to separate the item "IDs" and whatnot (the ".csv" equivalent) from the actual creation.
        #       In other words, building the ItemPool will depend on player options (eventually), and will NOT
        #       just be copying the .csv file into the create_items() code.
        # TODO: We also, I guess, might want to represent what item *was* at a given location by default.
        #       I.e., we have 1 Elixir at Tule X and 1 Elixir at Lix Y, and thus we add 2 Elixirs to the initial Item Pool
        #       (and this allows us to only add 1 if we set the flag that says "Only do World 3").

        # Put a "Final Boss" event -- TODO: there is a 'place_event()' in Location that we should use instead.
        # TODO: Some of this stuff goes into set_rules() if we're being pedantic...
        EventId = None  # Event Items/Locations don't have an ID
        EventClassification = ItemClassification.progression # By definition, an Event Item will always be for progression
        victoryEventLocation = FF5PRLocation(self.player, "Defeat Neo Ex-Death", EventId, final_boss_fight_region)
        victoryEventLocation.place_locked_item(FF5PRItem("Victory", EventClassification, EventId, self.player))
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)   # If you have Victory, release all items
        # Rule for getting into the final area
        # TODO: TEMP: For now, you need the Knight class to get into the final boss area
        # TODO: A better rule would be something like "You need a special key to get the chest in Location"; but the 
        #       rule "you need a Knight to access the Rift" is better as a Region Access Rule
        add_rule(victoryEventLocation, lambda state: state.has("Job: Knight", self.player))
        # TODO: Seems like we need this?
        final_boss_fight_region.locations.append(victoryEventLocation)

        # Connect all our Regions (assuming no Entrance randomization)
        # TODO: We can add Region Access Rules later; we should prioritize these over Location rules
        # TODO: We can also apply a rule to an 'Entrance' -- I guess this means you could lock the Boss door from one side...
        menu_region.connect(tule_greenhorns_club_region)
        menu_region.connect(wind_temple_region)
        #tule_greenhorns_club_region.connect(wind_temple_region) # TODO: Do we realy need this? Probably irrelevant with a World map...
        wind_temple_region.connect(final_boss_fight_region) # TODO: TEMP




    # Create this world's items and add them to the item pool
    # After this function call, all Items, Regions, and Locations are fixed (this includes Events).
    def create_items(self):
        # TODO: Items should be deferred
        items = []

        # TODO: We can add an item to the pool twice (if there are two chests with Potions, for example)
        items += [ self.create_item('Ether') ]
        items += [ self.create_item('100 Gil') ]
        items += [ self.create_item('Potion') ]
        items += [ self.create_item('Phoenix Down') ]
        items += [ self.create_item('Tent') ]
        items += [ self.create_item('Leather Shoes') ]
        items += [ self.create_item('Job: Knight') ]
        items += [ self.create_item('Job: Thief') ]

        # Update
        self.multiworld.itempool += items

        # TODO: Here is where we balance the Item-to-Location ratio; i.e., make 'Junk' items if we're short


    # Create an item on demand
    def create_item(self, name: str) -> FF5PRItem:
        return FF5PRItem(name, item_table[name].classification, item_table[name].id, self.player)

