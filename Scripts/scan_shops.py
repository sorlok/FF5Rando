#!/usr/bin/env python3


import os
import os.path
import json

from helpers import StringsAsset, CsvAsset


#
# Scan and annotate all shops
#


# This can be in different places
GamePath = '/mnt/d/Programs/Steam/steamapps/common/FINAL FANTASY V PR'
DataExportPath = 'FINAL FANTASY V_Data/StreamingAssets/MagiciteExport'
MasterPath = 'master/Assets/GameAssets/Serial/Data/Master'
MessagePath = 'message/Assets/GameAssets/Serial/Data/Message'


# Some known assets. These will be at <GamePath>/<DataExportPath>/<MasterPath>/<filename.csv>
ResourceFiles = {
  'shop.csv'
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




def scan_map_for_shops(map_dir, res):
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
        scan_indiv_map_for_shops(abs_path, res)



def scan_indiv_map_for_shops(imap_dir, res):
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
      areaName = asset_path.split('/')[-3]

      # Special processing for Mnemonics
      if 'Mnemonics' in root:
        # If we need a list of SysCalls (but I've already captured this)
        #for mn in root['Mnemonics']:
        #  if mn['mnemonic'] == 'SysCall':
        #    sysCallName = mn['operands']['sValues'][0]
        #    print("SysCall:",sysCallName)
        continue


      # Looking for a product_group
      if 'layers' in root:
        for layerId in range(len(root['layers'])):
          layer = root['layers'][layerId]
          if 'objects' in layer:
            for objId in range(len(layer['objects'])):
              obj = layer['objects'][objId]
              if 'properties' in obj:
                for prop in obj['properties']:
                  if prop['name'] == 'product_group_id':
                    productGroupId = int(prop['value'])
                    area_asset_name = areaName
                    json_xpath = f"/layers/[{layerId}]/objects/[{objId}]/properties/" + '{name=product_group_id}'
                    entry = [area_asset_name, asset_path, json_xpath]

                    res.setdefault(productGroupId, []).append(entry)







# Read our various assets
systemStrs = StringsAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MessagePath}/{StringFiles['system']}")
#
contentCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/content.csv")
productCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/product.csv")
productGroupCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/product_group.csv")  # Product "groups" are what the shop sells.
mapCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/map.csv")
areaCsv = CsvAsset.ReadFile(f"{GamePath}/{DataExportPath}/{MasterPath}/area.csv")




# Make a list of 'map' directories (map_1234); includes some weird ones like (map_1234_nigheffect) that probably set flags (they're usually cutscenes)
map_dirs = get_map_dirs(f"{GamePath}/{DataExportPath}")


# Scan maps for anything with a "product_group"
maps_lookup = {}  # productGroup => [ (area_asset_name, asset_path, json_xpath) ]
for map_dir in map_dirs:
  # Scan it!
  print(f"Scanning: {map_dir}")
  scan_map_for_shops(map_dir, maps_lookup)


# We need to replace the "area_asset_name" (which will be, e.g., Map_20011)
#   with the Area name string ("Tule""). We don't do map names since it's overkill
mapToAreaLookup = {}  # mapName -> areaId(s)
for entry in mapCsv.get_all_entries():
  asset_name = entry['asset_name']
  area_id = entry['area_id']
  mapToAreaLookup.setdefault(asset_name, set()).add(area_id)   # "Castle Walse" and "Water (Shiva) Tower" have slightly different stuff going on

# Ok, now just look it up...
for entries in maps_lookup.values():
  for entry in entries:
    area_asset_name = entry[0].lower()
    area_ids = mapToAreaLookup[area_asset_name]
    if len(area_ids) > 1:
      areaNameStr = "<CONFLICT_MULTI>"
    else:
      for area_id in area_ids:
        row = areaCsv.get_prop(int(area_id))
        areaNameMsg = row['area_name']
        areaNameStr = systemStrs.get_string(areaNameMsg)
        break
    # Save it!
    entry[0] = areaNameStr



# Build a product/shop lookup
shop_lookup = {}  # product_group -> { name_msg, name_str }
products = []  # { entries }
for shop in productGroupCsv.get_all_entries():
  pgId = int(shop['id'])
  pgMsg = shop['mes_id_name']
  shop_lookup[pgId] = { 'mes_id_name':pgMsg, 'group_name' : systemStrs.get_string(pgMsg), }

for prod in productCsv.get_all_entries():
  prod['content_name'] = '<MISSING>'
  row = contentCsv.get_prop(int(prod['content_id']))
  if row is not None:
    contentMsg = row.get('mes_id_name')
    prod['content_name'] = systemStrs.get_string(contentMsg)

  if int(prod['group_id']) in shop_lookup:
    prod['group_name'] = shop_lookup[int(prod['group_id'])]['group_name']
  else:
    prod['group_name'] = '<MISSING>'
  products.append(prod)

  # Set up remaining properties
  prod['towns_with_shop'] = '<MISSING>'
  prod['asset_paths'] = '<MISSING>'
  prod['json_xpaths'] = '<MISSING>'
  if int(prod['group_id']) in maps_lookup:
    towns = ''
    assets = ''
    xpaths = ''
    for entry in maps_lookup[int(prod['group_id'])]:
      towns += ';' if len(towns)>0 else ''
      towns += entry[0]
      assets += ';' if len(assets)>0 else ''
      assets += entry[1]
      xpaths += ';' if len(xpaths)>0 else ''
      xpaths += entry[2]
    prod['towns_with_shop'] = towns
    prod['asset_paths'] = assets
    prod['json_xpaths'] = xpaths



# NOTE: We need to scan maps (even though shops are product groups are used by multiple different shops),
#       since we plan to override these individually.



# Save shops to a .csv file
out_path = 'my_shops.csv'
with open(out_path, 'w', encoding='utf-8') as out:
  out.write("id,content_id,content_name,group_id,group_name,coefficient,purchase_limit,towns_with_shop,asset_paths,json_xpaths\n")

  for prod in products:
    out.write(f"{prod['id']},{prod['content_id']},{prod['content_name']},{prod['group_id']},{prod['group_name']},{prod['coefficient']},{prod['purchase_limit']},{prod['towns_with_shop']},{prod['asset_paths']},{prod['json_xpaths']}\n")



print(f"Done, saved to: {out_path}")
