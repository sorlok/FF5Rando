#!/usr/bin/env python3


import os
import os.path
import json

from helpers import StringsAsset


# This can be in different places
GamePath = '/mnt/d/Programs/Steam/steamapps/common/FINAL FANTASY V PR'
DataExportPath = 'FINAL FANTASY V_Data/StreamingAssets/MagiciteExport'
MasterPath = 'master/Assets/GameAssets/Serial/Data/Master'
MessagePath = 'message/Assets/GameAssets/Serial/Data/Message'


# Some known assets. These will be at <GamePath>/<DataExportPath>/<MasterPath>/<filename.csv>
ResourceFiles = {
  'ability.csv',
  'area.csv',
  'armor.csv',
  'character_default_name.csv',
  'condition.csv',
  'condition_group.csv',
  'item.csv',
  'job.csv',
  'game_constant_int.csv',
  'map.csv',
  'map_script.csv',
  'command.csv',
  'content.csv',
  'product.csv',
  'product_group.csv',
  'monster.csv',
  'monster_party.csv',
  'weapon.csv',
}


# Known 'strings', English version. These will be at <GamePath>/<DataExportPath>/<MessagePath>/<filename.txt>
StringFiles = {
  'system' : 'system_en.txt',
  'story_cha' : 'story_cha_en.txt',
  'story_mes' : 'story_mes_en.txt',
}


#
# TODO: It will eventually make sense to pull from package_info, keys, etc., rather than just guessing the file structure
#




def get_map_dirs(export_path):
  res = []
  for fname in os.listdir(export_path):
    abs_path = f"{export_path}/{fname}"
    if fname.startswith('map_') and os.path.isdir(abs_path):
      if len(fname) > 4 and fname[4] in '1234567890':  # Exceptions: map_script, map_ui, map_world, etc.
        res.append(abs_path)
  return res



def scan_indiv_map_for_treasure(imap_dir):
  json_path = f"{imap_dir}/entity_default.json"
  if not os.path.exists(json_path):
    print('   ', "WARNING: skipping!")
    return

  with open(json_path, encoding='utf-8') as f:
    root = json.load(f)

    # Scan through each layer
    title_id_override = None
    for layer in root['layers']:
      for obj in layer['objects']:
        # Retrieve the properties we care about
        gid = obj.get('gid')
        props = {
          'content_id' : None,
          'content_num' : None,
          'message_key' : None,
          'script_id' : None,   # Often used to start a battle
        }
        for prop in obj.get('properties', []):
          name = prop.get('name')
          if name in props:
            props[name] = prop.get('value')


          # Title ID is a little special
          if name == 'title_id' and prop.get('value','') != '':
            value = prop.get('value')
            if title_id_override is None or title_id_override == value:
              title_id_override = value
            else:
              print(f"Title ID conflict: {title_id_override} vs: {value}")
              #
              # TODO: These may have the same actual string, like MSG_ARA_NAME_80 and MSG_ARA_NAME_83
              #       We also don't care *that* much; these might just be some kind of NPC switch, and we're
              #       only using these names to inform our searches.
              #

        # Print it
        if props['content_id']:
          print('   ',f"{gid} , {props['content_id']} , {props['content_num']} , {props['message_key']} , {props['script_id']}")
    if title_id_override != None:
      print('   ', f"===> Title ID Override: {title_id_override}")





def scan_for_treasure(map_dir):
  temp_path = f"{map_dir}/Assets/GameAssets/Serial/Res/Map"
  subdirs = os.listdir(temp_path)
  
  if len(subdirs) != 1:
    raise Exception(f"Bad map; expected 1 subdir: {temp_path} => {subdirs}")
  
  # Scan individual map folders
  temp_path = f"{temp_path}/{subdirs[0]}"
  for fname in os.listdir(temp_path):
    abs_path = f"{temp_path}/{fname}"
    if fname.startswith('Map_') and os.path.isdir(abs_path):
      if len(fname) > 4 and fname[4] in '1234567890':
        print(' ',fname)
        scan_indiv_map_for_treasure(abs_path)






# Read our various assets
systemStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['system']}")
storyMsgStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['story_mes']}")

# Make a list of 'map' directories (map_1234); includes some weird ones like (map_1234_nigheffect) that we may need to hope don't have items
map_dirs = get_map_dirs(f"{GamePath}/{DataExportPath}")

# Within Assets/GameAssets/Serial/Res/Map/Map<XYZ>, we have a list of directories (at least 1) that contain "entity_default.json"
# These contain a list of Treasures that we care about
for map_dir in map_dirs:
  # Scan it!
  print(map_dir)
  scan_for_treasure(map_dir)


















print("Done")
