using AsmResolver.PE.Exports;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Last.Data;
using Last.Data.User;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using Last.Interpreter.Instructions.SystemCall;
using Last.Management;
using Last.Scene;
using Last.Systems;
using Last.UI;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
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
    private static MessageListPatcher MyStoryNameplatePatcher;

    // Replace SysCall(key) with SysCall(value); this allows us to put SysCalls into English
    // Not sure how far we want to go with this...
    private static Dictionary<string, string> SysCallReplacements = new Dictionary<string, string>
    {
        { "Party Joined: Bartz" , "パーティ加入：バッツ" },
        { "Party Joined: Lenna" , "パーティ加入：レナ" },
        { "Party Joined: Galuf" , "パーティ加入：ガラフ" },
        { "Party Joined: Faris" , "パーティ加入：ファリス" },
        { "Party Joined: Krile" , "パーティ加入：クルル" },
        { "Party Left: Bartz" , "パーティ離脱：バッツ" },
        { "Party Left: Lenna" , "パーティ離脱：レナ" },
        { "Party Left: Galuf" , "パーティ離脱：ガラフ" },
        { "Party Left: Faris" , "パーティ離脱：ファリス" },
        { "Party Left: Krile" , "パーティ離脱：クルル" },
    };




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

        // TODO: It might be useful to have a "event_post_patch.csv" that we load if it's present in the
        //       directory, and is used for debugging new content. That would look something like this:
        //string eventRandPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_script_input.csv");
        //Log.LogInfo($"Loading random event patches from path: {eventRandPath}");
        //MyEventPatcherPost = new EventPatcher(eventRandPath);

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

            // Read our two message files
            {
                ZipArchiveEntry entry = archive.GetEntry("message_strings.csv");
                if (entry != null)
                {
                    Stream stream = entry.Open();
                    using (var reader = new StreamReader(stream))
                    {
                        Log.LogInfo($"Loading message list strings from zip entry: {entry.Name}");
                        MyStoryMsgPatcher = new MessageListPatcher(reader);
                    }
                }
            }
            //
            {
                ZipArchiveEntry entry = archive.GetEntry("nameplate_strings.csv");
                if (entry != null)
                {
                    Stream stream = entry.Open();
                    using (var reader = new StreamReader(stream))
                    {
                        Log.LogInfo($"Loading nameplate list strings from zip entry: {entry.Name}");
                        MyStoryNameplatePatcher = new MessageListPatcher(reader);
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


    // TODO: DataInitializeManager()::CreateXYZ() might be part of the New Game...


    // UserSaveData.ToJSON is called for lots of things, it seems...
    // Nothing in Last.Data.User seems to have flags.
    // We actually don't need to know how it's stored in save files; we just need to change it.
    // The problem is that we change other things (like Items) via "UserDataManager" --so what "Manager" handles Flags?
    // Other terms: "Scenario" seems common.



    // TODO: Hook all 3:
    [HarmonyPatch(typeof(DataStorage), nameof(DataStorage.Set), new Type[] { typeof(DataStorage.Category), typeof(int), typeof(int) })]
    public static class DataStorage_Set1
    {
        public static void Prefix(DataStorage.Category c, int index, int value)
        {
            if (c != DataStorage.Category.kScriptLocalVariable)
            {
                Log.LogWarning($"Set: {c} , {index} , {value}");
            }
        }
    }
    /*
    //
    [HarmonyPatch(typeof(DataStorage), nameof(DataStorage.Set), new Type[] { typeof(string), typeof(int), typeof(int) })]
    public static class DataStorage_Set2
    {
        public static void Prefix(string c, int index, int value)
        {
            Log.LogWarning($"Set[2]: {c} , {index} , {value}");
        }
    }
    //
    [HarmonyPatch(typeof(DataStorage), nameof(DataStorage.SetFlag), new Type[] { typeof(DataStorage.Flags), typeof(int), typeof(int), typeof(int) })]
    public static class DataStorage_Set3
    {
        public static void Prefix(DataStorage.Flags f, int index, int segment, int value)
        {
            Log.LogWarning($"Set[3]: {f} , {index} , {segment} , {value}");
        }
    }
    */


    // TODO: How to interrupt SysCall?
    /* // NOTE: This is the "next" one; it polls all the time. :(
    [HarmonyPatch(typeof(Core), nameof(Core.GetNextMnemonic))]
    public static class Core_GetNextMnemonic
    {
        public static void Postfix(string __result)
        {
            Log.LogWarning($"GETNEXTMNEMONIC: {__result}");
        }
    }*/
    /* // NOPE, this goes all the time
    [HarmonyPatch(typeof(Core), nameof(Core.Execute))]
    public static class Core_Execute
    {
        public static void Postfix(Il2CppSystem.Nullable<int> __result, Core __instance)
        {
            Log.LogWarning($"EXECUTE: {__instance.currentInstruction} => {__result}");
        }
    }*/
    /* // NOPE
    [HarmonyPatch(typeof(Integrator), nameof(Integrator.ChangeScript), new Type[] { typeof(string), typeof(bool) })]
    public static class Integrator_ChangeScript
    {
        public static void Prefix(string scriptName, bool tbr)
        {
            Log.LogWarning($"CHANGE: {scriptName}");
        }
    } */
    /*
    [HarmonyPatch(typeof(Last.Interpreter.Instructions.External.Vehicle), nameof(Last.Interpreter.Instructions.External.Vehicle.SetVehicle), new Type[] { typeof(MainCore) })]
    public static class Vehicle_SetVehicle
    {
        public static void Prefix(MainCore mc)
        {
            Log.LogError($"EXTERNAL:MNEMONIC: {mc.currentInstruction.mnemonic}");
            Log.LogError($"EXTERNAL:IVALS: {string.Join("", mc.currentInstruction.operands.iValues)}");
            Log.LogError($"EXTERNAL:RVALS: {string.Join("", mc.currentInstruction.operands.rValues)}");
            Log.LogError($"EXTERNAL:SVALS: {string.Join("", mc.currentInstruction.operands.sValues)}");


            // Ugh
            foreach (var mn in mc.mnemonics)
            {
                Log.LogWarning($"{mn.mnemonic} => {string.Join(",", mn.operands.iValues)} => {string.Join(",", mn.operands.rValues)} => {string.Join(",", mn.operands.sValues)}");
            }

        }
    }*/



    //
    [HarmonyPatch(typeof(External.Misc), nameof(External.Misc.SystemCall), new Type[] { typeof(MainCore) })]
    public static class Some_Function
    {
        public static bool Prefix(ref MainCore mc, int __result)
        {
            // Handle our own fake SysCalls here, rather than trying to add them to the lookup dictionary.
            string sysCallFn = mc.currentInstruction.operands.sValues[0];
            if (sysCallFn == "InitOpenWorldRando")
            {
                Log.LogInfo($"Triggered custom SysCall: '{sysCallFn}'");

                // Set flags:
                DataStorage.instance.Set("ScenarioFlag1", 0, 1);  // Set after the intro cutscene
                DataStorage.instance.Set("ScenarioFlag1", 1, 1);  // Set when Bartz jumps off Boco and tells him to wait.
                DataStorage.instance.Set("ScenarioFlag1", 2, 1);  // Set when they're looking for Galuf at the meteorite
                DataStorage.instance.Set("ScenarioFlag1", 3, 1);  // Set when Galuf+Lenna leave the party
                DataStorage.instance.Set("ScenarioFlag1", 4, 1);  // Set when you get off Boco at the meteorite. TODO: Does this keep him from spawning on that map?
                DataStorage.instance.Set("ScenarioFlag1", 5, 1);  // Jump back on Boco after the cutscene where he throws you off
                DataStorage.instance.Set("ScenarioFlag1", 6, 1);  // Set after rescuing Lenna+Galuf (+cutscene) when you are sent back to the World Map
                DataStorage.instance.Set("ScenarioFlag1", 7, 1);  // Set when entering the Pirate's Cave, first "cave" room (with the healing spring).
                DataStorage.instance.Set("ScenarioFlag1", 8, 1);  // Set after watching the Pirate open the secret door.
                DataStorage.instance.Set("ScenarioFlag1", 9, 1);  // Set once you watch the ship sail in the cutscene partway through the cavern.
                DataStorage.instance.Set("ScenarioFlag1", 10, 1);  // Set after spying on the pirate base at the entrance.
                // Skip 11
                DataStorage.instance.Set("ScenarioFlag1", 12, 1);  // Set once Faris unties you and you teleport to the world map on the boat.
                DataStorage.instance.Set("ScenarioFlag1", 13, 1);  // Set once the pirate asks to pilot you to the Wind Shrine
                DataStorage.instance.Set("ScenarioFlag1", 14, 1);  // Wind Shrine 1F, entered room, "the Wind stopped"
                // Skip 15/16 (boss & crystal room)
                DataStorage.instance.Set("ScenarioFlag1", 17, 1);  // Pirates say "Grog, Grog!", and Faris says she'll go to the Pub and leaves the party.
                // Skip 18; TODO: related to Island Shrine???
                DataStorage.instance.Set("ScenarioFlag1", 19, 1);  // Set after watching the Faris at the Inn cutscene
                DataStorage.instance.Set("ScenarioFlag1", 20, 1);  // Set in front of Zok's house when Lenna tells you he built the canal.
                DataStorage.instance.Set("ScenarioFlag1", 21, 1);  // Seems to say "the Zok cutscene is done"
                DataStorage.instance.Set("ScenarioFlag1", 22, 1);  // Set after Faris bids farewell to the Pirates once you get the Canal key
                DataStorage.instance.Set("ScenarioFlag1", 23, 1);  // Set after Lenna worries about the crystals fading (after getting the Canal key).
                DataStorage.instance.Set("ScenarioFlag1", 24, 1);  // Appears to be a fade-in after unlocking the Canal
                DataStorage.instance.Set("ScenarioFlag1", 25, 1);  // Set after landing at the Ship's Graveyard
                DataStorage.instance.Set("ScenarioFlag1", 26, 1);  // Faris doesn't want to get wet
                DataStorage.instance.Set("ScenarioFlag1", 27, 1);  // Faris doesn't want to get dry
                // Skip 28 (raise the sunken ship)




                DataStorage.instance.Set("ScenarioFlag1", 33, 1);  // Set on entering the World Map after riding the Hiryu
                DataStorage.instance.Set("ScenarioFlag1", 34, 1);  // When you see Boco's tracks leading into the cave (World 1)
                DataStorage.instance.Set("ScenarioFlag1", 35, 1);  // Inside the pirate's cave; you find Boko recovering

                // Skipping 79,80,81 for now (meteor bosses)

                DataStorage.instance.Set("ScenarioFlag1", 197, 1);  // Set when you walk through the teleporter at the back of the Wind Shrine for the first time; "how to use crystals"
                DataStorage.instance.Set("ScenarioFlag1", 208, 1);  // Set after prompting that the Hot Spring is "right over there".
                DataStorage.instance.Set("ScenarioFlag1", 209, 1);  // Seems to be "this is a save point" script
                DataStorage.instance.Set("ScenarioFlag1", 417, 1);  // Set after defeating the first batch of Goblins in the canyon.
                DataStorage.instance.Set("ScenarioFlag1", 418, 1);  // Set after jumping over the gaps after the first batch of Goblins.
                DataStorage.instance.Set("ScenarioFlag1", 419, 1);  // Set after defeating the second batch of Goblins in the canyon.

                // ScenarioFlag 2
                DataStorage.instance.Set("ScenarioFlag2", 11, 1);  // Seems to be "we saw the Zok cutscene", but locally.



                // TODO: TEMP: We need to cheat a bit...
                OwnedItemClient client = new OwnedItemClient();
                client.AddOwnedItem(128, 20); // Fire Rod
                //client.AddOwnedItem(129, 20); // Frost Rod
                //client.AddOwnedItem(130, 20); // Thunder Rod


                return false;  // Don't continue to run this function.
            }

            // Rename our SysCall in certain cases
            if (SysCallReplacements.ContainsKey(sysCallFn))
            {
                mc.currentInstruction.operands.sValues[0] = SysCallReplacements[sysCallFn];
            }
            return true;  // Continue to run this function.
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
            // Avoid an infinite loop of errrors
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
                bool needsStringsPatching = MyStoryMsgPatcher.needsPatching(addressName) || MyStoryNameplatePatcher.needsPatching(addressName);
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
                // The game seems to reload the original asset from disk when you switch maps (with the original ID in fact).
                // I suppose we could save the patched json in memory and just return that... but it's fast enough to patch.
                // After patching, it looks like the game sometimes requests this asset again without switching maps, so
                //   this if statement does get some mileage.
                Il2CppSystem.Object originalAsset = __instance.completeAssetDic[addressName];
                if (knownAssets.Contains(originalAsset.Cast<UnityEngine.Object>().GetInstanceID()))
                {
                    return;
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
            MyStoryNameplatePatcher.patchMessageStrings(addressName, originalStrings);

            // Return the text as expected.
            return originalStrings.toAssetStr();
        }


    }



    // Trying to detect when flags are set
    // TODO: Does not appear to do anything; Get is also not used.
    //[HarmonyPatch(typeof(DataStorage.Flags), nameof(DataStorage.Flags.Set), new Type[] { typeof(int), typeof(bool) })]
    //public static class Flags_Set
    //{
    //public static void Prefix(int index, bool value, DataStorage.Flags __instance)
    //{
    //Log.LogWarning($"SETTING FLAG: {index} => {value}");
    //}
    //}


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

