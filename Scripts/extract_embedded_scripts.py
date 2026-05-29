#!/usr/bin/env python3


import os
import os.path
import sys
import json
import base64
import shutil

from helpers import StringsAsset, CsvAsset


#
# Pull base64-encoded scripts out of the World Map package, so that we can actually look at them.
#


# This can be in different places
GamePath = '/mnt/d/Programs/Steam/steamapps/common/FINAL FANTASY V PR'
DataExportPath = 'FINAL FANTASY V_Data/StreamingAssets/MagiciteExport'
MasterPath = 'master/Assets/GameAssets/Serial/Data/Master'
MessagePath = 'message/Assets/GameAssets/Serial/Data/Message'




#
# TODO: It will eventually make sense to pull from package_info, keys, etc., rather than just guessing the file structure
#



# Read our various assets
#systemStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['system']}")
#
#contentCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/content.csv")
#productCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/product.csv")
#productGroupCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/product_group.csv")  # Product "groups" are what the shop sells.
#mapCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/map.csv")
#areaCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/area.csv")


# What I think each map is representative of:
worlds = {
  'Map_10010' : 'World1',
  'Map_10020' : 'World2',
  
  # I think:
  #'Map_10030' : 'UnderWater2',
  #'Map_10040' : 'World3',
  #'Map_10050' : 'UnderWater3',
}


# World Name -> Script name -> parsed json
scripts = {}

# Read our map Package
# TODO: Worlds 2/3
for world in sorted(worlds.keys()):
  worldMapPkgPath = f"{GamePath}/{DataExportPath}/{world.lower()}/Assets/GameAssets/Serial/Res/Map/{world}/package.json"
  with open(worldMapPkgPath, encoding="utf-8") as f:
    root = json.load(f)

    for mapObj in root["map"]:
      # NOTE: Map Map_10010_1 has a copy of sc_e_0001_7, but I'm just assuming it's the same.
      world = worlds.get(mapObj['name'])  # E.g., Map_10010 -> World1
      if not world:
        continue

      # We need to see scripts
      for scrObj in mapObj['script']:
        scrName = scrObj['name']
        scrText = base64.b64decode(scrObj['inline'])
        jsonObj = json.loads(scrText)

        if scrName in scripts:
          raise Exception(f"Duplicate script name: {scrName}")

        scripts.setdefault(world, {})[scrName] = jsonObj


# Clear old files, make new directory structure
if os.path.exists('Embedded'):
  shutil.rmtree('Embedded')
os.mkdir('Embedded')
for world in worlds.values():
  os.mkdir(f"Embedded/{world}")

# Make all our new files
for world in sorted(scripts.keys()):
  for scrName in sorted(scripts[world].keys()):
    print(f"Saving: {world}/{scrName}")
    scrObj = scripts[world][scrName]
    with open(f"Embedded/{world}/{scrName}.json", 'w', encoding="utf-8") as out:
      json.dump(scrObj, out)

print(f"Done, saved to: Embedded/World[123]")
