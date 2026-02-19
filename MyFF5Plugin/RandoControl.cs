using Last.Data.Master;
using Last.Interpreter.Instructions.SystemCall;
using Last.Management;
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Unicode;
using System.Threading.Tasks;
using UnityEngine;
using static MyFF5Plugin.Engine;

namespace MyFF5Plugin
{

    // This class contains everything you need to interact with the randomizer and the multiworld. 
    // Some notes:
    //   1) The instance of this class stored in Plugin will never be null. To check if you're "in" a randomized
    //      save file, call "isVanilla()". If that returns true, then you're not randomizing anything,
    //      nor are you connecting to the server.
    //   2) This class needs to load various patch files AND deal with post-load patching of things like
    //      Messages and Master files. This includes un-patching those files when switching to a normal game.
    //   3) Care is taken to ensure that loading a save file loads that file's seed data (including patches, and
    //      re-patching the post-load resources).
    //   4) This class also manages the MultiWorld socket connection, so it must be able to handle cases where
    //      you can't connect. This could involve allowing the player to re-enter information, or to just play offline.
    //   5) This class should handle all the normal multiworld challenges of "being given Items, but delaying getting them
    //      since you're in a menu" and "you loaded a save file, so please send all Locations to the server", etc.
    public class RandoControl
    {
        // The name of the file that holds our patch data (the files zipped into the .apff5pr)
        // INTERNAL NOTE: We use this variable to check if we're in a vanilla run (whether or not it's null).
        private string multiWorldSeedFile;

        // These flags are used to control how we advance through our New/Load Game custom menus (for connecting to the server, etc.).
        // These are tied to the "SeedPicker" MonoBehavior, and if you break their logical assumptions the game will basically hang.
        private bool multiWorldSeedWasPicked;   // Are we in the "New Game" menu, and waiting for the player to pick a seed?
        private bool multiWorldServerPicked;    // Did the player confirm their Server settings? 
        private bool multiWorldServerConnected; // Did we connect to the server?


        // The server hostname+port, the player name, and the password
        // If null, we will prompt the player to confirm them then "Connect".
        // If non-null, we'll auto-connect
        private string serverName;
        private string playerName;
        private string serverPass; // This one is allowed to be null


        // These files are used to hot-patche resources as they are loaded (as we switch maps).
        private TreasurePatcher treasurePatcher;  // Treasures listed in entity_default (content_id + content_count)
        private EventPatcher eventPatcher;   // Events that need patching (generic open world changes + picking up crystal shards)
        public SecretSantaHelper secretSantaHelper;  // Contains stuff specific to sending/receiving multiworld data
        private CsvDataPatcher csvDataPostPatcher; // Patches the contents of the 'master' directory.

        // ...and these need to be un-patched, since they modify global state that is NOT reloaded
        private MessageListPatcher storyMsgPostPatcher;   // All messages you'll see in a message box
        private MessageListPatcher storyNameplatePostPatcher;  // The speaker of these messages (shown in the nameplate of the message box)


        // Current Json object to save to user data in their save file.
        // Try to keep this simple.
        //
        // TODO: document keys and expected values/purposes
        //
        private static JsonObject multiWorldData;



        // Helper function: Retrieve Messages or Nameplates
        private static Il2CppSystem.Collections.Generic.Dictionary<string, string> GetMessageDictionary()
        {
            return MessageManager.Instance.GetMessageDictionary();
        }
        private static Il2CppSystem.Collections.Generic.Dictionary<string, string> GetNameplateDictionary()
        {
            return MessageManager.Instance.speakerDictionary;
        }


        // Make a copy of the current multiWorldData object for inclusion in the user's save file.
        // A copy is made to avoid JSON "parent" problems
        public JsonNode getMultiworldSaveDateCopy()
        {
            return JsonNode.Parse(multiWorldData.ToJsonString());
        }



        // Are we in a "vanilla" game with no randomization?
        // Note that, technically speaking, we treat the Title screen and other
        //   "in-between" states as "vanilla", since it's easier than having 3 states
        //   (vanilla, in-rando, and other).
        public bool isVanilla()
        {
            return multiWorldSeedFile == null;
        }


        // Retrieve the seed as a string; e.g., '30016...789'
        public string getSeedName()
        {
            if (!isVanilla())
            {
                return secretSantaHelper.seed_name;
            }
            return "00000000000000000000";
        }


        // Change the multi-world seed file (can be null to mean "no seed" (vanilla)
        // This will cause all message/master files to become unpatched/repatched, and will
        // load all the .csv files associated with the zipped patch for use later.
        // Note: multiWorldDataObj will be null when starting a new game (or a vanilla game), and 
        //       will contain Server settings otherwise. If null, we need to prompt for server settings
        public void changeSeedAndReload(string newSeedFile, JsonObject multiWorldDataObj)
        {
            // We must always clear our modified Message and Master data, since a New Game won't expect them to 
            //   be modified, and a different patch might expect them to have their default values (and not patch over them).
            if (storyMsgPostPatcher != null)
            {
                storyMsgPostPatcher.unPatchAllStrings();
            }
            if (storyNameplatePostPatcher != null)
            {
                storyNameplatePostPatcher.unPatchAllStrings();
            }
            if (csvDataPostPatcher != null)
            {
                csvDataPostPatcher.unPatchAllCsvs();
            }

            // Don't show any messages for the old seed
            Marquee.Instance.cancelAllMessages();

            // We also always null out our patches, just to be thorough
            treasurePatcher = null;
            eventPatcher = null;
            secretSantaHelper = null;
            storyMsgPostPatcher = null;
            storyNameplatePostPatcher = null;
            csvDataPostPatcher = null;

            // Reset our connection settings too!
            serverName = null;
            playerName = null;
            serverPass = null;

            // Save the new seed
            multiWorldSeedFile = newSeedFile;

            // Discard old multiWorldData
            multiWorldData = null;

            // Clear state if we're starting a clean New Game
            if (multiWorldSeedFile == null)
            {
                Plugin.Log.LogInfo($"Clearing randomizer seed file and starting a clean new game");

                // Close our session to the server
                Engine.Instance.disconnectFromServer();

                // TODO: Missing anything else?

                return;
            }

            // Else, we're loading a multiworld seed
            Plugin.Log.LogInfo($"Loading randomizer seed file: '{multiWorldSeedFile}'");

            // Try to read our custom hack bundle
            reloadPatchZip();

            // Retrieve server settings from the config object
            if (multiWorldDataObj != null)
            {
                // Save this for later inclusion in the player's save file
                multiWorldData = JsonNode.Parse(multiWorldDataObj.ToJsonString()).AsObject(); // Le sigh...

                // ...and pull out the relevant server settings
                serverName = multiWorldData["server_name"].ToString();
                playerName = multiWorldData["player_name_to_server"].ToString();   // Not sure why this would differ...
                serverPass = multiWorldData["server_password"].ToString();
                if (serverPass == "")
                {
                    serverPass = null;
                }
            }
            else
            {
                // We need to start the player with some basic properties.
                multiWorldData = new JsonObject();
                multiWorldData.Add("seed_file_path", JsonValue.Create(newSeedFile));
                multiWorldData.Add("seed_name", JsonValue.Create(getSeedName()));
                //
                multiWorldData.Add("my_checked_locations", new JsonArray());
                multiWorldData.Add("gifts_from_santa", new JsonArray());
            }

            // Now patch our messages and nameplates.
            storyMsgPostPatcher.patchAllStrings();
            storyNameplatePostPatcher.patchAllStrings();
            csvDataPostPatcher.patchAllCsvs();

            // This counts as "picking" a seed
            multiWorldSeedWasPicked = true;
            multiWorldServerConnected = false;   // ...but we still need to connect

            // We're ready to connect to the multiworld server, now that we have all the patches in place to handle Items received on connect()
            if (serverName == null)
            {
                // Retrieve default values for server name, player name, and password
                // These come from our config file plus our seed bundle
                string playerDefault = secretSantaHelper.player_name;
                if (Plugin.cfgPlayerNameOverride.Value != "")
                {
                    playerDefault = Plugin.cfgPlayerNameOverride.Value;
                }
                string passwordDefault = Plugin.cfgServerPassword.Value;
                if (passwordDefault == "")
                {
                    passwordDefault = null;
                }

                // Confirm server settings with the player
                SeedPicker.Instance.PromptServerLogin(Plugin.cfgServerHostAndPort.Value, playerDefault, passwordDefault);
            }
            else
            {
                // If connection settings were passed, auto-connect
                StartServerConnect(serverName, playerName, serverPass);
            }
        }


        // Called externally: try to connect to the server (with GUI feedback)
        public void StartServerConnect(string serverAndPort, string playerName, string serverPassword)
        {
            this.serverName = serverAndPort;
            this.playerName = playerName;
            this.serverPass = serverPassword;

            // We need to update our save file object, or else this won't persist...
            string passWd = ""; // TODO: We should just save the empty string throughout, and ONLY replace it on the API call.
            if (this.serverPass != null)
            {
                passWd = this.serverPass; 
            }
            multiWorldData["server_name"] = JsonValue.Create(this.serverName);
            multiWorldData["player_name_to_server"] = JsonValue.Create(this.playerName);
            multiWorldData["server_password"] = JsonValue.Create(passWd);

            SeedPicker.Instance.TrackServerConnect();

            string[] parts = this.serverName.Split(":");  // hostname:port
            Engine.Instance.beginConnect(parts[0], Int32.Parse(parts[1]), this.playerName, this.serverPass);

            // We've now selected this
            multiWorldServerPicked = true;
        }



        // Called externally to check + prompt seed completion
        // Returns true if we beat the game.
        public bool CheckAndNotifyCompletion()
        {
            // Count unlocked jobs
            int count = 0;
            foreach (var job in UserDataManager.Instance().GetReleasedJobsClone())
            {
                if (job.Id != 1)  // Freelancer
                {
                    count += 1;
                }
            }

            bool completedSeed = count >= 10;  // TODO: Pull this condition from our .json file, in case we change it!
            if (completedSeed) 
            {
                // Add it to the array as "-1"
                // TODO: Reserve a faux "beat the game" Location ID in our .json, so that we don't risk an error here.
                if (!JsonIntArrayContains(multiWorldData["my_checked_locations"].AsArray(), -1))
                {
                    multiWorldData["my_checked_locations"].AsArray().Add(-1);

                    // Send a "Release" notification to the server (only if this is not in the array).
                    Engine.BeatTheSeed();
                    Marquee.Instance.ShowMessage("Congratulations, you completed your seed!");
                }
            }


            // Regardless of notification, just return the status here.
            return completedSeed;
        }


        // Called externally to say "yep, we connected!"
        public void ServerHasConnected()
        {
            // Did we beat the game?
            // This is basically a safety in case we somehow forget to hook one of the "got a job" methods
            // No point sending locations if we beat the game (they already got it).
            if (!CheckAndNotifyCompletion())
            {
                // Send all checked locations, just to be safe...
                JsonArray checkedLocations = multiWorldData["my_checked_locations"].AsArray();
                if (checkedLocations.Count > 0)
                {
                    List<long> checkedInts = new List<long>();
                    foreach (JsonNode entry in checkedLocations)
                    {
                        long locationId = entry.GetValue<int>();
                        if (locationId != -1)  // How we save the "beat the game" flag.
                        {
                            checkedInts.Add(locationId);
                        }
                    }

                    Plugin.Log.LogInfo($"On reconnect, sending {checkedInts.Count} previously checked locations.");
                    Engine.LocationsChecked(checkedInts.ToArray());
                }
            }

            // Done!
            multiWorldServerConnected = true;
        }


        // Called when the Player goes back to the Title screen
        public void justSwitchedToTitle()
        {
            // If they choose "New Game" they'll need to pick a seed; if they choose
            // "Load Game" then this will be set to True by changeSeedAndReload()
            multiWorldSeedWasPicked = false;
            multiWorldServerPicked = false;
            multiWorldServerConnected = false;
        }

        // Are we still waiting for the player to pick a seed? 
        // Only happens in New Game mode
        public bool isWaitingOnSeedSelection()
        {
            return !multiWorldSeedWasPicked;
        }

        // Are we still waiting for the player to confirm server settings?
        // Only happens in New Game Mode
        public bool isWaitingOnServerSettings()
        {
            return !multiWorldServerPicked;
        }

        // Are we still waiting for the client to connect to the server?
        public bool isWaitingOnServerConnection()
        {
            return !multiWorldServerConnected;
        }


        // Helper: searching through json Arrays is painful in C#
        private bool JsonIntArrayContains(JsonArray array, int value)
        {
            foreach (JsonNode node in array)
            {
                if (node.GetValue<int>() == value)
                {
                    return true;
                }
            }
            return false;
        }


        // Mark this item/job as collected, AND return true if this is the first time we collected it
        // We go by AP's asset_id (item_id), rather than any internal numbering, to keep things simple
        public bool checkAndMarkAsset(int asset_id)
        {
            bool newItem = false;
            JsonArray myGifts = multiWorldData["gifts_from_santa"].AsArray();

            if (!JsonIntArrayContains(myGifts, asset_id))
            {
                myGifts.Add(asset_id);
                newItem = true;
            }
            return newItem;
        }


        // Called when the game engine gives us an item; this function returns
        //   true (and "checks" the Location) if it's actually a Location in disguise.
        // We will only have locations in disguise for multiworld items (items for
        //   other players).
        // TODO: Need to track these so we can re-send them.
        public bool gotLocationAsFauxItem(int contentId, int contentCount)
        {
            // Check for our 'magic number' as the count
            if (contentCount == secretSantaHelper.local_location_content_num_incantation)
            {
                int locationId = contentId - secretSantaHelper.local_location_content_id_offset;
                Plugin.Log.LogInfo($"Got MultiWorld item '{contentId}', which is actually Location {locationId}");

                // Count this as "checked" for when we restart
                if (!JsonIntArrayContains(multiWorldData["my_checked_locations"].AsArray(), contentId))
                {
                    multiWorldData["my_checked_locations"].AsArray().Add(contentId);
                }
                else
                {
                    Plugin.Log.LogWarning($"Location checked twice: {contentId}");  // Harmless, but should be impossible.
                }

                // Send this off to our multiworld server! 
                // (It is expecting the LocationId, but that includes the 9000000)
                Engine.LocationChecked(contentId);

                // Yep, it's a Faux-Item Location
                return true; 
            }

            // This is a regular item
            return false;
        }


        // Open a remote present! Get an item with the given ID and name, from the Player with the given name
        // This may translate into a different item+count (e.g., "5 Potions"), or it may translate into a job.
        // Return the modified Item that we are being given.
        public void openedPresent(int origItemId, string origItemName, string giftGiverName, out Engine.PendingItem newItem, out Engine.PendingJob newJob)
        {
            // Assume nothing
            newItem = null;
            newJob = null;

            // Translate
            int contentId = origItemId - secretSantaHelper.remote_item_content_id_offset;
            int itemCount = 1;
            string marqueeMsg = "";   // What to show at the top of the screen.
            Plugin.Log.LogInfo($"(Pending) Item received: {origItemId} (content ID {contentId}) from: {giftGiverName}");


            // Translate: Some items are in bundles
            if (secretSantaHelper.content_id_special_items.ContainsKey(contentId))
            {
                string[] entry = secretSantaHelper.content_id_special_items[contentId];
                if (entry[0] == "item")
                {
                    contentId = Int32.Parse(entry[1]);
                    itemCount = Int32.Parse(entry[2]);
                    marqueeMsg = $"Received MultiWorld Item[{origItemId}] '{origItemName}' from player '{giftGiverName}'";
                    Plugin.Log.LogInfo($"(Pending) Translate item ID: {origItemId} into item ID: {contentId} , count: {itemCount}");

                    newItem = new PendingItem(origItemId);
                    newItem.content_id = contentId;
                    newItem.content_num = itemCount;
                    newItem.message = marqueeMsg;
                }
                else if (entry[0] == "job")
                {
                    // Translate this to a JobID
                    int jobId = Int32.Parse(entry[1]);
                    marqueeMsg = $"Received MultiWorld Item[{origItemId}] '{origItemName}' from player '{giftGiverName}'";
                    Plugin.Log.LogInfo($"(Pending) Translate item ID: {origItemId} into Job ID: {jobId}");

                    // Save it. Plugin will call Current.ReleaseJobCommon() when it's safe to do so.
                    Current.JobId newJobId = Current.JobId.NoMake; // 1 is Freelancer

                    if (jobId == 2)
                    {
                        newJobId = Current.JobId.Thief;
                    }
                    else if (jobId == 3)
                    {
                        newJobId = Current.JobId.Monk;
                    }
                    else if (jobId == 4)
                    {
                        newJobId = Current.JobId.RedMage;
                    }
                    else if (jobId == 5)
                    {
                        newJobId = Current.JobId.WhiteMage;
                    }
                    else if (jobId == 6)
                    {
                        newJobId = Current.JobId.BlackMage;
                    }
                    else if (jobId == 7)
                    {
                        newJobId = Current.JobId.Paladin;
                    }
                    else if (jobId == 8)
                    {
                        newJobId = Current.JobId.Ninja;
                    }
                    else if (jobId == 9)
                    {
                        newJobId = Current.JobId.Ranger;
                    }
                    else if (jobId == 10)
                    {
                        newJobId = Current.JobId.Geomancer;
                    }
                    else if (jobId == 11)
                    {
                        newJobId = Current.JobId.Doragoon;
                    }
                    else if (jobId == 12)
                    {
                        newJobId = Current.JobId.Bard;
                    }
                    else if (jobId == 13)
                    {
                        newJobId = Current.JobId.Summoner;
                    }
                    else if (jobId == 14)
                    {
                        newJobId = Current.JobId.Berserker;
                    }
                    else if (jobId == 15)
                    {
                        newJobId = Current.JobId.Samurai;
                    }
                    else if (jobId == 16)
                    {
                        newJobId = Current.JobId.TimeMage;
                    }
                    else if (jobId == 17)
                    {
                        newJobId = Current.JobId.Pharmacist;
                    }
                    else if (jobId == 18)
                    {
                        newJobId = Current.JobId.Dancer;
                    }
                    else if (jobId == 19)
                    {
                        newJobId = Current.JobId.BlueMage;
                    }
                    else if (jobId == 20)
                    {
                        newJobId = Current.JobId.MysticKnight;
                    }
                    else if (jobId == 21)
                    {
                        newJobId = Current.JobId.Beastmaster;
                    }
                    else if (jobId == 22)
                    {
                        newJobId = Current.JobId.Mime;
                    }
                    else
                    {
                        Plugin.Log.LogError($"Unknown job ID: {jobId}");
                    }

                    // Save it for later.
                    if (newJobId != Current.JobId.NoMake)
                    {
                        newJob = new PendingJob(origItemId);
                        newJob.job_id = newJobId;
                        newJob.message = marqueeMsg;
                    }
                }
                else
                {
                    Plugin.Log.LogError($"Could not determine composite item from: {contentId}, entry: {String.Join(",", entry)}");
                }
            }

            // Translate: Some items are just items
            // TODO: Clean this function up; it's a mess...
            else
            {
                marqueeMsg = $"Received MultiWorld Item[{origItemId}] '{origItemName}' from player '{giftGiverName}'";
                Plugin.Log.LogInfo($"(Pending) Found basic item: {origItemId} with ID: {contentId} , count: {itemCount}");

                newItem = new PendingItem(origItemId);
                newItem.content_id = contentId;
                newItem.content_num = itemCount;
                newItem.message = marqueeMsg;
            }

        }



        // Internal helper: Deal with the .zip file and its file streams; reloads all our "patch" contents
        // This is only called when in multiworld mode
        private void reloadPatchZip()
        {
            // Everything is pretty much stored in the zipped file
            using (ZipArchive archive = ZipFile.OpenRead(multiWorldSeedFile))
            {
                // Read the Treasure stuff
                {
                    ZipArchiveEntry entry = archive.GetEntry("treasure_mod.csv");
                    if (entry != null)
                    {
                        Stream stream = entry.Open();
                        using (var reader = new StreamReader(stream))
                        {
                            Plugin.Log.LogInfo($"Loading random treasure from zip entry: {entry.Name}");
                            treasurePatcher = new TreasurePatcher(reader);
                        }
                    }
                }

                // Read our script patch file
                {
                    ZipArchiveEntry entry = archive.GetEntry("script_patch.csv");
                    if (entry != null)
                    {
                        Stream stream = entry.Open();
                        using (var reader = new StreamReader(stream))
                        {
                            Plugin.Log.LogInfo($"Loading random event patches from zip entry: {entry.Name}");
                            eventPatcher = new EventPatcher(reader);
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
                            Plugin.Log.LogInfo($"Loading message list strings from zip entry: {entry.Name}");

                            //
                            // TODO: I *think* creating this from scratch works with our "string reset functionality, but if you see message errors here's where to look.
                            //
                            storyMsgPostPatcher = new MessageListPatcher(reader, GetMessageDictionary);
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
                            Plugin.Log.LogInfo($"Loading nameplate list strings from zip entry: {entry.Name}");
                            storyNameplatePostPatcher = new MessageListPatcher(reader, GetNameplateDictionary);
                        }
                    }
                }
                // Read our custom "multiworld" stuff
                {
                    ZipArchiveEntry entry = archive.GetEntry("multiworld_data.json");
                    if (entry != null)
                    {
                        Stream stream = entry.Open();
                        using (var reader = new StreamReader(stream))
                        {
                            Plugin.Log.LogInfo($"Loading some multiworld data from zip entry: {entry.Name}");
                            secretSantaHelper = new SecretSantaHelper(reader);
                        }
                    }
                }
            }

            // Load an event "post" patch, if present.
            // We simply append this on to the existing event patch to keep things simple.
            string eventPostPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_script_post.csv");
            if (File.Exists(eventPostPath))
            {
                Plugin.Log.LogError($"BE AWARE: Loading debug event 'post' script (this is usually only required for debugging) from path: {eventPostPath}");
                using (var reader = new StreamReader(eventPostPath))
                {
                    eventPatcher.readInData(reader);
                }
            }


            // TODO: Put this in the zip file...
            string masterCsvPath = Path.Combine(Application.streamingAssetsPath, "Rando", "rand_master.csv");
            Plugin.Log.LogInfo($"Loading csv partial patches from path: {masterCsvPath}");
            using (var reader = new StreamReader(masterCsvPath))
            {
                csvDataPostPatcher = new CsvDataPatcher(reader);
            }


        }


        // Does the given AssetPath need to be patched?
        public bool needsJsonPatch(string addressName)
        {
            // Do any of our patchers need to patch this asset?
            // Make sure we allow patching the same JSON resource twice, since we might have 
            //   two patches that reference the same Asset.
            return treasurePatcher.needsPatching(addressName) || eventPatcher.needsPatching(addressName);
        }



        // Hot-patch our json files
        public TextAsset patchAllJson(string addressName, Il2CppSystem.Object originalAsset)
        {
            // Both json and strings assets start as "Text" assets.
            TextAsset originalTextAsset = originalAsset.Cast<TextAsset>();
            string newAssetText = null; // This will be produced by our patching function.

            // We need to break off from here
            newAssetText = ApplyJsonPatches(addressName, originalTextAsset);

            // Needed when we overwrite the asset
            // This is copied from Magicite; I'm not sure if it's needed
            //   (we might just be able to steal the TextAsset's name in all cases)
            string name = originalTextAsset.name;
            if (name.Length == 0)
            {
                name = Path.GetFileName(addressName);
            }

            // Make a new TextAsset --we can't write to the '.Text' property, unfortunately...
            return new TextAsset(newAssetText) { name = name };
        }


        private string ApplyJsonPatches(string addressName, TextAsset originalTextAsset)
        {
            // Every function call will just modify this directly.
            JsonNode originalJson = JsonNode.Parse(originalTextAsset.text);

            // Try to patch this map's treasures
            treasurePatcher.patchMapTreasures(addressName, originalJson);

            // Patch events...
            eventPatcher.patchMapEvents(addressName, originalJson);

            // Return a compact version, but make sure we encode UTF-8 without escaping it
            var options = new JsonSerializerOptions { WriteIndented = false, Encoder = JavaScriptEncoder.Create(UnicodeRanges.All) };
            return originalJson.ToJsonString(options);
        }


    }

}
