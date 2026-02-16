# FF5 Pixel Remaster Archipelago Randomizer
This is a custom world for the Archipelago multi-world randomizer (https://archipelago.gg/). It lets you play Final Fantasy V (Pixel Remaster) as part of an Archipelago shared seed.

## $${\color{red}WARNING}$$
This is currently a prototype, so don't expect too much. The main limitation is that it's currently only for World 1, but you should read the "Limitations" and "Bugs" section for more things to watch out for. Please file Issues if you run into anything, but be patient --I work on this in my free time, and it's rarely my #1 priority. With that in mind, thank you so much for trying out my fun side project!

## Directories

* Data - Contains processed data extracted from the game once we're happy with it.
* MyFF5Plugin - Contains a BepInEx plugin that mods FF5 on the fly to do what we want it to do. Currently (maybe) requires Magicite + asset export, but the goal is to do that internal to the plugin as well.
* Sample - Just some random hand-generated f$${\color{red}Red}$$iles I'm playing around with. Not relevant.
* Scripts - Various Python scripts that analyze resources from the game and help with the process of randomization. This requires a Magicite export of game assets. 
* custom_world/ff5pr - Contains the World implementation for Archipelago. Copy the 'ff5pr' directory into the 'lib/worlds' folder of an Archipelago installation, and then you can use 'Final Fantasy V PR' in your Player.yml to generate a seed with FF5 in the mix!

## What's the Randomizer Like?
Start in World 1 with the Airship and fly around to (almost) any location, opening treasure chests, defeating bosses, and gettin crystal shards. The treasures are randomly shuffled, and the crystals/bosses can be anything at all ---Jobs, special Items (like Adamantite), and even items from other game's worlds, if you set it up that way! Unlocking 10 Jobs will also unlock the warp to World 2, which for now counts as completing the randomizer (since I haven't touched World 2 yet).

## Installation (One Time)


* TODO

## How to Play a Randomizer Seed

* TODO


## Limitations

* The game will (rarely) crash with no error in the logs. Hopefully Auto-Save will protect you here.
* Only World 1 is randomized for now. The plan is to get Worlds 2 and 3, each with their own unlock conditions, and then the final dungeon + boss. But I'm keeping it small for now.
* All bosses except Crystal bosses and Ramuh give you an extra "check". Crystal bosses don't because crystals already give you multiple checks. Ramuh doesn't because I can't figure out how to hack battle events. :)
  * Karlabos and Cray Claw cannot be fought, but that's mostly because I can't figure out a good way to hook the events.
* This is not a limitation, but you need the Adamantite to access the Ronka Ruins, and you neat to clear the Fire-Powered ship to access the chests in Karnak Castle. Once unlocked, both locations remain accessible forever. (TODO: Move this to a 'general' section)
* Not exacty a limitation, but we start with Encounters "off". Press F3 to turn them on again.
* Boss stats are not currently scaled, so Wing Raptor will always be weak and Titan will always be strong. FF5 is a game of exploits, though, so I'm figuring out if it makes sense to adjust this.
  * I would also like to add EXP/AP rewards for bosses, but I haven't figured out how much I want them to give.
  * I also want to give 3x XP/AP in general; just a reminder...
* The magic in chests isn't randomized (Mute, Speed, Teleport, and Float).
* If you "Load" a save file from within the game (i.e., not from the title screen), you won't be given any multi-world items until you open+close a menu or enter combat.
* Bosses effectively give their items twice --once as drops when you defeat them, and again due to their being added to the initial item pool. When we modify boss XP/AP, I need to remove default boss drops.
* The server hostname/port/password is saved into your Save File (which is a feature), but there is no way to change it. I'll need to add a "Connection" menu.
* If you can't connect to the AP server, you won't be able to play your seeded save files. Actually, everything *would* work fine offline (it would just sync when you rejoin); I just need to add a button.
* I'm not sure if the .NET client I'm using reconnects if the server goes down. Need to test this, and make sure our Item/Location behavior is correct in that case.
* I need to add a "Teleport to World 1" item, and the logic to block it in certain maps. This is needed to avoid soft-locking, and to make Worlds 2+3 easily accessible.
  * FF5's teleport is very broken in World 1 (since you're not supposed to have it), AND some of my patches don't reset the Teleport location properly. I need to catch all these cases, or to do it in a more automated way...
* More...

## Bugs

* DO NOT go into the Fire-Powered ship from the catapult; it's out of logic and could soft-lock you.
  * I'll just block this in collisions.json, but right now we hard-code that, and I need to write a patch reader for tilemaps and collisions
* I have not tested it, but I'm pretty sure giving the player an Item from Admin (the console) will make it confused w.r.t. Player Name
* I need to implement get_filler_item_name() (just using tags is fine), since otherwise you could get weird stuff as a filler
* Bartz's name is currently "???", and I need to add .csv parsing to fix it.
* The guy in Carwen won't move out of the way of the barrel (normally he does this after beating North Mountain ---I want it to always be open)
* The Black Chocobo that swalled 2 Crystal Shards doesn't appear in the forest (he used to!)
* The Flames in Karnak are not dying down when you defeat Liquid Flame.
* 

## Possible Features & Balance

* It would make sense to start with a random job unlocked; this removes the redundancy of "just use rods with Freelancer"
* I'd like to have some amount of shop randomization at some point.
* I want to force combat on in the Walse basement, but maybe people will just cheese it with Quicksave, so it might not be worth it.






