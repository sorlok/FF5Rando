using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;


namespace MyFF5Plugin
{
    // This IMGUI HUD is used to pick a seed file from disk (or start a non-seeded game).
    public sealed class SeedPicker : MonoBehaviour
    {
        private Texture2D bgTexture;
        private Texture2D bgBtnTexture;
        private GUIStyle guiStyle;
        private GUIStyle guiBtnStyle;

        // List of options for our drop-down box.
        // "Normal Game" vs. "Seed X,Y,Z"
        class SeedOption
        {
            public SeedOption(string fname)
            {
                this.fname = fname;
            }
            public string fname;
            public string absPath;
            public DateTime lastModified;
        }
        private static List<SeedOption> options = new List<SeedOption>();


        // Text the player has entered for server connections
        private string serverAndPort;
        private string playerName;
        private string serverPassword;


        // What mode is this dialog in?
        enum Mode
        {
            None = 0,    // We're done; don't do anything
            Seed = 1,    // Prompt for seed
            Server = 2,  // Prompt for server
            TrackConnect = 3,  // Track our connection attempt to the server; show an error if an error happens
        }
        Mode currMode = Mode.None;


        // Presumably Unity needs an IntPtr constructor?
        public SeedPicker(IntPtr ptr) : base(ptr)
        {
        }

        // Singleton class
        public static SeedPicker Instance { get; set; }

        public void Awake()
        {
            // Allow others to reference this without saving it.
            Instance = this;

            try
            {
                // Create our background texture
                bgTexture = new Texture2D(1, 1);
                bgTexture.SetPixel(0, 0, new Color(0.0f, 0.0f, 0.7f));
                bgTexture.Apply();
                bgTexture.hideFlags = HideFlags.HideAndDontSave;  // Otherwise it'll get discarded on Scene change.

                // Background for buttons
                bgBtnTexture = new Texture2D(1, 1);
                bgBtnTexture.SetPixel(0, 0, Color.black);
                bgBtnTexture.Apply();
                bgBtnTexture.hideFlags = HideFlags.HideAndDontSave;

                // Create our font info (used to write a message)
                guiStyle = new GUIStyle();
                guiStyle.fontSize = 24;
                guiStyle.normal.textColor = Color.white;
                guiStyle.alignment = TextAnchor.MiddleCenter;

                // We need a style for the buttons, too
                guiBtnStyle = new GUIStyle();
                guiBtnStyle.fontSize = 22;
                guiBtnStyle.normal.textColor = Color.white;
                guiBtnStyle.alignment = TextAnchor.MiddleCenter;
                guiBtnStyle.normal.background = bgBtnTexture;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"SeedPicker class unable to initialize GUI elements: {ex}");
            }

            // Don't process OnGUI() until we say to.
            enabled = false;
        }

        // Called externally; prompt to pick a Seed File!
        // This goes right into setting up a connection to the server.
        public void PromptUser()
        {
            // Make a list of all possible file options
            options.Clear();
            string randDir = Path.Combine(Application.streamingAssetsPath, "Rando");
            foreach (string absPath in Directory.GetFiles(randDir))
            {
                if (Path.GetExtension(absPath) == ".apff5pr")
                {
                    var entry = new SeedOption(Path.GetFileName(absPath));
                    entry.absPath = absPath.Replace('\\', '/');
                    entry.lastModified = File.GetLastWriteTimeUtc(entry.absPath);
                    options.Add(entry);
                }
            }

            // Sort it, append the "New Game" option
            options.Sort(delegate (SeedOption x, SeedOption y)
            {
                if (y.lastModified.CompareTo(x.lastModified) != 0)
                {
                    return y.lastModified.CompareTo(x.lastModified);  // Most recent first
                }
                if (x.absPath.CompareTo(y.absPath) != 0)
                {
                    return x.absPath.CompareTo(y.absPath);  // If abspath is the same, then fname certainly is.
                }

                return 0;
            });
            options.Insert(0, new SeedOption("New Game (Not Randomized)"));

            // Begin showing the GUI
            currMode = Mode.Seed;
            enabled = true;
        }


        // Prompt the user for server credentials
        public void PromptServerLogin(string serverAndPort, string playerName, string serverPassword)
        {
            // Default text values are set here
            this.serverAndPort = serverAndPort;
            this.playerName = playerName;
            this.serverPassword = serverPassword;

            // Begin showing the GUI
            currMode = Mode.Server;
            enabled = true;
        }

        // Track the server connection as it happens
        public void TrackServerConnect()
        {
            // Begin showing the GUI
            currMode = Mode.TrackConnect;
            enabled = true;
        }


        public void Update()
        {
            // We don't need to update anything.
        }

        // Called to handle GUI stuff (using IMGui)
        // Will be skipped if "enabled" is false
        // WARNING: Can be called multiple times per frame, once per GUI "event"
        //          So, if you perform a state transition (react to button press, etc.) in one of these sub-functions,
        //          you MUST set/check some flag to avoid performing this action twice within the same frame.
        public void OnGUI()
        {
            // Draw the background (cover everything)
            GUI.skin.box.normal.background = bgTexture;
            GUI.Box(new Rect(0, 0, Screen.width, Screen.height), GUIContent.none);

            // Which GUI to draw?
            if (currMode == Mode.Seed)
            {
                DrawGUISeed();
            }
            else if (currMode == Mode.Server)
            {
                DrawGUIServer();
            }
            else if (currMode == Mode.TrackConnect)
            {
                DrawGUITrackConn();
            }
        }

        // Draw the "pick a seed file" GUI
        private void DrawGUISeed()
        {
            // Draw the text
            int yPos = 200;
            GUI.Label(new Rect(0, yPos, Screen.width, 50), "Please select a seed file:", guiStyle);
            yPos += 50 + 4;

            // Forget combo boxes, let's just do buttons!
            int xPos = Screen.width / 2 - 300;
            foreach (var entry in options)
            {
                if (GUI.Button(new Rect(xPos, yPos, 600, 50), entry.fname, guiBtnStyle))
                {
                    // Stop showing the menu; the "Server" menu will re-enable this (while the "vanilla" game doesn't care)
                    enabled = false;

                    // React; close this GUI and continue loading the new game
                    if (entry.fname.EndsWith(".apff5pr"))
                    {
                        Plugin.LoadRandoFiles(entry.absPath, null); // Tell it to load the .zip
                    }
                    else
                    {
                        Plugin.LoadRandoFiles(null, null);   // "Normal game"
                    }

                    Plugin.Log.LogInfo($"Player selected multiworld seed: {entry.absPath}");
                }
                yPos += 50 + 4;
            }
        }


        // Draw the "enter server connetions" GUI
        private void DrawGUIServer()
        {
            //
            // TODO: We get a "System.NotSupportedException: Method unstripping failed" if we try to use TextField/TextArea
            //       It's probably not worth our time to get this working... we could probably steal the "prompt user name" dialog
            //       if we want to get fancy.
            //

            // Copy/paste?
            if (UnityEngine.Input.GetKeyDown(KeyCode.Alpha1))
            {
                serverAndPort = GUIUtility.systemCopyBuffer;
            }
            else if (UnityEngine.Input.GetKeyDown(KeyCode.Alpha2))
            {
                playerName = GUIUtility.systemCopyBuffer;
            }
            else if (UnityEngine.Input.GetKeyDown(KeyCode.Alpha3))
            {
                serverPassword = GUIUtility.systemCopyBuffer;
            }

            // Adjust!
            string starredPassword = "<No Password>";
            if (serverPassword != null)
            {
                starredPassword = new string('*', serverPassword.Length);
            }

            // Server label+text
            int yPos = 200;
            GUI.Label(new Rect(0, yPos, Screen.width, 30), "Server Hostname+Port:", guiStyle);
            yPos += 30;
            // 
            guiStyle.normal.textColor = Color.yellow;
            GUI.Label(new Rect(0, yPos, Screen.width, 30), serverAndPort, guiStyle);
            guiStyle.normal.textColor = Color.white;
            yPos += 30 + 10;

            // Player name label+text
            GUI.Label(new Rect(0, yPos, Screen.width, 30), "Player name:", guiStyle);
            yPos += 30 + 10;
            // 
            guiStyle.normal.textColor = Color.yellow;
            GUI.Label(new Rect(0, yPos, Screen.width, 30), playerName, guiStyle);
            guiStyle.normal.textColor = Color.white;
            yPos += 30 + 10;

            // Password label+text
            GUI.Label(new Rect(0, yPos, Screen.width, 30), "Server Password:", guiStyle);
            yPos += 30;
            // 
            guiStyle.normal.textColor = Color.yellow;
            GUI.Label(new Rect(0, yPos, Screen.width, 30), starredPassword, guiStyle);
            guiStyle.normal.textColor = Color.white;
            yPos += 30 + 10;

            // Connect button
            if (GUI.Button(new Rect(Screen.width/2-200, yPos, 400, 50), "Connect", guiBtnStyle))
            {
                // Stop showing the menu; the Plugin will re-enable it
                enabled = false;

                // React; close this GUI and then try to connect to the server
                Plugin.randoCtl.StartServerConnect(serverAndPort, playerName, serverPassword);
                Plugin.Log.LogInfo($"Player confirmed server settings: {serverAndPort} , {playerName} , {starredPassword}");
            }
            yPos += 50 + 20;


            // Tell them how to change these settings.
            guiStyle.fontSize = 20;
            guiBtnStyle.alignment = TextAnchor.UpperCenter;
            GUI.Label(new Rect(0, yPos, Screen.width, 30 * 3), 
                "To change these settings, please edit your BepInEx plugin config file:\n" + 
                Plugin.ConfigFilePath + "\n" + 
                "Or, copy text and press 1, 2, or 3 to paste it into the appropriate box\n" + 
                "Yes, this is annoying; sorry!\n" + 
                "These settings will be saved to your FF5 save file.", guiStyle);
            guiStyle.fontSize = 24;
            guiBtnStyle.alignment = TextAnchor.MiddleCenter;
        }


        // Track our connection attemp to the server and any errors.
        private void DrawGUITrackConn()
        {
            // Describe the connection attempt
            int yPos = 200;
            guiStyle.normal.textColor = Color.white;
            GUI.Label(new Rect(0, yPos, Screen.width, 30), "Connecting to server...", guiStyle);
            yPos += 30;

            // Status of the connection attempt
            if (Engine.Instance.ConnectErrorStr() != null)
            {
                guiStyle.normal.textColor = Color.red;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), $"ERROR: {Engine.Instance.ConnectErrorStr()}", guiStyle);
                return;   // Never show anything past an error
            }
            else if (!Engine.Instance.IsConnected())
            {
                guiStyle.normal.textColor = Color.yellow;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), "(Still connecting)", guiStyle);
                return;   // Don't show past the "connecting..." string
            }
            else
            {
                guiStyle.normal.textColor = Color.green;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), "Success!", guiStyle);
                // Keep going!
            }
            guiStyle.normal.textColor = Color.white;
            yPos += 30 + 10;

            // Describe the login attempt
            GUI.Label(new Rect(0, yPos, Screen.width, 30), "Logging in to server...", guiStyle);
            yPos += 30;

            // Status of the login attempt
            if (Engine.Instance.LoginErrorStr() != null)
            {
                guiStyle.normal.textColor = Color.red;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), $"ERROR: {Engine.Instance.ConnectErrorStr()}", guiStyle);
                return;   // Never show anything past an error
            }
            else if (!Engine.Instance.IsLoggedIn())
            {
                guiStyle.normal.textColor = Color.yellow;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), "(Still trying)", guiStyle);
                return;   // Don't show past the "connecting..." string
            }
            else
            {
                guiStyle.normal.textColor = Color.green;
                GUI.Label(new Rect(0, yPos, Screen.width, 30), "Success!", guiStyle);

                // Trigger the game to start (so they won't really see this screen, but that's ok).
                if (enabled)  // Necessary check, as the GUI function can be called multiple times.
                {
                    Plugin.randoCtl.ServerHasConnected();
                    Plugin.Log.LogInfo("Server has connected; starting game...");
                }

                // Stop drawing for real this time
                enabled = false;

                return;
            }
            //guiStyle.normal.textColor = Color.white;
            //yPos += 30 + 10;

            // TODO: At some point we may want to have a button to "Play Offline", but for now, nevermind.
        }



    }
}

