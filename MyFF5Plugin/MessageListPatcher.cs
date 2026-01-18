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
        private List<string[]> messagePatches;  // (key, message)


        // Load from the file. We use commas instead of tabs.
        public MessageListPatcher(string patchPath)
        {
            using (var reader = new StreamReader(patchPath))
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
            // Should be pretty simple!
            foreach (string[] patch in messagePatches)
            {
                origMessageCsv.setEntry(patch[0], patch[1]);
            }
        }


    }
}
