#!/usr/bin/env python3


# Stores a tab-separated string asset
class StringsAsset:
  @staticmethod
  def ReadFile(path):
    res = StringsAsset()

    with open(path, encoding='utf-8') as f:
      for line in f:
        # Handle empty lines
        line = line.strip("\r\n")
        if len(line) == 0:
          continue
        parts = line.split('\t', 1)

        # Quite simple, but we also check for duplicates
        if len(parts) != 2:
          raise Exception(f"Invalid line, should be two parts: {line}")
        if parts[0] in res.data and parts[1] != res.data[parts[0]]: ## Note: The end-game letter is... weird.
          raise Exception(f"Invalid line, key already exists: {line}")

        res.data[parts[0]] = parts[1]
        res.keys.append(parts[0])

    print(f"Read: {path}")
    return res


  def __init__(self):
    # (key, value)
    self.data = {}

    # list of keys in order, to preserve order when printing
    self.keys = []


  # Add some strings to the end of the file
  # 'strings' is a dict of key/values to add
  def add_strings(self, strings):
    for key, value in strings.items():
      # Make sure we're not clobbering any existing entry
      if key in self.data:
        raise Exception(f"String key already exists: {key}")

      self.data[key] = value
      self.keys.append(key)


  # Change an existing entry
  def change_string(self, key, newVal):
    if key not in self.data:
      raise Exception(f"String key does not exist: {key}")

    self.data[key] = newVal  # No need to update self.keys

  # Get an entry
  def get_string(self, key):
    if key not in self.data:
      raise Exception(f"String key does not exist: {key}")

    return self.data[key]


  def write(self, path):
    # Make sure assets were exported correctly.
    if not os.path.isfile(path):
      raise Exception(f"Trying to overwrite file that doesn't exist: {path}")

    # Write it.
    with open(path, 'w', encoding='utf-8', newline='') as f:
      # Write in order
      for key in self.keys:
        value = self.data[key]
        f.write(f"{key}\t{value}\r\n")

      # Seems like these might have an extra line at the end?
      f.write("\r\n")

    print(f"Wrote: {path}")




