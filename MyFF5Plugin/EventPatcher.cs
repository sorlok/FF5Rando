using HarmonyLib;
using Iced.Intel;
using Il2CppSystem.Runtime.Remoting.Messaging;
using Last.Interpreter.Instructions.SystemCall;
using LibCpp2IL;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using static Last.Interpreter.Instructions.Format;

namespace MyFF5Plugin
{
    // Class that describes how to apply a patch to an Event json file
    // TODO: Yeah, we probably want to use inheritance for this one...
    class EventJsonPatch
    {
        public string[] json_xpath;     // Typically: ["Mnemonics", "[<number>]"]; we might want to just enforce this.
        public string[] expected_name;  // Always ["mnemonic", "label"]; both are checked (if non-empty) versus the value found at the json_xpath
        public string command;          // What to do: "Overwrite", "SetIVal", etc.
        
        // TODO: I think we want 'args_s', 'args_i', etc. 
        public string[] args;           // Arguments to the given command. May be null.

        public JsonNode jsonSnippet;    // Used by command like "Overwrite" to specify what new code to put where.
    }


    // This class has methods to help patch Events (scripts) used by the PR
    public class EventPatcher
    {
        // asset_path -> [entries, to, apply]
        private Dictionary<String, List<EventJsonPatch>> TestRandPatches = new Dictionary<string, List<EventJsonPatch>>();

        // Load the given patch file and parse it.
        public EventPatcher(string patchPath)
        {
            using (var reader = new StreamReader(patchPath))
            {
                readInData(reader);
            }
        }

        // Load from a Stream instead
        public EventPatcher(StreamReader reader)
        {
            readInData(reader);
        }

        // Used by the constructor to load all information from disk
        // Will *append* data from the reader if called manually after the constructor finishes.
        public void readInData(StreamReader reader)
        {
            StringBuilder jsonStr = null;  // If non-null, we're appending to a big json string
            EventJsonPatch currEvent = null; // Will be non-null if we're parsing json

            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine().Trim();

                // Are we in the middle of parsing json?
                if (jsonStr != null)
                {
                    if (line != "")
                    {
                        jsonStr.Append(line + " ");  // \n would work too
                    }
                    else
                    {
                        // Done with this command, reset
                        if (jsonStr.ToString().Length > 0)
                        {
                            currEvent.jsonSnippet = JsonNode.Parse(jsonStr.ToString());
                        }
                        currEvent = null;
                        jsonStr = null;
                    }

                    continue;
                }

                // Remove empty lines and comments.
                if (line == "" || line.StartsWith("#"))
                {
                    continue;
                }

                // We are looking for the next non-json line. 
                // However, try to help detect stray newlines in user input.
                if (!line.StartsWith("Assets"))
                {
                    Plugin.Log.LogError($"Invalid Assets path in Event patch; check for stray newlines!");
                    return;
                }

                // Try to parse an entry.
                // Note that the number of 'args' (params after 4) is based on the command.
                string[] parts = line.Split(',');
                if (parts.Length < 4)
                {
                    Plugin.Log.LogError($"Invalid line in Event patch: {line}");
                    return;
                }

                // Make and add a new Event, before we forget
                string asset_path = parts[0];
                if (!TestRandPatches.ContainsKey(asset_path))
                {
                    TestRandPatches[asset_path] = new List<EventJsonPatch>();
                }
                currEvent = new EventJsonPatch();
                TestRandPatches[asset_path].Add(currEvent);

                // Easy stuff
                currEvent.json_xpath = JsonHelper.SplitJsonXPath(parts[1]);
                currEvent.expected_name = parts[2].Split(':', 2);
                currEvent.command = parts[3];

                // Detect the command and set the args
                if (currEvent.command == "Overwrite")
                {
                    // How many entries to skip before overwriting.
                    currEvent.args = new string[] { parts[4] };
                }
                else if (currEvent.command.StartsWith("SpotIArray"))
                {
                    // Nothing; everything's in the JSON
                }
                else if (currEvent.command.StartsWith("SetSVal"))
                {
                    // Retrieve the index, and then also provide the value to set this to.
                    string sValIndexStr = currEvent.command.Substring(7);

                    int sValIndex = 0;
                    if (sValIndexStr.StartsWith("[") && sValIndexStr.EndsWith("]"))
                    {
                        sValIndex = Int32.Parse(sValIndexStr.Substring(1, sValIndexStr.Length - 2));
                    }
                    else
                    {
                        Plugin.Log.LogError($"Invalid SetSVal command+index: {currEvent.command}");
                        return;
                    }

                    currEvent.command = "SetSVal";
                    currEvent.args = new string[] { sValIndex.ToString(), parts[4] };
                }
                else
                {
                    Plugin.Log.LogError($"Unknown Command in Event patch: {currEvent.command}");
                    return;
                }

                // Finally, go into 'json parsing' mode
                jsonStr = new StringBuilder();
            }

            // Any pending event text?
            if (jsonStr != null && jsonStr.ToString().Length > 0)
            {
                currEvent.jsonSnippet = JsonNode.Parse(jsonStr.ToString());
            }
        }

        // Is this a resource we expect to patch?
        // addressName = Needs to match the Resource Unity is loading (note the lack of extension). E.g.:
        //               Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_e_0017
        public bool needsPatching(string addressName)
        {
            return TestRandPatches.ContainsKey(addressName);
        }


        // Apply all event-related patches to this map/script
        // addressName = See: needsPatching()
        // originalJson = The Json object to modify
        public void patchMapEvents(string addressName, JsonNode originalJson)
        {
            // Is this a Map that we need to patch (for Treasures or other reasons)?
            if (!TestRandPatches.ContainsKey(addressName))
            {
                return;
            }

            // What to patch? json_xpath -> kv_to_patch
            List<EventJsonPatch> patches = TestRandPatches[addressName];
            Plugin.Log.LogInfo($"Patching Event Resource: {addressName} in {patches.Count} locations");

            // Patch the original asset
            PatchJsonEventAsset(addressName, originalJson, patches);
        }

        private static void PatchJsonEventAsset(string addressName, JsonNode rootNode, List<EventJsonPatch> patches)
        {
            // Should never happen
            if (rootNode is null)
            {
                Plugin.Log.LogError("Could not patch null asset (TODO: how?)");
                return;
            }

            // Now, modify our properties. We do them one at a time to keep it simple; we only ever do
            //   a dozen or so per map, so there's no need to interleave them.
            foreach (var jPatch in patches)
            {
                PatchEventJsonPath(rootNode, jPatch);
            }
        }

        // Patch a set of properties in a json object
        private static void PatchEventJsonPath(JsonNode rootNode, EventJsonPatch patch)
        {

            Plugin.Log.LogInfo($"Patching json entry: /{String.Join('/', patch.json_xpath)}");

            // Traverse to your destination node
            JsonNode[] foundNodes = JsonHelper.TraverseXPathWithParent(rootNode, patch.json_xpath);
            if (foundNodes is null)
            {
                Plugin.Log.LogError($"Could not traverse to path...");
                return;
            }

            JsonNode parentNode = foundNodes[0];
            JsonNode currNode = foundNodes[1];

            // Some commands need objects; others need arrays
            if (patch.command == "Overwrite" || patch.command == "SetSVal")
            {
                if (currNode.GetType() != typeof(JsonObject))
                {
                    Plugin.Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at path.");
                    return;
                }
            }
            //
            else if (patch.command == "SpotIArray")
            {
                if (currNode.GetType() != typeof(JsonArray))
                {
                    Plugin.Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at path.");
                    return;
                }
            }

            // Double-check our mnemonic
            if (patch.expected_name.Length > 0 && patch.expected_name[0].Length > 0)
            {
                JsonObject currObj = currNode.AsObject();
                bool pass = false;
                string actMnemonic = "<Missing>";
                if (currObj.ContainsKey("mnemonic"))
                {
                    actMnemonic = currObj["mnemonic"].GetValue<string>(); // TODO: check type
                    if (actMnemonic == patch.expected_name[0])
                    {
                        pass = true;
                    }
                }

                if (!pass)
                {
                    Plugin.Log.LogError($"INVALID: Expected Mnemonic was \"{patch.expected_name[0]}\", but actual one was \"{actMnemonic}\"");
                    return;
                }
            }

            // Double-check our label
            if (patch.expected_name.Length > 1 && patch.expected_name[1].Length > 0)
            {
                JsonObject currObj = currNode.AsObject();
                bool pass = false;
                string actLbl = "<Missing>";
                if (currObj.ContainsKey("label"))
                {
                    actLbl = currObj["label"].GetValue<string>();
                    if (actLbl == patch.expected_name[1])
                    {
                        pass = true;
                    }
                }

                if (!pass)
                {
                    Plugin.Log.LogError($"INVALID: Expected Label was \"{patch.expected_name[1]}\", but actual one was \"{actLbl}\"");
                    return;
                }
            }

            // React to the command in question
            if (patch.command == "Overwrite")
            {
                JsonObject currObj = currNode.AsObject();
                if (patch.jsonSnippet.GetType() != typeof(JsonArray))
                {
                    Plugin.Log.LogError($"INVALID: Expected Array, not: {patch.jsonSnippet.GetType()} for patch element.");
                    return;
                }

                // HACK: What index is the index of the currNode in the parentNode?
                JsonArray parentArray = parentNode.AsArray();
                int startIndex = 0;
                for (int i=0; i < parentArray.Count; i++)
                {
                    if (parentArray[i] == currObj)
                    {
                        startIndex = i;
                        break;
                    }
                }

                PatchEventOverwrite(parentArray, startIndex, Int32.Parse(patch.args[0]), patch.jsonSnippet.AsArray());
            }

            // SpotIArray
            else if (patch.command == "SpotIArray")
            {
                JsonArray currArray = currNode.AsArray();
                if (patch.jsonSnippet.GetType() != typeof(JsonObject))
                {
                    Plugin.Log.LogError($"INVALID: Expected Object, not: {patch.jsonSnippet.GetType()} for patch element.");
                    return;
                }

                PatchEventSpotIArray(currArray, patch.jsonSnippet.AsObject());
            }

            // SetSVar
            else if (patch.command == "SetSVal")
            {
                JsonObject currObj = currNode.AsObject();
                PatchSetSVar(currObj, Int32.Parse(patch.args[0]), patch.args[1]);
            }

            // Unknown?
            else
            {
                Plugin.Log.LogError($"Unknown Command in Event patch: {patch.command}");
                return;
            }

        }


        private static void PatchEventOverwrite(JsonArray origMnemonics, int startIndex, int startOffset, JsonArray newMnemonics)
        {
            // Initial sanity check
            if (startIndex + startOffset + newMnemonics.Count > origMnemonics.Count)
            {
                Plugin.Log.LogError($"Mnemonic Buffer Overflow");
                return;
            }

            // What we found is a series of:
            //    {
            //      "label": "",
            //      "mnemonic": "Wait",
            //      "operands": ... etc.
            //    }, ...
            // We need to overwrite this with our own list, but we want to make sure we don't overwrite 
            //   anything with a non-empty label, since that may represent a Call() point in the script.
            int destIndex = startIndex + startOffset;
            int srcIndex = 0;
            while (srcIndex < newMnemonics.Count)
            {
                // Sanity check -- skip IF we are overwriting the very first item with a direct (0) offset:
                bool skipSanityCheck = (destIndex == startIndex) && (startOffset == 0);
                if (!skipSanityCheck)
                {
                    if (origMnemonics[destIndex].GetType() == typeof(JsonObject))
                    {
                        JsonObject testObj = origMnemonics[destIndex].AsObject();
                        if (testObj.ContainsKey("mnemonic") && testObj["mnemonic"].GetValue<string>() == "Nop")
                        {
                            if (testObj.ContainsKey("label") && testObj["label"].GetValue<string>() != "")
                            {
                                Plugin.Log.LogError($"BAD: Trying to overwrite label: {testObj["label"].GetValue<string>()}");
                                return;
                            }
                        }
                    }
                }

                // Else, just change it!
                // We have to make a copy; the one in the array already has a parent.
                JsonNode node = JsonNode.Parse(newMnemonics[srcIndex].ToJsonString()); // Really C#?
                srcIndex += 1;
                origMnemonics[destIndex] = node;
                destIndex += 1;
            }
        }


        private static void PatchEventSpotIArray(JsonArray origArray, JsonObject kvSpot)
        {
            // The json object is just a series of entries, but we need to deal with a few Json-isms
            foreach (var spot in kvSpot)
            {
                int index = Int32.Parse(spot.Key);
                int val = spot.Value.GetValue<int>();
                if (index >= 0 && index < origArray.Count)
                {
                    origArray[index] = val;
                }
                else
                {
                    Plugin.Log.LogError($"Could not patch element at index: {index} ; out of range of array: {origArray.Count}");
                }
            }
        }


        private static void PatchSetSVar(JsonObject origObj, int argOffset, string newVal)
        {
            // Hmm... we can just... do this?
            JsonNode foundNode = JsonHelper.TraverseXPath(origObj, new string[] { "operands", "sValues" });
            if (foundNode == null)
            {
                Plugin.Log.LogError($"BAD: No 'operands/sValues' in json object: {origObj.ToJsonString()}");
                return;
            }

            // Check type
            if (foundNode.GetType() != typeof(JsonArray))
            {
                Plugin.Log.LogError($"INVALID: Expected Array, not: {foundNode.GetType()} for sValues we're patching.");
                return;
            }

            // Make sure our array index is in bounds
            JsonArray foundArray = foundNode.AsArray();
            if (argOffset >= foundArray.Count)
            {
                Plugin.Log.LogError($"INVALID: Cannot set index: {argOffset} for sValues array of size: {foundArray.Count}");
                return;
            }

            // Patch it!
            foundArray[argOffset] = newVal;
        }

    }



}


