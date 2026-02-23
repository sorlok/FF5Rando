using Archipelago.MultiClient.Net.Models;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using GooglePlayGames.BasicApi.Nearby;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Il2CppSystem.Linq;
using Last.Data;
using Last.Data.Master;
using Last.Data.User;
using Last.Defaine;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using Last.Interpreter.Instructions.SystemCall;
using Last.Management;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Unicode;
using UnityEngine;
using UnityEngine.InputSystem.Utilities;
using static UnityEngine.InputSystem.LowLevel.InputStateHistory;



namespace MyFF5Plugin;

[BepInPlugin(MyPluginInfo.PLUGIN_GUID, MyPluginInfo.PLUGIN_NAME, MyPluginInfo.PLUGIN_VERSION)]
[BepInProcess("FINAL FANTASY V.exe")]
public class Plugin : BasePlugin
{
    // Used for logging by all classes in this project
    internal static new ManualLogSource Log;

    // This object holds *all* multiworld and randomizer data. 
    // All interactions with the randomzier hapen through this.
    // Call isVanilla() to check if you're in a non-randomized save file.
    public static RandoControl randoCtl = new RandoControl();


    // What scene is currently active?
    private static bool onMainScene = false;
    private static bool onFieldOnce = false; // True if we've transitioned to InGame_Field at least once (reset on Load)
    //private static bool inSomeMenu = false;  // Are we in a menu of some kind? Don't give items in that case (it should be safe, but could get confusing)
                                             // TODO: Not sure if in-Battle menus have this problem. 
    private static int onFieldTicks = -1;     // Will be -1 when we're not on the field, 0 when we switch to the field, and +1 (up to 10) as frames pass. We will ONLY get items when this is >=10


    // What we think counts as a menu state
    private static HashSet<GameSubStates> MyMenuStates = new HashSet<GameSubStates> {
        GameSubStates.InGame_MainMenu_Ability,
        GameSubStates.InGame_MainMenu_Config,
        GameSubStates.InGame_MainMenu_Config_BattleUI,
        GameSubStates.InGame_MainMenu_Config_Controls,
        GameSubStates.InGame_MainMenu_Config_Field,
        GameSubStates.InGame_MainMenu_Config_Menu,
        GameSubStates.InGame_MainMenu_Config_Sound,
        GameSubStates.InGame_MainMenu_Config_System,
        GameSubStates.InGame_MainMenu_Equipment,
        GameSubStates.InGame_MainMenu_Formation,
        GameSubStates.InGame_MainMenu_Item,
        GameSubStates.InGame_MainMenu_Job,
        GameSubStates.InGame_MainMenu_Magic,
        GameSubStates.InGame_MainMenu_Main,
        GameSubStates.InGame_MainMenu_QuickSave,
        GameSubStates.InGame_MainMenu_Save,
        GameSubStates.InGame_MainMenu_Status,
        GameSubStates.InGame_MainMenu_Words,
    };


    // Will auto load from out own config file
    public static string ConfigFilePath = "";  // Helper
    private static ConfigEntry<bool> cfgOopsAllGoblins;    // All fights are goblins? Used for debugging.
    private static ConfigEntry<bool> cfgPrintFlagChanges;  // Print any time a flag (except a "local" flag) changes
    public static ConfigEntry<string> cfgServerHostAndPort;   // localhost:8765 or similar
    public static ConfigEntry<string> cfgServerPassword;      // If empty, means "no password"
    public static ConfigEntry<string> cfgPlayerNameOverride;  // If non-empty, this will always be your player name
    public static ConfigEntry<float> cfgMarqueeDuration;        // How long to show a "marquee" popup for each MW item



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

        // Set up our BepInEx config properties.
        // These will be auto-saved to our mod's config file in BepInEx/config/<MyProject>.cfg
        ConfigFilePath = Config.ConfigFilePath;
        cfgOopsAllGoblins = Config.Bind("Debug", "OopsAllGoblins", false, "Debug option: set to 'true' and most bosses will just be weak Goblins.");
        cfgPrintFlagChanges = Config.Bind("Debug", "PrintFlagChanges", false, "Debug option: set to 'true' and you'll see when any Flag is set or unset (except 'local' ones).");
        cfgServerHostAndPort = Config.Bind("Netplay", "ServerNameAndPort", "localhost:38281", "Server to connect to for your Multiworld game.");
        cfgServerPassword = Config.Bind("Netplay", "ServerPassword", "", "Password to log in to the server, or empty if there's no password");
        cfgPlayerNameOverride = Config.Bind("Netplay", "PlayerNameOverride", "", "Force your player to always have this name; otherwise, it's pulled from the patch. This should rarely be needed.");
        cfgMarqueeDuration = Config.Bind("General", "MarqueeDuration", 5.0f, "How long (in seconds) to show the popup for each time you get an item. Set to 0 to disable this entirely.");


        // Create all of our custom UI stuff.
        // We use Unity's IMGui for easy component UI
        createOurUI();

        // Try patching methods with Harmony
        PatchMethods();

        // Plugin startup logic
        Log.LogInfo($"Plugin {MyPluginInfo.PLUGIN_GUID} is loaded");
    }


    // Create an register our IMGui stuff.
    private void createOurUI()
    {
        // Seems like we need to inject our class into the game so that Unity can interact with it? I guess?
        ClassInjector.RegisterTypeInIl2Cpp<Marquee>();
        ClassInjector.RegisterTypeInIl2Cpp<Engine>();
        ClassInjector.RegisterTypeInIl2Cpp<SeedPicker>();

        // Create a Singleton game object to manage our various IMGui MonoBehaviors
        // Not sure exactly why we need this higher-level thing; maybe it's for Scene ownership?
        string name = typeof(Marquee).FullName;
        GameObject singleton = new GameObject(name);
        // Don't show this in the hierarchy, don't save it to the Scene, don't unload it via "UnloadUnusedAssets()"
        // Our script will manage this singleton entirely.
        singleton.hideFlags = HideFlags.HideAndDontSave;
        // If we don't do this, Unity will remove the GameObject when we change scenes
        GameObject.DontDestroyOnLoad(singleton);

        // Create an instance of our Marquee, so that we can interact with it later.
        // You can access this later via Marquee.Instance()
        // I *think* this causes it to be added to the scene and awakened.
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
        SeedPicker seedPicker = singleton.AddComponent<SeedPicker>();
        if (seedPicker is null)
        {
            GameObject.Destroy(singleton);
            throw new Exception($"The object is missing the required component: SeedPicker");
        }
    }



    private void PatchMethods()
    {
        // We patch all methods even if we're in "normal" game mode, since this our only chance to do so.
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



    // If "multiWorldDataObj" is null, that means we're loading a New Game, so we need to prompt for Server settings.
    // If it's not null, we have known server settings, and we can try to connect.
    public static void LoadRandoFiles(string newMultiWorldSeedFile, JsonObject multiWorldDataObj)
    {
        //Plugin.Log.LogError($"LOADING RANDO: {newMultiWorldSeedFile}"); if (multiWorldData != null) { Plugin.Log.LogError(multiWorldDataObj.ToJsonString()); } else { Plugin.Log.LogError("NULL"); }

        // No receiving multiworld items until we get back to the world map
        onFieldOnce = false;

        randoCtl.changeSeedAndReload(newMultiWorldSeedFile, multiWorldDataObj);

        // This technically works (makes Potions have "Omega Badge" as the name).
        //var potion = MasterManager.Instance.GetData<Content>(2);
        //potion.MesIdName = "MSG_ITEM_NAME_33";
        //Log.LogError($"TESTING: {potion.MesIdName}");
        //
        // This is, howver, too late (we've already set the player's name in the Save file).
        // (We'll just have to hack the name in System strings... blah...)
        //var bartz = MasterManager.Instance.GetData<CharacterStatus>(1);
        //bartz.MesIdName = "MSG_CHAR_NAME_01";
        //Log.LogError($"TESTING: {bartz.MesIdName}");

        // Reset?
        //onFieldTicks = -1;
    }



    // Turn all bosses into Goblins; works in both multiworld and vanilla (because why not!)
    [HarmonyPatch(typeof(External.Misc), nameof(External.Misc.EncountBoss), new Type[] { typeof(MainCore) })]
    public static class External_Misc_EncountBoss
    {
        public static void Prefix(ref MainCore mc)
        {
            int bossEncounterId = mc.currentInstruction.operands.iValues[0];
            if (cfgPrintFlagChanges.Value)
            {
                Log.LogInfo($"Starting boss encounter with ID: {bossEncounterId}");
            }

            // Debug switch to avoid fighting bosses.
            if (cfgOopsAllGoblins.Value)
            {
                mc.currentInstruction.operands.iValues[0] = 1;
            }
        }
    }

    // Prints each time a Flag is set (or unset) from within the game.
    // Super useful when debugging; set with our Config option
    [HarmonyPatch(typeof(DataStorage), nameof(DataStorage.Set), new Type[] { typeof(DataStorage.Category), typeof(int), typeof(int) })]
    public static class DataStorage_Set1
    {
        public static void Prefix(DataStorage.Category c, int index, int value)
        {
            if (cfgPrintFlagChanges.Value)
            {
                if (c != DataStorage.Category.kScriptLocalVariable && c != DataStorage.Category.kMapLocalVariable && c != DataStorage.Category.kAreaLocalVariable)
                {
                    Log.LogWarning($"SetFlag: {c} , {index} , {value}");
                }
            }
        }
    }


    // Hook receiving items; we need to flip switches and do multiworld stuff.
    [HarmonyPatch(typeof(OwnedItemClient), nameof(OwnedItemClient.AddOwnedItem), new Type[] { typeof(int), typeof(int) })]
    public static class OwnedItemClient_AddOwnedItem
    {
        public static bool Prefix(int contentId, int count, OwnedItemClient __instance)
        {
            // No multiworld?
            if (randoCtl.isVanilla())
            {
                return true;  // Normal processing.
            }

            // Multiworld item checks...
            if (randoCtl.gotLocationAsFauxItem(contentId, count))
            {
                return false; // DON'T get this item (it will crash the game, as it does not exist)
            }

            // Adamantite check: allow them to upgrade the Airship (which is a separate Flag)
            if (contentId == 47)
            {
                // Flag "got the Adamantite"
                DataStorage.instance.Set("ScenarioFlag1", 69, 1);
                Log.LogInfo("Hooking GetItem(Adamantite) and setting ScenarioFlag1:69");

                // They can still get it. Sure, why not?
                return true;
            }

            // Allow them to get the item in all other cases.
            Log.LogInfo($"About to get regular item: {contentId}");
            return true;
        }
    }


    //
    [HarmonyPatch(typeof(External.Misc), nameof(External.Misc.SystemCall), new Type[] { typeof(MainCore) })]
    public static class External_Misc_SystemCall
    {
        public static bool Prefix(ref MainCore mc, int __result)
        {
            // Don't hook anything when not running a multiworld
            // (It's harmless to run this, but let's keep things pristine.)
            if (randoCtl.isVanilla())
            {
                return true; // Normal processing
            }


            // Handle our own fake SysCalls here, rather than trying to add them to the lookup dictionary.
            string sysCallFn = mc.currentInstruction.operands.sValues[0];
            if (sysCallFn == "InitOpenWorldRando")
            {
                Log.LogInfo($"Triggered custom SysCall: '{sysCallFn}'");
                doInitOpenWorldRando();

                return false;  // Don't continue to run this function.
            }

            // Rename our SysCall in certain cases
            if (SysCallReplacements.ContainsKey(sysCallFn))
            {
                mc.currentInstruction.operands.sValues[0] = SysCallReplacements[sysCallFn];
                return true;  // Continue to run this function.
            }

            return true; // Normal processing
        }

        //
        // TODO: Long-term, I think we probably want to send *everything* as an Item (not a SysCall) and just intercept it.
        //       That makes our "beat the game" checks simpler, and it allows us to put jobs into Treasure Chests
        //       (which is trivial to manage, since we already basically do that for Remote-earned Jobs.
        //
        public static void Postfix(ref MainCore mc)
        {
            string sysCallFn = mc.currentInstruction.operands.sValues[0];
            if (sysCallFn.StartsWith("ジョブ開放："))
            {
                Log.LogInfo($"SysCall: {sysCallFn}");
                randoCtl.CheckAndNotifyCompletion();
            }
        }
    }


    // Our own custom SysCall, used to initialize the game
    private static void doInitOpenWorldRando()
    {
        // Note: For the sake of "forcing" an event to be always on/off, we reserve the following ScenarioFlag1 flags:
        //   38 = Always OFF
        //   19 = Always ON

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

        DataStorage.instance.Set("ScenarioFlag1", 140, 1);  // Press X to "STELLA!!!"
        DataStorage.instance.Set("ScenarioFlag1", 163, 1);  // Book Case won't block your path any more.
        DataStorage.instance.Set("ScenarioFlag1", 197, 1);  // Set when you walk through the teleporter at the back of the Wind Shrine for the first time; "how to use crystals"
                                                            // TODO: Win condition? DataStorage.instance.Set("ScenarioFlag1", 198, 1);  // Set when the all four meteorites are charged.
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
        DataStorage.instance.Set("ScenarioFlag2", 105, 1); // Seems to be set after viewing the first Tycoon flashback night scene
        DataStorage.instance.Set("ScenarioFlag2", 106, 1);  // Set after viewing the second Tycoon night scene(Lenna &Sarisa's past)
        DataStorage.instance.Set("ScenarioFlag2", 109, 1);  // Gohn, Track King Tycoon 1
        DataStorage.instance.Set("ScenarioFlag2", 110, 1);  // Gohn, Track King Tycoon 2
        DataStorage.instance.Set("ScenarioFlag2", 111, 1);  // Gohn, Track King Tycoon 3
        DataStorage.instance.Set("ScenarioFlag2", 112, 1);  // Gohn, Track King Tycoon 4
        DataStorage.instance.Set("ScenarioFlag2", 113, 1);  // After Cid+Mid fall onto the airship and then they go downstairs
        DataStorage.instance.Set("ScenarioFlag2", 114, 1);  // After defeating Cray Claw and then launching the ship.
        DataStorage.instance.Set("ScenarioFlag2", 175, 1);  // After fighting the Adamantite boss

        // Turn on auto-dash
        UserDataManager.Instance().Config.IsAutoDash = 1;

        // Turn off encounters
        // TODO: Can we prompt the in-game marquee for this? Less surprising for the player...
        CheatSettingsClient.Instance().SetIsEnableEncount(false);  // This makes the cheats appear as off in your save file (when you reload)
        UserDataManager.Instance().CheatSettingsData.IsEnableEncount = false;  // This.. actually turns encounters off (after a new game, etc.)
        UserDataManager.Instance().IsOpenedGameBoosterWindow = true;   // I think this makes the "Encouters Off" button appear on screen, but only after you reload.
                                                                       // TODO: How to get the "Encounters Off" button to appear after a new game? CheatSettingsClient doesn't seem to have it...

        // Boost EXP/AP, but not gil
        // Note: Something like "3" *could* work, but it won't show up in the Boost menu, and
        //       that will reset it to 0 (which is awkward).
        CheatSettingsClient.Instance().SetExpRate(4);
        CheatSettingsClient.Instance().SetAbpRate(4);

        // Give them our new "Server" item
        // TODO: Re-enable... and why do we get 4?
        OwnedItemClient client = new OwnedItemClient();
        client.AddOwnedItem(1691, 1); // Server Connection

        // Rename from "???" to "Bartz"
        // TODO: We *can* do custom names for everyone else, but it requires some hacking (see my other FF5 mod).
        foreach (var entry in UserDataManager.Instance().OwnedCharacterList)
        {
            if (entry.Id == 1)
            {
                entry.Name = "Bartz";
            }
        }


        // Debug: Give us some power items!
        //OwnedItemClient client = new OwnedItemClient();
        //client.AddOwnedItem(128, 20); // Fire Rod
        //client.AddOwnedItem(129, 20); // Frost Rod
        //client.AddOwnedItem(130, 20); // Thunder Rod
    }




    // Track the state the game is in; we need to know when we're on the 'Main' scene, and when we're back at the title screen
    // We must track the game's state in Vanilla mode as well as in Rando mode, because they might try to Load a different save file
    //   or reset to the Title screen.
    [HarmonyPatch(typeof(GameStateTracker), nameof(GameStateTracker.SetGameState), new Type[] { typeof(GameStates) })]
    public static class GameStateTracker_SetGameState
    {
        public static void Prefix(GameStates pNewState)
        {
            // Are we in the "MainGame" Scene (State: InGame)
            onMainScene = (pNewState == GameStates.InGame);

            // Did we transition to the title screen?
            // If so, ban receiving items for a bit
            if (pNewState == GameStates.Title)
            {
                onFieldOnce = false;

                randoCtl.justSwitchedToTitle();
            }

            //Log.LogInfo($"--------- NEW SCENE: {pNewState}");
        }
    }

    // Tracked across both vanilla and rando mode
    // There's also a PushSubState() that takes a state + a sub-state, but I don't think we need to track that too.
    // TODO: If you get weird state bugs, then maybe we *did* have to track it!
    [HarmonyPatch(typeof(GameStateTracker), nameof(GameStateTracker.PushSubState), new Type[] { typeof(GameSubStates) })]
    public static class GameStateTracker_PushSubState
    {
        public static void Prefix(GameSubStates pSubState)
        {
            // Are we in a menu of some kind?
            //inSomeMenu = MyMenuStates.Contains(pSubState);

            // Did we load onto a field map?
            // If so, we can receive multiworld items.
            //
            // TODO: There's a behavior issue here: if you Load a save file from within the game, you go from
            //       InGame_Field -> InGame_Field, *but* PushSubState isn't called after the load (you're still in the *same* state).
            //       That means any pending items will only show up after you go into a menu. For now, I'm ok with this behavior; it's
            //       kind of tricky to fix without breaking anything else.
            //
            onFieldTicks = -1;
            if (pSubState == GameSubStates.InGame_Field)
            {
                onFieldOnce = true;
                onFieldTicks = 0; // This will allow it to increment
            }

            // Title Screen menu item selections.
            else if (pSubState == GameSubStates.Title_NewGame)  // There's also 'GameSubStates.Title_LoadGame'
            {
                // The player needs to pick a seed!
                // This happens in Vanilla mode too; we're not really in a "mode" per se when at the Title Screen
                SeedPicker.Instance.PromptUser();
            }

            //Log.LogInfo($"+++++++++ PUSH SUB STATE A: {pSubState}");
        }
    }


    // TEMP
    /*
    [HarmonyPatch(typeof(GameStateTracker), nameof(GameStateTracker.PushSubState), new Type[] { typeof(GameStates), typeof(GameSubStates) })]
    public static class GameStateTracker_PushSubState2
    {
        public static void Prefix(GameStates pGameState, GameSubStates pSubState)
        {

            Log.LogInfo($"+++++++++ PUSH SUB STATE B: {pSubState} (state: {pGameState})");
        }
    }*/



    // Save our "multiworld" options as a single variable in the "userdata" section of the FF5 save file
    // (We used to use "config", but it loads too late ---we need our patch to load *before* we start adding items to our inventory)
    [HarmonyPatch(typeof(UserDataManager), nameof(UserDataManager.ToJSON), new Type[] { typeof(bool) })]
    public class UserDataManager_ToJSON
    {
        public static void Postfix(bool isClear, ref string __result)
        {
            // Are we currently playing a multiworld game?
            DateTime timerStart = DateTime.Now;
            if (!randoCtl.isVanilla())
            {
                // 1. Parse it
                JsonNode originalJson = JsonNode.Parse(__result);

                // 2. Add in our own saved settings
                originalJson.AsObject().Add("multi_world_data", randoCtl.getMultiworldSaveDateCopy());

                // 3. Serialize the wole thing back to json
                var options = new JsonSerializerOptions { WriteIndented = false, Encoder = JavaScriptEncoder.Create(UnicodeRanges.All) };
                __result = originalJson.ToJsonString(options);

                Log.LogInfo("Save multiworld-aware save file");
            }
            float diffTime = (float)(DateTime.Now - timerStart).TotalSeconds;
            Log.LogInfo($"ToJson hooked in: {diffTime} seconds");
        }
    }


    [HarmonyPatch(typeof(UserDataManager), nameof(UserDataManager.FromJsonAsync), new Type[] { typeof(string), typeof(bool), typeof(bool) })]
    public class UserDataManager_FromJsonAsync
    {
        public static void Prefix(ref string json, bool isClear, bool isExtraLibrary)
        {
            // Are we dealing with a multiworld save?
            DateTime timerStart = DateTime.Now;
            if (json.Contains("multi_world_data"))
            {
                // 1. Parse it to JSON
                JsonNode originalJson = JsonNode.Parse(json);

                // 2. Remove our saved setting
                JsonObject mwData = originalJson.AsObject()["multi_world_data"].AsObject();

                // 3. Remove it (so that it doesn't mess up FF5's JSON loader)
                originalJson.AsObject().Remove("multi_world_data");

                // 4. Serialize it back to a string so that FF5 is none the wiser
                var options = new JsonSerializerOptions { WriteIndented = false, Encoder = JavaScriptEncoder.Create(UnicodeRanges.All) };
                json = originalJson.ToJsonString(options);

                Log.LogInfo("Loading multiworld-aware save file");

                // We actually have to load the patches now!
                LoadRandoFiles(mwData["seed_file_path"].ToString(), mwData);
            }
            float diffTime = (float)(DateTime.Now - timerStart).TotalSeconds;
            Log.LogInfo($"FromJson hooked in: {diffTime} seconds");
        }
    }


    // Grab all PendingItems cached by our Client, and clear that array.
    // Note: If you don't do anything with this return value, your items will not appear!
    static List<Engine.PendingItem> SwapAndClearPendingItems()
    {
        List<Engine.PendingItem> res = new List<Engine.PendingItem>();
        lock (Engine.PendingItems)
        {
            foreach (var entry in Engine.PendingItems)
            {
                res.Add(entry);
            }
            Engine.PendingItems.Clear();
        }
        return res;
    }
    // Same for Jobs
    static List<Engine.PendingJob> SwapAndClearPendingJobs()
    {
        var res = new List<Engine.PendingJob>();
        lock (Engine.PendingJobs)
        {
            foreach (var entry in Engine.PendingJobs)
            {
                res.Add(entry);
            }
            Engine.PendingJobs.Clear();
        }
        return res;
    }


    // Give the player the item (if they didn't get it before), track it, and pop up a notification
    static void ReceivedRemoteItem(Engine.PendingItem entry)
    {
        // Were we already given this? Also: add it to our list.
        if (!randoCtl.checkAndMarkAsset(entry.asset_id))
        {
            Log.LogInfo($"Item ignored; we already have it: {entry.asset_id}");
            return;
        }

        Log.LogInfo($"New Item Debug: A.1: {entry.content_id} , {entry.content_num}");  // TODO: We are having issuse with this...
        OwnedItemClient client = new OwnedItemClient();
        Log.LogInfo("New Item Debug: A.2");  // TODO: We are having issuse with this...
        client.AddOwnedItem(entry.content_id, entry.content_num);
        Log.LogInfo("New Item Debug: A.3");  // TODO: We are having issuse with this...

        // Show the player they got it!
        Marquee.Instance.ShowMessage(entry.message);
        Log.LogInfo(entry.message);
    }
    // Same for jobs
    static void ReceivedRemoteJob(Engine.PendingJob entry)
    {
        // Were we already given this? Also: add it to our list.
        if (!randoCtl.checkAndMarkAsset(entry.asset_id))
        {
            Log.LogInfo($"Job ignored; we already have it: {entry.asset_id}");
            return;
        }

        // Unlock the job
        Current.ReleaseJobCommon(entry.job_id);

        // Did they beat the game?
        randoCtl.CheckAndNotifyCompletion();
        
        // Show the player they got their job!
        // (We show this *after* the "beat the game" notification).
        Marquee.Instance.ShowMessage(entry.message);
        Log.LogInfo(entry.message);
    }



    // This is called every game frame, and it's called on the main thread.
    // We'll test adding items here...
    [HarmonyPatch(typeof(MainGame), nameof(MainGame.Update))]
    public class MainGame_Update
    {
        // Used as a rudimentary frame counter to avoid checking gained items every tick
        private static int frameTick = 0;

        public static void Prefix(MainGame __instance)
        {
            // Check nothing in a vanilla scenario
            if (randoCtl.isVanilla())
            {
                return;
            }

            // Check if we should deal with multiworld items/jobs
            if (onFieldOnce && onMainScene)
            {
                // Count up?
                if (onFieldTicks >= 0 && onFieldTicks < 10)
                {
                    //Log.LogError($"COUNTING UP: {onFieldTicks}");
                    onFieldTicks += 1;
                }

                if (onFieldTicks >= 10) {
                    // Every so often
                    frameTick += 1;
                    if (frameTick >= 30)
                    {
                        frameTick = 0;

                        // Items
                        {
                            List<Engine.PendingItem> items = SwapAndClearPendingItems();
                            foreach (var entry in items)
                            {
                                ReceivedRemoteItem(entry);
                            }
                        }

                        // Jobs
                        {
                            List<Engine.PendingJob> jobs = SwapAndClearPendingJobs();
                            foreach (var entry in jobs)
                            {
                                ReceivedRemoteJob(entry);
                            }
                        }
                    }
                }
            }

            // TODO: Need some logic here to check what scene we're in...
        }
    }


    // Patching JSON files
    [HarmonyPatch(typeof(ResourceManager), nameof(ResourceManager.IsLoadAssetCompleted), new Type[] { typeof(string) })]
    public static class ResourceManager_IsLoadAssetCompleted
    {
        // List of Assets (by ID) that Unity has loaded that we know we've already patched.
        // TODO: This should probably be cleared when we change seeds (since we will need to re-patch).
        private static SortedSet<int> knownAssets = new SortedSet<int>();

        public static bool Prefix(string addressName, ResourceManager __instance, bool __result)
        {
            // Pause (forever) on loading the first Map asset for the starting cutscene.
            // We will hold here while the user selects their Seed file (or a non-randomized New Game).
            // This needs to happen in 'vanilla' too, since we can pick either vanilla or rando from the New Game screen
            if (addressName == "Assets/GameAssets/Serial/Res/Map/Map_20250/package")
            {
                if (randoCtl.isWaitingOnSeedSelection())
                {
                    __result = false;
                    return false;
                }
            }


            // When connecting to the multiworld server, we do an async connection.
            // This particular resource is the safest one to wait on; we *know* it's coming.
            // I think other resources can load in the background?
            // TODO: This condition isn't exactly correct; they may be playing a "multiworld" seed entirely offline (or with only 1 player).
            if (!randoCtl.isVanilla())
            {
                // We assume they are loading *some* map, and use our randoCtl.isX() functions to fill in the gaps
                //if (addressName == "Assets/GameAssets/Serial/Res/Map/Map_20250/Map_20250/entity_default")
                if (addressName.StartsWith("Assets/GameAssets/Serial/Res/Map/") && addressName.EndsWith("/entity_default"))
                {
                    // Are we waiting on anything server related?
                    if (randoCtl.isWaitingOnServerSettings() || randoCtl.isWaitingOnServerConnection())
                    {
                        //Log.LogWarning("Waiting.....................");
                        __result = false;
                        return false;
                    }
                }
            }
                


            return true;
        }

        // addressName is the path to the asset; something like:
        //   "Assets/GameAssets/Serial/Res/Map/Map_20011/Map_20011_1/entity_default"
        // ...meanwhile, the lookup within our dictionary is something like:
        //   map_20011:Map_20011_1:/layers/0/objects/2
        public static void Postfix(string addressName, ResourceManager __instance, bool __result)
        {
            // Don't hook anything if we have no seed selected.
            // This also occurs when the game has been started but before a random seed has been selected.
            if (randoCtl.isVanilla())
            {
                return;
            }

            //
            // NOTE: Most things like maps, events, and scripts are loaded every time you switch maps,
            //       so they can be easily patched here. Two exceptions are "Message" and "Master" files.
            //       These are only ever loaded once (globally) when the game starts up. We can't patch them
            //       then, because we might switch rando seeds at some point. Thus, we have to patch 
            //       message/master files after the fact, and undo this patching if we switch seeds or 
            //       move to a vanilla save file. Just be aware.
            //

            // Avoid an infinite loop of errrors
            try
            {
                // Is the base asset fully loaded? If so, it will be in the PR's big list of known Asset objects
                // Presumably the "__res" would also be true in that case, but the completeAssetDic is a stronger check.
                if (!__instance.completeAssetDic.ContainsKey(addressName))
                {
                    return;  // Don't worry, this function will be called again (for this asset) later.
                }

                //Log.LogError($"ASSET CHECK: {addressName}");

                // Do we need to patch this resource?
                if (!randoCtl.needsJsonPatch(addressName))
                {
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

                // Patch it!
                TextAsset newAsset = randoCtl.patchAllJson(addressName, originalAsset);

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


    }



}

