using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Helpers;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Packets;
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
using System.Net.Sockets;
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


        // Our MultiClient session
        // TODO: Pull settings from a config file. 
        //       Also, I think the RandoControl class should probably drive the Engine, and
        //       the only communication with the main thread should be via the Pending arrays.
        // TODO: I should probably modify the ArchipelagoMultiClient to stop using 
        //       Newtonsoft.Json.dll -- I don't care about its config.
        private static ArchipelagoSession session;



        public Engine(IntPtr ptr) : base(ptr)
        {
        }
        public static Engine Instance { get; set; }



        public void Awake()
        {
            // Everything else is done in doConnect() now
            Instance = this;
        }


        // Try to connect to the given address/port server.
        // This also clears the set of pending items
        // Returns false if the connection attempt fails.
        public bool doConnect(string hostname, int port, string username)
        {
            // First, try to disconnect
            if (Engine.session != null && Engine.session.Socket != null && Engine.session.Socket.Connected)
            {
                Task task = Engine.session.Socket.DisconnectAsync();
                task.Wait(TimeSpan.FromSeconds(0.5));

                // We don't really care if it worked or not, but might as well log it
                if (task.IsCompleted)
                {
                    Plugin.Log.LogInfo($"Clean disconnect successful...");
                }
                else
                {
                    Plugin.Log.LogWarning($"Clean disconnect timed out; this is probably still fine.");
                }

                Engine.session = null;
            }

            // Next, clear all pending items
            lock (Engine.PendingItems)
            {
                Engine.PendingItems.Clear();
            }
            lock (Engine.PendingJobs)
            {
                Engine.PendingJobs.Clear();
            }

            // Bail early if we're told not to bother (i.e., in a vanilla world)
            if (hostname == null)
            {
                return true; // Still counts as success
            }

            // Launch our session
            // TODO: Get hostname/port from config or save file data
            Engine.session = ArchipelagoSessionFactory.CreateSession(hostname, port);

            // Set up our "Item Received" handler
            Engine.session.Items.ItemReceived += On_ItemReceived;

            // ...and try to connect.
            // TODO: We'll need to reconnect if the server changes (think about mult. save files too)
            // TODO: Also, player name. Gah... this is getting complicated.
            LoginResult result;
            try
            {
                // Only request items being given to you, not all items that you pick up (or starting items).
                result = Engine.session.TryConnectAndLogin("Final Fantasy V PR", username, ItemsHandlingFlags.RemoteItems);
            }
            catch (Exception e)
            {
                result = new LoginFailure(e.GetBaseException().Message);
            }

            // Report more standard errors.
            if (!result.Successful)
            {
                LoginFailure failure = (LoginFailure)result;
                string errorMessage = $"Failed to Connect to {hostname}:{port} as {username}:";
                foreach (string error in failure.Errors)
                {
                    errorMessage += $"\n    {error}";
                }
                foreach (ConnectionRefusedError error in failure.ErrorCodes)
                {
                    errorMessage += $"\n    {error}";
                }

                Plugin.Log.LogError($"MULTIWORLD ERROR: {errorMessage}");
                Plugin.Log.LogError($"Turning off internet functionality; you are now playing offline...");
                Engine.session = null;

                return false;
            }
            else
            {
                // Deal with successful connection
                var loginSuccess = (LoginSuccessful)result;
                string slotKeys = String.Join(",", loginSuccess.SlotData.Keys);
                Plugin.Log.LogInfo($"Multiworld connected! Slot: {loginSuccess.Slot}; Slot Data Keys: {slotKeys}");
            }

            return true;
        }



        // Called remotely to say "you got the item"
        // TODO: Eventually we need better logic for things like loading Save Files, etc.
        //       I.e., You can't react to this if you're on the title screen,
        //       but let's get our prototype working first...
        private void On_ItemReceived(ReceivedItemsHelper itemHelper)
        {
            // TODO: It's unclear if this can ever be called with a null session, but we check just in case.
            if (Engine.session != null)
            {
                // Which item was it?
                ItemInfo origItem = itemHelper.PeekItem();

                // Translate it, get it, and track that we've received it.
                // Note that our ItemId will never be greater than INT_MAX since we define it ourselves.
                // TODO: I think we probably want the Engine to pend items if the RandoControl isn't ready
                //       (since it has an 'Update()' function). This makes sense; RandoCtl does all the save file
                //       manipulation, etc.
                PendingItem item;
                PendingJob job;
                Plugin.randoCtl.openedPresent((int)origItem.ItemId, origItem.ItemName, origItem.Player.Name, out item, out job);

                // Save the item for later
                if (item != null)
                {
                    lock (Engine.PendingItems)
                    {
                        Engine.PendingItems.Add(item);
                    }
                }

                // Save the job for later
                if (job != null && job.job_id != Current.JobId.NoMake)
                {
                    lock (Engine.PendingJobs)
                    {
                        Engine.PendingJobs.Add(job);
                    }
                }
                // Confirm that we processed this.
                itemHelper.DequeueItem();
            }
        }

        // Called from within our code to tell it that a location ID has been checked.
        public static void LocationChecked(int locationId)
        {
            // TODO: We need our RandoControl to track and add this to our save file json, and 
            //       we need to send *all* remote locations once on startup (load save).
            if (Engine.session != null)
            {
                session.Locations.CompleteLocationChecks(new long[] { locationId });
                Plugin.Log.LogInfo($"Sent MultiWorld Location check '{locationId}' to the server");
            }
        }

        public void Update()
        {
            // TODO: Here is where we should track if we have Items backed up due to being in a menu, etc., and then sending them.


            // Generic "debug on F9" functionality
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
