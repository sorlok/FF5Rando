import Utils
import os
import settings
import base64
import json
import threading
import requests
import zipfile
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import add_rule, add_item_rule
from worlds.Files import APPatch
from BaseClasses import Tutorial, MultiWorld, ItemClassification, LocationProgressType, Item, Location, Region, CollectionState

from .Options import FF5PROptions
from .Pristine import pristine_items, pristine_locations, pristine_regions, pristine_connections, pristine_shops, optional_split_shops, pristine_game_patches, validate_pristine, custom_messages, get_all_item_names, normalize_item_name, parse_jumbo_items, PristineMultiworldItemStart, JumboItemStartID, ShopLocationStart, CurrMaxContentId, MaxProductId, MaxProductGroupId
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
        if data.loc_id is None:
            location = FF5PRLocation(world.player, name, EventId, res)
            location.place_locked_item(FF5PRItem(data.event_item, EventClassification, EventId, world.player))
            if 'CompletionCondition' in data.tags:
                completion_items.append(data.event_item)
        else:
            location = FF5PRLocation(world.player, name, data.loc_id, res)

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


# Helper: Retrieve a shop object from either the pristine list or the optional list
def get_pristine_shop(shopName: str):
    if shopName in pristine_shops:
        return pristine_shops[shopName]
    return optional_split_shops[shopName]


# Create a given Shop Locations
def create_shop(world: World, shopName: str, itemName: str, locId: int):
    # Find the Region
    region = None
    for rg in world.multiworld.regions:
        if rg.name == get_pristine_shop(shopName).region:
            region = rg
            break
    if region is None:
        raise Exception(f"Shop referenced invalid region: {get_pristine_shop(shopName).region}")

    # Make the Location
    locName = f"{shopName}: {itemName}"
    location = FF5PRLocation(world.player, locName, locId, region)
    location.progress_type = LocationProgressType.DEFAULT  # TODO: MultiWorld options are different
    # TODO: Call add_rule() if you need it. Right now I don't think anything blocks shops (beyond normal Region access)?

    # Don't allow Gil to be sold in shops
    ruleFn = lambda item: world.dont_sell_gil(item)
    add_item_rule(location, ruleFn)

    # Include it!
    region.locations.append(location)




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

    # List of shop items that will actually function as Locations
    #   { (shopName, origItemName) => LocationId, ... }
    shop_checks = {}

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
    location_name_to_id = { name: data.loc_id for name, data in pristine_locations.items() if data.loc_id is not None }

    # Shop Slots count as Locations too...
    # TODO: It's going to be a pain to keep track of these once we start making them more dynamic (via Options)
    # TODO: Copied code (making the shop name, calculating the location ID, etc.)
    for shop_dict in [pristine_shops, optional_split_shops]:
        for shopName,data in shop_dict.items():
            for itemName,prodId in data.items.items():
                locName = f"{shopName}: {itemName}"
                location_name_to_id[locName] = ShopLocationStart + prodId
    
    options_dataclass = FF5PROptions

    web = FF5PRWebWorld()
 
    def __init__(self, world: MultiWorld, player: int):
        super().__init__(world, player)


    # Some access rules
    # TODO: Move to the .Rules file... but how to get playerID in that case?
    def require_world_1_teleport(self, state: CollectionState) -> bool:
        return state.has("W1Teleport", self.player)
    def require_10_jobs(self, state: CollectionState) -> bool:
        return state.has_group("Job", self.player, 10)
    def require_adamant(self, state: CollectionState) -> bool:
        return state.has("Adamantite", self.player)
    def require_fire_be_gone(self, state: CollectionState) -> bool:
        return state.has("FireBeGone", self.player)

    # Some item rules
    def dont_sell_gil(self, item: Item) -> bool:
        return not item.name.endswith(' Gil')



    # Called before any other randomization step.
    # We'll use this to decide which Shop items count as Locations
    def generate_early(self):
        # Turn Shops into Locations
        if self.options.add_shop_locations:
            for shopName in sorted(pristine_shops.keys()):
                shop = pristine_shops[shopName]
                for itemName in sorted(shop.items.keys()):
                    productId = shop.items[itemName]
                    self.shop_checks[(shopName, itemName)] = ShopLocationStart + productId

        # ...and optionally split shops that have shared inventories
        if self.options.split_shared_shops:
            for shopName in sorted(optional_split_shops.keys()):
                shop = optional_split_shops[shopName]
                for itemName in sorted(shop.items.keys()):
                    productId = shop.items[itemName]
                    self.shop_checks[(shopName, itemName)] = ShopLocationStart + productId



    # Helper: Retrieve a region object
    def getRegion(self, regionName):
        for region in self.multiworld.regions:
            if region.player == self.player and region.name == regionName:
                return region
        return None

    # Place this world's Regions and their Locations in the multiworld regions list
    # TODO: Dispatch to .Region.create_regions()
    def create_regions(self):
        # TODO: Put this as early as possible
        if self.options.validate_pristine_data:
            validate_pristine()

        # Create all regions, and their child locations
        completion_items = []
        for region_name, region_data in pristine_regions.items():
            create_region(self, region_name, region_data.locations, completion_items, self.options.prog_items_in_chests)

        # Make shop locations
        for shopPair,locId in self.shop_checks.items():
            create_shop(self, shopPair[0], shopPair[1], locId)

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

        # Build a lookup of Shop Locations
        shop_lookup = {} # LocationName -> (ShopName, ItemName)
        for shopPair in sorted(self.shop_checks.keys()):
            locName = f"{shopPair[0]}: {shopPair[1]}"
            shop_lookup[locName] = (shopPair[0], shopPair[1])

        # By default, we add the original set of items to the item pool.
        # In other words, if Chest X contains a Potion and Chest Y contains an Ether, add a Potion then an Ether
        for region in self.multiworld.regions:
            if region.player == self.player:  # I think this is right?
                for location in region.locations:
                    # Is this a shop?
                    if location.name in shop_lookup:
                        shopPair = shop_lookup[location.name]
                        #shopName = shopPair[0]
                        itemName = shopPair[1]
                        new_item = self.create_item(itemName)
                        items.append(new_item)
                    else:
                        pristine_location = GetPristine(location)
                        if pristine_location.loc_id is not None:   # Not an "Event" location+item
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


    # Retrieve a JSON serialized string that we'll pass on to our Client to handle specific MultiWorld stuff
    #   (player name, seed, etc.)
    # @special_items_str - { itemId -> [pseudoItem, pseudoItem, ...]}  (but in string format)
    #   pseudoItems can be: ['item', content_id, content_num] or ['job', job_id] or ['remote', location_id]
    # @mundane_prog_items - [contentId, contentId, ...]
    #   These are *normal* game items (like Adamantite) that are used for Progression (so we should not allow the player to buy >1 of them)
    def serialize_multiworl_data(self, location_cid_to_item_cid, special_shop_str, special_items_str, mundane_prog_items):
        res = {}

        # The seed is displayed in a few places.
        res['seed_name'] = self.multiworld.seed_name

        # This is in Archipelago.json, but might as well copy it here in case they change that.
        res['player_name'] = self.multiworld.get_player_name(self.player)

        # NOTE: When we receive items, we are given a list of NetworkItems, which contain an item ID
        # Since we control the ItemId, we should be able to just subtract 3000000 to get the content_id
        res['remote_item_content_id_offset'] = PristineMultiworldItemStart

        # Mapping of non-standard items to their actions.
        # This could be a Remote item, a Jumbo item, etc.
        res['item_cid_to_action'] = '@@SPECIAL_ITEM_STR@@'

        # Shop reverse lookup is similar
        res['shop_item_to_location_revlookup'] = '@@SPECIAL_SHOP_STR@@'

        res['mundane_prog_items'] = mundane_prog_items

        res['location_cid_to_item_cid'] = location_cid_to_item_cid

        # Turn our json object into a string
        res = json.dumps(res, sort_keys=True, indent=2)

        # Substitute our magic formatted values
        res = res.replace('"@@SPECIAL_ITEM_STR@@",', "{\n"+special_items_str+"\n  },", 1)
        res = res.replace('"@@SPECIAL_SHOP_STR@@"', "{\n"+special_shop_str+"\n  }", 1)    # NOTE: No comma, since it's the last element for now...

        return res


    # Write our set of custom messages, along with any extra that were generated along the way
    def write_custom_messages(self, extra_messages):
        message_strings = "Assets/GameAssets/Serial/Data/Message/story_mes_en\n\n"
        nameplate_strings = "Assets/GameAssets/Serial/Data/Message/story_cha_en\n\n"
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
                newMsg = f"Welcome to the randomizer! Your seed is: {self.multiworld.seed_name}"

            # Write the message
            message_strings += f"{key},{newMsg}\n"

            # Write the nameplace (default to empty string)
            name_str = custom_messages['Assets/GameAssets/Serial/Data/Message/story_cha_en'].get(key,'')  # TODO: Better abstraction
            nameplate_strings += f"{key},{name_str}\n"

        # Add our extra messages
        for key, val in extra_messages.items():
            if not isinstance(val, list):
                val = ['', val]
            message_strings += f"{key},{val[1]}\n"
            nameplate_strings += f"{key},{val[0]}\n"

        return message_strings, nameplate_strings


    # The goal here is to map every Location to a simple "item ID" that refers to "whatever you get at that location",
    #   so that we don't need to play around with content_count, or other misdirections.
    def gen_pre_process_locations(self, location_cid_to_item_cid, item_cid_to_action, item_cid_to_msg_desc):
        APCustomIcon = '<IC_BRS>'
        JobCustomIcon = '<IC_GMB>'
        JumboCustomIcon = '<IC_SCR>'

        #remote_id = RemoteIdStart
        for loc in self.get_locations():
            # Skip Event Items; they are meant to be built in to the Game Engine (or just abstractions)
            if loc.item.code is None:
                continue

            # I think this is guaranteed
            if loc.address is None:
                raise Exception(f"Invalid location; no address: {loc.name} for player: {loc.player}")

            # A Location is its own content_id, but we need to force 1 extra layer of abstraction here.
            # So, we must track which item (by content_id) this Location refers to. That is needed in case
            #   we are given this Item (by content_id) from a remote user or an admin.
            # If we open the Chest, we'll be given the Location ID, which we are required to report to the server,
            #   hence we also need the map from Location (cid) to Item (cid).
            loc_cid = loc.address

            # Determine progression type (for our description)
            progType = 'Filler'
            if (loc.item.classification & ItemClassification.progression) != 0:
                progType = '<color="#ffff00">Progression</color>'

            # Deal with items in *our* Locations that are destined for *other* players
            # Note that *we* own the location (always), but the *item* may be owned by anyone.
            if loc.item.player != self.player:
                # Our locations that we send to a Remote player can never be "sent" to us, so we don't need
                #   a parallel item_content_id here ---just refer to yourself...
                location_cid_to_item_cid[loc_cid] = loc_cid

                # ...and then add an Action for your own location_content_id
                item_cid_to_action[loc_cid] = ['remote']
                item_cid_to_msg_desc[loc_cid] = [
                  f"{APCustomIcon}AP: {loc.item.name}",
                  f"Gain an item for {self.multiworld.player_name.get(loc.item.player, f"Player {loc.item.player}")} [{progType}]",
                ]

            # Deal with items in *our* Locations that are that are destined for *us*
            else:
                # Item Received (NOT the original item at that location)
                # We must add Item Actions later, since this loop doesn't see remote-sourced items.
                item_id = loc.item.code - PristineMultiworldItemStart
                location_cid_to_item_cid[loc_cid] = item_id


        # Add Actions for all of our Items. This is needed regardless of whether we get these items from our own world or another's
        for item in self.multiworld.itempool:
            if item.player == self.player and item.code is not None:
                # The item's ID (as our game refers to it)
                item_id = item.code - PristineMultiworldItemStart

                # We must skip remote items; we've already dealt with them.
                # TODO: Isn't this already guaranteed by the item.player == self.player?
                # TODO: Ah, I see, we need to *NOT* add our "remote" items to the pool, or whatever it is we do?
                #if item_id in item_cid_to_action:
                #    continue

                # Mundane vs. jumbo vs. job
                # TODO: If we add Jumbo items for everything AND use the RANDO_GOT_ style messages, we can simplify all this.
                if item.name in pristine_items and 'Job' not in pristine_items[item.name].tags:
                    # Mundane; no special action.
                    # Item descriptions for mundane+progression (like Adamantite) will have "[Progression]" added manually (for now)
                    # TODO: Maybe put an 'item' entry in item_id_to_action and then filter it later?
                    pass
                elif item.name in pristine_items and 'Job' in pristine_items[item.name].tags:  # TODO: simplify, once we check the TEST above
                    # TODO: This is annoying right now...
                    #       We can probably pull most of this logic up into Pristine itself (have every item report its 'action')
                    subItems = parse_jumbo_items(item.name)
                    if len(subItems)!=1 or not subItems[0][1].startswith('Job:'):
                        raise Exception("Bad jumbo job: {item.name}")
                    pristine_item = pristine_items[subItems[0][1]]
                    item_cid_to_action[item_id] = ['job', pristine_item.optattrs['JobId']]
                    item_cid_to_msg_desc[item_id] = [
                      f"{JobCustomIcon}{item.name}",
                      f"Unlock the {item.name}",
                    ]
                else:  # This is a Jumbo item
                    # List of [content_id, content_num]
                    subItems = parse_jumbo_items(item.name)
                    values = []

                    # TODO: This is also annoying...
                    for entry in subItems:
                        if entry[1].startswith('Job:'):
                            raise Exception("Bad jumbo non-job: {item.name}")
                        pristine_item = pristine_items[entry[1]]
                        values.append(pristine_item.content_id)  # content_id
                        values.append(entry[0])  # content_num

                    item_cid_to_action[item_id] = ['jumbo'] + values
                    item_cid_to_msg_desc[item_id] = [
                      f"{JumboCustomIcon}{item.name}",
                      f"A bundle of your favorite items!",
                    ]


    # Generate any scaffolding related to our new "faux" items
    #
    # TODO: We actually have to make proper text/descriptions for these, since they will show up in shops *before* we buy them.
    #
    def gen_pre_process_faux_items(self, location_cid_to_item_cid, item_cid_to_action, item_cid_to_msg_desc, system_extra_messages):
        res = ''

        # In case we mess up, it is better to have some glitch item than it is to crash. Thus, the second
        #   thing we do is to create Items for each of the pseudo-items in the previous list. If we mess up our 
        #   Client code (and the Client tries to actually give the pseudo-item to the player), they'll at least 
        #   be given something they can see in their menu, instead of crashing outright.
        res += "# Faux Items; these should never be in the player's inventory, but if we mess up it's better not to crash\n"
        res += "Assets/GameAssets/Serial/Data/Master/content\n"
        res += "+id,mes_id_name,mes_id_battle,mes_id_description,icon_id,type_id,type_value\n"
        for item_id in sorted(item_cid_to_action.keys()):
            # Does our 'new' item actually already exist?
            if item_id <= CurrMaxContentId:
                raise Exception(f"Faux Item actually exists: {item_id} => {action}")

            # TODO: If this item is sold in a shop, we need to find the 'type' of the shop (item, weapon, etc.)
            #       and modify the "for show" item that we're referencing. We do not actually need 1 new item/weapon/etc. for 
            #       each of these "for show" items, since we never actually get them anyway.
            # TODO: Probably easier to put this into 'item_cid_to_msg_desc', since it's based on the Location... and I guess it won't work
            #       for normal items anyway  ---but it's possible we'll add an option to keep "Magic" in "Magic" shops, etc...
            forShowItemType = 1   # "Items"
            forShowItemId = 59    # Our custom for-show "Item"
            itemNameKey = f"MSG_RANDO_FAUX_ITEM_NAME_{len(system_extra_messages)}"
            itemDescKey = f"MSG_RANDO_FAUX_ITEM_DESC_{len(system_extra_messages)}"
            res += f"{item_id},{itemNameKey},None,{itemDescKey},0,{forShowItemType},{forShowItemId}\n"

            # Add the message too!
            msg_and_desc = item_cid_to_msg_desc[item_id]
            system_extra_messages[itemNameKey] = msg_and_desc[0]
            system_extra_messages[itemDescKey] = msg_and_desc[1]
        res += "\n"

        # Add our shared string for mundane "local" items
        itemNameKey = f"MSG_RANDO_FAUX_LOCAL_ITEM_NAME"
        itemDescKey = f"MSG_RANDO_FAUX_LOCAL_ITEM_DESC"
        system_extra_messages[itemNameKey] = "<IC_MCN>ERROR: Mundane Local Item"
        system_extra_messages[itemDescKey] = "If you're seeing this, we messed something up."

        # We add a separate patch for "local" items (Locations), to keep things organized
        res += "# Faux Mundane Item Locations; these also exist to avoid crashing in case of mistakes\n"
        res += "Assets/GameAssets/Serial/Data/Master/content\n"
        res += "+id,mes_id_name,mes_id_battle,mes_id_description,icon_id,type_id,type_value\n"
        for loc_id in sorted(location_cid_to_item_cid.keys()):
            # Have we already procesed this (as a Remote item)?
            if loc_id in item_cid_to_action:
                continue
            
            # Note: Local mundane items are never sold in shops, so they can all share the same description/name.
            # We *really* should never see these.
            res += f"{loc_id},{itemNameKey},None,{itemDescKey},0,1,59\n"   # Just use "Item" number "59" as a template
        res += "\n"

        return res


    # Determine how to show the "you got an item" message for a given item+action
    def gen_pre_location_msg(self, action, loc, extra_messages):
        # Construct the message_key
        if action is None or action[0]=='item':  # We may eventually add item (not itemS) for 1x Mundane items
            # There is also 'T0003_03_01' => 'Found <NUM> gil.', but we'd only get that with Jumbo items.
            # And there's the single "Found a Great Sword in the water". We can play with these later.
            return 'T0003_01_01'  # "Found <ITEM>!"
        elif action[0] == 'remote':
            # NOTE: Some of these, like the Crystal Shrine rooms, will never be used by our game.
            #       The reason for this is that anything that gives out multiple *Locations* (NOT multiple *Items*)
            #       will automatically aggregate those into a single text box.
            #       We leave these extra messags here on the off chance that something references them.
            res = f"RANDO_GOT_MULTIWORLD_ITEM_{len(extra_messages)}"
            extra_messages[res] = f"Found multiworld item: {loc.item}"
            return res
        elif action[0] == 'job':
            res = f"RANDO_GOT_JOB_ITEM_{len(extra_messages)}"
            extra_messages[res] = f"Unlocked: {loc.item.name}"
            return res
        elif action[0] == 'jumbo':
            res = f"RANDO_GOT_JUMBO_ITEM_{len(extra_messages)}"
            extra_messages[res] = f"Found: {loc.item.name}"
            return res
        else:
            raise Exception(f"Unknown action: {action} at Location: {loc}")


    # Helper: Set an Item/Ability cost (in gil) for things that might end up in shops at some point.
    # Returns a string that can be appended to master_csvs_file
    def fix_shop_no_costs(self):
        res = ""

        # Set a default cost for items that cost 0 gil (otherwise they will crash the game when you buy them)
        res += "# Default cost for items that normally cost nothing\n"
        res += "Assets/GameAssets/Serial/Data/Master/item\n"
        res += "id,buy\n"
        res += "46,100\n"   # Adamantite
        res += "\n"
        #
        res += "# Default cost for abilities that normally cost nothing\n"
        res += "Assets/GameAssets/Serial/Data/Master/ability\n"
        res += "id,buy\n"
        res += "165,100\n"  # Shiva
        res += "166,100\n"  # ...
        res += "167,100\n"
        res += "168,100\n"
        res += "169,100\n"
        res += "170,100\n"
        res += "171,100\n"
        res += "172,100\n"
        res += "173,100\n"
        res += "174,100\n"
        res += "175,100\n"
        res += "176,100\n"  # Bahamut
        res += "383,100\n"  # Doom (Blue Magic)
        res += "384,100\n"  # ...
        res += "385,100\n"
        res += "386,100\n"
        res += "387,100\n"
        res += "388,100\n"
        res += "389,100\n"
        res += "390,100\n"
        res += "391,100\n"
        res += "392,100\n"
        res += "393,100\n"
        res += "394,100\n"
        res += "395,100\n"
        res += "396,100\n"
        res += "397,100\n"
        res += "398,100\n"
        res += "399,100\n"
        res += "400,100\n"
        res += "401,100\n"
        res += "402,100\n"
        res += "403,100\n"
        res += "404,100\n"
        res += "405,100\n"
        res += "406,100\n"
        res += "407,100\n"
        res += "408,100\n"
        res += "409,100\n"
        res += "410,100\n"
        res += "411,100\n"
        res += "412,100\n"   # Missile (Blue Magic)
        res += "\n"

        return res



    # Create the patch file
    # The way Items and Locations interact with the game is complicated enough that I've had to basically
    #  rewrite the logic here three times. In order to avoid a fourth rewrite, I'm going to document
    #  the specifics of that behavior here.
    # Behavior + Constraints:
    #   * When you open a Chest (also: Shop/Boss/etc.), you mark a "Location".
    #   * Both Remote and Local Locations must be sent to the server. Local Locations also give you the item.
    #     * Caveat: We ban the server from sending us our own Local items back. We *could* accept this, but it breaks shops.
    #   * When you get a Remote item from the server, it is an Item ID. This is the *AP* concept of an item.
    #   * Some of our Items are things like Jobs or Jumbos, so we need to be able to translate Location -> AP Item -> Our Item(s)
    #   * Locations all have unique IDs, but it's possible for 3 different Locations to refer to the same Item (by ID). So we can't
    #     just rely on Item ID to differentiate Checks.
    # My Approach:
    #   * Every Chest (etc.) will give the Location ID as an Item. We will ensure that our Location IDs start >1690 (max Content ID)
    #     * We will make a fake Content entry for every Location ID, as a failsafe against crashing.
    #   * We will create a Mapping of Location ID -> AP Item ID, and store it in the custom patch data.
    #     * The "AP Item ID" will just be the current Item ID. So, the actual Item ID for mundane items, the Jumbo Item ID for Jumbos,
    #       Jobs, etc. We will *remove* the faux items for Jobs, Jumbos, etc., since it will never be relevant.
    #   * We can use the existing Mapping of Item ID -> Action mostly as-is; we just need to remove the "Location ID" from "Remote".
    #     * When a player opens a Chest, send that Location to the server, and lookup and perform the Action (unless Remote). Don't let them
    #       acquire the faux "Location Item".
    #   * Shops won't work this way (they'd only let you buy 1 of each Item that's a Location), so we can do this instead:
    #     * Shops selling Locations that are mundane items will just list the mundane item. NOTE: This means we can have one shop
    #       selling two "Potion" Location checks!
    #     * We will store a mapping of { ProductGroup -> { ItemId -> [Location, Location,...] } }, which maps items in shops to Locations
    #     * When the player buys N of Item X, we will mark off "N" of the Locations in this store's lookup for Item X. If we've already 
    #       marked them all, just do nothing (let them buy the item).
    #       * We can accomplish this by checking the "Locations sent to server" Dictionary; we don't need to store additional data.
    def generate_output(self, output_directory: str) -> None:
        # If we need to put hints in message boxes, do this:
        #if self.hints != 'none':
        #    self.hint_data_available.wait()

        #
        # We have a series of output 'files', but we'll keep them in-memory to make zipping simpler.
        #


        # Prepare a file that contains all of our game-modifying patches. 
        # These will be applied before anything else is patched.
        script_patch_file = "# These patches are applied before any later item-modifying patches.\n\n"
        for name in pristine_game_patches:
            script_patch_file += all_patch_contents[name]
        script_patch_file += "\n\n# These patches are applied last; they modify the actual items being placed\n\n"



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

        # Will contain *all* .csv patches
        master_csvs_file = ""

        # Set a default cost for items that cost 0 gil (otherwise they will crash the game when you buy them)
        master_csvs_file += self.fix_shop_no_costs()

        # When we get multiworld items, we want to show a meaningful message box.
        # To do that, we'll need to pad the system message list with a bunch of extra messages, since each one is unique.
        extra_messages = {}   # { key -> value } (nameplate is empty) OR { key -> [nameplate, value] }
        system_extra_messages = {}  # Same, but for 'system', and nameplates are not supported

        # We patch a few of these to list 'Progression' (which is useful if they're in shops)
        # If we end up with lots of these, we may want some kind of "Append" logic for messages.
        system_extra_messages['MSG_KEY_INF_07'] = 'A particularly hard precious metal.' + ' [<color="#ffff00">Progression</color>]'

        # Build a lookup of Shop Locations
        # TODO: This is duplicated code; we need a better lookup for Shop Locations
        shop_lookup = {} # LocationName -> (ShopName, ItemName)
        for shopPair in sorted(self.shop_checks.keys()):
            locName = f"{shopPair[0]}: {shopPair[1]}"
            shop_lookup[locName] = (shopPair[0], shopPair[1])

        # Keep track of which product_groups we've seen
        prod_groups = {}   # product_group -> shopName


        # The first thing we need to do is to create a mapping from (location) -> content_id
        # The Location ID will be tied to the Chest, Boss, etc. The content_ID will further be mapped to
        #   either a mundane item or an Action. Neither will be visible to the FF5 game engine, but we may
        #   create Faux items for all of these, just to avoid potential crashes in case we mess up.
        # I *think* you should be able to call "GetItem()" on either a Location ID or a Content ID,
        #   and the game engine will fill in the blanks to give you the *actual* item you need.
        location_cid_to_item_cid = {}  # content_id_of_location -> content_id_of_item
        item_cid_to_action = {}        # content_id_of_item -> [item_type, param1, param2...] ; this now includes "mundane" items
        item_cid_to_msg_desc = {}      # content_id -> [content_name_msg, content_desc_msg] ; the text you'll see when you are in a shop that has this item
                                       # TODO: Should only need to be items, since we don't put Locations in stores as-is. Won't need to be mundane either.
        self.gen_pre_process_locations(location_cid_to_item_cid, item_cid_to_action, item_cid_to_msg_desc)
        master_csvs_file += self.gen_pre_process_faux_items(location_cid_to_item_cid, item_cid_to_action, item_cid_to_msg_desc, system_extra_messages)

        # Make a list of mundante items that are also Key+Progression items in game. 
        # These are typically plot items (like the Adamantite) that you might now see in stores (via rando magic)
        mundane_prog_items = []
        for name in sorted(pristine_items.keys()):
            entry = pristine_items[name]
            if (entry.classification.lower() == 'progression') and ('KeyItem' in entry.tags) and ('Job' not in entry.tags) and ('WorldTeleport' not in entry.tags):
                mundane_prog_items.append(entry.content_id)

        # Patch all of *our* Locations
        shop_item_to_location_revlookup = {}  # (product_group,item_cid) -> [location_cid, location_cid, ...] ; used when we buy "item_cid" in Shop 'product_group'; we need to tell the Server which Location we triggered.
        shop_adds_txt = {}  # If we make new shops, their products will need new entries (product_id -> line)
        shop_changes_txt = {}  # We'll append these all at once, later (product_id -> line)
        for loc in self.get_locations():
            # Skip Event Items; they are meant to be built in to the Game Engine (or just abstractions)
            if loc.item.code is None:
                continue

            # Is this a shop?
            shopPair = None
            if loc.name in shop_lookup:
                shopPair = shop_lookup[loc.name]

            # What we need in order to populate our struct
            loc_cid = loc.address
            item_cid = location_cid_to_item_cid[loc_cid]
            action = item_cid_to_action.get(item_cid)  # May be None for mundane items
            message_key = self.gen_pre_location_msg(action, loc, extra_messages)

            # Shops are modified differently than treasure chests/NPCs/scripts
            if shopPair is not None:
                # Get the original shop object
                orig_shop = get_pristine_shop(shopPair[0])
                product_id = orig_shop.items[shopPair[1]]

                #print("BLAH:",shopPair)
                #print("   >>",loc.item)
                #print("   >>",item_id)   # Oops, this is a Faux Location ID (if remote)!
                #print("   >>",product_id)  # Product ID

                # Track the product group
                prod_groups[orig_shop.product_group] = shopPair[0]

                # Alter the existing Product entry. (New Product entries should have already been added by now.)
                # NOTE: purchase_limit prevents buying more than 1 in a single "buy" action --we set it to 1 so
                #       that players can't buy 10x of a Job (for example). It does *not* prevent you from buying 
                #       that same item again from the shop right away.
                #       For coefficient, we subtract 1 from the cost, since the default item cost (that we set) 
                #       is 1 --if we set it to 0, then the shop menu will crash.
                cost = 0
                max_buy = 0
                if action is not None:  # Remote, Jumbo, etc.
                    cost = 100 - 1  # TODO: Determine this somehow
                    max_buy = 1     # TODO: Probably fine for Jumbos?

                # Special case for Adamantite
                # TODO: We already have the "mundane items" list --- use it here!
                if item_cid == 47:  # Adamantite
                    max_buy = 1

                # Add vs. edit
                if product_id > MaxProductId:
                    shop_adds_txt[product_id] = f"{product_id},{item_cid},{orig_shop.product_group},{cost},{max_buy}\n"   # id,content_id,group_id,coefficient,purchase_limit
                else:
                    shop_changes_txt[product_id] = f"{product_id},{item_cid},{cost},{max_buy}\n"   # id,content_id,coefficient,purchase_limit

                # Update our reverse lookup
                shop_item_to_location_revlookup.setdefault((orig_shop.product_group,item_cid), []).append(loc_cid)


            # Non-shops are simple: we always patch them with their own Location (content) ID
            else:
                # Original data for this location
                pristine_location = GetPristine(loc)

                # TODO: We also need to make a "you found <num> <item>s!" and "treasure chest contained <num> <item>s!"
                #       messages. We can make this part of some patch; this is needed since the NPC "5 Potions", etc., can be
                #       given to the party via Treasure. For now, it "works", though (just wrong message); we'll tidy this up later.

                # There can (rarely) be multiple parallel game maps for this Location; it's assumed game logic will handle keeping them aligned.
                # NOTE: I'm referring to the Flying Ronka Ruins here, which has duplicated maps for some reason.
                asset_paths = pristine_location.asset_path
                if not isinstance(asset_paths, list):
                    asset_paths = [asset_paths]
                for asset_path in asset_paths:
                    # 1. Is this a simple chest? (No event; part of entity_default?)
                    if 'entity_default' in asset_path:
                        parts = asset_path.split(':')
                        treasure_mod_file += f"{parts[0]},{parts[1]},{loc_cid},1,{message_key}\n"
                        continue

                    # 2. Use GetItem for SysCall in scripts AND for GetItem in scripts
                    else:
                        # We use GetItem here
                        parts = asset_path.split(':')
                        script_patch_file += f"{parts[0]},{parts[1]},Nop:{pristine_location.optattrs['Label']},Overwrite,0\n"
                        script_patch_file += "[" + GetJsonItemObj(loc_cid, 1) + "]\n\n" # Two newlines are necessary

        # Patch all events that open shops (to open the correct product_group)
        # This may overwrite a product_group with the same value, but that's fine.
        if len(prod_groups) > 0:
            #new_pg_id = MaxProductGroupId+1  # Any new product_group will start at this number
            prod_group_adds_txt = {}      # Additional entries in the txt file (prod_group -> line)
            prod_group_changes_txt = {}   # Changes to the txt file (prod_group -> line)
            for prod_group, shopName in prod_groups.items():
                # Retrieve the shop
                shop = get_pristine_shop(shopName)
                asset_path = shop.asset_path

                # New product group?
                # Patch existing ones anyway, in case we want to change their name (e.g., "Tule Weapon Shop")
                msg_key = f"RANDO_PROD_GROUP_NAME_{len(system_extra_messages)}"
                if prod_group > MaxProductGroupId:
                    prod_group_adds_txt[prod_group] = f"{prod_group},{msg_key}\n"    # id,mes_id_name
                else:
                    prod_group_changes_txt[prod_group] = f"{prod_group},{msg_key}\n"    # id,mes_id_name
                system_extra_messages[msg_key] = shop.pgroup_name

                # ...and, patch the script
                orig_shop = get_pristine_shop(shopPair[0])
                product_id = orig_shop.items[shopPair[1]]
                parts = shop.asset_path.split(':', 1)
                treasure_mod_file += f"{parts[0]},{parts[1]},product_group_id,int,{prod_group}\n"

            # TODO: Also.... we should structure this as "map locationId -> itemId" (including creating jumbos, etc.), 
            #       and then "do the thing with the locationId". And then just PUT THE LOCATIOn->ACTION MAPPING INTO
            #       the in-game map! It's way too unwieldy otherwise.

            # Patch in any new product groups
            if len(prod_group_adds_txt) > 0:
                master_csvs_file += "# Add new product_groups for new stores\n"
                master_csvs_file += "Assets/GameAssets/Serial/Data/Master/product_group\n"
                master_csvs_file += "+id,mes_id_name\n"  # Note the '+'
                for prod_group in sorted(prod_group_adds_txt.keys()):
                    line = prod_group_adds_txt[prod_group]
                    master_csvs_file += line
                master_csvs_file += "\n"

            # ...and overwrite any existing ones
            if len(prod_group_changes_txt) > 0:
                master_csvs_file += "# Change product group names for existing stores\n"
                master_csvs_file += "Assets/GameAssets/Serial/Data/Master/product_group\n"
                master_csvs_file += "id,mes_id_name\n"    # Note: no '+'
                for prod_group in sorted(prod_group_changes_txt.keys()):
                    line = prod_group_changes_txt[prod_group]
                    master_csvs_file += line
                master_csvs_file += "\n"

        # Patch all shop Product additions
        if len(shop_adds_txt) > 0:
            master_csvs_file += "# Add new Product (shop) entries\n"
            master_csvs_file += "Assets/GameAssets/Serial/Data/Master/product\n"
            master_csvs_file += "+id,content_id,group_id,coefficient,purchase_limit\n"
            for prod_id in sorted(shop_adds_txt.keys()):
                line = shop_adds_txt[prod_id]
                master_csvs_file += line
            master_csvs_file += "\n"

        # Patch all shop Product changes
        if len(shop_changes_txt) > 0:
            master_csvs_file += "# Set Product (shop) entries\n"
            master_csvs_file += "Assets/GameAssets/Serial/Data/Master/product\n"
            master_csvs_file += "id,content_id,coefficient,purchase_limit\n"
            for prod_id in sorted(shop_changes_txt.keys()):
                line = shop_changes_txt[prod_id]
                master_csvs_file += line
            master_csvs_file += "\n"

        # Map all "jumbo"/job items *in this seed* to lists of items to be received.
        # We make a custom JSON string since we don't have fine-tuned formatting options and I want to be able to read this.
        # Note: We could one day treat all items as jumbo/special, but it might not simplify that much on the .NET side...
        special_item_str = ''
        for itemId in sorted(item_cid_to_action.keys()):
            if len(special_item_str) > 0:
                special_item_str += ',\n'
            action = item_cid_to_action[itemId]
            special_item_str += f'    "{itemId}": {json.dumps(action, indent=None)}'

        # Build another nice formatted string for shops
        special_shop_str = ''
        for pgItemId in sorted(shop_item_to_location_revlookup.keys()):
            if len(special_shop_str) > 0:
                special_shop_str += ',\n'
            locations = shop_item_to_location_revlookup[pgItemId]
            special_shop_str += f'    "{pgItemId[0]}:{pgItemId[1]}": {json.dumps(locations, indent=None)}'

        # Write our custom Messages + Nameplates
        message_strings_file,nameplate_strings_file = self.write_custom_messages(extra_messages)

        # Prepare our various .csv patches (things like items, etc.)
        # TODO: Not exactly sure how to organize this...
        master_csvs_file += "# Add any new items\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/item\n"
        master_csvs_file += "+id,sort_id,type_id,system_id,item_lv,attribute_id,accuracy_rate,destroy_rate,standard_value,renge_id,menu_renge_id,battle_renge_id,invalid_reflection,period_id,throw_flag,preparation_flag,drink_flag,machine_flag,condition_group_id,battle_effect_asset_id,menu_se_asset_id,menu_function_group_id,battle_function_group_id,buy,sell,sales_not_possible\n"
        master_csvs_file += "58,58,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"   # "Server Connection" key item
        master_csvs_file += "59,59,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1\n"   # "Display" Normal Item (Content Type 1) (Item Type 2 == Key)
        master_csvs_file += "\n"
        # 
        master_csvs_file += "# ...and their content entries\n"
        master_csvs_file += "Assets/GameAssets/Serial/Data/Master/content\n"
        master_csvs_file += "+id,mes_id_name,mes_id_battle,mes_id_description,icon_id,type_id,type_value\n"
        master_csvs_file += "1691,MSG_RANDO_SERVER_ITEM_NAME,None,MSG_RANDO_SERVER_ITEM_DESC,0,1,58\n"
        master_csvs_file += "\n"

        # Add our new item name/descriptions to system
        system_strings_file = "Assets/GameAssets/Serial/Data/Message/system_en\n"
        system_strings_file += f"MSG_RANDO_SERVER_ITEM_NAME,<IC_RING>Server Connection\n"
        system_strings_file += f"MSG_RANDO_SERVER_ITEM_DESC,TBD\n"   # Will be intercepted by the engine
        for key, val in system_extra_messages.items():
            system_strings_file += f"{key},{val}\n"

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


        # Some stuff is required to interact with the multiworld server, or for general bookkeeping
        # We'll store this all into one big JSON object that the C# app can read and make use of
        multiworld_data_file = self.serialize_multiworl_data(location_cid_to_item_cid, special_shop_str, special_item_str, mundane_prog_items)

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




