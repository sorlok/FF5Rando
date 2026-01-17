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
        private Dictionary<String, Dictionary<String, Dictionary<String, String>>> TestRandTreasures; // path_ident -> { entry }

        // Load the given patch file and parse it.
        public TreasurePatcher(string patchPath)
        {
            TestRandTreasures = new Dictionary<string, Dictionary<string, Dictionary<string, string>>>();
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

                        Dictionary<String, String> entry = new Dictionary<string, string>();
                        for (int i = 0; i < columnNames.Length; i++)
                        {
                            entry[columnNames[i]] = row[i];
                        }

                        // Extract Keys, lest we patch the wrong thing
                        string key = entry["entity_default"];
                        string key2 = entry["json_xpath"];
                        entry.Remove("entity_default");
                        entry.Remove("json_xpath");

                        // Top-level key
                        if (!TestRandTreasures.ContainsKey(key))
                        {
                            TestRandTreasures[key] = new Dictionary<string, Dictionary<string, string>>();
                        }

                        // Second-level key
                        if (TestRandTreasures[key].ContainsKey(key2))
                        {
                            throw new Exception($"Duplicat treasure key: {key} + {key2}");
                        }
                        TestRandTreasures[key][key2] = entry;
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
        // originalJson = The Json objec to modify
        public void patchMapTreasures(string addressName, JsonNode originalJson)
        {
            // Is this a Map that we need to patch (for Treasures or other reasons)?
            if (!TestRandTreasures.ContainsKey(addressName))
            {
                return;
            }

            // What to patch? json_xpath -> kv_to_patch
            Dictionary<String, Dictionary<String, String>> patches = TestRandTreasures[addressName];
            Plugin.Log.LogInfo($"Patching Resource: {addressName} in {patches.Count} locations");

            // Patch the original asset
            PatchJsonTreasureAsset(addressName, originalJson, patches);
        }


        private static void PatchJsonTreasureAsset(string addressName, JsonNode rootNode, Dictionary<String, Dictionary<String, String>> patches)
        {
            // Should never happen
            if (rootNode is null)
            {
                Plugin.Log.LogError("Could not patch null asset (TODO: how?)");
                return;
            }

            // Now, modify our properties. We do them one at a time to keep it simple; we only ever do
            //   a dozen or so per map, so there's no need to interleave them.
            foreach (var xpath in patches.Keys)
            {
                PatchTreasureJsonPath(rootNode, xpath, patches[xpath]);
            }
        }


        // Patch a set of properties in a json object
        static void PatchTreasureJsonPath(JsonNode rootNode, string xpath, Dictionary<String, String> keysNewValues)
        {
            // Remove leading '/'
            if (xpath.StartsWith("/"))
            {
                xpath = xpath.Substring(1);
            }

            Plugin.Log.LogInfo($"Patching json entry: {xpath}");

            // Ok, start from the root
            string[] xparts = xpath.Split("/");
            JsonNode currNode = rootNode;
            foreach (var part in xparts)
            {
                // Arrays are special
                if (part.StartsWith("[") && part.EndsWith("]"))
                {
                    if (currNode.GetType() != typeof(JsonArray))
                    {
                        Plugin.Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at: {part}");
                        return;
                    }

                    int targetIndex = Int32.Parse(part.Substring(1, part.Length - 2));
                    if (targetIndex < 0 || targetIndex >= currNode.AsArray().Count)
                    {
                        Plugin.Log.LogError($"INVALID: Array element out of bounds: {part}");
                        return;
                    }
                    currNode = currNode.AsArray()[targetIndex];
                }

                // Normal object properties are simple
                else
                {
                    if (currNode.GetType() != typeof(JsonObject))
                    {
                        Plugin.Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at: {part}");
                        return;
                    }

                    if (!currNode.AsObject().ContainsKey(part))
                    {
                        Plugin.Log.LogError($"INVALID: Cannot find part: {part}");
                        return;
                    }
                    currNode = currNode.AsObject()[part];
                }
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
