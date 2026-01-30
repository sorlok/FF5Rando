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
using System.IO.Compression;
using System.IO.Pipes;
using System.Reflection;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Unicode;
using System.Xml.Linq;
using UnityEngine;
using static Disarm.Disassembler;


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
    //private static UserDataManager BlahMgr;  // TODO: We can probably just use UserDataManager.Instance -- that seems to be the pattern
    //private static Il2CppSystem.Collections.Generic.List<Last.Data.User.OwnedItemData> BlahItems;

    private static TreasurePatcher MyTreasurePatcher;
    private static EventPatcher MyEventPatcher;
    private static MessageListPatcher MyStoryMsgPatcher;




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
        // Try to find our custom hack bundle.
        string randDir = Path.Combine(Application.streamingAssetsPath, "Rando");
        string myPatchZip = null;
        foreach (string fname in Directory.GetFiles(randDir)) {
            if (Path.GetExtension(fname) == ".apff5pr")
            {
                myPatchZip = fname;
                break;
            }
        }
        Log.LogInfo($"Loading patch file: '{myPatchZip}'");


        // Just read it manually; this is config, not a "resource"
        // TODO: Eventually remove these and just use the zip
        //string treasRandPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_treasure_input.csv");
        //Log.LogInfo($"Loading random treasure from path: {treasRandPath}");
        //MyTreasurePatcher = new TreasurePatcher(treasRandPath);

        // Read our other files too
        //string eventRandPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_script_input.csv");
        //Log.LogInfo($"Loading random event patches from path: {eventRandPath}");
        //MyEventPatcher = new EventPatcher(eventRandPath);

        // ...and this one!
        string storyMsgPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_message_input.csv");
        Log.LogInfo($"Loading random story messages from path: {storyMsgPath}");
        MyStoryMsgPatcher = new MessageListPatcher(storyMsgPath);

        // Try to read our custom hack bundle.
        using (ZipArchive archive = ZipFile.OpenRead(myPatchZip))
        {
            // Read our script patch file
            {
                ZipArchiveEntry entry = archive.GetEntry("script_patch.csv");
                if (entry != null)
                {
                    Stream stream = entry.Open();
                    using (var reader = new StreamReader(stream))
                    {
                        Log.LogInfo($"Loading random event patches from zip entry: {entry.Name}");
                        MyEventPatcher = new EventPatcher(reader);
                    }
                }
            }

            // Read the Treasure stuff
            {
                ZipArchiveEntry entry = archive.GetEntry("treasure_mod.csv");
                if (entry != null)
                {
                    Stream stream = entry.Open();
                    using (var reader = new StreamReader(stream))
                    {
                        Log.LogInfo($"Loading random treasure from zip entry: {entry.Name}");
                        MyTreasurePatcher = new TreasurePatcher(reader);
                    }
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
            //Log.LogInfo($"XXXXX =====> OwnedItemClient::AddOwnedItem[1]({contentId},{count}) called for: {__instance.Pointer}");
        }
    }
    //
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.AddOwnedItem), new Type[] { typeof(Last.Data.Master.Content), typeof(int) })]
    public static class OwnedItemClient_AddOwnedItem2
    {
        public static void Prefix(Last.Data.Master.Content targetData, int count, OwnedItemClient __instance)
        {
            //Log.LogInfo($"XXXXX =====> OwnedItemClient::AddOwnedItem[2](({targetData.MesIdName},{targetData.TypeId},{targetData.Id}),{count}) called for: {__instance.Pointer}");
        }
    }
    //
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.CreateOwnedItem), new Type[] { typeof(Last.Data.Master.Content), typeof(int) })]
    public static class OwnedItemClient_CreateOwnedItem
    {
        public static void Prefix(Last.Data.Master.Content content, int count, OwnedItemClient __instance)
        {
            //Log.LogInfo($"XXXXX =====> OwnedItemClient::CreateOwnedItem[](({content.MesIdName},{content.TypeId},{content.Id}),{count}) called for: {__instance.Pointer}");
        }
    }


    // Trying to understand this
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.RemoveOwnedItem), new Type[] { typeof(int), typeof(int) })]
    public static class OwnedItemClient_RemoveOwnedItem
    {
        public static void Prefix(int contentId, int count, OwnedItemClient __instance)
        {
            // Save it!
            //Log.LogInfo($"XXXXX =====> OwnedItemClient::RemoveOwnedItem[1]({contentId},{count}) called.");
        }
    }
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.RemoveOwnedItem), new Type[] { typeof(int), typeof(int), typeof(int) })]
    public static class OwnedItemClient_RemoveOwnedItem2
    {
        public static void Prefix(int itemType, int itemId, int count, OwnedItemClient __instance)
        {
            // Save it!
            //Log.LogInfo($"XXXXX =====> OwnedItemClient::RemoveOwnedItem[2]({itemType}, {itemId},{count}) called.");
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
            /*int myId = 0;
            foreach (var item in BlahMgr.normalOwnedItems)
            {
                Log.LogInfo($"######## ({item.key}) => {item.value.Name} , {item.value.Count}");
                myId = item.key;
                break;
            }*/

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
            //Log.LogInfo($"UserDataManager::normalItems PTR: {BlahMgr.normalOwnedItems.Pointer}");
            //Log.LogInfo($"Saved Cloned Item List PTR: {BlahItems.Pointer}");
            //Log.LogInfo($"UserDataManager::normalItems COUNT: {BlahMgr.normalOwnedItems.Count}");
            //Log.LogInfo($"Saved Cloned Item List COUNT: {BlahItems.Count}");
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
            //BlahMgr = __instance;
            //BlahItems = __result;
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
        }
    }





    // TODO: Put into its own file with the hooked function, or into Utils



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
            // Avoid an infinite loop
            try
            {

                // Is the base asset fully loaded? If so, it will be in the PR's big list of known Asset objects
                // Presumably the "__res" would also be true in that case, but the completeAssetDic is a stronger check.
                if (!__instance.completeAssetDic.ContainsKey(addressName))
                {
                    return;  // Don't worry, this function will be called again (for this asset) later.
                }

                // Do any of our patchers need to patch this asset?
                // TODO: We do this here to allow easier sharing of the asset and its json object
                //       (i.e., don't parse twice). I don't expect to multi-patch any resource, but 
                //       might as well build it stable from the start, eh?
                bool needsJsonPatching = MyTreasurePatcher.needsPatching(addressName);
                needsJsonPatching = needsJsonPatching || MyEventPatcher.needsPatching(addressName);
                bool needsStringsPatching = MyStoryMsgPatcher.needsPatching(addressName);
                if (!(needsJsonPatching || needsStringsPatching))
                {
                    return;
                }
                if (needsJsonPatching && needsStringsPatching)
                {
                    Log.LogError($"Resource is requesting json and strings processing, and that's just plain invalid!");
                    return;
                }

                // Have we already patched this Asset?
                Il2CppSystem.Object originalAsset = __instance.completeAssetDic[addressName];
                if (knownAssets.Contains(originalAsset.Cast<UnityEngine.Object>().GetInstanceID()))
                {
                    return;  // Shouldn't happen, but know that we don't need to "re-patch" if it does.
                }


                // Both json and strings assets start as "Text" assets.
                TextAsset originalTextAsset = originalAsset.Cast<TextAsset>();
                string newAssetText = null; // This will be produced by our patching function.

                // We need to break off from here
                if (needsJsonPatching)
                {
                    newAssetText = ApplyJsonPatches(addressName, originalTextAsset);
                }
                else if (needsStringsPatching)
                {
                    newAssetText = ApplyStringsPatches(addressName, originalTextAsset);
                }
                else
                {
                    Log.LogError($"Unknown patch type... not json or strings.");
                    return;
                }

                // Needed when we overwrite the asset
                // This is copied from Magicite; I'm not sure if it's needed
                //   (we might just be able to steal the TextAsset's name in all cases)
                string name = originalTextAsset.name;
                if (name.Length == 0)
                {
                    name = Path.GetFileName(addressName);
                }

                // Make a new TextAsset --we can't write to the '.Text' property, unfortunately...
                TextAsset newAsset = new TextAsset(newAssetText) { name = name };

                // Override the existing asset stored by Unity
                __instance.completeAssetDic[addressName] = newAsset;

                // Update our list so that we don't re-patch.
                knownAssets.Add(newAsset.GetInstanceID());

                // TODO: We may want to a flag that serializes and saves all patched resources (with proper formatting!)
                //       so that we can debug more easily.
            }
            catch (Exception ex)
            {
                // TODO: We may want to try/catch more stuff, but this is the function that
                //       can really cause the game to spin.
                Log.LogError($"EXCEPTION while processing: {ex}");
            }
        }

        private static string ApplyJsonPatches(string addressName, TextAsset originalTextAsset)
        {
            // Every function call will just modify this directly.
            JsonNode originalJson = JsonNode.Parse(originalTextAsset.text);

            // Try to patch this map's treasures
            MyTreasurePatcher.patchMapTreasures(addressName, originalJson);

            // Patch events...
            MyEventPatcher.patchMapEvents(addressName, originalJson);

            // Return a compact version, but make sure we encode UTF-8 without escaping it
            var options = new JsonSerializerOptions { WriteIndented = false, Encoder = JavaScriptEncoder.Create(UnicodeRanges.All) };
            return originalJson.ToJsonString(options);
        }


        private static string ApplyStringsPatches(string addressName, TextAsset originalTextAsset)
        {
            // Every function call can just modify this directly.
            StringsAsset originalStrings = new StringsAsset(originalTextAsset.text);

            // Try to patch messages
            MyStoryMsgPatcher.patchMessageStrings(addressName, originalStrings);

            // Return the text as expected.
            return originalStrings.toAssetStr();
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

