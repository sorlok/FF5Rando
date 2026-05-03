#
# This file contains information on Bosses; it is meant to help manage boss scaling.
# Bosses can scale their stats (HP, AttackCount, etc.) and sometimes also their spells (Fire -> Firaga).
# We use the idea of a "recommended level" to scale enemies; this is roughly the level your party
#   should be expected to defeat this boss at.
#




# Simple classes

class Monster:
  def __init__(self, monster_id: int, ai_script: str, scale_factors: list[float], magic: list):
    self.monster_id = monster_id
    self.ai_script = ai_script
    self.scale_factors = scale_factors
    self.magic = magic  # May include non-scalable magic

  def __repr__(self):
    return f"Monster({self.monster_id}, {self.ai_script})"

  # The way these scaling factors work is as follows. We have a formula for each stat; e.g., HP is:
  #   HP = 262.222 * RecLvl - 933.33
  # ...this formula can be used for any arbitrary boss to define its HP for a given "recommended level".
  # For example, if we put Wing Raptor (OrigRecLvl:4) in the spot where Sandworm (OrigRecLvl:18) appears,
  #   then its base HP will be 262.222 * 18 - 933.33 => 3,787 HP
  # However, we need to account for each boss's natural variance from the baseline; the Soul Cannon, for example,
  #   has way more HP than the Purobolos. Each boss is thus given a scaling factor based on its variance from baseline
  #   at its original location. So, Wing Raptor's baseline is 262.222 * 4 - 933.33 => 116 HP, but its actual HP in the 
  #   Wind Shrine is 250 HP, so its scaling factor is 250 / 116 => 2.16. So, when Wing Raptor appears at the Sandworm
  #   location, its actual HP value will be 3,787 * 2.16 = 8179.92 HP
  # Note that Bosses can be scaled without swapping location; we could, for example, imagine what a "Recommended Level 90 Wing Raptor"
  #   or even a "Recommended Level 999 Wing Raptor" might look like. Their stats will be bound between some reasonable min/max, though.
  def hp_scale_factor(self):
  	return self.scale_factors[0]
  # TODO: MORE




# Magic that we know how to scale.
# This is tagged by name -- if you use a skill named "Fire", then we know how to scale it.
# We typically scale within three tiers; if tier 2 is None then that means there is no middle spell (so fall back to 'Slow'
#   until you are strong enough for 'Slowga'). You could presumably add a fourth tier here.
# Each monster's unique skills will be scaled, so if Monster X uses Fire with an ID of Y, then we'll create our own "Fira" and "Firaga" based
#   on that spell by ID, *not* by name. This is because monsters use customized skills (to force "target all", for example.)
scalable_magic = {
  ( 'Fire', 'Fira', 'Firaga' ) : None ,  # TODO: for real, though. Also, the value  should be some class; we need to put the "Black Magic" type, as well as info on "how" to scale it.
}



# Monsters are all accessed by name
# TODO: Figure out what we want to do for multiple monsters of the same type (or in the same encounter).
monsters = {
  'Wing Raptor' : Monster(281, 'sc_ai_281_WingRaptor', [2.16],
    [
      ('Breath Wing',471),
      ('Claw',961),
    ]
  ),

  'Wing Raptor Closed' : Monster(282, 'sc_ai_282_WingRaptor', [2.16],
    [
      ('Breath Wing',471),
    ]
  ),

  




}







