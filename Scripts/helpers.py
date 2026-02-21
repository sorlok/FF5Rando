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



# Stores a CSV-type asset
class CsvAsset:
  @staticmethod
  def ReadFile(path):
    res = CsvAsset()

    lineNum = -1
    with open(path) as f:
      for line in f:
        parts = line.strip("\r\n").split(',')
        lineNum += 1

        # Header vs. data
        if lineNum == 0:
          res.headers = parts
          if 'id' not in res.headers:
            raise Exception(f"Invalid header set, doesn't contain 'id': {res.headers}")
        else:
          if len(parts) != len(res.headers):
            raise Exception(f"Invalid line: {len(parts)}, for headers: {len(res.headers)}")

          entry = {}
          for i in range(len(parts)):
            entry[res.headers[i]] = parts[i]
          res.data.append(entry)

    print(f"Read: {path}")
    return res



  def __init__(self):
    # header_name, in order
    self.headers = []

    # rows of { k:v } entries; guaranteed to have exactly 1 entry per header
    self.data = []


  # Do we have every column accounted for?
  def same_fields(self, entry):
    if len(entry) != len(self.headers):
      return False
    for col in entry:
      if col not in self.headers:
        return False
    return True

  # Add an entry to the end of a csv file
  def add_entry(self, entry):
    # Make sure we have exactly the same fields.
    if not self.same_fields(entry):
      raise Exception(f"Fields don't match: {entry}")

    # Make sure the index is the next one in line. 
    # We could auto-generate the index, but we'd need a way to
    #   make sure these are consistent across runs of the program
    #   (or else we'd break save files).
    if int(entry['id']) != int(self.data[-1]['id']) + 1:
      raise Exception(f"Invalid id for: {entry}; previous id is: {self.data[-1]['id']}")

    # Now just add it
    self.data.append(entry)


  # Get all entries
  def get_all_entries(self):
    return self.data


  # Retrieve an entry with the following id
  def get_prop(self, entryId):
    for entry in self.data:
      if int(entry['id']) == entryId:
        return entry

  # Retrieve an entry by looking for a specific key/value (return all entries with that k/v)
  # We do string matching, since type isn't preserved within self.data
  def search_for_prop(self, key, value):
    res = []
    for entry in self.data:
      if str(entry[key]) == str(value):
        res.append(entry)
    return res


  # Modify an entry
  #   entryId can also be an array of entries, or the string 'all'
  #   operand can be '=' to set it, or '*' to multiply, etc.
  def modify_prop(self, entryId, key, operand, value):
    if key not in self.headers:
      raise Exception(f"Can't modify key: {key}; known headers are: {self.headers}")

    if isinstance(entryId, int):
      entryId = [entryId]

    modified = 0
    for entry in self.data:
      if entryId == 'all' or int(entry['id']) in entryId:
        modified += 1
        newVal = entry[key]
        if operand != '=':
          newVal = int(newVal)

        if operand == '=':
          newVal = value
        elif operand == '+':
          newVal += value
        elif operand == '-':
          newVal -= value
        elif operand == '*':
          newVal *= value
        elif operand == '/':
          newVal /= value
        else:
          raise Exception(f"Unknown operand: {operand}")

        # Avoid some common pitfalls
        if operand != '=':
          newVal = int(newVal)
          if newVal < 1 and int(entry[key]) != 0:
            newVal = 1

        entry[key] = newVal

    if modified == 0:
      raise Exception(f"No entry modified: {entryId}")


  def write(self, path):
    # Make sure assets were exported correctly.
    if not os.path.isfile(path):
      raise Exception(f"Trying to overwrite file that doesn't exist: {path}")

    # Write it.
    with open(path, 'w', encoding='utf-8', newline='') as f:
      # Headers:
      f.write(f"{','.join(self.headers)}\r\n")

      # Data
      for entry in self.data:
        line = ''
        for col in self.headers:
          line += f"{'' if len(line)==0 else ','}{entry[col]}"
        f.write(f"{line}\r\n")

      # For some reason, these files all end with an empty line... or not?
      #f.write("\r\n")

    print(f"Wrote: {path}")

