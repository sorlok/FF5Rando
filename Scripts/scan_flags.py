#!/usr/bin/env python3


import os
import os.path
import json

from helpers import StringsAsset, CsvAsset


#
# This script makes a table of where each ScenarioFlag is used/set, so that we don't step on our own toes.
#


# TODO: The command 'ResetFlag' will set a flag to 0, but I don't have the energy to re-scan these.
# TODO: Some flags are set via "global" scripts, that are chained to on ChangeMap(). For example, "sc_e_0480_2" is 
#       chained to by "Map_40002/sc_e_0480_1" in its ChangeMap command, and it (I think) sets ScenarioFlag1:6
#       These appear to be "inline" assets, which are base-64 encoded into the World Map via "Map_10010/package.json"
#       I don't scan these yet, but they probably have some good stuff.


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



# Our flags are, e.g., "ScenarioFlag1(80)" -- this is setting Flag 80 within ScenarioFlag1, NOT setting it TO 80
class Flag:
  def __init__(self, name, flagId):
    self.name = name
    self.flagId = flagId

  def __repr__(self):
    return f"Flag({self.name},{self.flagId})"

  def __hash__(self):
    return hash((self.name, self.flagId))

  def __eq__(self, other):
    if isinstance(other, Flag):
      return (self.name, self.flagId) == (other.name, other.flagId)
    return NotImplemented  # I guess?

  def __lt__(self, other):
    if isinstance(other, Flag):
      return (self.name, self.flagId) < (other.name, other.flagId)
    return NotImplemented  # I guess?


# Each flag stores where it's set vs. used
class FlagEntry:
  def __init__(self):
    self.mapsWhereSet = {}   # AssetPath; e.g., Assets/GameAssets/Serial/Res/Map/Map_30021/Map_30021_4/sc_map_30021_4 =>
    self.mapsWhereUsed = {}  #   ... value is [map_area_name, map_override_name]

  def __repr__(self):
    return f"FlagEntry(TODO)"



def scan_indiv_map_for_flags(imap_dir, res):
  global systemStrs
  global title_overrides_per_map

  # Find every json file in this directory
  json_paths = []
  for fname in os.listdir(imap_dir):
    abs_path = f"{imap_dir}/{fname}"
    if fname.endswith('.json'):
      json_paths.append(abs_path)

  # Scan every json file
  for json_path in json_paths:
    with open(json_path, encoding='utf-8') as f:
      root = json.load(f)
      asset_path = json_path.replace(f"{GamePath}/{DataExportPath}/", '').split('/', 1)[1]   # Remove 'map_xyz'; it's not part of the Asset path
      if asset_path.endswith('.json'):  # Neither is the extension, annoyingly enough
        asset_path = asset_path[:-5]

      # Extract the specific map name
      mapName = asset_path.split('/')[-2]

      # entity_default is only needed for map name overrides
      if asset_path.endswith('entity_default'):
        title_id_override = None
        for layer in root['layers']:
          for obj in layer['objects']:
            for prop in obj.get('properties', []):
              name = prop.get('name')
              val = prop.get('value')
              if name == 'title_id':
                if prop.get('value','') != '':
                  if title_id_override is None or title_id_override == val:
                    title_id_override = val
                  elif systemStrs.get_string(title_id_override) == systemStrs.get_string(val):
                    pass
                  else:
                    raise Exception(f"Title ID conflict: {title_id_override} vs: {val} => ({systemStrs.get_string(title_id_override)}) vs: ({systemStrs.get_string(value)})")
        if title_id_override != None:
          title_overrides_per_map[mapName] = title_id_override

      # Look for mnemonics; this is how we expect to see events.
      if 'Mnemonics' not in root:
        continue

      # Iterate over Mnemonics and look for flags (both setting and using)
      # Add Mnemonics here as you find ones that are flag-relevant.
      for mn in root['Mnemonics']:
        # SetFlag, obviously, sets a flag
        if mn['mnemonic'] == 'SetFlag':
          flagName = mn['operands']['sValues'][0]
          flagId = mn['operands']['iValues'][0]

          # Brief sanity check: do these values ever show up anywhere else? Can you set a bunch at once?
          for i in range(1, len(mn['operands']['sValues'])):
            if 'Flag' in mn['operands']['sValues'][i]:
              raise Exception(f"Error: Assumptions invalidated re: SetFlag Mnemonics: {mn}")

          # Save it
          entry = res.setdefault(Flag(flagName, flagId), FlagEntry())
          entry.mapsWhereSet.setdefault(asset_path, mapName)

        # Branch can reat to flags; there's a few ways to do this, but we scan sVals and pair them with iVals 
        elif mn['mnemonic'] == 'Branch':
          for i in range(len(mn['operands']['sValues'])):
            if 'Flag' in mn['operands']['sValues'][i]:  # TODO: We may have to hand-hold this...
              flagName = mn['operands']['sValues'][i]
              flagId = mn['operands']['iValues'][i]

              # Save it
              entry = res.setdefault(Flag(flagName, flagId), FlagEntry())
              entry.mapsWhereUsed.setdefault(asset_path, mapName)



def scan_for_flags(map_dir, res):
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
        scan_indiv_map_for_flags(abs_path, res)



def print_row(flag, asset, map_name, setUseStr):
  global systemStrs
  global areaCsv
  global mapCsv
  global title_overrides_per_map

  # To pull data from the maps, first match on map_name
  rows = mapCsv.search_for_prop('map_name', map_name)
  if len(rows) != 1:
    raise Exception(f"Can't find expected map ({map_name}); instead, found: {rows}")
  row = rows[0]

  # The map_title becomes the map_name_str
  map_name_str = None
  map_title = row['map_title']
  if map_title != 'None':
    map_name_str = systemStrs.get_string(map_title)

  # Now, pull out the area ID, and grab the relevant column
  area_name_str = ''
  area_id = int(row['area_id'])
  row = areaCsv.get_prop(area_id)
  area_name = row['area_name']
  if area_name != 'None':
    area_name_str = systemStrs.get_string(area_name)

  map_area_name = area_name_str
  if map_name_str != None:
    map_area_name += f" - {map_name_str}"

  title_override = title_overrides_per_map.get(map_name, '')
  if title_override != '':
    if title_override in ['Map_30061_2', 'MSG_ARA_NAME_113']:
      title_override = "<Error_Missing>"   # Not sure why this one's not there...
    else:
      title_override = systemStrs.get_string(title_override)

  out.write(f"{flag.name},{flag.flagId},{map_name},{map_area_name},{title_override},{setUseStr},{asset}\n")




# Helper: Track title overrides (these appear in events for specific maps)
title_overrides_per_map = {}   # E.g., Map_2011_1 => 'My Map'

# Read our various assets
systemStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['system']}")
#storyMsgStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['story_mes']}")
#
#contentCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/content.csv")
mapCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/map.csv")
areaCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/area.csv")

# Make a list of 'map' directories (map_1234); includes some weird ones like (map_1234_nigheffect) that probably set flags (they're usually cutscenes)
map_dirs = get_map_dirs(f"{GamePath}/{DataExportPath}")

# Within Assets/GameAssets/Serial/Res/Map/Map<XYZ>, scan every possible json file and look for 'Mnemonics'.
# We expect only the 'sc_' ones to be relevant, but let's be cautious
flags = {}   # Flag -> FlagEntry
for map_dir in map_dirs:
  # Scan it!
  print(f"Scanning: {map_dir}")
  scan_for_flags(map_dir, flags)

# Fill in any missing information
#for entry in treasures:
#  update_metadata(entry)

# Print (debug)
#for flag,entry in flags.items():
#  print(flag)
#  for asset in entry.mapsWhereSet.keys():
#    print(f"  Set: {asset}")
#  for asset in entry.mapsWhereUsed.keys():
#    print(f"  Used: {asset}")

# Save treasure to a .csv file
out_path = 'my_flags.csv'
with open(out_path, 'w', encoding='utf-8') as out:
  out.write("flag_name,flag_id,map_name,map_area_name,map_override_name,set_or_used,asset_path\n")

  for flag in sorted(flags.keys()):
    entry = flags[flag]

    for asset in sorted(entry.mapsWhereSet.keys()):
      print_row(flag, asset, entry.mapsWhereSet[asset], 'Set')
    for asset in sorted(entry.mapsWhereUsed.keys()):
      print_row(flag, asset, entry.mapsWhereUsed[asset], 'Use')


print(f"Done, saved to: {out_path}")
