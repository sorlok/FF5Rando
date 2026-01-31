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




# Patch 1: Make a shortened version of the "you got these jobs!" scene from the Wind Temple
#          +4 moves us past the 3 "Call" events that move Bartz up and split the party; we will overwrite
#          the next command (Wait) to make it shorter.
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
    "mnemonic": "SetFlag",
    "operands": {
      "iValues": [197,0,0,0,0,0,0,0],
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

# The NPC from the Pirate's Hideout (TODO: what is map Map_20181_3?) that gives you items
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
"""







# Put 'em all together
all_patch_contents = {
  'Shorter Crystal Cutscenes' : shorter_crystal_cutscenes_csv,
  'Prepare NPC and Boss Event Checks' : prepare_npc_and_boss_event_checks,
}


