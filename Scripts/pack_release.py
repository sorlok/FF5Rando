# This script is used to create a Release for our Github page. 
# Pass in the version number you want and it will make a zip file.

import os
import sys
import shutil
import zipfile


# Usage
if len(sys.argv) != 2:
  print(f"Usage: {sys.argv[0]} <release_version>")
  sys.exit(1)


# Version
version = sys.argv[1]


# Clear any old files
outFile = f"FF5Rando_Release_{version}.zip"
outApWorldFile = 'ff5pr.apworld'
for fname in [outFile, outApWorldFile]:
  if os.path.exists(fname):
    os.remove(fname)

# Pack up our custom world
shutil.make_archive(outApWorldFile, 'zip', root_dir='custom_world')
os.rename(f"{outApWorldFile}.zip", outApWorldFile)

# Write our Release zip file
with zipfile.ZipFile(outFile, 'w') as zout:
  zout.write(outApWorldFile)
  zout.write('LICENSE')
  zout.write('dlls/LICENSE_DLLS', arcname='LICENSE_DLLS')
  zout.write('dlls/Archipelago.MultiClient.Net.dll', arcname='Archipelago.MultiClient.Net.dll')
  zout.write('dlls/Newtonsoft.Json.dll', arcname='Newtonsoft.Json.dll')
  zout.write('MyFF5Plugin/bin/Debug/net6.0/MyFF5Plugin.dll', arcname='MyFF5Plugin.dll')

# ...and delete the apworld temp file
os.remove(outApWorldFile)
