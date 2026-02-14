# FF5 Pixel Remaster Archipelago Randomizer
This is a custom world for the Archipelago multi-world randomizer (https://archipelago.gg/). It lets you play Final Fantasy V (Pixel Remaster) as part of an Archipelago shared seed.

## Directories

* Data - Contains processed data extracted from the game once we're happy with it.
* MyFF5Plugin - Contains a BepInEx plugin that mods FF5 on the fly to do what we want it to do. Currently (maybe) requires Magicite + asset export, but the goal is to do that internal to the plugin as well.
* Sample - Just some random hand-generated files I'm playing around with. Not relevant.
* Scripts - Various Python scripts that analyze resources from the game and help with the process of randomization. This requires a Magicite export of game assets. 
* custom_world/ff5pr - Contains the World implementation for Archipelago. Copy the 'ff5pr' directory into the 'lib/worlds' folder of an Archipelago installation, and then you can use 'Final Fantasy V PR' in your Player.yml to generate a seed with FF5 in the mix!

## How to Play

* TODO


## Limitations and Bugs

* Only World 1 is randomized for now. The plan is to get Worlds 2 and 3, each with their own unlock conditions, and then the final dungeon + boss. But I'm keeping it small for now.
* Boss stats are not currently scaled, so Wing Raptor will always be weak and Titan will always be strong. That said, FF5 is a game of exploits, so you *can* beat these bosses at low levels.
  * I would also like to add EXP/AP rewards for bosses, but I haven't figured out how much I want them to give.
* If you "Load" a save file from within the game (i.e., not from the title screen), you won't be given any multi-world items until you open+close a menu or enter combat.
* More...





