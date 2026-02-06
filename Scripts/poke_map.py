#!/usr/bin/env python3


import os
import os.path
import json

from helpers import StringsAsset, CsvAsset


#
# This is me trying to figure out how map tiles/collisions work without really putting in the effort to really understand it.
#


# This can be in different places
GamePath = '/mnt/d/Programs/Steam/steamapps/common/FINAL FANTASY V PR'
DataExportPath = 'FINAL FANTASY V_Data/StreamingAssets/MagiciteExport'
DataImportPath = 'FINAL FANTASY V_Data/StreamingAssets/Magicite/wgrpg'
MapPath = 'map_10010/Assets/GameAssets/Serial/Res/Map/Map_10010/Map_10010'

SrcFile = f"{GamePath}/{DataExportPath}/{MapPath}/tilemap.json"
DstFile = f"{GamePath}/{DataImportPath}/{MapPath}/tilemap.json"

SrcFile2 = f"{GamePath}/{DataExportPath}/{MapPath}/attribute.json"
DstFile2 = f"{GamePath}/{DataImportPath}/{MapPath}/attribute.json"

# Read the data!
obj = None
with open(SrcFile, encoding='utf-8') as f:
	obj = json.load(f)

# Poke the map!

# Meteor
obj['layers'][1]['layers'][2]['data'][161*256+62] = 334
obj['layers'][1]['layers'][2]['data'][162*256+62] = 334+32 # Tail
obj['layers'][1]['layers'][2]['data'][163*256+62] = 334+64 # Tail

# Town
obj['layers'][1]['layers'][2]['data'][162*256+64] = 54

# Save it!
with open(DstFile, 'w', encoding='utf-8') as f:
	json.dump(obj, f)

# Now, do the meteor collision

# Read the data!
obj = None
with open(SrcFile2, encoding='utf-8') as f:
	obj = json.load(f)

# Poke the map!

# Meteor
obj['layers'][0]['data'][161*256+62] = 34

# Might as well make the town land-able
obj['layers'][0]['data'][162*256+64] = 33
 
# Save it!
with open(DstFile2, 'w', encoding='utf-8') as f:
	json.dump(obj, f)




print(f"Done; wrote to: {DstFile}")