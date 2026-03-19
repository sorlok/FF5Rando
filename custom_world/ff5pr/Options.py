import typing
from dataclasses import dataclass
from Options import DefaultOnToggle, Range, Toggle, DeathLink, Choice, PerGameCommonOptions, OptionSet, OptionGroup, Visibility


# This class contains the Player Options for FF5PR. 
# Each option has its own class, and the @dataclass after lists all options that apply to this game.




class AllowProgItemsInChests(Toggle):
    """Allow Progression Items to appear in chests? If not, they will only appear
    at Crystal Shard and Boss locations. Roughly triples the number of checks if on."""
    display_name = "Allow Progression Items in chests"

class AddShopLocations(Toggle):
    """Allow shop items to be suffled into the Location pool?
    This adds several dozen items (right now all items from all shops are shuffled in, 
    there is no distinction for Weapons vs. Items, etc., and some towns naturally share shops)"""
    display_name = "Add Shop Locations"


class SplitSharedShops(Toggle):
    """Some shops share the same inventory; for example, the Walse and Carwen Item shops.
    By leaving this flag off, those shops will contain the same inventory after randomizing.
    By turning this on, each shop will have its own inventory after randomizing."""
    display_name = "Split Shared Shops"


class ValidatePristineData(Toggle):
    """Run various checks on the 'pristine' data source used by this randomizer.
    This is a developer option, and should remain off for all players."""
    display_name = "Validate Pristine Data"
    visibility = Visibility.none


# TODO: Add an "option_groups" variable?


@dataclass
class FF5PROptions(PerGameCommonOptions):
	# Normal stuff
    prog_items_in_chests: AllowProgItemsInChests
    add_shop_locations: AddShopLocations
    split_shared_shops: SplitSharedShops

    # Debug stuff
    validate_pristine_data: ValidatePristineData



