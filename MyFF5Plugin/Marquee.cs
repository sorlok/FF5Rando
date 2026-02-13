using AsmResolver.PE.Exports;
using Il2CppSystem.Asset;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.U2D;

namespace MyFF5Plugin
{
    // I'm trying to make a basic HUD that says "you got an item".
    // I borrowed most of this from Magicite, since I *really* don't know Unity.
    public sealed class Marquee : MonoBehaviour
    {
        private Texture2D _blackTexture;
        private GUIStyle _guiStyle;

        // Message to show
        private string message = null;

        // Pending messages
        private List<string> pendingMessages = new List<string>();

        // State of the message:
        //   0 = fade in
        //   1 = show message
        //   2 = fade out
        //   3 = pseudo-state, "done" with fade out
        private int state = 0;

        // Current alpha value, 0.0 to 1.0
        private float alpha = 0.0f;

        // The time the current state started
        DateTime timerStart;

        // How many seconds for each phase (seconds)
        private static float[] StateTimers = { 0.25f, 10.0f, 0.25f };


        // I guess these are required by Unity?
        public Marquee(IntPtr ptr) : base(ptr)
        {
        }
        //
        public static Marquee Instance { get; set; }

        public void Awake()
        {
            // Oh, maybe other files use Marquee.Instance() instead of saving it...
            Instance = this;

            // Modify our 'on screen' time (fade in/out remains constant)
            StateTimers[1] = Plugin.cfgMarqueeDuration.Value;

            try
            {
                // Create our black texture (used for the background)
                _blackTexture = new Texture2D(1, 1);
                _blackTexture.SetPixel(0, 0, Color.black);
                _blackTexture.Apply();
                _blackTexture.hideFlags = HideFlags.HideAndDontSave;  // Otherwise it'll get discarded on Scene change.

                // Create our font info (used to write a message)
                _guiStyle = new GUIStyle();
                _guiStyle.fontSize = 24;
                _guiStyle.normal.textColor = Color.white;
                _guiStyle.alignment = TextAnchor.MiddleCenter;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"Marquee class unable to initialize GUI elements: {ex}");
            }

            // Don't process OnGUI() until we say to.
            enabled = false;
        }


        // Called when the game is reloaded: clear all pending messages
        public void cancelAllMessages()
        {
            pendingMessages.Clear();

            // Might as well cancel the current message too.
            message = null;
            enabled = false;
        }


        // Called externally; show a message!
        // Note: The Marquee class will *always* show its messages when it's ready to (unless you call cancelAllMessages), so
        //       if you don't want popups in battle or something, you'll have to avoid sending messages then.
        public void ShowMessage(string message)
        {
            // Is this feature off entirely?
            if (StateTimers[1] <= 0)
            {
                return;
            }

            // Put it on the queue and handle it in update()
            pendingMessages.Add(message);
            enabled = true;
        }

        public void Update()
        {
            // TODO: This is where we will (presumably) count down and fade out the message (or pull the next one
            //       from the queue to display).
            // Can probably just cheat and use DateTime.Now (if we can't figure out how the engine stores it)
            //   ...I guess that means if they tab out they'll miss it?

            // Are we processing a message?
            if (message != null)
            {
                // State change?
                float diffTime = (float)(DateTime.Now - timerStart).TotalSeconds;
                if (diffTime >= StateTimers[state])
                {
                    state += 1;
                    timerStart = DateTime.Now;  // We'll burn the remaining ms, but it's close enough.
                    diffTime = 0;
                }

                // React to state
                this.alpha = 1.0f; // Represents state 1
                if (state == 0 || state == 2)
                {
                    // Fading in or out
                    alpha = diffTime / StateTimers[state];
                    if (state == 2)
                    {
                        alpha = 1.0f - alpha;
                    }
                }

                // Are we "done"?
                if (state == 3)
                {
                    // Done with current message
                    message = null;
                }
            }

            // Ready for the next message?
            if (message == null)
            {
                // Anything left to show?
                if (pendingMessages.Count > 0)
                {
                    this.message = pendingMessages[0];
                    pendingMessages.RemoveAt(0);
                    this.state = 0;
                    this.timerStart = DateTime.Now;
                    this.alpha = 0.0f;
                }
                else
                {
                    // Stop processing until we get a new message.
                    enabled = false;
                }
            }



        }

        // Called to handle GUI stuff.
        // Can be called multiple times per frame, once per GUI "event"
        // Will be skipped if "enabled" is false
        // I think we manually render GUI elements every frame, since it's like a DearIMGUI thing?
        public void OnGUI()
        {
            // TODO: We need a reasonable way to scale the HUD, the text, and the sprites.
            //       Maybe there's some camera auto-scaling param we can grab?
            //       We might also just hard code it to common resolutions...
            // ...or, does it auto-scale?

            // Could happen for 1 frame; don't confuse the player
            if (message == null)
            {
                return;
            }

            // Enforce the fade)
            GUI.color = new Color(1.0f, 1.0f, 1.0f, alpha);

            int buffer = 10;

            // Set the background texture, and stretch it over the area we want it to go over.
            GUI.skin.box.normal.background = _blackTexture;
            GUI.Box(new Rect(buffer, buffer, Screen.width-buffer*2, 60), GUIContent.none);

            // Set our label's text.
            GUI.Label(new Rect(buffer, buffer, Screen.width-buffer*2, 60), message, _guiStyle);

            // Reset to fully opaque
            GUI.color = Color.white;
        }
    }
}

