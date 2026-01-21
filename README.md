# FF5Rando
Trying to get FF5PR to randomize

## Directories

* MyFF5Plugin - Contains a BepInEx plugin that mods FF5 on the fly to do what we want it to do. Currently (maybe) requires Magicite + asset export, but the goal is to do that internal to the plugin as well.
* Scripts - Various Python scripts that analyze resources from the game and help with the process of randomization. This requires a Magicite export of game assets. 
* Data - Contains processed data extracted from the game once we're happy with it.
* custom_world/ff5pr - Contains the World implementation for Archipelago. Copy the 'ff5pr' directory into the 'lib/worlds' folder of an Archipelago installation, and then you can use 'Final Fantasy V PR' in your Player.yml to generate a seed with FF5 in the mix!




