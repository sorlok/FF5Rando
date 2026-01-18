using Microsoft.VisualBasic;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using static Last.Camera.FrontRenderTarget.MainGameArea;


namespace MyFF5Plugin
{
    // Represents the "list of strings" that the PR stores for things. 
    // Preserves ordering, and allows you to replace vs. add strings safely.
    // We use this (instead of patching the text on the fly) to allow multiple patchers to interact with 
    //   the same resource.
    public class StringsAsset
    {
        // Key, MessageText
        private Dictionary<string, string> data = new Dictionary<string, string>();

        // List of keys in order, to preserve order when printing
        private List<string> keys = new List<string>();

        // Load from a string buffer
        public StringsAsset(string sourceData)
        {
            foreach (string lineR in sourceData.Split("\n"))
            {
                string line = lineR.Trim('\r'); // Remove trailing '\r'. We don't want to remove '\t'

                // Skip empty lines, if that's even a thing
                if (line.Length == 0)
                {
                    continue;
                }

                // Split ONCE
                string[] parts = line.Split("\t", 2);
                if (parts.Length != 2)
                {
                    Plugin.Log.LogError($"Message file contains invalid line: {line}");
                    return;
                }

                // Store the key in order
                keys.Add(parts[0]);

                // Store the message itself
                // Note that the "End Letter" is stored twice with the exact same text; 
                // our code will basically remove that, but TOO BAD, FIX YOUR DATA NEXT TIME!
                data[parts[0]] = parts[1];
            }
        }

        // Add/Update an entry. If it's new, it'll be printed at the end of the list
        public void setEntry(string key, string msg)
        {
            if (!data.ContainsKey(key))
            {
                keys.Add(key);
            }
            data[key] = msg;
        }

        // Convert this to a string that tries to mimic the PR's format as closely as possible.
        public string toAssetStr()
        {
            StringBuilder res = new StringBuilder();
            foreach (string key in keys)
            {
                res.Append($"{key}\t{data[key]}\r\n");
            }
            res.Append("\r\n");  // Seems like these end with an empty line.
            return res.ToString();
        }

    }


}
