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
    class CsvPartialPatch
    {
        // Column names, will always start with "id"; any other field is optional.
        public string[] header;

        // Values to patch; based on header name.
        public List<string[]> rows = new List<string[]>();
    }


    // Base class that defines the methods required for patching and unpatching any .csv resource.
    // Subclasses will essentially specialize this (via inheritance) and then handle all the bookkeeping.
    abstract class AssetPatcher//<AssetType> where AssetType : MasterBase
    {
        // Set of original objects (to restore), indexed by ID
        private Dictionary<int, MasterBase> originals = new Dictionary<int, MasterBase>();

        //
        public void applyCsvPatch(List<CsvPartialPatch> patches) // where AssetType : MasterBase
        {
            // Do each patch one by one
            foreach (var patch in patches)
            {
                // Each patch affects multiple resources
                foreach (var entry in patch.rows)
                {
                    // Retrieve the id we're affecting. This will always be column 0
                    int id = Int32.Parse(entry[0]);

                    // ...and its object from the game
                    // NOTE: This creates the object if its ID is unknown; we may want to back up a "stale" object
                    //       in the originals list in this case (similar to messages), although it's not clear what that
                    //       would look like.
                    MasterBase orig = getGameObject(id);

                    // Have we backed up this asset yet?
                    if (!originals.ContainsKey(id))
                    {
                        // Store this pristine object in our dictionary
                        originals[id] = orig;

                        // ...and modify a clone instead
                        orig = cloneGameObj(orig);
                        replaceAsset(id, orig);
                    }

                    // Ok, apply the patch to each property in this asset (skip property 0, which is id)
                    for (int i = 1; i < patch.header.Length; i++)
                    {
                        applyPatch(orig, patch.header[i], entry[i]);
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

        // TODO: We probably want patch/unpatch to be non-abstract (provide a general implementation) and then
        //       have private abstract methods here that we override to actually do the specific stuff.

        // Retrieve the game object that the game engine currently considers valid,
        // OR make a new game object with that ID if no such object exists.
        // TODO: We may want to check (somehow) that the ID of new stuff is the "next" valid ID.
        protected abstract MasterBase getGameObject(int id);

        // Make a copy of the game object in question, and return it
        protected abstract MasterBase cloneGameObj(MasterBase orig);

        // Apply a single patch entry; e.g., (<Item>, "hit_rate", "100") sets the hitRate property of the given Item to 100%
        protected abstract void applyPatch(MasterBase orig, string key, string value);

        // Copy the given Asset over wholesale, replacing what was there with the new value.
        protected abstract void replaceAsset(int id,  MasterBase newObj);
    }

    // Subclasses: TODO: These should go into their own file; they are very verbose!
    class ItemPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id)
        {
            var assets = MasterManager.Instance.GetList<Item>();
            if (!assets.ContainsKey(id))
            {
                assets[id] = new Item();   // Initial state shouldn't matter; the first patch is required to overwrite everything.
            }

            return assets[id];
        }

        protected override MasterBase cloneGameObj(MasterBase orig)
        {
            // Copy everything, and pray we're not missing anything!
            Item origItem = (Item)orig;
            Item newItem = new Item();
            newItem.Id = origItem.Id;
            newItem.SortId = origItem.SortId;
            newItem.TypeId = origItem.TypeId;
            newItem.SystemId = origItem.SystemId;
            newItem.ItemLv = origItem.ItemLv;
            newItem.AttributeId = origItem.AttributeId;
            newItem.AccuracyRate = origItem.AccuracyRate;
            newItem.DestroyRate = origItem.DestroyRate;
            newItem.StandardValue = origItem.StandardValue;
            newItem.RengeId = origItem.RengeId;
            newItem.MenuRengeId = origItem.MenuRengeId;
            newItem.BattleRengeId = origItem.BattleRengeId;
            newItem.InvalidReflection = origItem.InvalidReflection;
            newItem.PeriodId = origItem.PeriodId;
            newItem.ThrowFlag = origItem.ThrowFlag;
            newItem.PreparationFlag = origItem.PreparationFlag;
            newItem.DrinkFlag = origItem.DrinkFlag;
            newItem.MachineFlag = origItem.MachineFlag;
            newItem.ConditionGroupId = origItem.ConditionGroupId;
            newItem.BattleEffectAssetId = origItem.BattleEffectAssetId;
            newItem.MenuSeAssetId = origItem.MenuSeAssetId;
            newItem.MenuFunctionGroupId = origItem.MenuFunctionGroupId;
            newItem.BattleFunctionGroupId = origItem.BattleFunctionGroupId;
            newItem.Buy = origItem.Buy;
            newItem.Sell = origItem.Sell;
            newItem.SalesNotPossible = origItem.SalesNotPossible;
            return newItem;
        }

        protected override void applyPatch(MasterBase orig, string key, string value)
        {
            // Perhaps if I were a better programmer...
            Item origItem = (Item)orig;
            switch (key)
            {
                case "sort_id":
                    origItem.SortId = Int32.Parse(value);
                    break;
                case "type_id":
                    origItem.TypeId = Int32.Parse(value);
                    break;
                case "system_id":
                    origItem.SystemId = Int32.Parse(value);
                    break;
                case "item_lv":
                    origItem.ItemLv = Int32.Parse(value);
                    break;
                case "attribute_id":
                    origItem.AttributeId = Int32.Parse(value);
                    break;
                case "accuracy_rate":
                    origItem.AccuracyRate = Int32.Parse(value);
                    break;
                case "destroy_rate":
                    origItem.DestroyRate = Int32.Parse(value);
                    break;
                case "standard_value":
                    origItem.StandardValue = Int32.Parse(value);
                    break;
                case "renge_id":
                    origItem.RengeId = Int32.Parse(value);
                    break;
                case "menu_renge_id":
                    origItem.MenuRengeId = Int32.Parse(value);
                    break;
                case "battle_renge_id":
                    origItem.BattleRengeId = Int32.Parse(value);
                    break;
                case "invalid_reflection":
                    origItem.InvalidReflection = Int32.Parse(value);
                    break;
                case "period_id":
                    origItem.PeriodId = Int32.Parse(value);
                    break;
                case "throw_flag":
                    origItem.ThrowFlag = Int32.Parse(value);
                    break;
                case "preparation_flag":
                    origItem.PreparationFlag = Int32.Parse(value);
                    break;
                case "drink_flag":
                    origItem.DrinkFlag = Int32.Parse(value);
                    break;
                case "machine_flag":
                    origItem.MachineFlag = Int32.Parse(value);
                    break;
                case "condition_group_id":
                    origItem.ConditionGroupId = Int32.Parse(value);
                    break;
                case "battle_effect_asset_id":
                    origItem.BattleEffectAssetId = Int32.Parse(value);
                    break;
                case "menu_se_asset_id":
                    origItem.MenuSeAssetId = Int32.Parse(value);
                    break;
                case "menu_function_group_id":
                    origItem.MenuFunctionGroupId = Int32.Parse(value);
                    break;
                case "battle_function_group_id":
                    origItem.BattleFunctionGroupId = Int32.Parse(value);
                    break;
                case "buy":
                    origItem.Buy = Int32.Parse(value);
                    break;
                case "sell":
                    origItem.Sell = Int32.Parse(value);
                    break;
                case "sales_not_possible":
                    origItem.SalesNotPossible = Int32.Parse(value);
                    break;
                default:
                    Plugin.Log.LogError($"Unknown Item property: {key} (trying to set value to {value})");
                    break;
            }
        }

        protected override void replaceAsset(int id, MasterBase newObj)
        {
            MasterManager.Instance.GetList<Item>()[id] = (Item)newObj;
        }
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
                            currEntry.header = line.Split(',');
                            if (currEntry.header[0] != "id")
                            {
                                Plugin.Log.LogError($"Invalid .csv header line; 'id' must be first: {line}");
                                return;
                            }
                            continue;
                        }

                        // Any other line is a row of fields
                        string[] row = line.Split(',');
                        if (row.Length != currEntry.header.Length)
                        {
                            Plugin.Log.LogError($"Invalid .csv row line; expected {currEntry.header.Length} entries, but got {row.Length} in: {line}");
                            return;
                        }

                        // Save it
                        currEntry.rows.Add(row);
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

        // Is this a resource we expect to patch?
        // addressName = Needs to match the Resource Unity is loading (note the lack of extension). E.g.:
        //               Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_e_0017
        /*
        public bool needsPatching(string addressName)
        {
            return TestRandPatches.ContainsKey(addressName);
        }
        */

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


