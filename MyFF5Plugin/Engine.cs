using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Helpers;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Packets;
using Last.Interpreter.Instructions.SystemCall;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using static Last.Management.LogManager;

namespace MyFF5Plugin
{
    // This is meant to hold all of our "game" logic that *isn't* hooked in to the FF5 game engine.
    // I.e., we just add this to the Unity game as its own Component, and it just runs forever.
    public sealed class Engine : MonoBehaviour
    {
        // Helper: Keep it simple
        public const string GameNameAP = "Final Fantasy V PR";


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

        // Saved for later: login information
        string username;
        string password; // Can be null

        // Returned by the Connect method
        public RoomInfoPacket roomInfo;


        // State machine: If a given 'task' is non-null, we are waiting on it for 'remainingTaskTime'
        private Task<RoomInfoPacket> connectTask = null;
        private Task<LoginResult> loginTask = null;
        private float remainingTaskTime = 0.0f;
        private DateTime timerStart;  // The time the current task started
        private string currError;     // If non-null, it's an error (with either connect or login)
        private bool allDoneWithRemote;  // There's nothing to do w.r.t. the remote server; we either connected & logged in OR there's no host OR we failed to connect + log in




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
        // NOTE: The Update() function will finish the connection + login
        //       Call (TODO) to check state.
        public void beginConnect(string hostname, int port, string username, string password=null)
        {
            allDoneWithRemote = false;

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
            }
            Engine.session = null;

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
                allDoneWithRemote = true;
                return; // Still counts as success
            }

            // Save params for later login
            this.username = username;
            this.password = password;

            // Launch our session
            // TODO: Get hostname/port from config or save file data
            Engine.session = ArchipelagoSessionFactory.CreateSession(hostname, port);

            // Set up our "Item Received" handler
            Engine.session.Items.ItemReceived += On_ItemReceived;

            // Reset error string
            currError = null;

            // ...and try to connect.
            // TODO: We'll need to reconnect if the server changes (think about mult. save files too)
            // TODO: Also, player name. Gah... this is getting complicated.
            //LoginResult result;
            // Only request items being given to you, not all items that you pick up (or starting items).
            //result = Engine.session.TryConnectAndLogin(GameNameAP, username, ItemsHandlingFlags.RemoteItems);

            // Start an asynchronous connection
            connectTask = Engine.session.ConnectAsync();  // I think this doesn't throw
            remainingTaskTime = 4.0f;   // 4s max
            timerStart = DateTime.Now;
        }


        // Keep trying to connect (called from Update)
        private void continueConnection()
        {
            // Bail out?
            if (Engine.session == null || connectTask == null || currError != null)
            {
                return;
            }

            // Wait a small amount of time
            try
            {
                connectTask.Wait(TimeSpan.FromSeconds(0.1));
            }
            catch (AggregateException ex)
            {
                currError = ex.GetBaseException().Message;
                Engine.session = null;
                Plugin.Log.LogError($"MULTIWORLD CONNECT ERROR: {currError}");
                allDoneWithRemote = true;
                return;
            }

            // Did we time out?
            float diffTime = (float)(DateTime.Now - timerStart).TotalSeconds;
            if (!connectTask.IsCompleted)
            {
                if (diffTime > remainingTaskTime)
                {
                    currError = "Timeout";
                    Engine.session = null;
                    Plugin.Log.LogError($"MULTIWORLD CONNECT ERROR: Timeout[{diffTime}]");
                    allDoneWithRemote = true;
                    return;
                }
            }

            // Is it done?
            if (connectTask.IsCompleted)
            {
                // ...but did we succeed?
                if (connectTask.IsCompletedSuccessfully)
                {
                    roomInfo = connectTask.Result;
                    connectTask = null;  // So we don't try again
                    Plugin.Log.LogInfo($"Multiworld server connection succeded in {diffTime}s");

                    // Start an asynchronous login
                    // "RemoteItems" means "only contact me about items sent to me" (so, not every item and not starting items)
                    // nulls are [version, tags, uuid]
                    loginTask = Engine.session.LoginAsync(GameNameAP, username, ItemsHandlingFlags.RemoteItems, null, null, null, password);
                    remainingTaskTime = 4.0f;   // 4s max
                    timerStart = DateTime.Now;
                }
                else
                {
                    Plugin.Log.LogWarning($"??? I think it failed?");
                }
            }
        }

        // Keep trying to long (called from update)
        private void continueLogin()
        {
            // Bail out?
            if (Engine.session == null || loginTask == null || currError != null)
            {
                return;
            }

            // Wait a small amount of time
            try
            {
                loginTask.Wait(TimeSpan.FromSeconds(0.1));
            }
            catch (AggregateException ex)
            {
                currError = ex.GetBaseException().Message;
                Engine.session = null;
                Plugin.Log.LogError($"MULTIWORLD LOGIN ERROR: {currError}");
                allDoneWithRemote = true;
                return;
            }

            // Did we time out?
            float diffTime = (float)(DateTime.Now - timerStart).TotalSeconds;
            if (!loginTask.IsCompleted)
            {
                if (diffTime > remainingTaskTime)
                {
                    currError = "Timeout";
                    Engine.session = null;
                    Plugin.Log.LogError($"MULTIWORLD LOGIN ERROR: Timeout[{diffTime}]");
                    allDoneWithRemote = true;
                    return;
                }
            }

            // Is it done?
            if (loginTask.IsCompleted)
            {
                // ...but did we succeed?
                if (loginTask.IsCompletedSuccessfully && loginTask.Result.Successful)
                {
                    LoginSuccessful res = (LoginSuccessful)loginTask.Result;
                    loginTask = null;  // So we don't try again

                    string slotKeys = String.Join(",", res.SlotData.Keys);
                    Plugin.Log.LogInfo($"Multiworld server login succeded. Slot: {res.Slot}; Slot Data Keys: {slotKeys}; in {diffTime}s");

                    // We are now done!
                    allDoneWithRemote = true;
                }
                else
                {
                    Plugin.Log.LogWarning($"??? I think it failed?");
                }
            }
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
            // Continue trying to connect/login
            if (!allDoneWithRemote)
            {
                // These won't do anything if we're not waiting for them or they're in error; they're safe to call at any time.
                continueConnection();
                continueLogin();
            }


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
