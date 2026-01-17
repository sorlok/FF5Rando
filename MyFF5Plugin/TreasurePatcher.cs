using HarmonyLib;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using UnityEngine;

namespace MyFF5Plugin
{
    // Class that describes how to apply a Treasure patch to a json file
    class TreasureJsonPatch
    {
        public string[] json_xpath;   // Typically: ["layers", "[<number>]", "objects", "[<number>]", "properties"];
        public Dictionary<String, String> patches = new Dictionary<string, string>();  // Key/value pairs to overwrite.
    }

    // This class has methods to parse a patch file for Treasures, and then query+apply
    //   those patches at runtime.
    public class TreasurePatcher
    {
        // asset_path -> { json_xpath -> { entry_key_values } }, where asset_path is what Unity expects to see:
        //   Assets/GameAssets/Serial/Res/Map/Map_20011/Map_20011_1/entity_default
        // ...and json_xpath looks like this:
        //   /layers/0/objects/2
        // ...which is an XPath-like way of referring to something we need to change in our json files
        // The entry_key_values is a map of keys to change within that xpath
        //private Dictionary<String, Dictionary<String, Dictionary<String, String>>> TestRandTreasures; // path_ident -> { entry }
        private Dictionary<String, List<TreasureJsonPatch>> TestRandTreasures; // path_ident -> { list_of_patches }

        // Load the given patch file and parse it.
        public TreasurePatcher(string patchPath)
        {
            TestRandTreasures = new Dictionary<string, List<TreasureJsonPatch>>();
            string[] columnNames = null;
            using (var reader = new StreamReader(patchPath))
            {
                while (!reader.EndOfStream)
                {
                    var line = reader.ReadLine().Trim();

                    // First line is column names
                    if (columnNames == null)
                    {
                        columnNames = line.Split(',');
                    }

                    // Any other line must match
                    else
                    {
                        string[] row = line.Split(',');
                        if (row.Length != columnNames.Length)
                        {
                            throw new Exception($"Bad line: {line}");
                        }

                        string entity_default = "";  // entity_default
                        TreasureJsonPatch entry = new TreasureJsonPatch();
                        for (int i = 0; i < columnNames.Length; i++)
                        {
                            // First two columns are special
                            if (columnNames[i] == "entity_default")
                            {
                                entity_default = row[i];
                            }
                            //
                            else if (columnNames[i] == "json_xpath")
                            {
                                entry.json_xpath = JsonHelper.SplitJsonXPath(row[i]);
                            }

                            // Everything else is a key/value based on column header
                            else
                            {
                                entry.patches.Add(columnNames[i], row[i]);
                            }
                        }

                        // Top-level key
                        if (!TestRandTreasures.ContainsKey(entity_default))
                        {
                            TestRandTreasures[entity_default] = new List<TreasureJsonPatch>();
                        }

                        // Second-level key (duplicates are alowed at this point, even though it'd be weird).
                        TestRandTreasures[entity_default].Add(entry);
                    }
                }
            }
        }


        // Is this a resource we expect to patch?
        // addressName = Needs to match the Resource Unity is loading (note the lack of extension). E.g.:
        //               Assets/GameAssets/Serial/Res/Map/Map_20011/Map_20011_1/entity_default
        public bool needsPatching(string addressName)
        {
            return TestRandTreasures.ContainsKey(addressName);
        }


        // Apply all treasure-related patches to this map
        // addressName = See: needsPatching()
        // originalJson = The Json object to modify
        public void patchMapTreasures(string addressName, JsonNode originalJson)
        {
            // Is this a Map that we need to patch (for Treasures or other reasons)?
            if (!TestRandTreasures.ContainsKey(addressName))
            {
                return;
            }

            // What to patch? json_xpath -> kv_to_patch
            List<TreasureJsonPatch> patches = TestRandTreasures[addressName];
            Plugin.Log.LogInfo($"Patching Treasure Resource: {addressName} in {patches.Count} locations");

            // Patch the original asset
            PatchJsonTreasureAsset(addressName, originalJson, patches);
        }


        private static void PatchJsonTreasureAsset(string addressName, JsonNode rootNode, List<TreasureJsonPatch> patches)
        {
            // Should never happen
            if (rootNode is null)
            {
                Plugin.Log.LogError("Could not patch null asset (TODO: how?)");
                return;
            }

            // Now, modify our properties. We do them one at a time to keep it simple; we only ever do
            //   a dozen or so per map, so there's no need to interleave them.
            foreach (var tPatch in patches)
            {
                PatchTreasureJsonPath(rootNode, tPatch.json_xpath, tPatch.patches);
            }
        }


        // Patch a set of properties in a json object
        private static void PatchTreasureJsonPath(JsonNode rootNode, string[] xpath, Dictionary<String, String> keysNewValues)
        {

            Plugin.Log.LogInfo($"Patching json entry: /{String.Join('/',xpath)}");

            // Traverse to your destination node
            JsonNode currNode = JsonHelper.TraverseXPath(rootNode, xpath);
            if (currNode is null)
            {
                Plugin.Log.LogError($"Could not traverse to path...");
                return;
            }

            // We've found it, now modify it. Looks like this:
            //  [
            //    {
            //      "name": "accept_action_direction",
            //      "type": "int",
            //      "value": 15
            //    },
            //    ... and then many more. 
            if (currNode.GetType() != typeof(JsonArray))
            {
                Plugin.Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at: <properties>");
                return;
            }

            // Iterate over all of these, and track how many we changed
            int numModifiedProps = 0;
            JsonArray currArray = currNode.AsArray();
            for (int i = 0; i < currArray.Count; i++)
            {
                // This needs to be an object...
                currNode = currArray[i];
                if (currNode.GetType() != typeof(JsonObject))
                {
                    Plugin.Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at: <properties[{i}]>");
                    return;
                }

                // ...with known keys
                JsonObject currObj = currNode.AsObject();
                if (!(currObj.ContainsKey("name") && currObj.ContainsKey("type") && currObj.ContainsKey("value")))
                {
                    // Probably small enough to print this object...
                    Plugin.Log.LogError($"INVALID: Node at: <properties[{i}]> is missing name/type/value: {currObj.ToString()}");
                    return;
                }

                // Is it a key we care about?
                string nameStr = currObj["name"].GetValue<string>(); // TODO: check json type somewhere?
                if (keysNewValues.ContainsKey(nameStr))
                {
                    // Use the "type" field to guide us
                    string typeStr = currObj["type"].GetValue<string>();
                    if (typeStr == "bool")
                    {
                        bool newVal = Boolean.Parse(keysNewValues[nameStr]);
                        currObj["value"] = newVal;
                    }
                    else if (typeStr == "int")
                    {
                        int newVal = Int32.Parse(keysNewValues[nameStr]);
                        currObj["value"] = newVal;
                    }
                    else if (typeStr == "float")
                    {
                        float newVal = (float)Double.Parse(keysNewValues[nameStr]);
                        currObj["value"] = newVal;
                    }
                    else if (typeStr == "string")
                    {
                        // Save it as a string
                        currObj["value"] = keysNewValues[nameStr];
                    }
                    else
                    {
                        Plugin.Log.LogWarning($"Unknown Json type: {typeStr} for resource: {xpath}");

                        // Save it as a string and hope for the best! Expect a Kaboom later!
                        currObj["value"] = keysNewValues[nameStr];
                    }

                    numModifiedProps += 1;
                }
            }

            // Did we patch everything we expected to?
            if (numModifiedProps != keysNewValues.Count)
            {
                Plugin.Log.LogError($"INVALID: Expected to patch {numModifiedProps} properties; but we only patched {keysNewValues.Count}");
                return;
            }

        }

    }


}
