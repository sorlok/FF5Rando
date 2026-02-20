using HarmonyLib;
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

    // Content: All items/weapons/spells/etc. are represented with a unique "content_id"
    class ContentPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id, string newCsvStr)
        {
            var assets = MasterManager.Instance.GetList<Content>();
            if ((newCsvStr == null) == (assets.ContainsKey(id))) {
                if (newCsvStr != null)
                {
                    assets[id] = new Content(newCsvStr);
                }
                return assets[id];
            }
            return null;  // Logic error; will be reported by caller.
        }

        protected override void replaceAsset(int id, MasterBase newObj)
        {
            MasterManager.Instance.GetList<Content>()[id] = (Content)newObj;
        }

        protected override MasterBase cloneGameObj(MasterBase orig)
        {
            Content origContent = (Content)orig;
            Content newContent = new Content();
            newContent.Id = origContent.Id;
            newContent.MesIdName = origContent.MesIdName;
            newContent.MesIdBattle = origContent.MesIdBattle;
            newContent.MesIdDescription = origContent.MesIdDescription;
            newContent.IconId = origContent.IconId;
            newContent.TypeId = origContent.TypeId;
            newContent.TypeValue =  origContent.TypeValue;
            return newContent;
        }

        protected override void applyPatch(MasterBase orig, string key, string value)
        {
            Content origContent = (Content)orig;
            switch (key)
            {
                case "mes_id_name":
                    origContent.MesIdName = value;
                    break;
                case "mes_id_battle":
                    origContent.MesIdBattle = value;
                    break;
                case "mes_id_description":
                    origContent.MesIdDescription = value;
                    break;
                case "icon_id":
                    origContent.IconId = Int32.Parse(value);
                    break;
                case "type_id":
                    origContent.TypeId = Int32.Parse(value);
                    break;
                case "type_value":
                    origContent.TypeValue = Int32.Parse(value);
                    break;
                default:
                    Plugin.Log.LogError($"Unknown Content property: {key} (trying to set value to {value})");
                    break;
            }
        }
    }


    // Items: Usable from the field and when in battle
    class ItemPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id, string newCsvStr)
        {
            var assets = MasterManager.Instance.GetList<Item>();
            if ((newCsvStr == null) == (assets.ContainsKey(id)))
            {
                if (newCsvStr != null)
                {
                    assets[id] = new Item(newCsvStr);
                }
                return assets[id];
            }
            return null;  // Logic error; will be reported by caller.
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
