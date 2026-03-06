import typing
from dataclasses import dataclass
from Options import DefaultOnToggle, Range, Toggle, DeathLink, Choice, PerGameCommonOptions, OptionSet, OptionGroup


# This class contains the Player Options for FF5PR. 
# Each option has its own class, and the @dataclass after lists all options that apply to this game.




class AllowProgItemsInChests(Toggle):
    """Allow Progression Items to appear in chests? If not, they will only appear
    at Crystal Shard and Boss locations. Roughly triples the number of checks if on."""
    display_name = "Allow Progression Items in chests"



# TODO: Add an "option_groups" variable?


@dataclass
class FF5PROptions(PerGameCommonOptions):
    prog_items_in_chests: AllowProgItemsInChests



