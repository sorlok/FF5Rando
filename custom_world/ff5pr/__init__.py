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

from .Pristine import pristine_items, pristine_locations, pristine_regions, pristine_connections, pristine_game_patches, validate_pristine, custom_messages, PristineMultiworldLocationStart, PristineMultiworldLocationMagicNumber
from .Patches import all_patch_contents

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
            elif connectRule == "require_adamant":
                ruleFn = lambda state: self.require_adamant(state)
            elif connectRule == "require_fire_be_gone":
                ruleFn = lambda state: self.require_fire_be_gone(state)
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



    # Create the patch file
    def generate_output(self, output_directory: str) -> None:
        # If we shuffle entrances, we could write them here

        # Some stuff is required to interact with the multiworld server, or for general bookkeeping
        # We'll store this all into one big JSON object that the C# app can read and make use of
        multiworld_data = {}

        # The seed is displayed in a few places.
        multiworld_data['seed_name'] = self.multiworld.seed_name

        # We need to send unlocked "location_ids" to the other players
        # The only sane way to get these through the scripting system is to represent them as 
        #   items with very high content_ids (i.e., 9000000+), and to translate that to a location ID.
        # Since we control the location_ids, we can just add/subtract 9000000 to get this translation.
        multiworld_data['local_location_content_id_offset'] = PristineMultiworldLocationStart
        multiworld_data['local_location_content_num_incantation'] = PristineMultiworldLocationMagicNumber  # This will appear in the 'content_num'

        # TODO: The other one
        
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
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_10010/Map_10010/entity_default,/layers/[1]/objects/{id=259}/properties,map_id,int,211\n"
        treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_10010/Map_10010/entity_default,/layers/[1]/objects/{id=259}/properties,point_id,int,1\n"
        # Always allow "pull"-ing the switch in the Catapult
        treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_20231/Map_20231_4/ev_e_0224,/layers/[0]/objects/{id=30}/properties,script_id,int,2666\n"


        # TEMP: TODO
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/entity_default,/layers/[0]/objects/{id=23}/properties,direction,int,1\n"
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/entity_default,/layers/[0]/objects/{id=25}/properties,direction,int,1\n"
        #treasure_mod_file += "Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/entity_default,/layers/[0]/objects/{id=29}/properties,direction,int,1\n"
        # END TODO


        # Patch all Locations
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
            sys_call_name = None    # Do we need a SysCall to give the player this item (for us, it's just jobs)

            # Deal with multiworld items
            # Note that *we* own the location (always), but the *item* may be owned by anyone.
            if loc.item.player != self.player:
                # I think this is guaranteed
                if loc.address is None:
                    raise Exception(f"Invalid location; no address: {loc.name} for player: {loc.player}")

                # Convert the location to a faux "content_id" that we can pass through our system.
                content_id = loc.address
                content_num = PristineMultiworldLocationMagicNumber   # Magic number; "this is a multiworld item"
                sys_call_name = None   # We *could* do this, but it would limit where we can receive multiworld items. In the future, we can prob. elimiate these entirely.

                # ...and prompt the player
                message_key = f"RANDO_GOT_MULTIWORLD_ITEM_{len(extra_found_multiworld_item_messages)}"
                extra_found_multiworld_item_messages[message_key] = f"Found multiworld item: {loc.item}"

            # Deal with our own world's items
            else:
                # Item Received (NOT the original item at that location)
                pristine_item = GetPristine(loc.item)

                # How many of this item? (TODO: We can streamline this earlier in the code)
                content_id = pristine_item.content_id
                content_num = 1
                if content_id >= 9000:
                    content_num = loc.item.name.split(' ')[0]
                    if 'Gil' in loc.item.name:
                        content_id = 1
                    elif 'Potions' in loc.item.name:
                        content_id = 2
                    else:
                        raise Exception(f"BAD BUNDLE: {loc.item.name}")

                # What Message do we want to show? Hard-coding this a bit for now....
                # TODO: There are two "got an item" messages (one for "chests" and one for "found").
                # Additionally, there's "found a great sword in the water" that we can modify.
                message_key = 'T0003_01_01'  # "Found <ITEM>!"
                if content_id == 1:
                    message_key = 'T0003_03_01'  # "Found <NUM> gil."

                # Is there a SysCall associate with this (should only be Jobs)
                sys_call_name =  pristine_item.optattrs.get('SysCall')


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
                    # Is this a Progression item? It should be banned by our rules for now.
                    # TODO: Other-world items shouldn't be too hard; we'd also need to support crystals.
                    if loc.item.classification != ItemClassification.filler:
                        raise Exception(f"UNEXPECTED: PROGRESSION ITEM: {loc.item.name} AT CHEST LOCATION: {loc.name}")

                    parts = asset_path.split(':')
                    treasure_mod_file += f"{parts[0]},{parts[1]},{content_id},{content_num},{message_key}\n"
                    continue

                # 2. Right now, we don't support adding anything to Script Events.
                # TODO: Give Crystals at these locations.
                # TODO: Eventually give items too!
                else:
                    # Jobs
                    if sys_call_name is not None:
                        # We overwrite with SysCall to add the job
                        parts = asset_path.split(':')
                        script_patch_file += f"{parts[0]},{parts[1]},Nop:{pristine_location.optattrs['Label']},Overwrite,0\n"
                        script_patch_file += "[" + GetJsonSysCallObj(sys_call_name) + "]\n\n" # Two newlines are necessary
                        continue

                    # Pretty much anything without 'optattrs' is implicitly added via 'GetItem'
                    if True:  #loc.item.classification == ItemClassification.filler:
                        # TODO: Need to check and handle MultiWorld a special way here...

                        # We use GetItem here
                        parts = asset_path.split(':')
                        script_patch_file += f"{parts[0]},{parts[1]},Nop:{pristine_location.optattrs['Label']},Overwrite,0\n"
                        script_patch_file += "[" + GetJsonItemObj(content_id, content_num) + "]\n\n" # Two newlines are necessary
                        continue
                    
                    # What's left?
                    raise Exception(f"Unexpected item type for: {loc.item.name} at {loc.name}")



        # Add our extra messages
        for key, val in extra_found_multiworld_item_messages.items():
            message_strings_file += f"{key},{val}\n"
            nameplate_strings_file += f"{key},\n"



        # TODO:
        #patch_rom(self, rom)

        # TODO: AP_68495769440403234312_P1_Sorlok

        #rom.update_header()
        #patch_data = create_patch_file(rom, self.random)
        #rom.restore()

        #apz5 = OoTContainer(patch_data, outfile_name, output_directory,
        #    player=self.player,
        #    player_name=self.multiworld.get_player_name(self.player))
        #apz5.write()

        # Turn our json object into a string
        multiworld_data_file = json.dumps(multiworld_data, sort_keys=True, indent=2)

        # Create a path to the patched ".zip" file":
        file_path = os.path.join(output_directory, f"{self.multiworld.get_out_file_name_base(self.player)}.apff5pr")
        
        # Write our various small files into one big zip file
        APFF5PR = APFF5PRFile(file_path, player=self.player, player_name=self.multiworld.player_name[self.player])
        with zipfile.ZipFile(file_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as zf:
            zf.writestr("treasure_mod.csv", treasure_mod_file)
            zf.writestr("script_patch.csv", script_patch_file)
            zf.writestr("message_strings.csv", message_strings_file)
            zf.writestr("nameplate_strings.csv", nameplate_strings_file)
            zf.writestr("multiworld_data.json", multiworld_data_file)
        
            APFF5PR.write_contents(zf)


# I guess this is how we indicate what our patch files look like?
class APFF5PRFile(APPatch):
    game = "Final Fantasy V PR"

    def get_manifest(self):
        manifest = super().get_manifest()
        manifest["patch_file_ending"] = ".apff5pr"
        return manifest




