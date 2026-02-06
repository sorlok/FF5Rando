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

# Wind Crystal -- Note: We use "
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
      "iValues": [14,0,0,0,0,0,0,0],
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


# Modify the Wind Crystal cutscene to check Flag 14 instead of Flag 16
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_8/sc_map_30041_8,/Mnemonics/[1],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [14,1,4,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# Modify the "NPCs talked to you when you entered the Wind Shrine" script to check for Flag 19 (always on) instead of Flag 14
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_1/sc_map_30041_1,/Mnemonics/[7],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [19,1,9,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# ...and to change the "NPCs have left the Wind Shrine forever" flag from 16 to 38 (always off)
Assets/GameAssets/Serial/Res/Map/Map_30041/Map_30041_1/sc_map_30041_1,/Mnemonics/[6],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [38,1,12,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]



# Start the fight with Garula early
Assets/GameAssets/Serial/Res/Map/Map_30121/Map_30121_10/sc_e_0039,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0039_00_234_a_02","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [444,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0039_1","","","","","","",""]
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

# After the Garula fight, grab the crystals without sinking the Tower
# NOTE: We also "collect" the lower-left and lower-right crystal shards so that the player doesn't see them and get confused.
Assets/GameAssets/Serial/Res/Map/Map_30121/Map_30121_10/sc_e_0039_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_WATER_CRYSTAL_MSG_1","","","","","","",""]
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
      "sValues": ["RANDO_WATER_CRYSTAL_MSG_2","","","","","","",""]
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
    "label": "WaterCrystalShard1",
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
    "label": "WaterCrystalShard2",
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
    "label": "WaterCrystalShard3",
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
    "label": "WaterCrystalShard4",
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
    "label": "WaterCrystalShard5",
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
      "iValues": [39,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [167,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [170,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,11,0,0,0,0,0,0],
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

# Patch: Use Flag 39 instead of 38 to detect that the Water Crystal has shattered.
# Block the door with the guard NPC
# TODO: Is the underwater Walse Tower a different map? If not, this might be a problem...
Assets/GameAssets/Serial/Res/Map/Map_30121/Map_30121_10/sc_map_30121_10,/Mnemonics/[7],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [39,1,11,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# We need to patch the "Walse meteorite entrance is open" flag, or else the Adamantite can't be placed
Assets/GameAssets/Serial/Res/Map/Map_30130/Map_30130/sc_map_30130,/Mnemonics/[2],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [19,1,6,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# ...and patch the King's cutscene to use Flag 19 so that we don't lock ourselves out of a check by mistake.
# (actually, the King won't be in bed unless flag 38 is set, but let's be extra safe just in case...)
Assets/GameAssets/Serial/Res/Map/Map_20041/Map_20041_3/sc_e_0040,/Mnemonics/[2],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [19,1,19,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# Patch the Liquid Flame fight to give you the crystals after.
Assets/GameAssets/Serial/Res/Map/Map_30151/Map_30151_21/sc_e_0046,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0046_00_271_a_03","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [445,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0046_1","","","","","","",""]
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

# ...now give them the stuff
Assets/GameAssets/Serial/Res/Map/Map_30151/Map_30151_21/sc_e_0046_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_FIRE_CRYSTAL_MSG_1","","","","","","",""]
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
      "sValues": ["RANDO_FIRE_CRYSTAL_MSG_2","","","","","","",""]
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
    "label": "FireCrystalShard1",
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
    "label": "FireCrystalShard2",
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
    "label": "FireCrystalShard3",
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
      "iValues": [45,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [46,0,0,0,0,0,0,0],
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
      "iValues": [1,36,0,0,0,0,0,0],
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


# Force Queen Karnak to block the door to the crystal room after the cutscene (it's harmless, but the room looks weird)
Assets/GameAssets/Serial/Res/Map/Map_30151/Map_30151_21/sc_map_30151_21,/Mnemonics/[56],SetPos,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "SetPos",
    "operands": {
      "iValues": [15,14,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  }
]


# Force the "Bookcase moves to block you" event to do nothing (this is in addition to the Flag)
Assets/GameAssets/Serial/Res/Map/Map_20221/Map_20221_7/sc_e_0222,/Mnemonics/[1],Call,Overwrite,0
[
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


# Avoid an earth-shattering Kaboom when you leave Karnak Castle
# NOTE: We remove the sc_e_0048_2 trigger on ChangeMap
# NOTE: Keeping flag 47 unset means Queen Karnak stays inside the Flame-Powered ship... which is good!
Assets/GameAssets/Serial/Res/Map/Map_20070/Map_20070/sc_e_0048_1,/Mnemonics/[3],ChangeMap,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,36,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Get the 2 Crystal Shards from the Black Chocobo
# Note: Amazingly, they *remove* Lenna/Faris/Galuf from your party for this part! We'll skip all that...
Assets/GameAssets/Serial/Res/Map/Map_20110/Map_20110/sc_e_0056,/Mnemonics/[0],Nop:Main,Overwrite,2
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0056_00_129_a_02","","","","","","",""]
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
      "sValues": ["RANDO_BLACK_CHOCOBO_CRYSTAL_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BlackChocoboShard1",
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
    "label": "BlackChocoboShard2",
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
      "iValues": [108,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [159,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
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
      "sValues": ["RANDO_BLACK_CHOCOBO_CRYSTAL_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,31,0,0,0,0,0,0],
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


# Don't let them ride the Black Chocobo twice
Assets/GameAssets/Serial/Res/Map/Map_20110/Map_20110/sc_e_0200,/Mnemonics/[1],PlayBGM,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0371_00_189_a_01","","","","","","",""]
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


# Fight Archeoavis...
Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/sc_e_0074,/Mnemonics/[0],Nop:Main,Overwrite,2
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0074_00_305_a_09","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [453,23,22,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0074_1","","","","","","",""]
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


# WARNING: Manually overwrite a label; this is not listed in the "Segments" list, so I'm taking my chances...
Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/sc_e_0074_1,/Mnemonics/[3],Nop,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Nop:先頭がレナ",
    "operands": {
      "iValues": [0,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 2,
    "comment": ""
  }
]


# ...and get the Earth crystals
# NOTE: We re-use World Map Script sc_e_0071_4 here (the one that plays when we get the high-altitude ship
#       from the Catapult for the first time), since we need to warp back to "flying the airship", and I
#       don't want to (a) have the Ronka Ruins crash, or (b) write a base64-encoding-patcher. This is
#       *probably* safe (the flag it sets (70) is already set when we upgrade the airship).
Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/sc_e_0074_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_EARTH_CRYSTAL_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "EarthCrystalShard1",
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
    "label": "EarthCrystalShard2",
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
    "label": "EarthCrystalShard3",
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
    "label": "EarthCrystalShard4",
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
      "iValues": [73,0,0,0,0,0,0,0],
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
      "sValues": ["RANDO_EARTH_CRYSTAL_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "FadeOut",
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
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,29,0,1,1,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0071_4","","","","","","",""]
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


# Don't let them go into the Earth Crystal room
# TODO: There is 1 tile above this event that you can walk onto. I think we can just block this, but it requires editing the collision map.
Assets/GameAssets/Serial/Res/Map/Map_30191/Map_30191_12/sc_e_0075_13,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_EARTH_CRYSTAL_MSG_3","","","","","","",""]
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

# The Chancellor in Tycoon Castle (W1) that gives you items
Assets/GameAssets/Serial/Res/Map/Map_20051/Map_20051_5/sc_npc_20051_5_1,/Mnemonics/[0],Nop:Main,Overwrite,6
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_CHANCELLOR_HEAL_STAFF_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# Same Chancellor; give the player the item in question
Assets/GameAssets/Serial/Res/Map/Map_20051/Map_20051_5/sc_npc_20051_5_1,/Mnemonics/[0],Nop:Main,Overwrite,10
[
  {
    "label": "ChancellorHealStaff",
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
      "sValues": ["RANDO_BOSS_SIREN_ITEM_MSG_1","","","","","","",""]
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

# Boss: Shiva - Note that the "EncountBoss" doesn't need to be patched because Shiva's just that swell!
#               We also need to convert "MsgFunFare" into "Message" to be faster
Assets/GameAssets/Serial/Res/Map/Map_20041/Map_20041_15/sc_e_0183_1,/Mnemonics/[0],Nop:Main,Overwrite,5
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0183_00_066_a_02","","","","","","",""]
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
      "sValues": ["RANDO_BOSS_SIREN_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]

# ...and the message steals a 'Restart BGM' command
Assets/GameAssets/Serial/Res/Map/Map_20041/Map_20041_15/sc_e_0183_1,/Mnemonics/[0],Nop:Main,Overwrite,8
[
  {
    "label": "BossShivaItem",
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

# ...for this to work we need to stop the fanfare and skip the 'Stop BGM'
Assets/GameAssets/Serial/Res/Map/Map_20041/Map_20041_15/sc_e_0183_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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


# Boss: Ifrit
Assets/GameAssets/Serial/Res/Map/Map_20221/Map_20221_8/sc_e_0049,/Mnemonics/[0],Nop:Main,Overwrite,3
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
      "sValues": ["E0049_00_275_a_04","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [495,5,6,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0049_1","","","","","","",""]
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

# After the Ifrit fight, get his item.
Assets/GameAssets/Serial/Res/Map/Map_20221/Map_20221_8/sc_e_0049_1,/Mnemonics/[10],GetItem,Overwrite,0
[
  {
    "label": "BossIfritItem",
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
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0049_00_275_a_07","","","","","","",""]
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
      "sValues": ["RANDO_BOSS_IFRIT_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [48,0,0,0,0,0,0,0],
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

# Boss Fight: Byblos
Assets/GameAssets/Serial/Res/Map/Map_20221/Map_20221_12/sc_e_0050,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0050_00_283_a_03","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Encount",
    "operands": {
      "iValues": [447,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0050_1","","","","","","",""]
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

# After Byblos fight, Get Item
Assets/GameAssets/Serial/Res/Map/Map_20221/Map_20221_12/sc_e_0050_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
    "label": "BossByblosItem",
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
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_BYBLOS_ITEM_MSG_1","","","","","","",""]
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
      "sValues": ["RANDO_BOSS_BYBLOS_ITEM_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [49,0,0,0,0,0,0,0],
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
      "iValues": [273,1,0,0,0,0,0,0],
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

# Sandworm: Skip to the boss faster
Assets/GameAssets/Serial/Res/Map/Map_30170/Map_30170/sc_e_0060,/Mnemonics/[10],Msg,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [448,53,13,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0060_1","","","","","","",""]
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


# Sandworm: Give the reward
Assets/GameAssets/Serial/Res/Map/Map_30170/Map_30170/sc_e_0060_1,/Mnemonics/[5],Msg,Overwrite,0
[
  {
    "label": "BossSandwormItem",
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
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_SANDWORM_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [59,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [31,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
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
      "sValues": ["RANDO_BOSS_SANDWORM_ITEM_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,14,0,0,0,0,0,0],
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


# Sandworm: Don't erase the trigger when Cid+Mid return the Black Chocobo
Assets/GameAssets/Serial/Res/Map/Map_30170/Map_30170/sc_map_30170,/Mnemonics/[3],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [38,1,13,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# Adamantite boss (fight when you pick it up)
Assets/GameAssets/Serial/Res/Map/Map_30011/Map_30011_1/sc_e_0070,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0427_00_190_a_01","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [449,11,10,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0427_1","","","","","","",""]
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


# Adamantite boss, after the fight, get the Item
# NOTE: We keep flag 69 as "got Adamantite", but re-purpose flag 61 as "defated Adamantoise"
#       Flag 61 used to refer to the cutscene once dropping down the pit in Gohn, so it's naturally impossible to reach now.
Assets/GameAssets/Serial/Res/Map/Map_30011/Map_30011_1/sc_e_0427_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_BOSS_ADAMANTOISE_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossAdamantoiseItem",
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
      "iValues": [61,0,0,0,0,0,0,0],
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
      "sValues": ["RANDO_BOSS_ADAMANTOISE_ITEM_MSG_2","","","","","","",""]
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


# Load Adamantoise fight via flag 61 instead of flag 69
Assets/GameAssets/Serial/Res/Map/Map_30011/Map_30011_1/sc_map_30011_1,/Mnemonics/[2],Branch,Overwrite,0
[
  {
    "label": "",
    "mnemonic": "Branch",
    "operands": {
      "iValues": [61,1,5,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","＝","imm","","","","",""]
    },
    "type": 1,
    "comment": ""
  }
]


# Upgrade the airship faster:
Assets/GameAssets/Serial/Res/Map/Map_20231/Map_20231_7/sc_e_0071,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0071_00_296_a_01","","","","","","",""]
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
      "sValues": ["E0071_00_296_a_03","","","","","","",""]
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
      "sValues": ["E0071_00_296_a_04","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [70,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "FadeOut",
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
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,29,0,1,1,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0071_4","","","","","","",""]
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


# Purobolos fight, shortened
Assets/GameAssets/Serial/Res/Map/Map_30130/Map_30130/sc_e_0079,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0079_00_244_a_05","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "Encount",
    "operands": {
      "iValues": [456,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0079_1","","","","","","",""]
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


# ...and, get the items
Assets/GameAssets/Serial/Res/Map/Map_30130/Map_30130/sc_e_0079_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_BOSS_PUROBOLOS_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossPurobolosItem",
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
      "iValues": [78,0,0,0,0,0,0,0],
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
      "sValues": ["E0079_00_244_a_04","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,12,0,0,0,0,0,0],
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


# Karnak meteor fight
# Note: The interior is actually a different map than the 'Teleport' meteor map
Assets/GameAssets/Serial/Res/Map/Map_30141/Map_30141_2/sc_e_0081,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0080_00_248_a_03","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [455,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0081_1","","","","","","",""]
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


# And get the item!
Assets/GameAssets/Serial/Res/Map/Map_30141/Map_30141_2/sc_e_0081_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_BOSS_TITAN_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "GetItem",
    "operands": {
      "iValues": [434,1,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossTitanItem",
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
      "iValues": [80,0,0,0,0,0,0,0],
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
      "sValues": ["RANDO_BOSS_TITAN_ITEM_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,9,0,0,0,0,0,0],
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


# Gohn meteorite boss
Assets/GameAssets/Serial/Res/Map/Map_30201/Map_30201_2/sc_e_0083,/Mnemonics/[0],Nop:Main,Overwrite,1
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0083_00_309_a_02","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "EncountBoss",
    "operands": {
      "iValues": [454,15,11,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["sc_e_0083_1","","","","","","",""]
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


# Gohn meteorite boss, get reward
Assets/GameAssets/Serial/Res/Map/Map_30201/Map_30201_2/sc_e_0083_1,/Mnemonics/[0],Nop:Main,Overwrite,1
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
      "sValues": ["RANDO_BOSS_MANTICORE_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossManticoreItem",
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
      "iValues": [82,0,0,0,0,0,0,0],
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
      "sValues": ["RANDO_BOSS_MANTICORE_ITEM_MSG_2","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "",
    "mnemonic": "ChangeMap",
    "operands": {
      "iValues": [1,24,0,0,0,0,0,0],
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


# Jachol Cave check (misc, NPC-like)
Assets/GameAssets/Serial/Res/Map/Map_30161/Map_30161_2/sc_e_0362,/Mnemonics/[0],Nop:Main,Overwrite,5
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_JACHOL_CAVE_SPECIAL_CHEST_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "JacholCaveSpecialChestItem",
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
      "iValues": [179,0,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["ScenarioFlag2","","","","","","",""]
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


# Don't let them rescue Lone Wolf, or else some checks go away
Assets/GameAssets/Serial/Res/Map/Map_20041/Map_20041_9/sc_e_0428,/Mnemonics/[0],Nop:Main,Overwrite,3
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_NO_LONE_WOLF_MSG","","","","","","",""]
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


# Set up a reward for Sol Cannon, but don't disturb that scene too much
Assets/GameAssets/Serial/Res/Map/Map_20260/Map_20260/sc_e_0073_2,/Mnemonics/[0],Nop:Main,Overwrite,4
[
  {
    "label": "",
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["RANDO_BOSS_SOL_CANNON_ITEM_MSG_1","","","","","","",""]
    },
    "type": 1,
    "comment": ""
  },
  {
    "label": "BossSolCannonItem",
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
    "mnemonic": "Msg",
    "operands": {
      "iValues": [0,2,0,0,0,0,0,0],
      "rValues": [0,0,0,0,0,0,0,0],
      "sValues": ["E0073_00_299_a_05","","","","","","",""]
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


