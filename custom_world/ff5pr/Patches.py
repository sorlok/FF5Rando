# This contains a dictionary of all our patches. 
# Key is some identifier, like 'Shorter Crystal Cutscenes'
# Value is the contents of the .csv file to generate. 
# We store them this way so that it's easier to mix-and-match patches.


# The format of the .csv file is not strictly CSV (since patches have commas); rather:
# unity_asset_path,json_xpath,mnemonic_check,action,<args_for_this_action>
# <any number of lines of optional json>
# <empty line>
#
# Examples:
#   Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_e_0017,/Mnemonics/[41],MoveTo,SetIVal[2],14
#   => Retrieve mnemonic 41 in the sc_e_0017 script, confirm it's a 'MoveTo' type, then set operands.iValues[2] to 14
#
#   Assets/.../sc_e_0017,/Mnemonics/[0],Nop:Main,Overwrite,1
#   [{ ...your_mnemonics... }, ...]
#   => Retreives mnemonic 0 in the sc_e_0017 script, confirm it's a "Nop" type with a label of "Main", and overwrite
#      everything *after* this (+1) with the json object array you provide. Some checks are performed to make sure we don't
#      overwrite anything with a "Label", and we don't *remove* anything (since the script length must be kept
#      exactly the same for now).
#
#  TODO: We may eventually want Shortcut commands. For example, ["Wait", 0.25] could expand into the full "Wait" command.
#        You could always fall back to the verbose command if you want.




# Patch: "New Game", but start a new rando
new_game_open_world_csv = """
# WARNING: Manually overwrite a label; this is not listed in the "Segments" list, so I'm taking my chances...
Assets/GameAssets/Serial/Res/Map/Map_20250/Map_20250/sc_e_0001,/Mnemonics/[10],Nop,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  }
]

# Now the main patch
Assets/GameAssets/Serial/Res/Map/Map_20250/Map_20250/sc_e_0001,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "FadeOut",
    "operands": {
      "iValues": [0,0,0,255,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_WELCOME_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SysCall",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["Party Joined: Bartz","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SysCall",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["Party Joined: Lenna","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SysCall",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["Party Joined: Galuf","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SysCall",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["Party Joined: Faris","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SysCall",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["InitOpenWorldRando","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetVehicle",
    "operands": {
      "iValues": [6,1,170,144,0,3,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,1,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]
"""




# Patch: Make a shortened version of the "you got these jobs!" scene from the Wind Temple
#        +4 moves us past the 3 "Call" events that move Bartz up and split the party; we will overwrite
#        the next command (Wait) to make it shorter.
shorter_crystal_cutscenes_csv = """
# Patch: Shorter Crystal Cutscenes
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_e_0017,/Mnemonics/[0],Nop:Main,Overwrite,4
[
  {
    "label": "",
    "mnemonic": "Wait",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_WIND_CRYSTAL_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_WIND_CRYSTAL_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Wait",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "WindCrystalShard1",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "WindCrystalShard2",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "WindCrystalShard3",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "WindCrystalShard4",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "WindCrystalShard5",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "WindCrystalShard6",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [16,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,5,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]
"""


prepare_npc_and_boss_event_checks = """
# Patch: Prepare NPC and Boss Event Checks

# The NPC from the Pirate's Hideout that gives you items
Assets/GameAssets/Serial/Res/Map/Map_30021/Map_30021_4/sc_npc_30021_4_1,/Mnemonics/[0],Nop:Main,Overwrite,4
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_PIRATE_POTION_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Same Pirate NPC; give the player the item in question
Assets/GameAssets/Serial/Res/Map/Map_30021/Map_30021_4/sc_npc_30021_4_1,/Mnemonics/[0],Nop:Main,Overwrite,6
[
  {
    "label": "PiratePotions",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  }
]

# The NPC from the Wind Shrine that gives you items
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_1/sc_npc_30041_1_1,/Mnemonics/[0],Nop:Main,Overwrite,4
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_WIND_SHRINE_POTION_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Same Wind Shrine NPC; give the player the item in question
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_1/sc_npc_30041_1_1,/Mnemonics/[0],Nop:Main,Overwrite,5
[
  {
    "label": "WindShrinePotions",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  }
]

# Boss: Magissa and Forza
Assets/GameAssets/Serial/Res/Map/Map_30100/Map_30100/sc_e_0033,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0033_00_232_a_01","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [443,21,12,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0033_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Boss: Magissa and Forza reward:
Assets/GameAssets/Serial/Res/Map/Map_30100/Map_30100/sc_e_0033_1,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "FadeIn",
    "operands": {
      "iValues": [0,0,0,255,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Wait",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_MAGISSA_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossMagissaItem",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "GetItem",
    "operands": {
      "iValues": [206,1,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [32,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_MAGISSA_POST_FIGHT_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,33,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Boss: Siren
Assets/GameAssets/Serial/Res/Map/Map_30060/Map_30060/sc_e_0030,/Mnemonics/[0],Nop:Main,Overwrite,9
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0030_00_211_a_01","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [442,47,19,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0030_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Boss: Siren reward:
Assets/GameAssets/Serial/Res/Map/Map_30060/Map_30060/sc_e_0030_1,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "FadeIn",
    "operands": {
      "iValues": [0,0,0,255,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Wait",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0.25,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_SIREN_TEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossSirenItem",
    "mnemonic": "Nop",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ColorFade",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [29,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Exit",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]
"""
          







# Put 'em all together
all_patch_contents = {
  'New Game Open World' : new_game_open_world_csv,
  'Shorter Crystal Cutscenes' : shorter_crystal_cutscenes_csv,
  'Prepare NPC and Boss Event Checks' : prepare_npc_and_boss_event_checks,
}


