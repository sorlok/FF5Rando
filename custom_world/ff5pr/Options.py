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

class RandomizeFirstJob(DefaultOnToggle):
    """If true, your first job may not be Freelancer. You will still be able to 
    unlock Freelancer at a Location elsewhere in the game. EXPERIMENTAL: Stuff may break!"""
    display_name = "Randomize First Job"

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


class SellBlueMagicInShops(Toggle):
    """If true, creates Blue Magic shops in Crescent, Istory, and Jachol (which
    normally have duplicates of Karnak's magic inventory). This is independent of
    'SplitSharedShops'. Blue Magic can be further randomized into chests."""
    display_name = "Sell Blue Magic In Shops"


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


class ShopCustomPriceJobs(Range):
    """How much should a Job cost when it appears in a shop?
    Right now only a flat value is supported (nothing dynamic)."""
    display_name = "Shop Custom Price Jobs"
    range_start = 1
    range_end = 10000
    default = 5000


class ShopCustomPriceMultiworldItems(Range):
    """How much should an AP (MultiWorld) item cost when it appears in a shop?
    Right now only a flat value is supported (nothing dynamic)."""
    display_name = "Shop Custom Price Multiworld Items"
    range_start = 1
    range_end = 10000
    default = 1000


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


class ShuffleBosses(Toggle):
    """If true, shuffle all bosses around to different locations.
    Bosses will be scaled to the location they appear in, so a Wing Raptor
    at Titan's location will be significantly stronger."""
    display_name = "Shuffle Bosses"


class ScaleBossHP(DefaultOnToggle):
    """If true, any boss that is scaled will have its HP scaled. 
    You know what HP is, right? It's the damage you must do to defeat the monster.
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss HP"

class ScaleBossMP(DefaultOnToggle):
    """If true, any boss that is scaled will have its MP scaled. 
    Bosses can actually fully use up their MP pool (and be unable to cast spells).
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss MP"

class ScaleBossAttack(DefaultOnToggle):
    """If true, any boss that is scaled will have its Attack scaled. 
    An enemy's Attack stat is used to determine the base damage value (see: Defense).
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss Attack"

class ScaleBossDefense(DefaultOnToggle):
    """If true, any boss that is scaled will have its Defense scaled. 
    An enemy's Defense stat will offset the base damage done by hero physical attacks.
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss Defense"

class ScaleBossAttackCount(DefaultOnToggle):
    """If true, any boss that is scaled will have its AttackCount scaled. 
    The AttackCount stat is a multiplier on the total damage dealt (after Defense is factored in).
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss AttackCount"

class ScaleBossMagic(DefaultOnToggle):
    """If true, any boss that is scaled will have its Magic scaled. 
    The Magic stat affects the base value that a monster's magic will do.
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss Magic"

class ScaleBossAgility(DefaultOnToggle):
    """If true, any boss that is scaled will have its Agility scaled. 
    The Agility stat affects how quickly a monster will get its next turn once its current turn is finished.
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss Agility"

class ScaleBossExperience(DefaultOnToggle):
    """If true, bosses are given experience based on their location (i.e., how difficult they are), so a Karlabos
    in one of the meteors will give way more than Titan in the Wind Shrine. If false, bosses give an XP value that
    is based on their location in the main game. 
    Note that bosses in the original game do not typically give experience, but the randomizer always does.
    This only takes effect if boss scaling is on; for example, if "Shuffle Bosses" is on."""
    display_name = "Scale Boss Experience"

class SoloCharacterChallenge(Toggle):
    """If true, your party for the whole game will be Bartz, and no-one else.
    Your friends will still show up for cutscenes.
    EXPERIMENTAL: Some things may break! Let us know if you get stuck!"""
    display_name = "Solo Character Challenge"

class BringYourGranddaughterToWorkDay(Toggle):
    """If true, your party for the whole game will be Galuf and Krile, and no-one else.
    Your friends will still show up for cutscenes.
    BUGGY: This causes Bartz-NPCs to appear and block your path and crash your game. I'm still
    trying to figure out why this happens."""
    display_name = "Bring Your Granddaughter To Work Day"



# TODO: Add an "option_groups" variable?


@dataclass
class FF5PROptions(PerGameCommonOptions):
	# Normal stuff
    prog_items_in_chests: AllowProgItemsInChests
    randomize_first_job: RandomizeFirstJob

    # Shop stuff
    add_shop_locations: AddShopLocations
    sell_blue_magic_in_shops: SellBlueMagicInShops
    split_shared_shops: SplitSharedShops
    shuffle_shops: ShuffleShops
    shop_custom_price_jobs: ShopCustomPriceJobs
    shop_custom_price_multiworld_items: ShopCustomPriceMultiworldItems
    #
    percent_shop_inventory_as_locations: PercentShopInventoryAsLocations
    percent_shop_inventory_as_locations_min: PercentShopInventoryAsLocationsMin
    percent_shop_inventory_as_locations_max: PercentShopInventoryAsLocationsMax
    #
    percent_shop_inventory_shuffled: PercentShopInventoryShuffled
    percent_shop_inventory_shuffled_min: PercentShopInventoryShuffledMin
    percent_shop_inventory_shuffled_max: PercentShopInventoryShuffledMax

    # Boss Scaling
    shuffle_bosses: ShuffleBosses
    #
    scale_boss_hp: ScaleBossHP
    scale_boss_mp: ScaleBossMP
    scale_boss_atk: ScaleBossAttack
    scale_boss_def: ScaleBossDefense
    scale_boss_atkcount: ScaleBossAttackCount
    scale_boss_mag: ScaleBossMagic
    scale_boss_agi: ScaleBossAgility
    scale_boss_exp: ScaleBossExperience

    # Fun stuff
    bring_your_granddaughter_to_work_day: BringYourGranddaughterToWorkDay
    solo_character_challenge: SoloCharacterChallenge

    # Goals
    jobs_for_world1_completion: JobsForWorld1Completion

    # Debug stuff
    validate_pristine_data: ValidatePristineData



