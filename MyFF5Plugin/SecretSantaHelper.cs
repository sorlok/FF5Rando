using Last.Data.Master;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using static MyFF5Plugin.Plugin;

namespace MyFF5Plugin
{
    // Loaded from our Zip file; contains data that helps distribute gifts to/from your friends in other worlds
    public class SecretSantaHelper
    {
        public string player_name = "";
        public string seed_name = "";
        public int remote_item_content_id_offset = 0;
        public int jobs_for_world1_completion = 10;

        // Maps a given Location to the content_id it unlocks. Values will either be:
        //   * The content_id for the item you should get here (either a mundane content_id, or one in "item_cid_to_action")
        //   * The same Location ID, which means this is a "remote" item (but you should still look it up in "item_cid_to_action" just to be sure)
        // Note that we typically unlock Locations from Chests, Bosses, etc., since we are required to send the Location ID
        //   to the Server when we unlock it ---even if it's just a "local" Item. (If we don't do this, the "/missing" command
        //   will report as missing Items that we actually may have collected.)
        private Dictionary<int, int> location_cid_to_item_cid = new Dictionary<int, int>();

        // Describes actions to take to process a given special item
        //   <item_id> -> <action>, where <action> is one of:
        //     ["job", <job_id>]   # Learn this job
        //     ["remote"]  # Unlock the "item_cid" as a remote Location
        //     ["jumbo", <item_id>, <item_count>, ...]  # Gain these counts of these items
        //     ["item", <content_id>]  # Currently never appears, but is effectively the default action. 
        //                               (The way we set this up, 'item_id' would always be equal to 'content_id' for any single 'item')
        private Dictionary<int, List<string>> item_cid_to_action = new Dictionary<int, List<string>>();

        // Used to unlock Locations when they are on sale in Shops.
        //   * key = "<ProductGroupId>:<ItemContentId>"
        //   * value = [Location 1, Location 2, ...] that we should unlock
        // Every Location *except* shops use the Location as the content_id that we unlock. Shops cannot do this,
        //   since it would (a) limit us to only buying, e.g., 1 Fire Rod from a given shop, and (b) make it hard
        //   to set the Item's cost, description, etc. (we'd have to import it all into Pristine in our World).
        // Instead, we list the Mundane/Job/Jumbo item in the shop directly, and then, when the player buys an item,
        //   we scan through this list an unlock ONE Location per purchased item. 
        // The reason the value is a List is that, for example, the "Walse Item Shop" may have 2 Locations that
        //   both sell "Potion"s. But since these are effectively indestinguishable, we can simply unlock the first
        //   Location when the first Potion is bought, and the second Location when the second Potion is bought.
        // This way, players can keep buying Potions and be none the wiser.
        private Dictionary<string, List<int>> shop_item_to_location_revlookup = new Dictionary<string, List<int>>();

        // Set of "mundane" (normal game) items (by content_id) that are used for Progression.
        // Right now, the only reason this matters is that we don't want a shop to allow multiple 
        //   purchases of things like the Adamantite.
        private HashSet<int> mundaneProgressionItems = new HashSet<int>();

        // Class that describes how to scale a single Monster (Boss)
        private class MonsterScaleData
        {
            // Recommended Level to defeat this monster (see spreadsheet).
            // If we're shuffling boss locations, then this is the Level you're expected to be at for the given location;
            //   i.e., any boss at the "Wing Raptor" location will have a baseRecLvl of 4
            public int baseRecLvl = 0;

            // Regardless of dynamic scaling factor, never go above this value. Can be used to keep enemies within
            //   "world 1" levels, or to scale beyond World 3 levels (gives us flexibility).
            public int maxRecLvl = 0;

            // Any additional scaling to apply. 
            // TODO: Things like "num checks" or "time".
            public string dynamicScaleBy = "";

            // What abilities should we scale? (e.g., "Fire" -> "Fira" -> "Firaga")
            // Any Ability ID present here will be subject to scaling; see the (TODO) data structure
            //   for logic on how abilities scale.
            public List<int> abilitiesToScale = new List<int>();

            // Scale factors for various stats. 1.0 == no adjustment.
            // Used to help differentiate monsters; for example, Wing Raptor has
            //   fairly high HP for its location (so its scale factor is around 2),
            //   while Purobolos has low HP (and will thus have its HP reduced).
            // When scaling these stats, multiply the result by these weights.
            // Independent of Location/dynamic scaling.
            public float hpWeightFactor = 1.0f;
            public float mpWeightFactor = 1.0f;
            public float defWeightFactor = 1.0f;
            // TODO: more
        }

        // Monsters that should have their stats/spells scaled, and how to scale them.
        //   MonsterId -> info about how to scale that monster when encountered.
        private Dictionary<int, MonsterScaleData> monsterScaling = new Dictionary<int, MonsterScaleData>();

        // The slope-intercept formula that describes how different stats are scaled.
        private class StatScaler
        {
            public StatScaler(float slope, float yIntercept, int minVal, int maxVal)
            {
                this.slope = slope;
                this.yIntercept = yIntercept;
                this.minval = minVal;
                this.maxVal = maxVal;
            }

            // Scale a given stat based on the "Recommended Level" you want to be able to fight it at.
            // Apply an optional "weight factor" to boost this further up/down (pass in 1.0 to skip this step).
            // Returns an integer value, within min/max
            public int scaleStat(int recLvl, float weight)
            {
                int res = (int)Math.Round(weight * (slope * recLvl + yIntercept));
                return Math.Max(minval, Math.Min(maxVal, res));
            }

            // Y + mX + b
            float slope;
            float yIntercept;

            // Absolute min/max. This should be game engine specific "hard" limits; we want
            //   soft maximums in particular to be emergent based on the Options selected.
            int minval;
            int maxVal;
        }

        // Scalers for our various stats
        private StatScaler hpScaler;
        private StatScaler mpScaler;
        private StatScaler defScaler;

        // Ability scalers. Skill A -> Skill B if RecLvl is exceeded.
        // This lookup should be performed recursively, so that Fire -> Fira, and then Fira -> Firaga
        //  (if the RecLvl conditions are met)
        private class AbilityScaleData
        {
            public AbilityScaleData(int newAbilityId, int recLvlThreshold)
            {
                this.newAbilityId = newAbilityId;
                this.recLvlThreshold = recLvlThreshold;
            }
            public int newAbilityId;
            public int recLvlThreshold;
        }
        private Dictionary<int, AbilityScaleData> abilityScaler = new Dictionary<int, AbilityScaleData>();

        // Monster parties to substitute.
        // Used to make Boss Location randomization much easier to prototype.
        // MonsterPartyId -> ReplacementPartyId ; should work with all types of encounter IDs
        private Dictionary<int, int> monsterPartySwap = new Dictionary<int, int>();

        // Encounter Id -> [ monster1, monster2, ... ]
        // Includes monsters in that encounter at the start as well as monsters that can be swapped in
        //   (think: the forms of Archeoavis)
        private Dictionary<int, HashSet<int>> encounterMobLookup = new Dictionary<int, HashSet<int>>();




        public SecretSantaHelper(StreamReader reader)
        {
            // Parse it
            string fileContents = reader.ReadToEnd();
            JsonObject root = JsonNode.Parse(fileContents).AsObject();

            // Retrieve basic properties
            player_name = root["player_name"].ToString();
            seed_name = root["seed_name"].ToString();
            remote_item_content_id_offset = root["remote_item_content_id_offset"].GetValue<int>();
            jobs_for_world1_completion = root["jobs_for_world1_completion"].GetValue<int>();

            // Parse our Location -> Content lookup
            JsonObject locationCidToItemCid = root["location_cid_to_item_cid"].AsObject();
            foreach (var entry in locationCidToItemCid)
            {
                int key = Int32.Parse(entry.Key);
                int val = entry.Value.GetValue<int>();
                location_cid_to_item_cid[key] = val;
            }

            // Dictionaries of Lists are kind of a pain...
            JsonObject itemCidToAction = root["item_cid_to_action"].AsObject();
            foreach (var entry in itemCidToAction)
            {
                int key = Int32.Parse(entry.Key);
                JsonArray valArray = entry.Value.AsArray();
                item_cid_to_action[key] = new List<string>();

                // First, just parse everything as a string value, *but* validate as you go.
                string actionName = null;
                foreach (JsonNode valEntry in valArray)
                {
                    // Validate the action
                    if (actionName == null)
                    {
                        actionName = valEntry.ToString();
                        if (actionName != "job" && actionName != "remote" && actionName != "jumbo")
                        {
                            Log.LogError($"BAD CUSTOM ITEM ACTION: {key} => {actionName}");
                            break;
                        }
                    }

                    // Validate the args
                    else
                    {
                        try
                        {
                            valEntry.GetValue<int>();
                        }
                        catch (FormatException ex)
                        {
                            Log.LogError($"BAD CUSTOM ITEM PARAM: {key} => {valEntry.ToString()}");
                            break;
                        }
                    }

                    // Append it
                    item_cid_to_action[key].Add(valEntry.ToString());
                }

                // Now, do some basic ation validation
                if (actionName == "job")
                {
                    if (item_cid_to_action[key].Count != 2)
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[1]: {key} => {String.Join(',', item_cid_to_action[key])}");
                    }
                }
                else if (actionName == "remote")
                {
                    if (item_cid_to_action[key].Count != 1)
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[2]: {key} => {String.Join(',', item_cid_to_action[key])}");
                    }
                }
                else if (actionName == "jumbo")
                {
                    if (item_cid_to_action[key].Count % 2 != 1)  // Need even pairs + 1 action == odd
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[3]: {key} => {String.Join(',', item_cid_to_action[key])}");
                    }
                }
                else
                {
                    Log.LogError($"Unknown action: {actionName}");
                }
            }

            // Yep, still annoying
            JsonObject shopItemToLocationRevLookup = root["shop_item_to_location_revlookup"].AsObject();
            foreach (var entry in shopItemToLocationRevLookup)
            {
                string key = entry.Key;
                JsonArray valArray = entry.Value.AsArray();
                shop_item_to_location_revlookup[key] = new List<int>();

                foreach (JsonNode valEntry in valArray)
                {
                    int valI = valEntry.GetValue<int>();
                    shop_item_to_location_revlookup[key].Add(valI);
                }
            }

            // So's the Set, but slightly less so!
            JsonArray mundProg = root["mundane_prog_items"].AsArray();
            foreach (var entry in mundProg)
            {
                int key = entry.GetValue<int>();
                mundaneProgressionItems.Add(key);
            }

            // Read in monster party swaps (optional)
            if (root.ContainsKey("monster_party_swap"))
            {
                JsonObject monstSwap = root["monster_party_swap"].AsObject();
                foreach (var entry in monstSwap)
                {
                    int keyI = Int32.Parse(entry.Key);
                    int valI = entry.Value.GetValue<int>();
                    monsterPartySwap[keyI] = valI;
                }
            }

            // Read in the encounter->monster lookup
            if (root.ContainsKey("encounter_mobs"))
            {
                JsonObject encLookup = root["encounter_mobs"].AsObject();
                foreach (var entry in encLookup)
                {
                    int keyI = Int32.Parse(entry.Key);
                    JsonArray valArray = entry.Value.AsArray();
                    HashSet<int> monsters = new HashSet<int>();
                    foreach (JsonNode valEntry in valArray)
                    {
                        int valI = valEntry.GetValue<int>();
                        monsters.Add(valI);
                    }
                    encounterMobLookup[keyI] = monsters;
                }
            }

            // Read in ability scaling data (optional)
            if (root.ContainsKey("ability_scaling"))
            {
                JsonObject abilScale = root["ability_scaling"].AsObject();
                foreach (var entry in abilScale)
                {
                    int keyI = Int32.Parse(entry.Key);
                    JsonArray valA = entry.Value.AsArray();
                    int valI1 = valA[0].GetValue<int>();
                    int valI2 = valA[1].GetValue<int>();
                    abilityScaler[keyI] = new AbilityScaleData(valI1, valI2);
                }
            }

            // Read in various stat scale params (optional)
            if (root.ContainsKey("stat_scaling"))
            {
                JsonObject statScale = root["stat_scaling"].AsObject();

                // HP
                {
                    JsonArray statObj = statScale["hp"].AsArray();
                    hpScaler = new StatScaler(statObj[0].GetValue<float>(), statObj[1].GetValue<float>(), statObj[2].GetValue<int>(), statObj[3].GetValue<int>());
                }

                // MP
                {
                    JsonArray statObj = statScale["mp"].AsArray();
                    mpScaler = new StatScaler(statObj[0].GetValue<float>(), statObj[1].GetValue<float>(), statObj[2].GetValue<int>(), statObj[3].GetValue<int>());
                }

                // Defense
                {
                    JsonArray statObj = statScale["def"].AsArray();
                    defScaler = new StatScaler(statObj[0].GetValue<float>(), statObj[1].GetValue<float>(), statObj[2].GetValue<int>(), statObj[3].GetValue<int>());
                }

                // TODO: more
            }

            // Read in monster scaling params (optional)
            if (root.ContainsKey("monster_scaling"))
            {
                JsonObject monstersToScale = root["monster_scaling"].AsObject();
                foreach (var entry in monstersToScale)
                {
                    int keyI = Int32.Parse(entry.Key);
                    JsonArray valA = entry.Value.AsArray();

                    // Just positional, for now
                    MonsterScaleData newMonst = new MonsterScaleData();
                    newMonst.baseRecLvl = valA[0].GetValue<int>();
                    newMonst.maxRecLvl = valA[1].GetValue<int>();
                    newMonst.dynamicScaleBy = valA[2].ToString();  // TODO: unused for now
                    newMonst.hpWeightFactor = valA[3].GetValue<float>();
                    newMonst.mpWeightFactor = valA[4].GetValue<float>();
                    newMonst.defWeightFactor = valA[5].GetValue<float>();

                    // Abilities are an array of ints
                    JsonArray abilA = valA[valA.Count-1].AsArray();
                    foreach (var abilId in abilA)
                    {
                        newMonst.abilitiesToScale.Add(abilId.GetValue<int>());
                    }

                    // Save it
                    monsterScaling[keyI] = newMonst;
                }
            }
        }


        // Modifies the monster party ID that's passed in
        public void swapMonsterParty(ref int monsterPartyId)
        {
            if (monsterPartySwap.ContainsKey(monsterPartyId))
            {
                Plugin.Log.LogInfo($"Swapping monster party {monsterPartyId} with {monsterPartySwap[monsterPartyId]}");
                monsterPartyId = monsterPartySwap[monsterPartyId];
            }
        }

        // What monsters are in this encounter (or could be swapped in)?
        public HashSet<int> getMonstersInEncounter(int encounterId)
        {
            if (encounterMobLookup.ContainsKey(encounterId))
            {
                return encounterMobLookup[encounterId];
            }
            return new HashSet<int>();
        }


        // Retrieve the IDs of any monsters we plan to scale later
        public List<int> monstersToScale()
        {
            return monsterScaling.Keys.ToList();
        }


        // Called to scale the stats of a given monster
        public void scaleMonsterStats(int monsterId)
        {
            // Do we need to scale this monster?
            if (!monsterScaling.ContainsKey(monsterId))
            {
                return;
            }

            // Get the monster. Note that we have already backed this monster up, so 
            //   we can just modify it in-place (it will reset when we clear our patch data).
            Monster monster = MasterManager.Instance.GetList<Monster>()[monsterId];

            // Get the relevant stat scale params
            MonsterScaleData scaleStats = monsterScaling[monsterId];

            // TODO: apply dynamic, etc.
            int recLvl = scaleStats.baseRecLvl;

            // TEMP: Logging
            Plugin.Log.LogInfo($"MONSTER {monsterId} original, HP: {monster.Hp} ; MP: {monster.Mp} ; Def: {monster.Defense}");
            // END TEMP

            // Scale HP
            monster.Hp = hpScaler.scaleStat(recLvl, scaleStats.hpWeightFactor);
            // MP
            monster.Mp = mpScaler.scaleStat(recLvl, scaleStats.mpWeightFactor);
            // Def
            monster.Defense = defScaler.scaleStat(recLvl, scaleStats.defWeightFactor);

            // SPECIAL CASE: Right now, we have to hard-code Soul Cannon, since it self-destructs below 10k HP,
            // and putting it at Wing Raptor could break this.
            if (monsterId == 300)
            {
                monster.Hp += 10000;
                Plugin.Log.LogInfo("Special case: +10k HP to Soul Cannon");
            }


            // TODO: TEMP - note: Bartz has +1 str vs. Galuf (not sure if relevant)
            //monster.Defense = 0;   // 30 or 32 damage
            //monster.Defense = 5;   // 20 or 22 damage
            //monster.Defense = 10;   // 10 or 10 damage
            //monster.Defense = 15;   // 2 or 0 damage
            // END TEMP


            // TEMP: Logging
            Plugin.Log.LogInfo($"MONSTER {monsterId} scaled, HP: {monster.Hp} ; MP: {monster.Mp} ; Def: {monster.Defense}");
            // END TEMP
        }

        // Scale the magic used by a given monster
        // Store the results in abilitySubs (which will be applied later).
        public void scaleMonsterMagic(int monsterId, Dictionary<int, int> abilitySubs)
        {
            // Do we need to scale this monster?
            if (!monsterScaling.ContainsKey(monsterId))
            {
                return;
            }

            // Get the monster. See note in scaleMonsterStats() on the orig value
            Monster monster = MasterManager.Instance.GetList<Monster>()[monsterId];

            // Get the relevant ability scale params
            MonsterScaleData scaleStats = monsterScaling[monsterId];

            // TODO: apply dynamic, etc.
            //
            // TODO: We might want to merge this function with the previous one... lots of duplicate code.
            int recLvl = scaleStats.baseRecLvl;

            // Check each marked ability and scale it.
            foreach (int oldAbilityId in scaleStats.abilitiesToScale)
            {
                // Loop, but put a bound on it in case we get into an infinite loop
                int newAbilityId = oldAbilityId;
                for (int i=0; i<10 && abilityScaler.ContainsKey(newAbilityId); i++)
                {
                    AbilityScaleData adata = abilityScaler[newAbilityId];
                    if (recLvl >= adata.recLvlThreshold)
                    {
                        newAbilityId = adata.newAbilityId;
                    }
                    else
                    {
                        break;
                    }
                }

                // Replace it
                if (oldAbilityId != newAbilityId)
                {
                    Plugin.Log.LogInfo($"Substituting ability {oldAbilityId} with {newAbilityId} for monster {monsterId}");
                    abilitySubs[oldAbilityId] = newAbilityId;
                }
            }
        }


        // Is this a mundane item that is also used for Progression (like Adamantite)?
        public bool isMundaneProgItem(int contentId)
        {
            return mundaneProgressionItems.Contains(contentId);
        }

        // Retrieve the Item CID given a Location CID. If this isn't a Location CID, return -1
        public int locationCIdToItemCId(int locCId)
        {
            if (location_cid_to_item_cid.ContainsKey(locCId))
            {
                return location_cid_to_item_cid[locCId];
            }
            return -1;
        }

        // Retrive the Action associated with this Item (by content_id), or null if none
        public List<string> getActionFromItemCId(int itemCId)
        {
            if (item_cid_to_action.ContainsKey(itemCId))
            {
                return item_cid_to_action[itemCId];
            }
            return null;
        }

        // Retrieve the list of Locations that this Shop's purchased Item should unlock
        public List<int> getShopLocationFromItemCId(int productGroupId, int itemCId)
        {
            string key = $"{productGroupId}:{itemCId}";
            if (shop_item_to_location_revlookup.ContainsKey(key))
            {
                return shop_item_to_location_revlookup[key];
            }
            return null;
        }

        // Returns true if this Location content_id refers to a Remote item
        public bool isRemoteLocation(int locationCId)
        {
            // Locations are their own CIds, but look it up anyway
            if (location_cid_to_item_cid.ContainsKey(locationCId)) {
                int itemCId = location_cid_to_item_cid[locationCId];
                if (item_cid_to_action.ContainsKey(itemCId))
                {
                    return item_cid_to_action[itemCId][0] == "remote";
                }
            }

            // If it's not in our list, it's definitely not Remote
            return false;
        }



    }
}
