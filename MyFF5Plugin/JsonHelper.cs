using HarmonyLib;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

namespace MyFF5Plugin
{
    // Various functions that we use in a few places
    public class JsonHelper
    {
        // Turn:
        //   "/Mnemonics/[0]"
        // ...into:
        //   ["Mnemonics", "[0]"]
        public static string[] SplitJsonXPath(string xpath)
        {
            // Remove leading "/"
            if (xpath.StartsWith("/"))
            {
                xpath = xpath.Substring(1);
            }

            // Now just split it.
            return xpath.Split("/");
        }

        // Follow an xpath-like string. For example:
        //   ["Mnemonics", "[0]"]
        // ...will traverse from the root to the "Mnemonics" property,
        // and then to the first element in that array.
        // This function returns an array with [0] = parent and [1] = the node searched for, which
        //   is useful if you need to loop over the array that the child node is in. 
        // See: TraverseXPath() when you just need the searched-for node and not the parent.
        // See: SplitJsonXPath() for the normal input format: "/Mnemonics/[0]"
        public static JsonNode[] TraverseXPathWithParent(JsonNode rootNode, string[] json_xpath)
        {
            // Ok, start from the root
            JsonNode prevNode = null;
            JsonNode currNode = rootNode;
            foreach (var part in json_xpath)
            {
                // Save the parent!
                prevNode = currNode;

                // Arrays are special
                if (part.StartsWith("[") && part.EndsWith("]"))
                {
                    if (currNode.GetType() != typeof(JsonArray))
                    {
                        Plugin.Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at: {part}");
                        return null;
                    }

                    int targetIndex = Int32.Parse(part.Substring(1, part.Length - 2));
                    if (targetIndex < 0 || targetIndex >= currNode.AsArray().Count)
                    {
                        Plugin.Log.LogError($"INVALID: Array element out of bounds: {part}");
                        return null;
                    }
                    currNode = currNode.AsArray()[targetIndex];
                }

                // We allow a 'search for object with this property' shorthand, to avoid counting IDs manually.
                // E.g., "{id=42}" looks through the current *array* for an object with id=42
                // For now, I guess we do string comparison? Seems pretty reasonable...
                else if (part.StartsWith("{") && part.EndsWith("}"))
                {
                    // Parse the key
                    string[] parts = part.Substring(1, part.Length - 2).Split("=");
                    string key = parts[0];
                    string val = parts[1];

                    if (currNode.GetType() != typeof(JsonArray))
                    {
                        Plugin.Log.LogError($"INVALID: Expected Array (for id search), not: {currNode.GetType()} at: {part}");
                        return null;
                    }

                    // Search for it
                    bool foundIt = false;
                    foreach (var candidateNode in currNode.AsArray())
                    {
                        if (candidateNode.GetType() != typeof(JsonObject))
                        {
                            Plugin.Log.LogError($"INVALID: Expected Object (for id search), not: {candidateNode.GetType()} at: {part}");
                            return null;
                        }

                        if (candidateNode.AsObject().ContainsKey(key))
                        {
                            if (candidateNode.AsObject()[key].ToJsonString() == val)
                            {
                                currNode = candidateNode;
                                foundIt = true;
                            }
                        }
                    }

                    if (!foundIt)
                    {
                        Plugin.Log.LogError($"INVALID: Could not find {key},{val} at: {part}");
                        return null;
                    }
                }

                // Normal object properties are simple
                else
                {
                    if (currNode.GetType() != typeof(JsonObject))
                    {
                        Plugin.Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at: {part}");
                        return null;
                    }

                    if (!currNode.AsObject().ContainsKey(part))
                    {
                        Plugin.Log.LogError($"INVALID: Cannot find part: {part}");
                        return null;
                    }
                    currNode = currNode.AsObject()[part];
                }
            }

            // We found it!
            return [prevNode, currNode];
        }


        // Retrieve just the node, not the parent
        public static JsonNode TraverseXPath(JsonNode rootNode, string[] json_xpath)
        {
            JsonNode[] res = TraverseXPathWithParent(rootNode, json_xpath);
            if (res is null)
            {
                return null;
            }
            return res[1];
        }

    }
}
