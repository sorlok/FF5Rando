using BepInEx;
using HarmonyLib;
using Last.Data.Master;
using SEAD;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;


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

    // Monster: Everything monster-related except AP
    class MonsterPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id, string newCsvStr)
        {
            var assets = MasterManager.Instance.GetList<Monster>();
            if ((newCsvStr == null) == (assets.ContainsKey(id)))
            {
                if (newCsvStr != null)
                {
                    assets[id] = new Monster(newCsvStr);
                }
                return assets[id];
            }
            return null;  // Logic error; will be reported by caller.
        }

        protected override void replaceAsset(int id, MasterBase newObj)
        {
            MasterManager.Instance.GetList<Monster>()[id] = (Monster)newObj;
        }

        protected override MasterBase cloneGameObj(MasterBase orig)
        {
            Monster origMonster = (Monster)orig;
            Monster newMonster = new Monster();
            newMonster.Id = origMonster.Id;
            newMonster.MesIdName = origMonster.MesIdName;
            newMonster.CursorXPosition = origMonster.CursorXPosition;
            newMonster.CursorYPosition = origMonster.CursorYPosition;
            newMonster.InTypeId = origMonster.InTypeId;
            newMonster.DisappearTypeId = origMonster.DisappearTypeId;
            newMonster.Species = origMonster.Species;
            newMonster.ResistanceAttribute = origMonster.ResistanceAttribute;
            newMonster.ResistanceCondition = origMonster.ResistanceCondition;
            newMonster.InitialCondition = origMonster.InitialCondition;
            newMonster.Lv = origMonster.Lv;
            newMonster.Hp = origMonster.Hp;
            newMonster.Mp = origMonster.Mp;
            newMonster.Exp = origMonster.Exp;
            newMonster.Gill = origMonster.Gill;
            newMonster.AttackCount = origMonster.AttackCount;
            newMonster.AttackPlus = origMonster.AttackPlus;
            newMonster.AttackPlusGroup = origMonster.AttackPlusGroup;
            newMonster.AttackAttribute = origMonster.AttackAttribute;
            newMonster.Strength = origMonster.Strength;
            newMonster.Vitality = origMonster.Vitality;
            newMonster.Agility = origMonster.Agility;
            newMonster.Intelligence = origMonster.Intelligence;
            newMonster.Spirit = origMonster.Spirit;
            newMonster.Magic = origMonster.Magic;
            newMonster.Attack = origMonster.Attack;
            newMonster.AbilityAttack = origMonster.AbilityAttack;
            newMonster.Defense = origMonster.Defense;
            newMonster.AbilityDefense = origMonster.AbilityDefense;
            newMonster.AbilityDefenseRate = origMonster.AbilityDefenseRate;
            newMonster.AccuracyRate = origMonster.AccuracyRate;
            newMonster.DodgeTimes = origMonster.DodgeTimes;
            newMonster.EvasionRate = origMonster.EvasionRate;
            newMonster.MagicEvasionRate = origMonster.MagicEvasionRate;
            newMonster.AbilityDisturbedRate = origMonster.AbilityDisturbedRate;
            newMonster.CriticalRate = origMonster.CriticalRate;
            newMonster.Luck = origMonster.Luck;
            newMonster.Weight = origMonster.Weight;
            newMonster.Boss = origMonster.Boss;
            newMonster.MonsterFlagGroupId = origMonster.MonsterFlagGroupId;
            newMonster.DropRate = origMonster.DropRate;
            newMonster.DropContentId1 = origMonster.DropContentId1;
            newMonster.DropContentId1Value = origMonster.DropContentId1Value;
            newMonster.DropContentId2 = origMonster.DropContentId2;
            newMonster.DropContentId2Value = origMonster.DropContentId2Value;
            newMonster.DropContentId3 = origMonster.DropContentId3;
            newMonster.DropContentId3Value = origMonster.DropContentId3Value;
            newMonster.DropContentId4 = origMonster.DropContentId4;
            newMonster.DropContentId4Value = origMonster.DropContentId4Value;
            newMonster.DropContentId5 = origMonster.DropContentId5;
            newMonster.DropContentId5Value = origMonster.DropContentId5Value;
            newMonster.DropContentId6 = origMonster.DropContentId6;
            newMonster.DropContentId6Value = origMonster.DropContentId6Value;
            newMonster.DropContentId7 = origMonster.DropContentId7;
            newMonster.DropContentId7Value = origMonster.DropContentId7Value;
            newMonster.DropContentId8 = origMonster.DropContentId8;
            newMonster.DropContentId8Value = origMonster.DropContentId8Value;
            newMonster.StealContentId1 = origMonster.StealContentId1;
            newMonster.StealContentId2 = origMonster.StealContentId2;
            newMonster.StealContentId3 = origMonster.StealContentId3;
            newMonster.StealContentId4 = origMonster.StealContentId4;
            newMonster.ScriptId = origMonster.ScriptId;
            newMonster.MonsterAssetId = origMonster.MonsterAssetId;
            newMonster.BattleEffectAssetId = origMonster.BattleEffectAssetId;
            newMonster.PUseAbilityRandomGroupId = origMonster.PUseAbilityRandomGroupId;
            newMonster.CommandGroupType = origMonster.CommandGroupType;
            newMonster.ReleaseAbilityRandomGroupId = origMonster.ReleaseAbilityRandomGroupId;
            newMonster.RageAbilityRandomGroupId = origMonster.RageAbilityRandomGroupId;
            return newMonster;
        }

        protected override void applyPatch(MasterBase orig, string key, string value)
        {
            Monster origMonster = (Monster)orig;
            switch (key)
            {
                case "mes_id_name":
                    origMonster.MesIdName = value;
                    break;
                case "cursor_x_position":
                    origMonster.CursorXPosition = Int32.Parse(value);
                    break;
                case "cursor_y_position":
                    origMonster.CursorYPosition = Int32.Parse(value);
                    break;
                case "in_type_id":
                    origMonster.InTypeId = Int32.Parse(value);
                    break;
                case "disappear_type_id":
                    origMonster.DisappearTypeId = Int32.Parse(value);
                    break;
                case "species":
                    origMonster.Species = Int32.Parse(value);
                    break;
                case "resistance_attribute":
                    origMonster.ResistanceAttribute = Int32.Parse(value);
                    break;
                case "resistance_condition":
                    origMonster.ResistanceCondition = Int32.Parse(value);
                    break;
                case "initial_condition":
                    origMonster.InitialCondition = Int32.Parse(value);
                    break;
                case "lv":
                    origMonster.Lv = Int32.Parse(value);
                    break;
                case "hp":
                    origMonster.Hp = Int32.Parse(value);
                    break;
                case "mp":
                    origMonster.Mp = Int32.Parse(value);
                    break;
                case "exp":
                    origMonster.Exp = Int32.Parse(value);
                    break;
                case "gill":
                    origMonster.Gill = Int32.Parse(value);
                    break;
                case "attack_count":
                    origMonster.AttackCount = Int32.Parse(value);
                    break;
                case "attack_plus":
                    origMonster.AttackPlus = Int32.Parse(value);
                    break;
                case "attack_plus_grop":
                    origMonster.AttackPlusGroup = Int32.Parse(value);
                    break;
                case "attack_attribute":
                    origMonster.AttackAttribute = Int32.Parse(value);
                    break;
                case "strength":
                    origMonster.Strength = Int32.Parse(value);
                    break;
                case "vitality":
                    origMonster.Vitality = Int32.Parse(value);
                    break;
                case "agility":
                    origMonster.Agility = Int32.Parse(value);
                    break;
                case "intelligence":
                    origMonster.Intelligence = Int32.Parse(value);
                    break;
                case "spirit":
                    origMonster.Spirit = Int32.Parse(value);
                    break;
                case "magic":
                    origMonster.Magic = Int32.Parse(value);
                    break;
                case "attack":
                    origMonster.Attack = Int32.Parse(value);
                    break;
                case "ability_attack":
                    origMonster.AbilityAttack = Int32.Parse(value);
                    break;
                case "defense":
                    origMonster.Defense = Int32.Parse(value);
                    break;
                case "ability_defense":
                    origMonster.AbilityDefense = Int32.Parse(value);
                    break;
                case "ability_defense_rate":
                    origMonster.AbilityDefenseRate = Int32.Parse(value);
                    break;
                case "accuracy_rate":
                    origMonster.AccuracyRate = Int32.Parse(value);
                    break;
                case "dodge_times":
                    origMonster.DodgeTimes = Int32.Parse(value);
                    break;
                case "evasion_rate":
                    origMonster.EvasionRate = Int32.Parse(value);
                    break;
                case "magic_evasion_rate":
                    origMonster.MagicEvasionRate = Int32.Parse(value);
                    break;
                case "ability_disturbed_rate":
                    origMonster.AbilityDisturbedRate = Int32.Parse(value);
                    break;
                case "critical_rate":
                    origMonster.CriticalRate = Int32.Parse(value);
                    break;
                case "luck":
                    origMonster.Luck = Int32.Parse(value);
                    break;
                case "weight":
                    origMonster.Weight = Int32.Parse(value);
                    break;
                case "boss":
                    origMonster.Boss = Int32.Parse(value);
                    break;
                case "monster_flag_group_id":
                    origMonster.MonsterFlagGroupId = Int32.Parse(value);
                    break;
                case "drop_rate":
                    origMonster.DropRate = Int32.Parse(value);
                    break;
                case "drop_content_id1":
                    origMonster.DropContentId1 = Int32.Parse(value);
                    break;
                case "drop_content_id1_value":
                    origMonster.DropContentId1Value = Int32.Parse(value);
                    break;
                case "drop_content_id2":
                    origMonster.DropContentId2 = Int32.Parse(value);
                    break;
                case "drop_content_id2_value":
                    origMonster.DropContentId2Value = Int32.Parse(value);
                    break;
                case "drop_content_id3":
                    origMonster.DropContentId3 = Int32.Parse(value);
                    break;
                case "drop_content_id3_value":
                    origMonster.DropContentId3Value = Int32.Parse(value);
                    break;
                case "drop_content_id4":
                    origMonster.DropContentId4 = Int32.Parse(value);
                    break;
                case "drop_content_id4_value":
                    origMonster.DropContentId4Value = Int32.Parse(value);
                    break;
                case "drop_content_id5":
                    origMonster.DropContentId5 = Int32.Parse(value);
                    break;
                case "drop_content_id5_value":
                    origMonster.DropContentId5Value = Int32.Parse(value);
                    break;
                case "drop_content_id6":
                    origMonster.DropContentId6 = Int32.Parse(value);
                    break;
                case "drop_content_id6_value":
                    origMonster.DropContentId6Value = Int32.Parse(value);
                    break;
                case "drop_content_id7":
                    origMonster.DropContentId7 = Int32.Parse(value);
                    break;
                case "drop_content_id7_value":
                    origMonster.DropContentId7Value = Int32.Parse(value);
                    break;
                case "drop_content_id8":
                    origMonster.DropContentId8 = Int32.Parse(value);
                    break;
                case "drop_content_id8_value":
                    origMonster.DropContentId8Value = Int32.Parse(value);
                    break;
                case "steal_content_id1":
                    origMonster.StealContentId1 = Int32.Parse(value);
                    break;
                case "steal_content_id2":
                    origMonster.StealContentId2 = Int32.Parse(value);
                    break;
                case "steal_content_id3":
                    origMonster.StealContentId3 = Int32.Parse(value);
                    break;
                case "steal_content_id4":
                    origMonster.StealContentId4 = Int32.Parse(value);
                    break;
                case "script_id":
                    origMonster.ScriptId = Int32.Parse(value);
                    break;
                case "monster_asset_id":
                    origMonster.MonsterAssetId = Int32.Parse(value);
                    break;
                case "battle_effect_asset_id":
                    origMonster.BattleEffectAssetId = Int32.Parse(value);
                    break;
                case "p_use_ability_random_group_id":
                    origMonster.PUseAbilityRandomGroupId = Int32.Parse(value);
                    break;
                case "command_group_type":
                    origMonster.CommandGroupType = Int32.Parse(value);
                    break;
                case "release_ability_random_group_id":
                    origMonster.ReleaseAbilityRandomGroupId = Int32.Parse(value);
                    break;
                case "rage_ability_random_group_id":
                    origMonster.RageAbilityRandomGroupId = Int32.Parse(value);
                    break;
                default:
                    Plugin.Log.LogError($"Unknown Monster property: {key} (trying to set value to {value})");
                    break;
            }
        }
    }


    // MonsterParty: Details about the groups of monsters you fight together
    class MonsterPartyPatcher : AssetPatcher
    {
        protected override MasterBase getGameObject(int id, string newCsvStr)
        {
            var assets = MasterManager.Instance.GetList<MonsterParty>();
            if ((newCsvStr == null) == (assets.ContainsKey(id)))
            {
                if (newCsvStr != null)
                {
                    assets[id] = new MonsterParty(newCsvStr);
                }
                return assets[id];
            }
            return null;  // Logic error; will be reported by caller.
        }

        protected override void replaceAsset(int id, MasterBase newObj)
        {
            MasterManager.Instance.GetList<MonsterParty>()[id] = (MonsterParty)newObj;
        }

        protected override MasterBase cloneGameObj(MasterBase orig)
        {
            MonsterParty origParty = (MonsterParty)orig;
            MonsterParty newParty = new MonsterParty();
            newParty.Id = origParty.Id;
            newParty.BattleBackgroundAssetId = origParty.BattleBackgroundAssetId;
            newParty.BattleBgmAssetId = origParty.BattleBgmAssetId;
            newParty.AppearanceProduction = origParty.AppearanceProduction;
            newParty.ScriptNameId = origParty.ScriptNameId;
            newParty.BattlePattern1 = origParty.BattlePattern1;
            newParty.BattlePattern2 = origParty.BattlePattern2;
            newParty.BattlePattern3 = origParty.BattlePattern3;
            newParty.BattlePattern4 = origParty.BattlePattern4;
            newParty.BattlePattern5 = origParty.BattlePattern5;
            newParty.BattlePattern6 = origParty.BattlePattern6;
            newParty.NotEscape = origParty.NotEscape;
            newParty.BattleFlagGroupId = origParty.BattleFlagGroupId;
            newParty.GetValue = origParty.GetValue;
            newParty.GetAp = origParty.GetAp;
            newParty.Monster1 = origParty.Monster1;
            newParty.Monster1XPosition = origParty.Monster1XPosition;
            newParty.Monster1YPosition = origParty.Monster1YPosition;
            newParty.Monster1Group = origParty.Monster1Group;
            newParty.Monster2 = origParty.Monster2;
            newParty.Monster2XPosition = origParty.Monster2XPosition;
            newParty.Monster2YPosition = origParty.Monster2YPosition;
            newParty.Monster2Group = origParty.Monster2Group;
            newParty.Monster3 = origParty.Monster3;
            newParty.Monster3XPosition = origParty.Monster3XPosition;
            newParty.Monster3YPosition = origParty.Monster3YPosition;
            newParty.Monster3Group = origParty.Monster3Group;
            newParty.Monster4 = origParty.Monster4;
            newParty.Monster4XPosition = origParty.Monster4XPosition;
            newParty.Monster4YPosition = origParty.Monster4YPosition;
            newParty.Monster4Group = origParty.Monster4Group;
            newParty.Monster5 = origParty.Monster5;
            newParty.Monster5XPosition = origParty.Monster5XPosition;
            newParty.Monster5YPosition = origParty.Monster5YPosition;
            newParty.Monster5Group = origParty.Monster5Group;
            newParty.Monster6 = origParty.Monster6;
            newParty.Monster6XPosition = origParty.Monster6XPosition;
            newParty.Monster6YPosition = origParty.Monster6YPosition;
            newParty.Monster6Group = origParty.Monster6Group;
            newParty.Monster7 = origParty.Monster7;
            newParty.Monster7XPosition = origParty.Monster7XPosition;
            newParty.Monster7YPosition = origParty.Monster7YPosition;
            newParty.Monster7Group = origParty.Monster7Group;
            newParty.Monster8 = origParty.Monster8;
            newParty.Monster8XPosition = origParty.Monster8XPosition;
            newParty.Monster8YPosition = origParty.Monster8YPosition;
            newParty.Monster8Group = origParty.Monster8Group;
            newParty.Monster9 = origParty.Monster9;
            newParty.Monster9XPosition = origParty.Monster9XPosition;
            newParty.Monster9YPosition = origParty.Monster9YPosition;
            newParty.Monster9Group = origParty.Monster9Group;
            return newParty;
        }

        protected override void applyPatch(MasterBase orig, string key, string value)
        {
            MonsterParty origParty = (MonsterParty)orig;
            switch (key)
            {
                case "battle_background_asset_id":
                    origParty.BattleBackgroundAssetId = Int32.Parse(value);
                    break;
                case "battle_bgm_asset_id":
                    origParty.BattleBgmAssetId = Int32.Parse(value);
                    break;
                case "appearance_production":
                    origParty.AppearanceProduction = Int32.Parse(value);
                    break;
                case "script_name":
                    origParty.ScriptNameId = Int32.Parse(value);
                    break;
                case "battle_pattern1":
                    origParty.BattlePattern1 = Int32.Parse(value);
                    break;
                case "battle_pattern2":
                    origParty.BattlePattern2 = Int32.Parse(value);
                    break;
                case "battle_pattern3":
                    origParty.BattlePattern3 = Int32.Parse(value);
                    break;
                case "battle_pattern4":
                    origParty.BattlePattern4 = Int32.Parse(value);
                    break;
                case "battle_pattern5":
                    origParty.BattlePattern5 = Int32.Parse(value);
                    break;
                case "battle_pattern6":
                    origParty.BattlePattern6 = Int32.Parse(value);
                    break;
                case "not_escape":
                    origParty.NotEscape = Int32.Parse(value);
                    break;
                case "battle_flag_group_id":
                    origParty.BattleFlagGroupId = Int32.Parse(value);
                    break;
                case "get_value":
                    origParty.GetValue = Int32.Parse(value);
                    break;
                case "get_ap":
                    origParty.GetAp = Int32.Parse(value);
                    break;
                case "monster1":
                    origParty.Monster1 = Int32.Parse(value);
                    break;
                case "monster1_x_position":
                    origParty.Monster1XPosition = Int32.Parse(value);
                    break;
                case "monster1_y_position":
                    origParty.Monster1YPosition = Int32.Parse(value);
                    break;
                case "monster1_group":
                    origParty.Monster1Group = Int32.Parse(value);
                    break;
                case "monster2":
                    origParty.Monster2 = Int32.Parse(value);
                    break;
                case "monster2_x_position":
                    origParty.Monster2XPosition = Int32.Parse(value);
                    break;
                case "monster2_y_position":
                    origParty.Monster2YPosition = Int32.Parse(value);
                    break;
                case "monster2_group":
                    origParty.Monster2Group = Int32.Parse(value);
                    break;
                case "monster3":
                    origParty.Monster3 = Int32.Parse(value);
                    break;
                case "monster3_x_position":
                    origParty.Monster3XPosition = Int32.Parse(value);
                    break;
                case "monster3_y_position":
                    origParty.Monster3YPosition = Int32.Parse(value);
                    break;
                case "monster3_group":
                    origParty.Monster3Group = Int32.Parse(value);
                    break;
                case "monster4":
                    origParty.Monster4 = Int32.Parse(value);
                    break;
                case "monster4_x_position":
                    origParty.Monster4XPosition = Int32.Parse(value);
                    break;
                case "monster4_y_position":
                    origParty.Monster4YPosition = Int32.Parse(value);
                    break;
                case "monster4_group":
                    origParty.Monster4Group = Int32.Parse(value);
                    break;
                case "monster5":
                    origParty.Monster5 = Int32.Parse(value);
                    break;
                case "monster5_x_position":
                    origParty.Monster5XPosition = Int32.Parse(value);
                    break;
                case "monster5_y_position":
                    origParty.Monster5YPosition = Int32.Parse(value);
                    break;
                case "monster5_group":
                    origParty.Monster5Group = Int32.Parse(value);
                    break;
                case "monster6":
                    origParty.Monster6 = Int32.Parse(value);
                    break;
                case "monster6_x_position":
                    origParty.Monster6XPosition = Int32.Parse(value);
                    break;
                case "monster6_y_position":
                    origParty.Monster6YPosition = Int32.Parse(value);
                    break;
                case "monster6_group":
                    origParty.Monster6Group = Int32.Parse(value);
                    break;
                case "monster7":
                    origParty.Monster7 = Int32.Parse(value);
                    break;
                case "monster7_x_position":
                    origParty.Monster7XPosition = Int32.Parse(value);
                    break;
                case "monster7_y_position":
                    origParty.Monster7YPosition = Int32.Parse(value);
                    break;
                case "monster7_group":
                    origParty.Monster7Group = Int32.Parse(value);
                    break;
                case "monster8":
                    origParty.Monster8 = Int32.Parse(value);
                    break;
                case "monster8_x_position":
                    origParty.Monster8XPosition = Int32.Parse(value);
                    break;
                case "monster8_y_position":
                    origParty.Monster8YPosition = Int32.Parse(value);
                    break;
                case "monster8_group":
                    origParty.Monster8Group = Int32.Parse(value);
                    break;
                case "monster9":
                    origParty.Monster9 = Int32.Parse(value);
                    break;
                case "monster9_x_position":
                    origParty.Monster9XPosition = Int32.Parse(value);
                    break;
                case "monster9_y_position":
                    origParty.Monster9YPosition = Int32.Parse(value);
                    break;
                case "monster9_group":
                    origParty.Monster9Group = Int32.Parse(value);
                    break;
                default:
                    Plugin.Log.LogError($"Unknown MonsterParty property: {key} (trying to set value to {value})");
                    break;
            }
        }
    }





}
