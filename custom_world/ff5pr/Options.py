import typing
from dataclasses import dataclass
from Options import DefaultOnToggle, Range, Toggle, DeathLink, Choice, PerGameCommonOptions, OptionSet, OptionGroup, Visibility


# This class contains the Player Options for FF5PR. 
# Each option has its own class, and the @dataclass after lists all options that apply to this game.


###############################################################
# General Stuff
###############################################################


class AllowProgItemsInChests(Toggle):
    """Allow Progression Items to appear in chests? If not, they will only appear
    at Crystal Shard and Boss locations. Roughly triples the number of checks if on."""
    display_name = "Allow Progression Items in chests"

class JobsForWorld1Completion(Range):
    """How many Jobs must the player obtain in order to count World 1 as 'done'. This does not include the
    job you start with (Freelancer by default), so if you set this to '10', that means you'll need 11 jobs
    in your Job menu to count as completed.
    NOTE: This is subject to change; right now the World 2 unlock condition is Jobs,
    but that is not guaranteed to be final."""
    display_name = "Jobs for World 1 Completion"
    range_start = 1
    range_end = 20
    default = 10

class ValidatePristineData(Toggle):
    """Run various checks on the 'pristine' data source used by this randomizer.
    This is a developer option, and should remain off for all players."""
    display_name = "Validate Pristine Data"
    visibility = Visibility.none



###############################################################
# Shop Stuff
###############################################################

class AddShopLocations(Toggle):
    """Allow shop items to be suffled into the Location pool?
    This adds several dozen items (right now all items from all shops are shuffled in, 
    there is no distinction for Weapons vs. Items, etc., and some towns naturally share shops)"""
    display_name = "Add Shop Locations"


class PercentShopInventoryAsLocations(Range):
    """What percentage of each shop's inventory will be turned into Locations.
    This is the 'mode' of a triangular distribution, so any shop may still have
    from 0.0 to 1.0 of its inventory transformed. If you need to change the lower/upper
    bounds, use the '_min' and '_max' values as well as this one. For example, if you always
    want exactly 33% of shop items to be Locations, set all three values to 33."""
    display_name = "Percent Job Inventory As Locations"
    range_start = 0
    range_end = 100
    default = 10
#
class PercentShopInventoryAsLocationsMin(Range):
    """See: PercentShopInventoryAsLocations"""
    display_name = "Percent Job Inventory As Locations (Lower Bound)"
    range_start = 0
    range_end = 100
    default = 0
#
class PercentShopInventoryAsLocationsMax(Range):
    """See: PercentShopInventoryAsLocations"""
    display_name = "Percent Job Inventory As Locations (Upper Bound)"
    range_start = 0
    range_end = 100
    default = 100


class SplitSharedShops(Toggle):
    """Some shops share the same inventory; for example, the Walse and Carwen Item shops.
    By leaving this flag off, those shops will contain the same inventory after randomizing.
    By turning this on, each shop will have its own inventory after randomizing."""
    display_name = "Split Shared Shops"


class ShuffleShops(Toggle):
    """If true, all the shops in the game will shuffle some of their inventories.
    In other words, 'Fire' from Tule's magic shop may now appear in Karnak's Weapon shop."""
    display_name = "Shuffle Shops"


class PercentShopInventoryShuffled(Range):
    """What percentage of each shop's inventory will be shuffled. A shop being shuffled is
    independent of whether or not it's chosen as a Location. Note that this value is the mode of a
    triangular distribution, so '33' means that each shop will default to '33%', but values of 0
    and 100% (and anything in between) are stil possible."""
    display_name = "Percent Job Inventory Shuffled"
    range_start = 0
    range_end = 100
    default = 30
#
class PercentShopInventoryShuffledMin(Range):
    """See: PercentShopInventoryShuffled"""
    display_name = "Percent Job Inventory Shuffled (Lower Bound)"
    range_start = 0
    range_end = 100
    default = 0
#
class PercentShopInventoryShuffledMax(Range):
    """See: PercentShopInventoryShuffled"""
    display_name = "Percent Job Inventory Shuffled (Upper Bound)"
    range_start = 0
    range_end = 100
    default = 100



# TODO: Add an "option_groups" variable?


@dataclass
class FF5PROptions(PerGameCommonOptions):
	# Normal stuff
    prog_items_in_chests: AllowProgItemsInChests

    # Shop stuff
    add_shop_locations: AddShopLocations
    split_shared_shops: SplitSharedShops
    shuffle_shops: ShuffleShops
    #
    percent_shop_inventory_as_locations: PercentShopInventoryAsLocations
    percent_shop_inventory_as_locations_min: PercentShopInventoryAsLocationsMin
    percent_shop_inventory_as_locations_max: PercentShopInventoryAsLocationsMax
    #
    percent_shop_inventory_shuffled: PercentShopInventoryShuffled
    percent_shop_inventory_shuffled_min: PercentShopInventoryShuffledMin
    percent_shop_inventory_shuffled_max: PercentShopInventoryShuffledMax

    # Goals
    jobs_for_world1_completion: JobsForWorld1Completion

    # Debug stuff
    validate_pristine_data: ValidatePristineData



