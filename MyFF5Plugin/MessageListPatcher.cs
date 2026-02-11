using Last.Management;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

namespace MyFF5Plugin
{

    // This patches the "message list" Assets (sometimes called "strings" assets) that are basic
    // <key, value> entries used to populate message boxes, system settings, etc.
    public class MessageListPatcher
    {
        // Typically: Assets/GameAssets/Serial/Data/Message/story_mes_en
        private string asset_path;

        // Messages <Key, Value>. Stored in a list to ensure a consistent file output
        // TODO: We can't apply this patch to the resource; we need to apply it "live".
        //       Rework this to a Dictionary, avoid the asset path, etc.
        private List<string[]> messagePatches;  // (key, message)

        // Set of strings we've patched, along with their original values (so we can restore them when loading a "new" game).
        // Note: We put our custom message keys here with an "original" value of "ERROR: OLD MESSAGE" -- this allows us to find
        //       any edge cases while also avoiding removing messages from the data structure (which I don't trust).
        // WARNING: Make sure you pass the exact same thing in to patchAllStrings() and unpatchAllStrings() every time, or else
        //          you'll get drift. (Maybe we want to pass a lambda to the constructor instead, to enforce this?)
        private Dictionary<string, string> modMessageDefaults = new Dictionary<string, string>();


        // Load from the file. We use commas instead of tabs.
        public MessageListPatcher(string patchPath)
        {
            using (var reader = new StreamReader(patchPath))
            {
                readInData(reader);
            }
        }

        // Load from a Stream
        public MessageListPatcher(StreamReader reader)
        {
            readInData(reader);
        }

        // Used by the constructor to load all information from disk
        void readInData(StreamReader reader)
        {
            messagePatches = new List<string[]>();
            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine().Trim();

                // Skip comments, empty lines
                if (line == "" || line.StartsWith("#"))
                {
                    continue;
                }

                // First line must be a path, which will likely start with 'Assets'
                if (asset_path is null)
                {
                    if (!line.StartsWith("Assets"))
                    {
                        Plugin.Log.LogError($"Invalid Assets path in Message patch; check for stray newlines!");
                        return;
                    }

                    asset_path = line;
                    continue;
                }

                // Remaining lines are pretty simple
                string[] parts = line.Split(',', 2);
                if (parts.Length != 2)
                {
                    Plugin.Log.LogError($"Invalid Message line: {line}");
                    return;
                }

                messagePatches.Add(parts);
            }
        }


        // Patch all string entries into the game's dictionary
        // WARNING: 'gameDict' may have been modified by us; be careful to track your assumptions here.
        //          We try to track this with 'modMessageDefaults', and to restore them when needed.
        public void patchAllStrings(Il2CppSystem.Collections.Generic.Dictionary<string,string> gameDict)
        {
            foreach (var entry in messagePatches)
            {
                string key = entry[0];
                string value = entry[1];

                // Have we not saved a default yet?
                if (!modMessageDefaults.ContainsKey(key))
                {
                    // Does a default exist in the base game?
                    if (gameDict.ContainsKey(key))
                    {
                        modMessageDefaults[key] = gameDict[key];
                    }
                    else
                    {
                        modMessageDefaults[key] = $"ERROR: STALE MESSAGE: {key}";
                    }
                    //Log.LogWarning($"SAVING: {entry.Key} => {modMessageDefaults[entry.Key]}");
                }

                // Patch it
                gameDict[key] = value;
            }
        }

        // Unpatch everything back to default. This leaves "new" strings with an error message for easy identification
        public void unPatchAllStrings(Il2CppSystem.Collections.Generic.Dictionary<string, string> gameDict)
        {
            // Clear our modified messages
            foreach (var entry in modMessageDefaults)
            {
                gameDict[entry.Key] = entry.Value;
            }
        }


        // Is this a resource we expect to patch?
        // addressName = Needs to match the Resource Unity is loading (note the lack of extension). E.g.:
        //               Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_e_0017
        public bool needsPatching(string addressName)
        {
            return asset_path == addressName;
        }

        // Apply all event-related patches to this message
        // addressName = See: needsPatching()
        // origMessageCsv = The text to modify, stored in an easy accessor.
        public void patchMessageStrings(string addressName, StringsAsset origMessageCsv)
        {
            if (!needsPatching(addressName))
            {
                return;
            }

            // Should be pretty simple!
            foreach (string[] patch in messagePatches)
            {
                origMessageCsv.setEntry(patch[0], patch[1]);
            }
        }


    }
}
