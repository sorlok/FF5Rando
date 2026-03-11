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
        //public int local_location_content_id_offset = 0;
        //public int local_location_content_num_incantation = 0;   // For remote items that we need to send to the server
        public int remote_item_content_id_offset = 0;

        // Describes actions to take to process a given special item
        //   <item_id> -> <action>, where <action> is one of:
        //     ["job", <job_id>]   # Learn this job
        //     ["remote", <location>id>]  # Unlock this remote location for some other player
        //     ["items", <item_id>, <item_count>, ...]  # Gain these counts of these items
        //     ["item", <content_id>]  # Currently never appears, but is effectively the default action. 
        //                               (The way we set this up, 'item_id' would always be equal to 'content_id' for any single 'item')
        public Dictionary<int, List<string>> content_id_special_items = new Dictionary<int, List<string>>();

        // TODO: If the server sends me a job, I will only get '1' of them. The "local_location" is because loc_id and item_id may
        //       (in theory) overlap. What we actually need is just a lookup.
        //public int jumbo_location_content_num_incantation = 0;   // For local (jumbo) items that need special processing


        public SecretSantaHelper(StreamReader reader)
        {
            // Parse it
            string fileContents = reader.ReadToEnd();
            JsonObject root = JsonNode.Parse(fileContents).AsObject();

            // Retrieve basic properties
            player_name = root["player_name"].ToString();
            seed_name = root["seed_name"].ToString();
            //local_location_content_id_offset = root["local_location_content_id_offset"].GetValue<int>();
            //local_location_content_num_incantation = root["local_location_content_num_incantation"].GetValue<int>();
            remote_item_content_id_offset = root["remote_item_content_id_offset"].GetValue<int>();

            // The dictionary is kind of a pain...
            JsonObject specialItems = root["content_id_special_items"].AsObject();
            foreach (var entry in specialItems)
            {
                int key = Int32.Parse(entry.Key);
                JsonArray valArray = entry.Value.AsArray();
                content_id_special_items[key] = new List<string>();

                // First, just parse everything as a string value, *but* validate as you go.
                string actionName = null;
                foreach (JsonNode valEntry in valArray)
                {
                    // Validate the action
                    if (actionName == null)
                    {
                        actionName = valEntry.ToString();
                        if (actionName != "job" && actionName != "remote" && actionName != "items")
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
                    content_id_special_items[key].Add(valEntry.ToString());
                }

                // Now, do some basic ation validation
                if (actionName == "job")
                {
                    if (content_id_special_items[key].Count != 2)
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[1]: {key} => {String.Join(',', content_id_special_items[key])}");
                    }
                }
                else if (actionName == "remote")
                {
                    if (content_id_special_items[key].Count != 2)
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[2]: {key} => {String.Join(',', content_id_special_items[key])}");
                    }
                }
                else if (actionName == "items")
                {
                    if (content_id_special_items[key].Count % 2 != 1)  // Need even pairs + 1 action == odd
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[3]: {key} => {String.Join(',', content_id_special_items[key])}");
                    }
                }
                else
                {
                    Log.LogError($"Unknown action: {actionName}");
                }
            }
        }
    }

}
