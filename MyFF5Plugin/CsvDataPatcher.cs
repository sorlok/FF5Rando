using Last.Data.Master;
using System;
using System.Collections.Generic;
using System.IO;


namespace MyFF5Plugin
{
    // Class that describes how to apply a patch to the master "data" .csv files
    // We can do partial patches, so one patch might do:
    //   id,accuracy_rate
    //    2,0.75
    // ..and a separate patch could do:
    //   id,preparation_flag,drink_flag
    //    2,               1,         1
    //    5,               0,         1
    // ..and they'd all be merged correctly into the final item(s).
    // Special case: If there's only 1 string inside the header, then we are adding *new* assets.
    //   In this case, each row will also only have 1 entry each (in the string[] array).
    //   This is safe because "id" is required at all times, and having just a single entry of "id"
    //   is pointless (and checked). We use "new" as a concept to make item ID checks more reliable,
    //   and to use the more robust "new Whatever(<csv_string>)" constructor for assets.
    class CsvPartialPatch
    {
        // Column names, will always start with "id"; any other field is optional.
        public string[] header;

        // Values to patch; based on header name.
        public List<string[]> rows = new List<string[]>();
    }


    // Base class that defines the methods required for patching and unpatching any .csv resource.
    // Subclasses will essentially specialize this (via inheritance) and then handle all the bookkeeping.
    abstract class AssetPatcher //<AssetType> where AssetType : MasterBase
    {
        // Set of original objects (to restore), indexed by ID
        private Dictionary<int, MasterBase> originals = new Dictionary<int, MasterBase>();

        //
        public void applyCsvPatch(List<CsvPartialPatch> patches) // where AssetType : MasterBase
        {
            // Do each patch one by one
            foreach (var patch in patches)
            {
                // Are we adding a new entry or modifying an existing one?
                bool isNew = patch.header.Length == 1;

                // Each patch affects multiple resources
                foreach (var entry in patch.rows)
                {
                    // Retrieve the id we're affecting. This will always be column 0
                    int id = isNew ? Int32.Parse(entry[0].Split(',')[0]) : Int32.Parse(entry[0]);

                    // ...and its object from the game
                    // NOTE: This creates the object if its ID is unknown; we may want to back up a "stale" object
                    //       in the originals list in this case (similar to messages), although it's not clear what that
                    //       would look like.
                    MasterBase orig = getGameObject(id, isNew ? entry[0] : null);
                    if (orig == null)
                    {
                        Plugin.Log.LogError($"Could not retrieve a {(isNew ? "new" : "existing")} asset with id: {id}");
                        return;
                    }

                    // Have we backed up this asset yet?
                    if (!originals.ContainsKey(id))
                    {
                        Plugin.Log.LogWarning($"Backing up original and cloning: {id}");

                        // Store this pristine object in our dictionary
                        originals[id] = orig;

                        // ...and modify a clone instead
                        orig = cloneGameObj(orig);
                        replaceAsset(id, orig);
                    }

                    // Ok, apply the patch to each property in this asset (skip property 0, which is id)
                    if (!isNew)
                    {
                        for (int i = 1; i < patch.header.Length; i++)
                        {
                            Plugin.Log.LogWarning($"Patching value: {patch.header[i]} => {entry[i]}");
                            applyPatch(orig, patch.header[i], entry[i]);
                        }
                    }
                }
            }
        }

        //
        public void unpatchCsvPatches()
        {
            // Simply revert every object to its original value.
            // Note that this will leave our "new" IDs in a weird state (basically empty items), but that's probably fine.
            foreach (var asset in originals)
            {
                replaceAsset(asset.Key, asset.Value);
            }
        }

        // Retrieve the game object that the game engine currently considers valid,
        // OR make a new game object with that ID if no such object exists.
        // Initial state shouldn't matter; the first patch is required to overwrite everything.
        // Note: id's don't have to be contiguous; the main game skips lots of items (in "content", at least),
        //       and the MasterManager retrieves Dictionaries of objects, which implies that ordering doesn't matter.
        // TODO: If newCsvStr is non-null, we are expecting to add a NEW object with this ID; else, we're retrieving an
        //       existing one. If this assumption fails, return null.
        protected abstract MasterBase getGameObject(int id, string newCsvStr);

        // Copy the given Asset over wholesale, replacing what was there with the new value.
        protected abstract void replaceAsset(int id, MasterBase newObj);

        // Make a copy of the game object in question, and return it
        protected abstract MasterBase cloneGameObj(MasterBase orig);

        // Apply a single patch entry; e.g., (<Item>, "hit_rate", "100") sets the hitRate property of the given Item to 100%
        protected abstract void applyPatch(MasterBase orig, string key, string value);

    }


    // This class has methods to help patch Events (scripts) used by the PR
    // Note that we do a basic "patch+unpatch", similar to MessageListPatcher.
    // This is because patching Generic functions (MasterManger.Get<T>) is beyond me.
    // For this to work, we require:
    //   * Any "new" entry (custom items, etc.) must *always* specify a full row of data; otherwise, you'll get 
    //     default values for some columns, and you should not rely on defaults.
    //   * We leave the stale "custom" items in place when unpatching, since I'm worried about removing entries from this list.
    public class CsvDataPatcher
    {
        // asset_path -> [entries, to, apply]
        private Dictionary<String, List<CsvPartialPatch>> TestRandPatches = new Dictionary<string, List<CsvPartialPatch>>();


        // Set of assets we've patched, along with their original values (so we can restore them when loading a "new" game).
        // NOTE: Be very careful not to let these get out of sync when you modify this class. We try to wrap everything
        //       in a class to encapsulate the "modify" and "roll back" behaviors. But it's a little fragile.
        // key = the Asset path (same as in TestRandPatches)
        // value = some subclass that handles modifying this type.
        private Dictionary<string, AssetPatcher> assetModifiers = new Dictionary<string, AssetPatcher>()
        {
            { "Assets/GameAssets/Serial/Data/Master/item", new ItemPatcher() },
            { "Assets/GameAssets/Serial/Data/Master/content", new ContentPatcher() },
            { "Assets/GameAssets/Serial/Data/Master/monster", new MonsterPatcher() },
            { "Assets/GameAssets/Serial/Data/Master/monster_party", new MonsterPartyPatcher() },
        };



        // Load the given patch file and parse it.
        public CsvDataPatcher(string patchPath)
        {
            using (var reader = new StreamReader(patchPath))
            {
                readInData(reader);
            }
        }

        // Load from a Stream instead
        public CsvDataPatcher(StreamReader reader)
        {
            readInData(reader);
        }

        // Used by the constructor to load all information from disk
        // Will *append* data from the reader if called manually after the constructor finishes.
        private void readInData(StreamReader reader)
        {
            CsvPartialPatch currEntry = null; // Will be non-null as we parse table entries.

            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine().Trim();

                // Are we in the middle of parsing a table?
                if (currEntry != null)
                {
                    if (line != "")
                    {
                        // First row is always headers
                        if (currEntry.header == null)
                        {
                            // A "+" at the start of this line indicats an "add"
                            if (line.StartsWith("+"))
                            {
                                // TODO: We could presumably check that the header string is exactly correct (via the asset patcher)
                                currEntry.header = new string[] { line.Substring(1) };
                            }
                            else
                            {
                                currEntry.header = line.Split(',');
                            }

                            // Check: we must always list the ID first.
                            if (currEntry.header[0] != "id" && !currEntry.header[0].StartsWith("id,"))
                            {
                                Plugin.Log.LogError($"Invalid .csv header line; 'id' must be first: {line}");
                                return;
                            }

                            // Sanity check; we can't use a single-entry row
                            if (currEntry.header.Length == 1 && currEntry.header[0] == "id")
                            {
                                Plugin.Log.LogError($"Invalid .csv header line; must have at least 2 columns: {line}");
                                return;
                            }

                            continue;
                        }

                        // Any other line is a row of fields (or a "new" item)
                        if (currEntry.header.Length == 1)
                        {
                            // Add new
                            string[] row = new string[] { line };
                            int rowCommas = row[0].Split(',').Length;
                            int headerCommas = currEntry.header[0].Split(',').Length;
                            if (rowCommas != headerCommas)
                            {
                                Plugin.Log.LogError($"Invalid .csv row line; expected {rowCommas} entries, but got {headerCommas} in: {line}");
                                return;
                            }

                            // Save it
                            currEntry.rows.Add(row);
                        }
                        else
                        {
                            // Modify existing
                            string[] row = line.Split(',');
                            if (row.Length != currEntry.header.Length)
                            {
                                Plugin.Log.LogError($"Invalid .csv row line; expected {currEntry.header.Length} entries, but got {row.Length} in: {line}");
                                return;
                            }

                            // Save it
                            currEntry.rows.Add(row);
                        }
                    }
                    else
                    {
                        // Done with this command, reset
                        currEntry = null;
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
                    Plugin.Log.LogError($"Invalid Assets path in Csv patch; check for stray newlines!");
                    return;
                }

                // Make and add a new Event, before we forget
                string asset_path = line.Trim();
                if (!TestRandPatches.ContainsKey(asset_path))
                {
                    TestRandPatches[asset_path] = new List<CsvPartialPatch>();
                }
                currEntry = new CsvPartialPatch();
                TestRandPatches[asset_path].Add(currEntry);
            }
        }


        public void patchAllCsvs()
        {
            // Just go one by one
            foreach (var patch in TestRandPatches)
            {
                // We have to add these manually (and it's a slog), so we don't support them all right out the gate.
                if (!assetModifiers.ContainsKey(patch.Key))
                {
                    Plugin.Log.LogError($"Don't know how to patch 'master' (csv) asset of type: {patch.Key}");
                    continue;
                }

                // Apply the patch
                assetModifiers[patch.Key].applyCsvPatch(patch.Value);
            }
        }

        public void unPatchAllCsvs()
        {
            // Just go one by one
            foreach (var patch in TestRandPatches)
            {
                // Apply the patch
                foreach (var asset in assetModifiers)
                {
                    assetModifiers[asset.Key].unpatchCsvPatches();
                }
            }
        }
    }


}


