using System;
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


        public SecretSantaHelper(StreamReader reader)
        {
            // Parse it
            string fileContents = reader.ReadToEnd();
            JsonObject root = JsonNode.Parse(fileContents).AsObject();

            // Retrieve basic properties
            player_name = root["player_name"].ToString();
            seed_name = root["seed_name"].ToString();
            remote_item_content_id_offset = root["remote_item_content_id_offset"].GetValue<int>();

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

                    Plugin.Log.LogError($"TEST: {key} => {valI}");
                }
            }

            // So's the Set, but slightly less so!
            JsonArray mundProg = root["mundane_prog_items"].AsArray();
            foreach (var entry in mundProg)
            {
                int key = entry.GetValue<int>();
                mundaneProgressionItems.Add(key);
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




    }
}
