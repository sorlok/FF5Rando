using Last.Management;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;

namespace MyFF5Plugin
{
    // This is meant to hold all of our "game" logic that *isn't* hooked in to the FF5 game engine.
    // I.e., we just add this to the Unity game as its own Component, and it just runs forever.
    public sealed class Engine : MonoBehaviour
    {
        public void Awake()
        {

        }

        public void Update()
        {
            bool isDown = UnityEngine.Input.GetKeyDown(KeyCode.F9);
            string isDownKey = "";
            if (isDown)
            {
                isDownKey = "F9";
                Plugin.Log.LogInfo($"!!! NEW INPUT: {isDownKey}");

                // Give us some items!
                // Note that, in reality, we may want to avoid doing this while they're in the Item menu (or Battle Item Menu) or a Shop.
                // The game seems robust against this, but it *does* seem confusing.
                OwnedItemClient client = new OwnedItemClient();
                client.AddOwnedItem(243, 1); // Thief's Gloves

                // Show it!
                Marquee.Instance.ShowMessage($"Got an item: {"Thief's Gloves"}!");
            }
        }


    }


}
