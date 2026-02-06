using AsmResolver.PE.Exports;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using Common;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Il2CppSystem.Linq;
using Last.Data;
using Last.Data.User;
using Last.Defaine;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using Last.Interpreter.Instructions.SystemCall;
using Last.Management;
using Last.Scene;
using Last.Systems;
using Last.UI;
using MonoMod.RuntimeDetour;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
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

    // TODO: Make this a setting later...
    private static bool OopsAllGoblins = true;   // Replace all bosses with Goblins, to make debugging easier.

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



    // Try to override combat...
    [HarmonyPatch(typeof(External.Misc), nameof(External.Misc.EncountBoss), new Type[] { typeof(MainCore) })]
    public static class External_Misc_EncountBoss
    {
        public static void Prefix(ref MainCore mc)
        {
            int bossEncounterId = mc.currentInstruction.operands.iValues[0];
            Log.LogError($"BOSS: {bossEncounterId}");
            if (OopsAllGoblins)
            {
                mc.currentInstruction.operands.iValues[0] = 1;
            }
        }
    }



    // Hook receiving items; we need to flip switches and do multiworld stuff.
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.AddOwnedItem), new Type[] { typeof(int), typeof(int) })]
    public static class OwnedItemClient_AddOwnedItem
    {
        public static bool Prefix(int contentId, int count, OwnedItemClient __instance)
        {
            // TODO: Multiworld item checks...
            // "return false" will, in fact, prevent them from getting any item!

            // Adamantite check: allow them to upgrade the Airship (which is a separate Flag)
            if (contentId == 47)
            {
                // Flag "got the Adamantite"
                DataStorage.instance.Set("ScenarioFlag1", 69, 1);
                Log.LogInfo("Hooking GetItem(Adamantite) and setting ScenarioFlag1:69");

                // They can still get it. Sure, why not?
                return true;
            }

            // Allow them to get the item.
            return true;
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


    // TODO: DataInitializeManager()::CreateXYZ() might be part of the New Game...


    // UserSaveData.ToJSON is called for lots of things, it seems...
    // Nothing in Last.Data.User seems to have flags.
    // We actually don't need to know how it's stored in save files; we just need to change it.
    // The problem is that we change other things (like Items) via "UserDataManager" --so what "Manager" handles Flags?
    // Other terms: "Scenario" seems common.



    // TODO: We should provide a debug option in our (BepInEx) config file that lets people print flags.
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





    //
    [HarmonyPatch(typeof(External.Misc), nameof(External.Misc.SystemCall), new Type[] { typeof(MainCore) })]
    public static class External_Misc_SystemCall
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
                // NOTE: We hijack Flag 14 to use in place of flag 16 (the wind crystal cutscene) // DataStorage.instance.Set("ScenarioFlag1", 14, 1);  // Wind Shrine 1F, entered room, "the Wind stopped"
                // Skip 15 (boss)
                DataStorage.instance.Set("ScenarioFlag1", 16, 1);  // Got Wind Crystal Shards. NOTE: This *also* lets you access the Job menu.
                                                                   // NOTE: We hack around this and use X in some places that expect it.
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
                // Skip 29 (Siren battle finished)
                DataStorage.instance.Set("ScenarioFlag1", 30, 1);  // Something about asking people about the Wind Drake and getting to Walse...
                DataStorage.instance.Set("ScenarioFlag1", 31, 1);  // Set in Carwen when the party figures out the Wind Drake is at the North Mountain
                // Skip 32 (after fighting Magissa and Forza)
                DataStorage.instance.Set("ScenarioFlag1", 33, 1);  // Set on entering the World Map after riding the Hiryu
                DataStorage.instance.Set("ScenarioFlag1", 34, 1);  // When you see Boco's tracks leading into the cave (World 1)
                DataStorage.instance.Set("ScenarioFlag1", 35, 1);  // Inside the pirate's cave; you find Boko recovering
                DataStorage.instance.Set("ScenarioFlag1", 36, 1);  // Set after the "welcome back" cutscene in Castle Tycoon(World 1)
                DataStorage.instance.Set("ScenarioFlag1", 37, 1);  // After talking to the king, opens the tower
                // Never set flag 38; it sinks Walse Island (NOTE: The meteor won't be unlocked; TODO: check if later flags unlock it...)
                // Flag 39 is stolen and used instead of flag 38, so it's set by the Walse cutscene.
                DataStorage.instance.Set("ScenarioFlag1", 40, 1);  // First time teleporting between meteors
                DataStorage.instance.Set("ScenarioFlag1", 41, 1);  // After being thrown in Jail(you can walk around the jail cell)
                DataStorage.instance.Set("ScenarioFlag1", 42, 1);  // After the Chancelor lets you out of jail
                DataStorage.instance.Set("ScenarioFlag1", 43, 1);  // Outside Karnak Castle; the guards scare the Werewolf away with dynamite
                DataStorage.instance.Set("ScenarioFlag1", 44, 1);  // After Cid meets you on the Fire-powered ship and tells you to stop the engine
                // Skipping 45: Set after defeating Liquid Flame
                // Skipping 46: This is the "Flames Be Gone" flag, and we set it after killing Liquid Flame
                // Skipping 47: This is set when we get the Fire Crystal shards after the castle explodes; we NEVER set this (to keep the Castle there).
                // Skipping 48: This is set when you defeat Ifrit
                // Skipping 49: This is set when you defeat Byblos
                DataStorage.instance.Set("ScenarioFlag1", 50, 1);  // Set after talking to Mid and warping back to the Library
                DataStorage.instance.Set("ScenarioFlag1", 51, 1);  // After Mid talks to Cid in the Pub
                DataStorage.instance.Set("ScenarioFlag1", 52, 1);  // After Galuf remembers Krile on the ship (exit onto ship, still need to talk to Cid)
                DataStorage.instance.Set("ScenarioFlag1", 53, 1);  // After getting the Fire-Powered Ship and setting sail
                DataStorage.instance.Set("ScenarioFlag1", 54, 1);  // Set when the Crescent earthquake starts, but before you walk out of town
                DataStorage.instance.Set("ScenarioFlag1", 55, 1);  // Set after the Fire-Powered ship sinks in the earthquake
                DataStorage.instance.Set("ScenarioFlag1", 56, 1);  // Shows a cutscene when talking to the guy at the lake in the middle of town (if unset)
                DataStorage.instance.Set("ScenarioFlag1", 57, 1);  // Shows a cutscene when you sleep at the Inn (if unset)
                DataStorage.instance.Set("ScenarioFlag1", 58, 1);  // NOTE: World map, set after Cid+Mid tell you to go through the Desert
                // Skipping 59; set when we beat the Sand Worm
                DataStorage.instance.Set("ScenarioFlag1", 60, 1);  // After arriving in Gohn; Bartz says "guess we're  here"
                // Stealing: this now means "defeated Adamantoise" DataStorage.instance.Set("ScenarioFlag1", 61, 1);  // Overly long "Abandoning Galuf" gag
                DataStorage.instance.Set("ScenarioFlag1", 62, 1);  // After falling into the pit in Gohn and getting to the Catapult
                DataStorage.instance.Set("ScenarioFlag1", 63, 1);  // After pushing the switch, and Cid+Mid fall down the hole
                DataStorage.instance.Set("ScenarioFlag1", 64, 1);  // After finding the Fire-Powered ship in the Catapult basement
                DataStorage.instance.Set("ScenarioFlag1", 65, 1);  // On the deck of the airship after launching, but before fighting Cray Claw
                DataStorage.instance.Set("ScenarioFlag1", 66, 1);  // Set when Gohn begins to rise from the ground
                DataStorage.instance.Set("ScenarioFlag1", 67, 1);  // Set when Cid tells you to go get the Adamantite
                DataStorage.instance.Set("ScenarioFlag1", 68, 1);  // Set when Galuf opens the Tycoon meteorite
                // Skipping 69; get the Adamantite (but don't fight the boss yet)
                // DataStorage.instance.Set("ScenarioFlag1", 70, 1);  // Set after upgrading the airship (scene occurs in Catapult Inn)
                // 71 and 72 are related to Sol Cannon. 73 is after beating Archeoavis
                DataStorage.instance.Set("ScenarioFlag1", 74, 1);  // Set after the lengthy Earth Crystal scene.
                DataStorage.instance.Set("ScenarioFlag1", 75, 1);  // Set after talking on the airship about how you want to go to the other world (but should see Cid first)
                DataStorage.instance.Set("ScenarioFlag1", 76, 1);  // Read the note saying that Cid+Mid went to return the Adamant
                DataStorage.instance.Set("ScenarioFlag1", 77, 1);  // After returning the Adamant and charging the Tycoon meteorite (no boss)
                DataStorage.instance.Set("ScenarioFlag1", 79, 1);  // Cutscene where Cid/Mid are like "can you clear out the monster in there?". 
                DataStorage.instance.Set("ScenarioFlag1", 81, 1);  // Cutscene where Cid/Mid go into the meteorite, and Bartz is like "they're taking forever".
                



                // Skippin 53; this will be set by our patch upon defeating Liquid Flame to remove the Ship dungeon from the map.

                // Skipping 79,80,81 for now (meteor bosses)

                DataStorage.instance.Set("ScenarioFlag1", 140, 1);  // Press X to "STELLA!!!"
                DataStorage.instance.Set("ScenarioFlag1", 163, 1);  // Book Case won't block your path any more.
                DataStorage.instance.Set("ScenarioFlag1", 197, 1);  // Set when you walk through the teleporter at the back of the Wind Shrine for the first time; "how to use crystals"
                DataStorage.instance.Set("ScenarioFlag1", 208, 1);  // Set after prompting that the Hot Spring is "right over there".
                DataStorage.instance.Set("ScenarioFlag1", 209, 1);  // Seems to be "this is a save point" script
                DataStorage.instance.Set("ScenarioFlag1", 245, 1);  // Set when you defeat Lone Wolf/Iron Claw -- NOTE: He doesn't trigger an after-battle script, so we can't make this a check right now.
                DataStorage.instance.Set("ScenarioFlag1", 417, 1);  // Set after defeating the first batch of Goblins in the canyon.
                DataStorage.instance.Set("ScenarioFlag1", 418, 1);  // Set after jumping over the gaps after the first batch of Goblins.
                DataStorage.instance.Set("ScenarioFlag1", 419, 1);  // Set after defeating the second batch of Goblins in the canyon.

                // ScenarioFlag 2
                DataStorage.instance.Set("ScenarioFlag2", 11, 1);   // Seems to be "we saw the Zok cutscene", but locally.
                //DataStorage.instance.Set("ScenarioFlag2", 31, 1);   // Cid & Mid told you about the sandworm but you haven't fought it yet.
                DataStorage.instance.Set("ScenarioFlag2", 97, 1);   // After Cid dynamites your cell but before you talk to him
                DataStorage.instance.Set("ScenarioFlag2", 109, 1);  // Gohn, Track King Tycoon 1
                DataStorage.instance.Set("ScenarioFlag2", 110, 1);  // Gohn, Track King Tycoon 2
                DataStorage.instance.Set("ScenarioFlag2", 111, 1);  // Gohn, Track King Tycoon 3
                DataStorage.instance.Set("ScenarioFlag2", 112, 1);  // Gohn, Track King Tycoon 4
                DataStorage.instance.Set("ScenarioFlag2", 113, 1);  // After Cid+Mid fall onto the airship and then they go downstairs
                DataStorage.instance.Set("ScenarioFlag2", 114, 1);  // After defeating Cray Claw and then launching the ship.
                DataStorage.instance.Set("ScenarioFlag2", 175, 1);  // After fighting the Adamantite boss
                

                // TODO: This is... crashing?
                Log.LogInfo("New Item Debug: A");
                OwnedItemClient client = new OwnedItemClient();
                Log.LogInfo("New Item Debug: B.1");
                client.AddOwnedItem(128, 20); // Fire Rod
                Log.LogInfo("New Item Debug: B.2");
                client.AddOwnedItem(129, 20); // Frost Rod
                Log.LogInfo("New Item Debug: B.3");
                client.AddOwnedItem(130, 20); // Thunder Rod
                Log.LogInfo("New Item Debug: C");



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








    // TODO: Testing
    [HarmonyPatch(typeof(SceneLoadTask), nameof(SceneLoadTask.LoadUnityScene), new Type[] { typeof(string), typeof(string), typeof(UnityEngine.SceneManagement.LoadSceneMode) })]
    public static class SceneLoadTask_LoadUnityScene
    {
        public static void Prefix(string loadAssetGroup, string loadSceneName, UnityEngine.SceneManagement.LoadSceneMode loadSceneMode, SceneLoadTask __instance)
        {
            //Log.LogInfo($"XXXXX =====> SceneLoadTask::LoadUnityScene({loadSceneName})");
        }
    }

    // TODO: We need to track some amount of scene or menu state so that we know when it's safe to give them remote items.
    //       We'd also need to track Save File loading, etc., so that we don't queue up items *before* a save and then give them the items *after* loading a different save.
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



    // Does this do what I think?
    /*
    [HarmonyPatch(typeof(MainGame), nameof(MainGame.Update))]
    public class MainGame_Update
    {
        public static void Prefix(MainGame __instance)
        {
            // Yes, this is called all the time. 
            // Will have to be careful what we put here.
        }
    }
    */





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

