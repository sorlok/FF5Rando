using Last.Data.User;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using Last.Interpreter.Instructions.SystemCall;
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

                // TODO: TEMP: Try setting a flag!
                //DataStorage.instance.Set("ScenarioFlag1", 21, 1);

                // TODO: Debug
                //Plugin.Log.LogError("Checking transport:");
                //foreach (var transport in UserDataManager.instance.OwnedTransportationList)
                //{
                //  Plugin.Log.LogError($"Transportation: {transport.MapId} , {transport.Position} , {transport.flagNumber}, {transport.Enable} , {transport.WasCollected} , {transport.saveData.ToJSON()}");
                //}
                // Check if we can move it...
                // TODO: This doesn't seem to move the actual ship on the map (even if we change maps)
                //foreach (var transport in UserDataManager.instance.OwnedTransportationList)
                //{
                //    transport.Position.Set(132, 90, 149);
                //    transport.MapId = 1;
                //    transport.Direction = 4;
                //}
                // TODO: *maybe* if you teleport after?

                // TODO: Record these...
                foreach (string name in Current.SystemCallTable.Keys)
                {
                    External.Instruction val = Current.SystemCallTable[name];
                    string fnName = "???";
                    if (val.method_info != null)
                    {
                        fnName = val.method_info.Name;
                    }
                    else if (val.original_method_info != null)
                    {
                        fnName = val.original_method_info.Name;
                    }

                    Plugin.Log.LogWarning($"XXX \n{name}\t{fnName}");
                }


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
