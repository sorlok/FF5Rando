import Utils
import os
import settings
import base64
import json
import threading
import requests
import zipfile
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import add_rule
from worlds.Files import APPatch
from BaseClasses import Tutorial, MultiWorld, ItemClassification, LocationProgressType, Item, Location, Region, CollectionState

from .Options import FF5PROptions
from .Pristine import pristine_items, pristine_locations, pristine_regions, pristine_connections, pristine_game_patches, validate_pristine, custom_messages, PristineMultiworldLocationStart, PristineMultiworldLocationMagicNumber, PristineJumboLocationMagicNumber, PristineMultiworldItemStart, JumboItemStartID, get_all_item_names, normalize_item_name, parse_jumbo_items
from .Patches import all_patch_contents

# TODO: Put Options in its own file
from Options import Choice, FreeText, ItemsAccessibility, Toggle, Range, PerGameCommonOptions
from dataclasses import dataclass


# TODO: these go into their own classes too



# Very basic representation of items(+jobs) for our engine.
# To store a job, pass "job" for content_num)
#class MiniItem:
#    def __init__(self, content_id, content_num):
#        self.content_id = content_id
#        self.content_num = content_num
#
#    def isJob():
#        return self.content_num == "job"
#
#    def jobId():
#        return self.content_id



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
def create_region(world: World, name: str, locations, completion_items, prog_items_in_chests):
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
            
            # Block progression items from chests, unless the player wants them there.
            if "Chest" in data.tags:
                if not prog_items_in_chests:
                    location.progress_type = LocationProgressType.EXCLUDED

            # Lock via fire?
            if "BlockedByFire" in data.tags:
                ruleFn = lambda state: world.require_fire_be_gone(state)
                add_rule(location, ruleFn)

        res.locations.append(location)

    # Append it to the multiworld's list of regions
    world.multiworld.regions.append(res)

    return res



# Helper: Return a json object for the "SysCall" Mnemonic
# TODO: Very much goes into output tools
def GetJsonSysCallObj(jobSysCallName):
    return '{"label": "","mnemonic": "SysCall","operands": {"iValues": [0,0,0,0,0,0,0,0],"rValues": [0,0,0,0,0,0,0,0],"sValues": ["' + jobSysCallName + '","","","","","","",""]},"type": 1,"comment": ""}'
# Similar, but for GetItem
def GetJsonItemObj(content_id, content_num):
    return '{"label": "","mnemonic": "GetItem","operands": {"iValues": [' + f"{content_id},{content_num}" + ',0,0,0,0,0,0],"rValues": [0,0,0,0,0,0,0,0],"sValues": ["","","","","","","",""]},"type": 1,"comment": ""}'


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

    # TODO: Option Groups can go here.



# One world is created for each Player. The world has a reference to the broader "multiworld" object.
class FF5PRWorld(World):
    """Final Fantasy V Pixel Remaster stuff..."""

    game = "Final Fantasy V PR"

    options_dataclass = FF5PROptions
    options: FF5PROptions   # This just exists to give us type hints
    #settings: typing.ClassVar[FF5PRSettings]  # I don't think we need this yet?

    # Does this world have any meaningful layout or pathing?
    # If so, set this to True, and the paths to various checks will be shown in the spoiler log
    # The way I currently lay out items doesn't really give useful pathing; it would just be "World 1 -> Dungeon X", etc.
    # This might be useful in theory, but right now it's just a bunch of clutter.
    topology_present = True  # TODO: Needs to be on for now for debugging...

    # Contains a mapping from normalized_name -> ID
    # Things like "5 Potions" or "10 Gil and 1 Frost Rod"
    jumbo_items = {}

    # Make a mapping from item 'name' to item 'id', so that we can look up 'Elixir' and get 14
    # See note in get_all_item_names() re: consistency
    item_name_to_id = {}
    for name in get_all_item_names():
        item_id = None
        if name in pristine_items:
            item_id = pristine_items[name].content_id
        else:
            jumbo_items.setdefault(name, len(jumbo_items))
            item_id = JumboItemStartID + jumbo_items[name]
        item_name_to_id[name] = PristineMultiworldItemStart + item_id

    #
    # TODO: This and item_name_to_id don't take jumbo items into account yet; probably best to do this after item creation?
    # TODO: Ugh, jumbo items really mess this up!
    #
    item_name_groups = {}
    for name in item_name_to_id.keys():
        if name in pristine_items:
            data = pristine_items[name]
            for tag in data.tags:
                item_name_groups.setdefault(tag, set()).add(name)
        else:  # Jumbo Item
            item_name_groups.setdefault('Jumbo', set()).add(name)


    # TODO: Set from Pristine (and make sure Regions propagate to their children, if we still want that...)
    location_name_groups = {}

    # Make a mapping from location 'name' to 'id', so that we can look up 'Greenhorns_Club_1F_Treasure1' and get 1234
    location_name_to_id = { name: data.id() for name, data in pristine_locations.items() if data.id() is not None }
    
    options_dataclass = FF5PROptions

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
    def require_adamant(self, state: CollectionState) -> bool:
        return state.has("Adamantite", self.player)
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
            create_region(self, region_name, region_data.locations, completion_items, self.options.prog_items_in_chests)

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
            elif connectRule == "require_adamant":
                ruleFn = lambda state: self.require_adamant(state)
            elif connectRule == "require_fire_be_gone":
                ruleFn = lambda state: self.require_fire_be_gone(state)
            elif connectRule is not None:
                raise Exception(f"BAD RULE: {connectRule}")

            self.getRegion(regA).connect(self.getRegion(regB), None, ruleFn)  # Third param is "name"



    # Create this world's items and add them to the item pool
    # After this function call, all Items, Regions, and Locations are fixed (this includes Events).
    def create_items(self):
        # Build up a list of all items that we want to add to the pool
        items = []

        # By default, we add the original set of items to the item pool.
        # In other words, if Chest X contains a Potion and Chest Y contains an Ether, add a Potion then an Ether
        for region in self.multiworld.regions:
            if region.player == self.player:  # I think this is right?
                for location in region.locations:
                    pristine_location = GetPristine(location)
                    if pristine_location.id() is not None:   # Not an "Event" location+item
                        pristine_item_name = pristine_location.orig_item
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
    # Some points of interest:
    #   * An item will always have the same ID. We add the `content_id` to the PristineMultiworldItemStart for easy debugging.
    #   * If you pass in "5x Potion + 1 Ether" (or similar), we will try to parse that into a series of items to give you.
    #   * The "Job: " items also parse correctly; if you (for whatever reason) did "Job: Knight + 5x Ether", then the "Progressive" flag will
    #     be based on the combined set (so, if *any* Progressive item exists, it counts as progressive).
    #   * ALL items are added to a lookup to make the .NET client code consistent. So, content_id 1 (Potion) will be given an entry
    #     that says "give them 1 Potion". A little verbose, but worth it for consistency.
    def create_item(self, fullName: str) -> FF5PRItem:
        # Create our item by parsing the name string
        normName = normalize_item_name(fullName)
        itemClassification = ParseItemClassification(pristine_items[normName].classification) if normName in pristine_items else ItemClassification.filler
        return FF5PRItem(normName, itemClassification, self.item_name_to_id[normName], self.player)


    # Create the patch file
    def generate_output(self, output_directory: str) -> None:
        # If we shuffle entrances, we could write them here

        # Some stuff is required to interact with the multiworld server, or for general bookkeeping
        # We'll store this all into one big JSON object that the C# app can read and make use of
        multiworld_data = {}

        # The seed is displayed in a few places.
        multiworld_data['seed_name'] = self.multiworld.seed_name

        # This is in Archipelago.json, but might as well copy it here in case they change that.
        multiworld_data['player_name'] = self.multiworld.get_player_name(self.player)

        # We need to send unlocked "location_ids" to the other players
        # The only sane way to get these through the scripting system is to represent them as 
        #   items with very high content_ids (i.e., 9000000+), and to translate that to a location ID.
        # Since we control the location_ids, we can just add/subtract 9000000 to get this translation.
        multiworld_data['local_location_content_id_offset'] = PristineMultiworldLocationStart
        multiworld_data['local_location_content_num_incantation'] = PristineMultiworldLocationMagicNumber  # This will appear in the 'content_num'
        multiworld_data['jumbo_location_content_num_incantation'] = PristineJumboLocationMagicNumber  # This will appear in the 'content_num'

        # NOTE: When we receive items, we are given a list of NetworkItems, which contain an item ID
        # Since we control the ItemId, we should be able to just subtract 3000000 to get the content_id
        multiworld_data['remote_item_content_id_offset'] = PristineMultiworldItemStart

        
        # When we get multiworld items, we want to show a meaningful message box.
        # To do that, we'll need to pad the system message list with a bunch of extra messages, since each one is unique.
        extra_found_multiworld_item_messages = {}   # key -> value ; nameplate will always be empty


        # If we need to put hints in message boxes, do this:
        #if self.hints != 'none':
        #    self.hint_data_available.wait()

        # We have a series of output 'files', but we'll keep them in-memory to make zipping simpler.


        # Prepare a file that contains all of our game-modifying patches. 
        # These will be applied before anything else is patched.
        script_patch_file = "# These patches are applied before any later item-modifying patches.\n\n"
        for name in pristine_game_patches:
            script_patch_file += all_patch_contents[name]
        script_patch_file += "\n\n# These patches are applied last; they modify the actual items being placed\n\n"

        # Write our custom Messages
        message_strings_file = "Assets/GameAssets/Serial/Data/Message/story_mes_en\n\n"
        for key,val in custom_messages['Assets/GameAssets/Serial/Data/Message/story_mes_en'].items():  # TODO: Better abstraction
            newMsg = val
            if isinstance(val, list):
                # Build up the message, which contains the names of all items (and players)
                newMsg = 'Found '
                for i in range(len(val)):
                    loc_name = val[i]
                    loc = self.get_location(loc_name)   # TODO: I guess we could put the 'pristine' name here if we ever filter Locations
                    if loc.item.player != self.player:
                        newMsg += str(loc.item)   # Includes "(PlayerName)" in the __repr
                    else:
                        newMsg += loc.item.name   # We don't need our own name in the item list
                    if i == len(val) - 2:
                        newMsg += ', and '
                    elif i < len(val) - 2:
                        newMsg += ', '

            #Special-case
            if key == 'RANDO_WELCOME_1':
                newMsg = f"Welcome to the randomizer! Your seed is: {multiworld_data['seed_name']}"

            message_strings_file += f"{key},{newMsg}\n"
        #
        nameplate_strings_file = "Assets/GameAssets/Serial/Data/Message/story_cha_en\n\n"
        for key,val in custom_messages['Assets/GameAssets/Serial/Data/Message/story_cha_en'].items():  # TODO: Better abstraction
            nameplate_strings_file += f"{key},{val}\n"


        # Treasure file is as basic a csv as they get
        treasure_mod_file = "entity_default,json_xpath,content_id,content_num,message_key\n"

        # TODO: Need a good place for these 'generic' entries. This one lets you use the normal airship in the Torna Canal.
        #       It's a generic version of the treasure format, and I don't feel like writing another parser.
        # TODO: Need these off for now; there's a few problems:
        #       1) The airship can enter this may while in "Flying" mode. It's either the type of "entity", or it's some collision flag.
        #       2) We'd have to hack the events a bunch, including closing the door once you beat the boss. But I'm having trouble 
        #          getting the door event to work. Not strictly wrong, but a little clunky.
        #       In short, too much effort for 1 boss.
        # TODO: We might be able to fix (1) with "ChangeView()" --- that causes the screen to shift to its "Mode 7" angle -- we *could* potentially make the airship "land" with this + a SysCall ?
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_10010/Map_10010/entity_default,/layers/[1]/objects/{id=234}/properties,target_transportation_ids,string,\n"
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_30050/Map_30050/entity_default,/layers/[0]/objects/{id=21}/properties,target_transportation_ids,string,\n"
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_30050/Map_30050/ev_e_0026,/layers/[0]/objects/{id=8}/properties,target_transportation_ids,string,\n"
        #
        # Make the Ship's Graveyard map entrance teleport you to the start of the Ship's Graveyard
        treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_10010/Map_10010/entity_default,/layers/[1]/objects/{id=259}/properties,point_id,int,1\n"
        # Always allow "pull"-ing the switch in the Catapult
        treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_20231/Map_20231_4/ev_e_0224,/layers/[0]/objects/{id=30}/properties,script_id,int,2666\n"


        # Make a list of all of our own items in the itempool (whether they are in our own world or someone else's)
        item_names_of_interest = set()
        for item in self.multiworld.itempool:
            if item.player == self.player and item.code is not None:
                item_names_of_interest.add(item.name)


        # Patch all of *our* Locations
        for loc in self.get_locations():
            # Skip Event Items; they are meant to be built in to the Game Engine (or just abstractions)
            if loc.item.code is None:
                continue

            # Original data for this location
            pristine_location = GetPristine(loc)

            # What we need in order to populate our struct
            content_id = None
            content_num = None
            message_key = None
            #sys_call_name = None    # Do we need a SysCall to give the player this item (for us, it's just jobs)

            # Deal with items in *our* Locations that are destined for *other* players
            # Note that *we* own the location (always), but the *item* may be owned by anyone.
            if loc.item.player != self.player:
                # I think this is guaranteed
                if loc.address is None:
                    raise Exception(f"Invalid location; no address: {loc.name} for player: {loc.player}")

                # Convert the location to a faux "content_id" that we can pass through our system.
                content_id = loc.address
                content_num = PristineMultiworldLocationMagicNumber   # Magic number; "this is a multiworld item"
                #sys_call_name = None   # We *could* do this, but it would limit where we can receive multiworld items. In the future, we can prob. elimiate these entirely.

                # ...and prompt the player
                # NOTE: Some of these, like the Crystal Shrine rooms, will never be used by our game.
                #       The reason for this is that anything that gives out multiple *Locations* (NOT multiple *Items*)
                #       will automatically aggregate those into a single text box.
                #       We leave these extra messags here on the off chance that something references them.
                message_key = f"RANDO_GOT_MULTIWORLD_ITEM_{len(extra_found_multiworld_item_messages)}"
                extra_found_multiworld_item_messages[message_key] = f"Found multiworld item: {loc.item}"

            # Deal with items in *our* Locations that are that are destined for *us*
            else:
                # Item Received (NOT the original item at that location)
                item_id = loc.item.code - PristineMultiworldItemStart

                # Mundane vs. jumbo vs. job
                # TODO: If we add Jumbo items for everything AND use the RANDO_GOT_ style messages, we can simplify all this.
                if loc.item.name in pristine_items and 'Job' not in pristine_items[loc.item.name].tags:
                    # Mundane
                    content_id = pristine_items[loc.item.name].content_id
                    content_num = 1

                    # What Message do we want to show? Hard-coding this a bit for now....
                    # TODO: There are two "got an item" messages (one for "chests" and one for "found").
                    # Additionally, there's "found a great sword in the water" that we can modify.
                    message_key = 'T0003_01_01'  # "Found <ITEM>!"
                    if content_id == 1:
                        message_key = 'T0003_03_01'  # "Found <NUM> gil."
                else:
                    # Tell the game to process this specially
                    content_id = item_id
                    content_num = PristineJumboLocationMagicNumber

                    # We'll need a custom message for this
                    # TODO: "Got 100x Gil" and "Got 2x Potion" don't look great; we may want a 'printable' form:
                    #       "Got 100 Gil" and "Got 2x Potions". For now it's fine...
                    message_key = f"RANDO_GOT_JUMBO_ITEM_{len(extra_found_multiworld_item_messages)}"
                    extra_found_multiworld_item_messages[message_key] = f"Found: {loc.item.name}"

                # Is there a SysCall associate with this (should only be Jobs)
                # NOPE! Treat Jobs as items for simplicity
                #sys_call_name =  pristine_item.optattrs.get('SysCall')


            # TODO: We also need to make a "you found <num> <item>s!" and "treasure chest contained <num> <item>s!"
            #       messages. We can make this part of some patch; this is needed since the NPC "5 Potions", etc., can be
            #       given to the party via Treasure. For now, it "works", though (just wrong message); we'll tidy this up later.

            # There can (rarely) be multiple parallel locations for this item; it's assumed game logic will handle keeping them aligned.
            asset_paths = pristine_location.asset_path
            if not isinstance(asset_paths, list):
                asset_paths = [asset_paths]
            for asset_path in asset_paths:
                # 1. Is this a simple chest? (No event; part of entity_default?)
                if 'entity_default' in asset_path:
                    parts = asset_path.split(':')
                    treasure_mod_file += f"{parts[0]},{parts[1]},{content_id},{content_num},{message_key}\n"
                    continue

                # 2. Right now, we don't support adding anything to Script Events.
                # TODO: Give Crystals at these locations.
                # TODO: Eventually give items too!
                else:
                    # Jobs
                    #if sys_call_name is not None:
                    #    # We overwrite with SysCall to add the job
                    #    parts = asset_path.split(':')
                    #    script_patch_file += f"{parts[0]},{parts[1]},Nop:{pristine_location.optattrs['Label']},Overwrite,0\n"
                    #    script_patch_file += "[" + GetJsonSysCallObj(sys_call_name) + "]\n\n" # Two newlines are necessary
                    #    continue

                    # Pretty much anything without 'optattrs' is implicitly added via 'GetItem'
                    #if True:  #loc.item.classification == ItemClassification.filler:
                        # TODO: Need to check and handle MultiWorld a special way here...

                    # We use GetItem here
                    parts = asset_path.split(':')
                    script_patch_file += f"{parts[0]},{parts[1]},Nop:{pristine_location.optattrs['Label']},Overwrite,0\n"
                    script_patch_file += "[" + GetJsonItemObj(content_id, content_num) + "]\n\n" # Two newlines are necessary
                    #continue
                    
                    # What's left?
                    #raise Exception(f"Unexpected item type for: {loc.item.name} at {loc.name}")

        # Map all "jumbo"/job items *in this seed* to lists of items to be recived.
        # Note: We could one day treat all items as jumbo/special, but it might not simplify that much on the .NET side...
        special_items = {}
        for itemName in sorted(item_names_of_interest):
            if itemName in pristine_items and 'Job' not in pristine_items[itemName].tags:
                continue
            itemId = self.item_name_to_id[itemName] - PristineMultiworldItemStart
            special_items[itemId] = []
            subItems = parse_jumbo_items(itemName)
            for entry in subItems:
                pristine_item = pristine_items[entry[1]]
                if 'Job' in pristine_item.tags:
                    special_items[itemId].append(["job",  pristine_item.optattrs['JobId']])  # job_id
                else:
                    special_items[itemId].append(["item", pristine_item.content_id,  entry[0]])  # (content_id, content_num)
        multiworld_data['content_id_special_items'] = special_items


        # Add our extra messages
        for key, val in extra_found_multiworld_item_messages.items():
            message_strings_file += f"{key},{val}\n"
            nameplate_strings_file += f"{key},\n"


        # Prepare our various .csv patches (things like items, etc.)
        # TODO: Not exactly sure how to organize this...
        master_csvs_file = ""
        master_csvs_file += "# Add any new items\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/item\n"
        master_csvs_file += "+id,sort_id,type_id,system_id,item_lv,attribute_id,accuracy_rate,destroy_rate,standard_value,renge_id,menu_renge_id,battle_renge_id,invalid_reflection,period_id,throw_flag,preparation_flag,drink_flag,machine_flag,condition_group_id,battle_effect_asset_id,menu_se_asset_id,menu_function_group_id,battle_function_group_id,buy,sell,sales_not_possible\n"
        master_csvs_file += "58,58,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"   # "Server Connection" key item
        master_csvs_file += "\n"
        master_csvs_file += "# ...and their content entries\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/content\n"
        master_csvs_file += "+id,mes_id_name,mes_id_battle,mes_id_description,icon_id,type_id,type_value\n"
        master_csvs_file += "1691,MSG_RANDO_SERVER_ITEM_NAME,None,MSG_RANDO_SERVER_ITEM_DESC,0,1,58\n"
        master_csvs_file += "\n"

        # Add our new item name/descriptions to system
        system_strings_file = "Assets/GameAssets/Serial/Data/Message/system_en\n"
        system_strings_file += f"MSG_RANDO_SERVER_ITEM_NAME,<IC_RING>Server Connection\n"
        system_strings_file += f"MSG_RANDO_SERVER_ITEM_DESC,TBD\n"   # Will be intercepted by the engine

        # Remove all (relevant) boss drops and give them XP
        # I think that "drop1" and "drop2" might have something to do with normal vs. rare drops (so bosses list the same item in both, but you only get one...)
        # TODO: Yeah, we really need to organize this...
        master_csvs_file += "# Add EXP to bosses but remove their drops (they're in the item pool)\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/monster\n"
        master_csvs_file += "id,exp,drop_content_id1,drop_content_id1_value,drop_content_id2,drop_content_id2_value\n"
        #master_csvs_file += "283,210,0,0,0,0\n"  # Karlabos - skipped
        master_csvs_file += "285,400,0,0,0,0\n"   # Siren
        master_csvs_file += "286,400,0,0,0,0\n"   # Siren (Undead)
        master_csvs_file += "287,530,0,0,0,0\n"   # Forza
        master_csvs_file += "288,530,0,0,0,0\n"   # Magissa
        master_csvs_file += "317,650,0,0,0,0\n"   # Shiva
        #master_csvs_file += "293,650,0,0,0,0\n"   # Ice Commander (already drops nothing)
        master_csvs_file += "54,1950,0,0,0,0\n"   # Ifrit (Note: 233 is also him, but I'm not sure why)
        master_csvs_file += "33,1950,0,0,0,0\n"   # Byblos (Note: 515 is also him; no idea why)
        master_csvs_file += "294,3070,0,0,0,0\n"  # Sandworm
        #master_csvs_file += "295,0,0,0,0,0\n"   # Hole (already drops nothing)
        #master_csvs_file += "364,3900,0,0,0,0\n"  # Cray Claw - skipped
        master_csvs_file += "296,4000,0,0,0,0\n"   # Adamantoise
        master_csvs_file += "300,4100,0,0,0,0\n"   # Soul Cannon
        #master_csvs_file += "371,4100,0,0,0,0\n"   # Launcher - skipped (leave drops/xp intact)
        master_csvs_file += "307,4100,0,0,0,0\n"   # Titan
        master_csvs_file += "306,4100,0,0,0,0\n"   # Chimera Brain
        master_csvs_file += "\n"

        # Keep "crystal" boss drops (and ramuh, etc.), but give them XP
        master_csvs_file += "# Add EXP to bosses (and keep their drops) if their items don't go into the item pool\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/monster\n"
        master_csvs_file += "id,exp\n"
        master_csvs_file += "281,200\n"   # Wing Raptor
        master_csvs_file += "282,200\n"   # Wing Raptor (Closed)
        master_csvs_file += "289,1120\n"  # Galura
        master_csvs_file += "290,1410\n"  # Liquid Flame
        master_csvs_file += "291,1410\n"  # Liquid Flame (Alt. Form 2)
        master_csvs_file += "292,1410\n"  # Liquid Flame (Alt. Form 3)
        master_csvs_file += "40,1500\n"   # Ramuh - should be in item pool but isn't (Note: he's also at 234)
        master_csvs_file += "301,4500\n"  # Archaeoavis
        master_csvs_file += "302,4500\n"  # Archaeoavis (Form 2)
        master_csvs_file += "303,4500\n"  # Archaeoavis (Form 3)
        master_csvs_file += "304,4500\n"  # Archaeoavis (Form 4)
        master_csvs_file += "305,4500\n"  # Archaeoavis (Form 5)
        master_csvs_file += "308,666\n"   # Purobolos (there's 6 of them, and they drop potions)
        master_csvs_file += "\n"

        # ...and give the bosses AP (via their encounters)
        master_csvs_file += "# Adjust boss AP amounts via their encounters\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/monster_party\n"
        master_csvs_file += "id,get_ap\n"
        master_csvs_file += "440,10\n"  # Wing Raptor
        #master_csvs_file += "441,10\n"  # Karlabos - skipped
        master_csvs_file += "442,10\n"   # Siren
        master_csvs_file += "443,11\n"   # Magissa and Forza - TODO: Confirm; this weird in the data.
        master_csvs_file += "444,13\n"   # Galura
        master_csvs_file += "498,20\n"   # Shiva (& Ice Commander)
        master_csvs_file += "445,15\n"   # Liquid Flame
        master_csvs_file += "654,16\n"   # Liquid Flame (Note: Unclear why this encounter exists, but its AP is consistent. I'm changing it, but giving it distinct AP so we can track it...)
        master_csvs_file += "655,17\n"   # Liquid Flame (Note: Unclear why this encounter exists, but its AP is consistent. I'm changing it, but giving it distinct AP so we can track it...)
        master_csvs_file += "495,20\n"   # Ifrit
        master_csvs_file += "447,20\n"   # Byblos
        #master_csvs_file += "77,20\n"   # Ramuh - skipped
        master_csvs_file += "448,15\n"   # Sandworm + Holes
        #master_csvs_file += "507,20\n"   # Cray Claw - skipped
        master_csvs_file += "449,15\n"   # Adamantoise
        master_csvs_file += "452,20\n"   # Soul Cannon & Launchers
        master_csvs_file += "453,20\n"   # Archeoaevis  (TODO: There's a *bunch* of these, no idea why)
        master_csvs_file += "456,20\n"   # Purobolos
        master_csvs_file += "455,20\n"   # Titan
        master_csvs_file += "454,20\n"   # Chimera Brain
        master_csvs_file += "\n"




        # Turn our json object into a string
        multiworld_data_file = json.dumps(multiworld_data, sort_keys=True, indent=2)

        # Create a path to the patched ".zip" file":
        file_path = os.path.join(output_directory, f"{self.multiworld.get_out_file_name_base(self.player)}.apff5pr")
        
        # Write our various small files into one big zip file
        APFF5PR = APFF5PRFile(file_path, player=self.player, player_name=self.multiworld.player_name[self.player])
        with zipfile.ZipFile(file_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as zf:
            zf.writestr("treasure_mod.csv", treasure_mod_file)
            zf.writestr("script_patch.csv", script_patch_file)
            zf.writestr("system_strings.csv", system_strings_file)
            zf.writestr("message_strings.csv", message_strings_file)
            zf.writestr("nameplate_strings.csv", nameplate_strings_file)
            zf.writestr("multiworld_data.json", multiworld_data_file)
            zf.writestr("master_csvs.json", master_csvs_file)
        
            APFF5PR.write_contents(zf)


# I guess this is how we indicate what our patch files look like?
class APFF5PRFile(APPatch):
    game = "Final Fantasy V PR"

    def get_manifest(self):
        manifest = super().get_manifest()
        manifest["patch_file_ending"] = ".apff5pr"
        return manifest




