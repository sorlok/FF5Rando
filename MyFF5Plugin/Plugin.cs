using AsmResolver.PE.Exports;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Il2CppSystem.Linq;
using Last.Data;
using Last.Data.User;
using Last.Interpreter.Instructions;
using Last.Management;
using Last.Scene;
using Last.Systems;
using Last.UI;
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Xml.Linq;
using UnityEngine;
using UnityEngine.InputSystem.Interactions;
using static UnityEngine.InputSystem.Utilities.JsonParser;

namespace MyFF5Plugin;

[BepInPlugin(MyPluginInfo.PLUGIN_GUID, MyPluginInfo.PLUGIN_NAME, MyPluginInfo.PLUGIN_VERSION)]
// [BepInDependency("com.bepinex.plugin.important")] // TODO: We can depend on Magicite!
[BepInProcess("FINAL FANTASY V.exe")]
public class Plugin : BasePlugin
{
    internal static new ManualLogSource Log;

    // Will auto load from out own config file
    private ConfigEntry<string> cfgCustomIntro;

    // TODO: Proper state variable
    private static UserDataManager BlahMgr;  // TODO: We can probably just use UserDataManager.Instance -- that seems to be the pattern
    private static Il2CppSystem.Collections.Generic.List<Last.Data.User.OwnedItemData> BlahItems;

    // asset_path -> { json_xpath -> { entry_key_values } }, where asset_path is what Unity expects to see:
    //   Assets/GameAssets/Serial/Res/Map/Map_20011/Map_20011_1/entity_default
    // ...and json_xpath looks like this:
    //   /layers/0/objects/2
    // ...which is an XPath-like way of referring to something we need to change in our json files
    // The entry_key_values is a map of keys to change within that xpath
    private static Dictionary<String, Dictionary<String, Dictionary<String, String>>> TestRandTreasures; // path_ident -> { entry }


    public override void Load()
    {
        Log = base.Log;

        // Set up this config entry
        cfgCustomIntro = Config.Bind("General", "CustomIntro", "Nothing to see here, folks!", "Custom message to show when starting the plugin.");

        // Seems like we need to inject our class into the game so that Unity can interact with it? I guess?
        ClassInjector.RegisterTypeInIl2Cpp<Marquee>();
        ClassInjector.RegisterTypeInIl2Cpp<Engine>();

        // Create an instance of our Marquee, so that we can interact with it later.
        // You can access this later via Marquee.Instance()
        // I *think* this causes it to be added to the scene and awakened.
        string name = typeof(Marquee).FullName;
        GameObject singleton = new GameObject(name);
        // Don't show this in the hierarchy, don't save it to the Scene, don't unload it via "UnloadUnusedAssets()"
        // Our script will manage this singleton entirely.
        singleton.hideFlags = HideFlags.HideAndDontSave;
        // If we don't do this, Unity will remove the GameObject when we change scenes
        GameObject.DontDestroyOnLoad(singleton);
        // Add the Marquee as a resource (component)
        Marquee component = singleton.AddComponent<Marquee>();
        if (component is null)
        {
            GameObject.Destroy(singleton);
            throw new Exception($"The object is missing the required component: {name}");
        }
        Engine engine = singleton.AddComponent<Engine>();
        if (engine is null)
        {
            GameObject.Destroy(singleton);
            throw new Exception($"The object is missing the required component: Engine");
        }


        // Try patching methods with Harmony
        PatchMethods();

        // Plugin startup logic
        Log.LogInfo($"Plugin {MyPluginInfo.PLUGIN_GUID} is loaded; custom message: {cfgCustomIntro.Value}");

        // Load "test" randomizer files?
        LoadTestRandoFiles();
    }


    private void LoadTestRandoFiles()
    {
        string treasRandPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_treasure_input.csv");
        Log.LogInfo($"Loading random treasure from path: {treasRandPath}");

        // Just read it manually; this is config, not a "resource"
        TestRandTreasures = new Dictionary<string, Dictionary<string, Dictionary<string, string>>>();
        string[] columnNames = null;
        using (var reader = new StreamReader(treasRandPath))
        {
            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine().Replace("\r", "");

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


    private void PatchMethods()
    {
        try
        {
            Log.LogInfo("Patching methods...");
            Harmony harmony = new Harmony("MyFF5Plugin");
            harmony.PatchAll(Assembly.GetExecutingAssembly());
        }
        catch (Exception ex)
        {
            throw new Exception("Failed to patch methods.", ex);
        }
    }



    // Save pointer?
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.AddOwnedItem), new Type[] { typeof(int), typeof(int) })]
    public static class OwnedItemClient_AddOwnedItem
    {
        public static void Prefix(int contentId, int count, OwnedItemClient __instance)
        {
            // Save it!
            Log.LogInfo($"XXXXX =====> OwnedItemClient::AddOwnedItem[1]({contentId},{count}) called for: {__instance.Pointer}");
        }
    }
    //
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.AddOwnedItem), new Type[] { typeof(Last.Data.Master.Content), typeof(int) })]
    public static class OwnedItemClient_AddOwnedItem2
    {
        public static void Prefix(Last.Data.Master.Content targetData, int count, OwnedItemClient __instance)
        {
            Log.LogInfo($"XXXXX =====> OwnedItemClient::AddOwnedItem[2](({targetData.MesIdName},{targetData.TypeId},{targetData.Id}),{count}) called for: {__instance.Pointer}");
        }
    }
    //
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.CreateOwnedItem), new Type[] { typeof(Last.Data.Master.Content), typeof(int) })]
    public static class OwnedItemClient_CreateOwnedItem
    {
        public static void Prefix(Last.Data.Master.Content content, int count, OwnedItemClient __instance)
        {
            Log.LogInfo($"XXXXX =====> OwnedItemClient::CreateOwnedItem[](({content.MesIdName},{content.TypeId},{content.Id}),{count}) called for: {__instance.Pointer}");
        }
    }


    // Trying to understand this
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.RemoveOwnedItem), new Type[] { typeof(int), typeof(int) })]
    public static class OwnedItemClient_RemoveOwnedItem
    {
        public static void Prefix(int contentId, int count, OwnedItemClient __instance)
        {
            // Save it!
            Log.LogInfo($"XXXXX =====> OwnedItemClient::RemoveOwnedItem[1]({contentId},{count}) called.");
        }
    }
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.RemoveOwnedItem), new Type[] { typeof(int), typeof(int), typeof(int) })]
    public static class OwnedItemClient_RemoveOwnedItem2
    {
        public static void Prefix(int itemType, int itemId, int count, OwnedItemClient __instance)
        {
            // Save it!
            Log.LogInfo($"XXXXX =====> OwnedItemClient::RemoveOwnedItem[2]({itemType}, {itemId},{count}) called.");
        }
    }

    // These IDs are working perfectly, no need to add/sub 1
    // Elixir, 1, 13
    // Leather Armor, 3, 40
    // Whip, 2, 104


    // Grabbing an item
    /*
    [HarmonyPatch(typeof(ShopUtility), nameof(ShopUtility.BuyItem), new Type[] { typeof(int), typeof(int) })]
    public static class ShopUtility_BuyItem
    {
        public static void Prefix(int productId, int count)
        {
            Log.LogInfo($"XXXXX =====> ShopUtility.BuyItem({productId} , {count})");
            //return true;
        }
    }*/
    //
    [HarmonyPatch(typeof(ShopUtility), nameof(ShopUtility.BuyItem), new Type[] { typeof(ShopProductData), typeof(int) })]
    public static class ShopUtility_BuyItem2
    {
        public static void Prefix(ShopProductData data, int count)
        {
            Log.LogInfo($"XXXXX =====> ShopUtility.BuyItem[pre]({data.ProductId} , {count})");
            InspectItems();

            // TEMP: Try giving the player an Iron Armor
            int myId = 0;
            foreach (var item in BlahMgr.normalOwnedItems)
            {
                Log.LogInfo($"######## ({item.key}) => {item.value.Name} , {item.value.Count}");
                myId = item.key;
                break;
            }

            // Here we GOOOOO
            // TODO: They had something important to say about making 'new' items...
            // TODO: Actually, we should probably just use one of the many "add item" API calls in the game...
            //ShopUtility.BuyItem(89, 1);  // Oops, infinite loop when called within a shop (duh!)
            //External.Item.GetItem();
            //OwnedItemData newItem = new OwnedItemData((IntPtr)myId);
            //BlahMgr.normalOwnedItems.Add(myId, newItem);


            //BlahMgr.normalOwnedItems.Add(89)
        }
        public static void Postfix(ShopProductData data, int count)
        {
            Log.LogInfo($"XXXXX =====> ShopUtility.BuyItem[post]({data.ProductId} , {count})");
            InspectItems();
        }
        private static void InspectItems()
        {
            // Trying to figure out *how* an item is bought.
            // TODO: WIP!
            Log.LogInfo($"UserDataManager::normalItems PTR: {BlahMgr.normalOwnedItems.Pointer}");
            Log.LogInfo($"Saved Cloned Item List PTR: {BlahItems.Pointer}");
            Log.LogInfo($"UserDataManager::normalItems COUNT: {BlahMgr.normalOwnedItems.Count}");
            Log.LogInfo($"Saved Cloned Item List COUNT: {BlahItems.Count}");
        }
    }

    // TODO: Maybe patch the get/set for normalOwnedItems in general?
    // NOTE: We don't call 'GetAllOwnedItemsClone' or 'GetImportantItemsClone' anywhere that I can see.
    [HarmonyPatch(typeof(UserDataManager), nameof(UserDataManager.GetOwnedItemsClone))]
    public static class UserDataManager_GetOwnedItemsClone
    {
        public static void Postfix(UserDataManager __instance, Il2CppSystem.Collections.Generic.List<Last.Data.User.OwnedItemData> __result)
        {
            if (__result == null)
            {
                // Log.LogInfo($"XXXXX =====> UserDataManager::GetOwnedItemsClone() => <null>");
            }
            else
            {
                // Log.LogInfo($"XXXXX =====> UserDataManager::GetOwnedItemsClone() => {__result.Count} , {__instance.normalOwnedItems.Count}");
                // Log.LogInfo($"XXXXX =====> UserDataManager::GetOwnedItemsClone() PTR {__result.Pointer} , {__instance.normalOwnedItems.Pointer}");
            }

            // TEMP: SAVE
            BlahMgr = __instance;
            BlahItems = __result;
        }
    }




    // TODO: ITEMS with {__instance.NormalOwnedItemList}   --- can we just save it on "set"?



    // TODO: Testing
    [HarmonyPatch(typeof(SceneLoadTask), nameof(SceneLoadTask.LoadUnityScene), new Type[] { typeof(string), typeof(string), typeof(UnityEngine.SceneManagement.LoadSceneMode) })]
    public static class SceneLoadTask_LoadUnityScene
    {
        public static void Prefix(string loadAssetGroup, string loadSceneName, UnityEngine.SceneManagement.LoadSceneMode loadSceneMode, SceneLoadTask __instance)
        {
            //Log.LogInfo($"XXXXX =====> SceneLoadTask::LoadUnityScene({loadSceneName})");
        }
    }

    // Also
    [HarmonyPatch(typeof(SceneManager), nameof(SceneManager.ChangeScene))]
    public static class SceneManager_ChangeScene
    {
        public static void Prefix(SceneManager __instance)
        {
            //Log.LogInfo($"XXXXX =====> SceneManager::ChangeScene[pre] => {__instance.currentSceneName}");
        }
        public static void Postfix(SceneManager __instance)
        {
            //Log.LogInfo($"XXXXX =====> SceneManager::ChangeScene[post] => {__instance.currentSceneName}");
        }
    }


    /*
    // TODO: See what this does:
    public Il2CppSystem.Collections.IEnumerator OpenTreasureBox(Last.Entity.Field.FieldTresureBox entity)
    Member of Last.Map.EventAction

    // Not sure why this is here and a string:
public static string OpenTresureBox { get; set; }
    Member of Last.Map.EventActionDefine

    // Track this too:
public Il2CppSystem.Collections.IEnumerator EventOpenTresureBox(Last.Entity.Field.FieldTresureBox tresureBoxEntity, [bool after = False], [bool message = True])
    Member of Last.Map.EventActionTreasure


    // Would be good to track scripts with this:
public bool RunScript(string scriptName, bool startChangeState, bool endChangeState)
    Member of Last.Map.EventActionScript

    // Try seing how this relates to the other functions (presumably it dispatches?)
public virtual void EventOpenTresureBox(Last.Entity.Field.FieldTresureBox tresureBoxEntity, [bool after = False], [bool message = True])
    Member of Last.Map.EventProcedure
    */


    // TODO: Testing constructor patching
    // Note that the default Constructor is never called.
    [HarmonyPatch(typeof(OwnedItemClient), MethodType.Constructor, new[] { typeof(IntPtr) })]
    public class GameFrameworkCtorPatch1
    {
        public static void Postfix(IntPtr pointer, OwnedItemClient __instance)
        {
            //Log.LogInfo($"################## OwnedItemClient({pointer}) => {__instance.Pointer}");
        }
    }


    // TODO: Later: getter/setter
    // [HarmonyPatch(typeof(TestClass), "GameInstance", MethodType.Getter)]


    // Does this do what I think?
    [HarmonyPatch(typeof(MainGame), nameof(MainGame.Update))]
    public class MainGame_Update
    {
        public static void Prefix(MainGame __instance)
        {
            // Yes, this is called all the time. 
            // Will have to be careful what we put here.
            /*
            bool isDown = UnityEngine.Input.GetKeyDown(KeyCode.F9);
            string isDownKey = "";
            if (isDown)
            {
                isDownKey = "F9";
                Log.LogInfo($"!!! INPUT: {isDownKey}");
                
                // Give us some items!
                // Note that, in reality, we may want to avoid doing this while they're in the Item menu (or Battle Item Menu) or a Shop.
                // The game seems robust against this, but it *does* seem confusing.
                OwnedItemClient client = new OwnedItemClient();
                client.AddOwnedItem(243, 1); // Thief's Gloves

                // Show it!
                Marquee.Instance.ShowMessage($"Got an item: {"Thief's Gloves"}!");
            }*/
        }
    }


    // Patch a set of properties in a json object
    static void PatchJsonPath(JsonNode rootNode, string xpath, Dictionary<String, String> keysNewValues)
    {
        // Remove leading '/'
        if (xpath.StartsWith("/"))
        {
            xpath = xpath.Substring(1);
        }

        Log.LogInfo($"Patching json entry: {xpath }");

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
                    Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at: {part}");
                    return;
                }

                int targetIndex = Int32.Parse(part.Substring(1, part.Length - 2));
                if (targetIndex < 0 || targetIndex >= currNode.AsArray().Count)
                {
                    Log.LogError($"INVALID: Array element out of bounds: {part}");
                    return;
                }
                currNode = currNode.AsArray()[targetIndex];
            }

            // Normal object properties are simple
            else
            {
                if (currNode.GetType() != typeof(JsonObject))
                {
                    Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at: {part}");
                    return;
                }

                if (!currNode.AsObject().ContainsKey(part))
                {
                    Log.LogError($"INVALID: Cannot find part: {part}");
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
            Log.LogError($"INVALID: Expected Array, not: {currNode.GetType()} at: <properties>");
            return;
        }

        // Iterate over all of these, and track how many we changed
        int numModifiedProps = 0;
        JsonArray currArray = currNode.AsArray();
        for (int i=0; i<currArray.Count; i++)
        {
            // This needs to be an object...
            currNode = currArray[i];
            if (currNode.GetType() != typeof(JsonObject))
            {
                Log.LogError($"INVALID: Expected Object, not: {currNode.GetType()} at: <properties[{i}]>");
                return;
            }

            // ...with known keys
            JsonObject currObj = currNode.AsObject();
            if (!(currObj.ContainsKey("name") && currObj.ContainsKey("type") && currObj.ContainsKey("value")))
            {
                // Probably small enough to print this object...
                Log.LogError($"INVALID: Node at: <properties[{i}]> is missing name/type/value: {currObj.ToString()}");
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
                    Log.LogWarning($"Unknown Json type: {typeStr} for resource: {xpath}");

                    // Save it as a string and hope for the best!
                    currObj["value"] = keysNewValues[nameStr];
                }

                numModifiedProps += 1;
            }
        }

        // Did we patch everything we expected to?
        if (numModifiedProps != keysNewValues.Count)
        {
            Log.LogError($"INVALID: Expected to patch {numModifiedProps} properties; but we only patched {keysNewValues.Count}");
            return;
        }

    }


    // TODO: Put into its own file with the hooked function, or into Utils
    static UnityEngine.Object PatchJsonAsset(string addressName, Il2CppSystem.Object originalAsset, Dictionary<String, Dictionary<String, String>> patches)
    {
        // Should never happen
        if (originalAsset is null)
        {
            Log.LogError("Could not patch null asset (TODO: how?)");
            return null;
        }

        // Json loads as a text asset
        TextAsset text = originalAsset.Cast<TextAsset>();

        // Needed when we overwrite the asset
        // This is copied from Magicite; I'm not sure if it's needed
        //   (we might just be able to steal the TextAsset's name in all cases)
        string name = text.name;
        if (name.Length == 0)
        {
            name = Path.GetFileName(addressName);
        }

        // We need to parse this as Json, modify it, then set it back.
        // TODO: There really should be some way to hook the code that reads this *as* json in 
        //       the game engine, but maybe it's more trouble than it's worth...
        JsonNode rootNode = JsonNode.Parse(text.text);

        // Now, modify our properties. 
        // We could do this all at once, but it's probably fast enough to scan each one from the root
        foreach (var xpath in patches.Keys)
        {
            PatchJsonPath(rootNode, xpath, patches[xpath]);
        }

        // Keep it compact, just like the original
        var options = new JsonSerializerOptions { WriteIndented = false };

        // Make a new TextAsset
        // TODO: Try just setting its 'text' attribute and seeing if that works.
        return new TextAsset(rootNode.ToJsonString(options)) { name = name };

        // Return the patched data as a simple string.
        //return rootNode.ToJsonString(options);
    }


    // Patching Partials
    // TODO: This might need to go into its own file
    [HarmonyPatch(typeof(ResourceManager), nameof(ResourceManager.IsLoadAssetCompleted), new Type[] { typeof(string) })]
    public static class ResourceManager_IsLoadAssetCompleted
    {
        // List of Assets (by ID) that Unity has loaded that we know we've already patched.
        private static SortedSet<int> knownAssets = new SortedSet<int>();

        // addressName is the path to the asset; something like:
        //   "Assets/GameAssets/Serial/Res/Map/Map_20011/Map_20011_1/entity_default"
        // ...meanwhile, the lookup within our dictionary is something like:
        //   map_20011:Map_20011_1:/layers/0/objects/2
        public static void Postfix(string addressName, ResourceManager __instance)
        {
            // Is the base asset fully loaded? If so, it will be in the PR's big list of known Asset objects
            // Presumably the "__res" would also be true in that case, but the completeAssetDic is a stronger check.
            if (!__instance.completeAssetDic.ContainsKey(addressName))
            {
                return;  // Don't worry, this function will be called again (for this asset) later.
            }

            // Is this a Map that we need to patch (for Treasures or other reasons)?
            if (TestRandTreasures.ContainsKey(addressName))
            {
                // Have we already patched this Asset?
                if (knownAssets.Contains(__instance.completeAssetDic[addressName].Cast<UnityEngine.Object>().GetInstanceID()))
                {
                    return;  // Shouldn't happen, but know that we don't need to "re-patch" if it does.
                }

                // What to patch? json_xpath -> kv_to_patch
                Dictionary<String, Dictionary<String, String>> patches = TestRandTreasures[addressName];
                Log.LogInfo($"Patching Resource: {addressName} in {patches.Count} locations");

                // Load the original asset
                UnityEngine.Object asset = PatchJsonAsset(addressName, __instance.completeAssetDic[addressName], patches);

                // Override the existing asset stored by Unity
                __instance.completeAssetDic[addressName] = asset;
                knownAssets.Add(asset.GetInstanceID());  // Update our list so that we don't re-patch.
            }
        }
    }



    // How about this?
    [HarmonyPatch(typeof(ItemWindowView), nameof(ItemWindowView.SetDescriptionText), new Type[] { typeof(string), typeof(bool), typeof(bool) })]
    public static class ItemWindowView_SetDescriptionText
    {
        public static void Prefix(ref string text, bool isParameter, bool isForcedChange, ItemWindowView __instance)
        {
            // Yep, this works too!
            //Log.LogInfo($"XXXXX =====> ItemWindowView::SetDescriptionText() called for: {text}");
            if (text.Length > 0)
            {
                //text = "Hacked hacked hacked!";

                // LOL, this works here, but it tries to spend money and refuses once you're out.
                // Amazing!
                //ShopUtility.BuyItem(89, 1);
                // Ok, it works now. Just pull from "content.csv"

                // Let's just make our own?
                // Yep, this seems to work.
                //OwnedItemClient client = new OwnedItemClient();
                //
                //client.AddOwnedItem(235, 1); // Iron Armor
                //client.RemoveOwnedItem(2, 10); // Remove all Potions
            }
        }
    }




}

