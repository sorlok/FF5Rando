using AsmResolver.PE.Exports;
using Il2CppSystem.Asset;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.U2D;
using static Disarm.Disassembler;

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
            enabled = true;
        }

        public void Update()
        {
            // We don't need to update anything.
        }

        // Called to handle GUI stuff (using IMGui)
        // Can be called multiple times per frame, once per GUI "event"
        // Will be skipped if "enabled" is false
        public void OnGUI()
        {
            // Draw the background (cover everything)
            GUI.skin.box.normal.background = bgTexture;
            GUI.Box(new Rect(0, 0, Screen.width, Screen.height), GUIContent.none);

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
                    // React; close this GUI and continue loading the new game
                    if (entry.fname.EndsWith(".apff5pr"))
                    {
                        Plugin.MultiWorldSeedFile = entry.absPath;
                    }
                    else
                    {
                        Plugin.MultiWorldSeedFile = null; // "Normal game"
                    }
                    Plugin.LoadRandoFiles(); // Tell it to load the .zip
                    Plugin.MultiWorldSeedWasPicked = true;

                    Plugin.Log.LogInfo($"Player selected multiworld seed: {entry.absPath}");

                    enabled = false; // Stop showing the menu
                }
                yPos += 50 + 4;
            }
        }
    }
}

