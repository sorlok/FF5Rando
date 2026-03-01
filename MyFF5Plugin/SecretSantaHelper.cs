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
        public int local_location_content_id_offset = 0;
        public int local_location_content_num_incantation = 0;   // For remote items that we need to send to the server
        public int remote_item_content_id_offset = 0;
        public Dictionary<int, List<string[]>> content_id_special_items = new Dictionary<int, List<string[]>>();

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
            local_location_content_id_offset = root["local_location_content_id_offset"].GetValue<int>();
            local_location_content_num_incantation = root["local_location_content_num_incantation"].GetValue<int>();
            remote_item_content_id_offset = root["remote_item_content_id_offset"].GetValue<int>();

            // The dictionary is kind of a pain...
            JsonObject specialItems = root["content_id_special_items"].AsObject();
            foreach (var entry in specialItems)
            {
                int key = Int32.Parse(entry.Key);
                JsonArray valArray = entry.Value.AsArray();
                content_id_special_items[key] = new List<string[]>();

                // Each jumbo item can add multiple items
                foreach (var valEntryNode in valArray)
                {
                    // Kind of a pain...
                    JsonArray valEntry = valEntryNode.AsArray();
                    string[] val = new string[valEntry.Count];
                    for (int i = 0; i < valEntry.Count; i++)
                    {
                        val[i] = valEntry[i].ToString();
                    }
                    content_id_special_items[key].Add(val);

                    // Some basic sanity check
                    if (val[0] == "item")
                    {
                        if (val.Length != 3)
                        {
                            Log.LogError($"BAD MULTIEWORLD ENTRY[1]: {key} => {val}");
                        }
                    }
                    else if (val[0] == "job")
                    {
                        if (val.Length != 2)
                        {
                            Log.LogError($"BAD MULTIEWORLD ENTRY[2]: {key} => {val}");
                        }
                    }
                    else
                    {
                        Log.LogError($"BAD MULTIEWORLD ENTRY[3]: {key} => {val}");
                    }
                }
            }
        }
    }

}
