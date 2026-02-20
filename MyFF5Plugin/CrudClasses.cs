using Last.Data.Master;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;


//
// This file contains classes for use with the CsvDataPatcher
// They are very manual and repetitive, so I'm throwing them in here.
// Maybe if I was a better coder I could automate this somehow...
// I mean, we could potentially move getGameObject() and replaceAsset() into the 
//   AssetPatcher class by using Generics, but they're the smallest part of this
//   (and it makes storing them in the Dictionary a pain).
//


namespace MyFF5Plugin
{


    // Items: Usable from the field and when in battle
    class ItemPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id)
        {
            var assets = MasterManager.Instance.GetList<Item>();
            if (!assets.ContainsKey(id))
            {
                assets[id] = new Item();
            }

            return assets[id];
        }

        protected override void replaceAsset(int id, MasterBase newObj)
        {
            MasterManager.Instance.GetList<Item>()[id] = (Item)newObj;
        }

        protected override MasterBase cloneGameObj(MasterBase orig)
        {
            Item origItem = (Item)orig;
            Item newItem = new Item();
            newItem.Id = origItem.Id;
            newItem.SortId = origItem.SortId;
            newItem.TypeId = origItem.TypeId;
            newItem.SystemId = origItem.SystemId;
            newItem.ItemLv = origItem.ItemLv;
            newItem.AttributeId = origItem.AttributeId;
            newItem.AccuracyRate = origItem.AccuracyRate;
            newItem.DestroyRate = origItem.DestroyRate;
            newItem.StandardValue = origItem.StandardValue;
            newItem.RengeId = origItem.RengeId;
            newItem.MenuRengeId = origItem.MenuRengeId;
            newItem.BattleRengeId = origItem.BattleRengeId;
            newItem.InvalidReflection = origItem.InvalidReflection;
            newItem.PeriodId = origItem.PeriodId;
            newItem.ThrowFlag = origItem.ThrowFlag;
            newItem.PreparationFlag = origItem.PreparationFlag;
            newItem.DrinkFlag = origItem.DrinkFlag;
            newItem.MachineFlag = origItem.MachineFlag;
            newItem.ConditionGroupId = origItem.ConditionGroupId;
            newItem.BattleEffectAssetId = origItem.BattleEffectAssetId;
            newItem.MenuSeAssetId = origItem.MenuSeAssetId;
            newItem.MenuFunctionGroupId = origItem.MenuFunctionGroupId;
            newItem.BattleFunctionGroupId = origItem.BattleFunctionGroupId;
            newItem.Buy = origItem.Buy;
            newItem.Sell = origItem.Sell;
            newItem.SalesNotPossible = origItem.SalesNotPossible;
            return newItem;
        }

        protected override void applyPatch(MasterBase orig, string key, string value)
        {
            Item origItem = (Item)orig;
            switch (key)
            {
                case "sort_id":
                    origItem.SortId = Int32.Parse(value);
                    break;
                case "type_id":
                    origItem.TypeId = Int32.Parse(value);
                    break;
                case "system_id":
                    origItem.SystemId = Int32.Parse(value);
                    break;
                case "item_lv":
                    origItem.ItemLv = Int32.Parse(value);
                    break;
                case "attribute_id":
                    origItem.AttributeId = Int32.Parse(value);
                    break;
                case "accuracy_rate":
                    origItem.AccuracyRate = Int32.Parse(value);
                    break;
                case "destroy_rate":
                    origItem.DestroyRate = Int32.Parse(value);
                    break;
                case "standard_value":
                    origItem.StandardValue = Int32.Parse(value);
                    break;
                case "renge_id":
                    origItem.RengeId = Int32.Parse(value);
                    break;
                case "menu_renge_id":
                    origItem.MenuRengeId = Int32.Parse(value);
                    break;
                case "battle_renge_id":
                    origItem.BattleRengeId = Int32.Parse(value);
                    break;
                case "invalid_reflection":
                    origItem.InvalidReflection = Int32.Parse(value);
                    break;
                case "period_id":
                    origItem.PeriodId = Int32.Parse(value);
                    break;
                case "throw_flag":
                    origItem.ThrowFlag = Int32.Parse(value);
                    break;
                case "preparation_flag":
                    origItem.PreparationFlag = Int32.Parse(value);
                    break;
                case "drink_flag":
                    origItem.DrinkFlag = Int32.Parse(value);
                    break;
                case "machine_flag":
                    origItem.MachineFlag = Int32.Parse(value);
                    break;
                case "condition_group_id":
                    origItem.ConditionGroupId = Int32.Parse(value);
                    break;
                case "battle_effect_asset_id":
                    origItem.BattleEffectAssetId = Int32.Parse(value);
                    break;
                case "menu_se_asset_id":
                    origItem.MenuSeAssetId = Int32.Parse(value);
                    break;
                case "menu_function_group_id":
                    origItem.MenuFunctionGroupId = Int32.Parse(value);
                    break;
                case "battle_function_group_id":
                    origItem.BattleFunctionGroupId = Int32.Parse(value);
                    break;
                case "buy":
                    origItem.Buy = Int32.Parse(value);
                    break;
                case "sell":
                    origItem.Sell = Int32.Parse(value);
                    break;
                case "sales_not_possible":
                    origItem.SalesNotPossible = Int32.Parse(value);
                    break;
                default:
                    Plugin.Log.LogError($"Unknown Item property: {key} (trying to set value to {value})");
                    break;
            }
        }


    }



}
