#!/usr/bin/env python3


import os
import os.path
import json

from helpers import StringsAsset, CsvAsset


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



# Our results class
class TreasureEntry:
  def __init__(self):
    # These are all pulled from the map files directly
    self.gid = None    # Not necessary, but I'm curious
    self.content_id = None
    self.content_num = None
    self.message_key = None
    self.script_id = None

    # These are part of the scanning process
    # Consider a path within <MagiciteExport> of "map_40022/Assets/GameAssets/Serial/Res/Map/Map_40022/Map_40022_1", then:
    self.asset_name = None   # Part of map.csv, but mostly used to find the file in question; e.g., map_40022 (can capitalize to Map_40022)
    self.map_name = None     # For looking up in our DB; e.g., "Map_40022_1"
    self.asset_path = None   # Uses our custom XPath-like lookup; e.g., /layers/[0]/objects/[5]

    # These need to be correlated with various external .csvs
    self.content_name_str = None  # Item/Weapon/Armor name, or 'gil'; interpolated from content.csv
    self.area_name_str = None  # E.g., "Tule"; from our strings
    self.map_name_str = None  # E.g., "Item Shop"; from our strings
    self.title_override = None # E.g., "Greenhorn Guild" -- used in specific caes

  # Helper: Visualize
  def __repr__(self):
    return f"TreasureEntry({self.asset_name}:{self.map_name}:{self.asset_path}) = ({self.gid},{self.content_id},{self.content_num},{self.message_key},{self.script_id}) ; [{self.content_name_str},{self.area_name_str},{self.map_name_str},{self.title_override}]"



def scan_indiv_map_for_treasure(imap_dir, res):
  global systemStrs
  global title_overrides_per_map

  json_path = f"{imap_dir}/entity_default.json"
  if not os.path.exists(json_path):
    #print('   ', "WARNING: skipping!")   # This is fine
    return

  with open(json_path, encoding='utf-8') as f:
    root = json.load(f)
    path_parts = imap_dir.replace(f"{GamePath}/{DataExportPath}/", '').split('/')  # Used later for asset_name/map_name

    # Scan through each layer
    title_id_override = None
    layerId = -1
    for layer in root['layers']:
      layerId += 1
      objId = -1
      for obj in layer['objects']:
        objId += 1
        entry = TreasureEntry()
        entry.asset_name = path_parts[0]
        entry.map_name = path_parts[-1]
        entry.asset_path = f"/layers/{layerId}/objects/{objId}"
        # Retrieve the properties we care about
        entry.gid = obj.get('gid')
        for prop in obj.get('properties', []):
          name = prop.get('name')
          val = prop.get('value')
          if name == 'content_id':
            entry.content_id = val
          elif name == 'content_num':
            entry.content_num = val
          elif name == 'message_key':
            entry.message_key = val
          elif name == 'script_id':
            entry.script_id = val

          # Title ID is a little special
          elif name == 'title_id':
            if prop.get('value','') != '':
              if title_id_override is None or title_id_override == val:
                title_id_override = val
              elif systemStrs.get_string(title_id_override) == systemStrs.get_string(val):
                pass
              else:
                raise Exception(f"Title ID conflict: {title_id_override} vs: {val} => ({systemStrs.get_string(title_id_override)}) vs: ({systemStrs.get_string(value)})")
                #
                # TODO: These may have the same actual string, like MSG_ARA_NAME_80 and MSG_ARA_NAME_83
                #       We also don't care *that* much; these might just be some kind of NPC switch, and we're
                #       only using these names to inform our searches.
                #

        # Save it
        if entry.content_id:
          res.append(entry)
    if title_id_override != None:
      title_overrides_per_map[path_parts[-1]] = title_id_override




def scan_for_treasure(map_dir, res):
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
        scan_indiv_map_for_treasure(abs_path, res)



# Set additional (treasure) properties that are only available in .csv files
def update_metadata(entry):
  global systemStrs
  global areaCsv
  global mapCsv
  global contentCsv
  global title_overrides_per_map

  # This is tracked in our lookup
  title_str = title_overrides_per_map.get(entry.map_name)
  if title_str:
    if title_str in ['MSG_ARA_NAME_113']:
      entry.title_override = "<Error_Missing>"   # Not sure why this one's not there...
    elif title_str.startswith('MSG_'):
      entry.title_override = systemStrs.get_string(title_str)

  # This one needs to come from content.csv
  row = contentCsv.get_prop(entry.content_id)
  name_str = row.get('mes_id_name')
  entry.content_name_str = systemStrs.get_string(name_str)

  # To pull data from the maps, first match on map_name
  rows = mapCsv.search_for_prop('map_name', entry.map_name)
  if len(rows) != 1:
    raise Exception(f"Can't find expected map ({map_name}); instead, found: {rows}")
  row = rows[0]

  # The map_title becomes the map_name_str
  map_title = row['map_title']
  if map_title != 'None':
    entry.map_name_str = systemStrs.get_string(map_title)

  # Now, pull out the area ID, and grab the relevant column
  area_id = int(row['area_id'])
  row = areaCsv.get_prop(area_id)
  area_name = row['area_name']
  if area_name != 'None':
    entry.area_name_str = systemStrs.get_string(area_name)





# Helper: Track title overrides (these appear in events for specific maps)
title_overrides_per_map = {}   # E.g., Map_2011_1 => 'My Map'

# Read our various assets
systemStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['system']}")
storyMsgStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['story_mes']}")
#
contentCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/content.csv")
mapCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/map.csv")
areaCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/area.csv")

# Make a list of 'map' directories (map_1234); includes some weird ones like (map_1234_nigheffect) that we may need to hope don't have items
map_dirs = get_map_dirs(f"{GamePath}/{DataExportPath}")

# Within Assets/GameAssets/Serial/Res/Map/Map<XYZ>, we have a list of directories (at least 1) that contain "entity_default.json"
# These contain a list of Treasures that we care about
treasures = []   # TreasureEntry
for map_dir in map_dirs:
  # Scan it!
  print(f"Scanning: {map_dir}")
  scan_for_treasure(map_dir, treasures)

# Fill in any missing information
for entry in treasures:
  update_metadata(entry)

# Print (debug)
#for entry in treasures:
#  print(entry)

# Save treasure to a .csv file
out_path = 'my_treasures.csv'
with open(out_path, 'w', encoding='utf-8') as out:
  out.write("path_ident,map_area_name,map_override_name,content_name_str,content_id,content_num,script_id,message_key,gid\n")

  for entry in treasures:
    path_ident = f"{entry.asset_name}:{entry.map_name}:{entry.asset_path}"
    map_area_name = entry.area_name_str
    if entry.map_name_str != None:
      map_area_name += f" - {entry.map_name_str}"
    out.write(f"{path_ident},{map_area_name},{entry.title_override},{entry.content_name_str},{entry.content_id},{entry.content_num},{entry.script_id},{entry.message_key},{entry.gid}\n")


print(f"Done, saved to: {out_path}")
