using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Helpers;
using Archipelago.MultiClient.Net.Models;
using Il2CppSystem.Runtime.Remoting.Messaging;
using Last.Data.Master;
using Last.Data.User;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using Last.Interpreter.Instructions.SystemCall;
using Last.Management;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Security.AccessControl;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using static Last.Interpreter.Instructions.External;

namespace MyFF5Plugin
{
    // This is meant to hold all of our "game" logic that *isn't* hooked in to the FF5 game engine.
    // I.e., we just add this to the Unity game as its own Component, and it just runs forever.
    public sealed class Engine : MonoBehaviour
    {
        // Things we're waiting on
        public class PendingItem
        {
            public int content_id;
            public int content_num;
            public string message;
        }
        public class PendingJob
        {
            public Current.JobId job_id;
            public string message;
        }

        // List of items that should be added to the player's inventory the next time we're on the main thread.
        // WARNING: Make sure you use "lock()" on this object when reading/modifying it.
        // (See: Plugin.Update())
        public static List<PendingItem> PendingItems = new List<PendingItem>();
        // Same for jobs
        public static List<PendingJob> PendingJobs = new List<PendingJob>();

        // Helper class: Manage multiworld state
        /* TODO: How much of this do we need?
        private class MultiWorldState
        {
            // List of locations that we've checked
            private List<int> locationsChecked = new List<int>();

            public void locationChecked(int locationId)
            {

            }
        }
        private static MultiWorldState state = new MultiWorldState();
        */

        // Our MultiClient session
        // TODO: Pull settings from a config file
        // TODO: I should probably modify the ArchipelagoMultiClient to stop using 
        //       Newtonsoft.Json.dll -- I don't care about its config.
        // TODO: Any way to compile the MultiClient DLL into our code? Maybe do this and
        //       the previous line at the same time?
        private static ArchipelagoSession session;


        public void Awake()
        {
            // Launch our session
            Engine.session = ArchipelagoSessionFactory.CreateSession("localhost", 38281);

            // ...and try to connect (only request notifications for remote items being given to you...)
            // TODO: We'll need to reconnect if the server changes (think about mult. save files too)
            // TODO: Also, player name. Gah... this is getting complicated.
            LoginResult result;

            // Set up our "Item Received" handler
            session.Items.ItemReceived += On_ItemReceived;

            // Try to connect.
            try
            {
                result = Engine.session.TryConnectAndLogin("Final Fantasy V PR", "Sorlok", ItemsHandlingFlags.RemoteItems);
            } catch (Exception e) {
                result = new LoginFailure(e.GetBaseException().Message);
            }

            // Report more standard errors.
            if (!result.Successful)
            {
                LoginFailure failure = (LoginFailure)result;
                string errorMessage = $"Failed to Connect to {"localhost"} as {"Sorlok"}:";
                foreach (string error in failure.Errors)
                {
                    errorMessage += $"\n    {error}";
                }
                foreach (ConnectionRefusedError error in failure.ErrorCodes)
                {
                    errorMessage += $"\n    {error}";
                }

                Plugin.Log.LogError($"MULTIWORLD ERROR: {errorMessage}");
                Plugin.Log.LogError($"Turning off multiworld; you are now playing offline...");
                Engine.session = null;  // TODO: We might keep this open and mark failure some other way...
            }
            else
            {
                // Deal with successful connection
                var loginSuccess = (LoginSuccessful)result;
                string slotKeys = String.Join(",", loginSuccess.SlotData.Keys);
                Plugin.Log.LogInfo($"Multiworld connected! Slot: {loginSuccess.Slot}; Slot Data Keys: {slotKeys}");
            }
        }

        // Called remotely to say "you got the item"
        // TODO: Eventually we need better logic for things like loading Save Files, etc.
        //       I.e., You can't react to this if you're on the title screen,
        //       but let's get our prototype working first...
        private void On_ItemReceived(ReceivedItemsHelper itemHelper)
        {
            // TODO: Of course this will never be null (it's a callback ON the session), but I 
            //       think eventually we want to have a separate "you're in a multiworld" check
            //       (consider; they start a multiworld, then reload a single player save).
            if (Engine.session != null)
            {
                // Which item was it?
                ItemInfo item = itemHelper.PeekItem();
                int itemId = (int)item.ItemId; // This will never be greater than INT_MAX, since we set it ourselves.
                int contentId = itemId - Plugin.secretSantaHelper.remote_item_content_id_offset;
                int itemCount = 1;
                string marqueeMsg = "";   // What to show at the top of the screen.
                Plugin.Log.LogInfo($"Item received: {itemId} (content ID {contentId}) from: {item.Player.Name}");

                // Translate: Some items are in bundles
                if (Plugin.secretSantaHelper.content_id_special_items.ContainsKey(contentId))
                {
                    string[] entry = Plugin.secretSantaHelper.content_id_special_items[contentId];
                    if (entry[0] == "item")
                    {
                        contentId = Int32.Parse(entry[1]);
                        itemCount = Int32.Parse(entry[2]);
                        marqueeMsg = $"Received MultiWorld Item[{item.ItemId}] '{item.ItemName}' from player '{item.Player}'";
                        Plugin.Log.LogInfo($"Translate item ID: {item.ItemId} into item ID: {contentId} , count: {itemCount}");
                    }
                    else if (entry[0] == "job")
                    {
                        // Translate this to a JobID
                        int jobId = Int32.Parse(entry[1]);
                        marqueeMsg = $"Received MultiWorld Item[{item.ItemId}] '{item.ItemName}' from player '{item.Player}'";
                        Plugin.Log.LogInfo($"Translate item ID: {item.ItemId} into Job ID: {jobId}");

                        // Save it. Game engine will call Current.ReleaseJobCommon()
                        Current.JobId newJob = Current.JobId.NoMake; // 1 is Freelancer

                        if (jobId == 2)
                        {
                            newJob = Current.JobId.Thief;
                        }
                        else if (jobId == 3)
                        {
                            newJob = Current.JobId.Monk;
                        }
                        else if (jobId == 4)
                        {
                            newJob = Current.JobId.RedMage;
                        }
                        else if (jobId == 5)
                        {
                            newJob = Current.JobId.WhiteMage;
                        }
                        else if (jobId == 6)
                        {
                            newJob = Current.JobId.BlackMage;
                        }
                        else if (jobId == 7)
                        {
                            newJob = Current.JobId.Paladin;
                        }
                        else if (jobId == 8)
                        {
                            newJob = Current.JobId.Ninja;
                        }
                        else if (jobId == 9)
                        {
                            newJob = Current.JobId.Ranger;
                        }
                        else if (jobId == 10)
                        {
                            newJob = Current.JobId.Geomancer;
                        }
                        else if (jobId == 11)
                        {
                            newJob = Current.JobId.Doragoon;
                        }
                        else if (jobId == 12)
                        {
                            newJob = Current.JobId.Bard;
                        }
                        else if (jobId == 13)
                        {
                            newJob = Current.JobId.Summoner;
                        }
                        else if (jobId == 14)
                        {
                            newJob = Current.JobId.Berserker;
                        }
                        else if (jobId == 15)
                        {
                            newJob = Current.JobId.Samurai;
                        }
                        else if (jobId == 16)
                        {
                            newJob = Current.JobId.TimeMage;
                        }
                        else if (jobId == 17)
                        {
                            newJob = Current.JobId.Pharmacist;
                        }
                        else if (jobId == 18)
                        {
                            newJob = Current.JobId.Dancer;
                        }
                        else if (jobId == 19)
                        {
                            newJob = Current.JobId.BlueMage;
                        }
                        else if (jobId == 20)
                        {
                            newJob = Current.JobId.MysticKnight;
                        }
                        else if (jobId == 21)
                        {
                            newJob = Current.JobId.Beastmaster;
                        }
                        else if (jobId == 22)
                        {
                            newJob = Current.JobId.Mime;
                        }
                        else
                        {
                            Plugin.Log.LogError($"Unknown job ID: {jobId}");
                        }

                        // Save it for later.
                        if (newJob != Current.JobId.NoMake)
                        {
                            lock (Engine.PendingJobs)
                            {
                                var newJobObj = new PendingJob();
                                newJobObj.job_id = newJob;
                                newJobObj.message = marqueeMsg;
                                Engine.PendingJobs.Add(newJobObj);
                            }
                        }

                        // Don't let them "add" this item
                        item = null;
                    }
                    else
                    {
                        Plugin.Log.LogError($"Could not determine composite item from: {contentId}, entry: {String.Join(",",entry)}");
                    }
                }

                // Add the item?
                if (item != null)
                {
                    // TODO: This should almost certainly be some kind of "EventLoop" action
                    // TODO: For now; we just send it!
                    //       ...yeah, it's crashing when booting the game (after earning 1 of these), since the framework to accept the item isn't there, I think...
                    lock (Engine.PendingItems)
                    {
                        var newItem = new PendingItem();
                        newItem.content_id = contentId;
                        newItem.content_num = itemCount;
                        newItem.message = marqueeMsg;
                        Engine.PendingItems.Add(newItem);
                    }
                }

                // Confirm that we processed this.
                itemHelper.DequeueItem();
            }
        }

        // Called from within our code to tell it that a location ID has been checked.
        public static void LocationChecked(int locationId)
        {
            // TODO: Tracking location checks might be useful long-term.
            if (Engine.session != null)
            {
                session.Locations.CompleteLocationChecks(new long[] { locationId });
                Plugin.Log.LogInfo($"Sent MultiWorld Location check '{locationId}' to the server");
            }
        }

        public void Update()
        {
            bool isDown = UnityEngine.Input.GetKeyDown(KeyCode.F9);
            string isDownKey = "";
            if (isDown)
            {
                //Plugin.Log.LogError("F9 DOWN!");
                //Plugin.FunkyFlag = true;

                //This might work if we pump the Interpreter, but there's probably an easier way...
                //Plugin.Log.LogError("TRYING JOB");
                //Current.ReleaseJobCommon(Current.JobId.Pharmacist);
                //
                //MainCore x = new MainCore();
                //Current.SystemCallTable["ジョブ開放：侍"].BeginInvoke(x, null, null);
                //Current.SystemCallTable["ジョブ開放：侍"].Invoke(x);
                //Current.SystemCallTable["ジョブ開放：侍"].EndInvoke(null);

                // Nothing?
                //foreach (var job in UserDataManager.Instance().ReleasedJobs)
                //{
                //    Plugin.Log.LogInfo($"RELEASED JOB: {job.Id}");
                //}

                // NOTE: SysCalls are mapped in Current.SystemCallTable, so I can get the Keys, but I 
                //       don't have a great way to pull the names of the functions they point to (due to
                //       the compiled layer in the middle).
                //       The functions seem to be defined in: Last.Interpreter.Instructions.SystemCall,
                //       so we could compare pointers manually, I suppose...

                // Give us some items!
                // Note that, in reality, we may want to avoid doing this while they're in the Item menu (or Battle Item Menu) or a Shop.
                // The game seems robust against this, but it *does* seem confusing.
                //OwnedItemClient client = new OwnedItemClient();
                //client.AddOwnedItem(243, 1); // Thief's Gloves

                // Show it!
                //Marquee.Instance.ShowMessage($"Got an item: {"Thief's Gloves"}!");
            }
        }


    }


}
