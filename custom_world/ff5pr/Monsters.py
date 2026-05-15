#
# This file contains information on Bosses; it is meant to help manage boss scaling.
# Bosses can scale their stats (HP, AttackCount, etc.) and sometimes also their spells (Fire -> Firaga).
# We use the idea of a "recommended level" to scale enemies; this is roughly the level your party
#   should be expected to defeat this boss at.
#


# A few notes on stats:
#   * Defense reduces damage if an attack hits. Some things (axes) reduce the effectiveness of defense.
#     Others (Bells) are blocked by Magic Defense instead. Monster attacks are always physical, and have an
#     "attack count" that simply scales the damage done.
#   * It looks like "attack count" is only 50% effective if the target is in the back row. No idea if monsters
#     have rows (in which case it could be down to 25%). So "attack" and "attack count" *do* differ. (The "Defend"
#     command may also reduce attack_count here. Various esoterica re: Jump, Throw, etc., that only some enemies do --and
#     that may just use a custom damage formula.)
#   * Some monster attacks pierce Defense (Def to 0). Looks like Toad sets Defense to 0 (try on Cray Claw?). Goblin Punch
#     seems to drop Defense to 0 if your level is the same (could be fun!). Critical Hits also drop Def. to 0. "Strong vs."
#     weapons (some Bows) and magic drop Defense to 0. (This is all based on a guide I'm reading.)
#   * Looks like "Attack" can randomly range from [WeaponAttack, 112.5% * WeaponAttack], so that's where our variance comes in.
#     Defense is subtracted from this, and then a "multiplier" based on one's level/strength is factored in. Min value is 2, so 
#     expect early-game attacks to only be even numbers of damage.
#   * Example, Wing Raptor:
#     * Monster Defense ==  0 ; 30 or 32 damage
#     * Monster Defense ==  5 ; 20 or 22 damage
#     * Monster Defense == 10 ; 10 or 12 damage
#     * Monster Defense == 15 ;  2 or  0 damage
#   * Magic + magic defense are somewhat similar to Attack Count and Defense
#   * Bows/Axes have a listed hit%, but swords are 100% hit. Monsters have their own Hit%
#   * Evade, Hit%, and Ability Def do not have a clear trend line. We should have a "squish" param that scales them from 75% to 125% based
#     where we find them.
#   * Actually hitting a target takes Level into account, but we can's scale that without messing up the "LvX" Blue Magic.
#   * Agility factors into some (player) attacks. 
#   * Agility factors into turn count; so does Equip Weight (for heroes). 
#     * Ok, so your ATB is reset to a base value based on agility. I.e., if your agility is 120+ and your weight is 0, 
#       you'll reset to 255 - 1 (min val) == 255 and basically have your turn right away.
#     * Thus... we probably want to scale this, but should be careful. (Max val is 88, but maybe we allow up to 90?)
#   * TODO: Individual switches for each thing to scale.


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
  #
  def mp_scale_factor(self):
    return self.scale_factors[1]
  def def_scale_factor(self):
    return self.scale_factors[2]
  def atk_scale_factor(self):
    return self.scale_factors[3]
  def atkcount_scale_factor(self):
    return self.scale_factors[4]
  def magic_scale_factor(self):
    return self.scale_factors[5]
  def agi_scale_factor(self):
    return self.scale_factors[6]
  # TODO: some "squish" params?




# Magic that we know how to scale.
# This is tagged by name -- if you use a skill named "Fire", then we know how to scale it.
# We typically scale within three tiers; if tier 2 is None then that means there is no middle spell (so fall back to 'Slow'
#   until you are strong enough for 'Slowga'). You could presumably add a fourth tier here.
# Each monster's unique skills will be scaled, so if Monster X uses Fire with an ID of Y, then we'll create our own "Fira" and "Firaga" based
#   on that spell by ID, *not* by name. This is because monsters use customized skills (to force "target all", for example.)
scalable_magic = {
  ( 'Fire', 'Fira', 'Firaga' ) : None ,  # TODO: for real, though. Also, the value  should be some class; we need to put the "Black Magic" type, as well as info on "how" to scale it (thresholds)
}



# Monsters are all accessed by name
monsters = {
  'Wing Raptor' : Monster(281, 'sc_ai_281_WingRaptor', [2.163, 1.000, 0.10, 1.000, 0.385, 1.000, 0.795],
    [
      ('Breath Wing', 471),
      ('Claw', 961),
    ]
  ),

  'Wing Raptor Closed' : Monster(282, 'sc_ai_282_WingRaptor', [2.163, 1.000, 0.10, 1.000, 0.385, 1.000, 0.795],
    [
      ('Breath Wing', 471),
    ]
  ),

  'Karlabos' : Monster(283, 'sc_ai_283_Karlabos', [1.016, 0.494, 0.07, 0.971, 0.714, 0.053, 0.938],
    [
      ('Feeler', 504),
      ('Tail Screw', 449),
    ]
  ),

  'Siren' : Monster(285, 'sc_ai_285_Siren', [0.773, 0.527, 0.03, 1.103, 1.000, 0.036, 1.075],
    [
      ('Silence', 111),
      ('Slow', 145),
      ('Haste', 987),
      ('Cure', 988),
      ('Blizzard', 127),
      ('Libra', 109),
      ('Protect', 949),
      ('Sleep', 130),
      ('Thunder', 128),
      ('Venomous Clasp', 538),
    ]
  ),

  'Siren Undead' : Monster(286, 'sc_ai_286_UndeadSiren', [0.773, 0.527, 4.00, 1.029, 1.333, 0.036, 1.075],
    [
      # Siren's undead form attacks are actually in Siren's main AI script
    ]
  ),

  'Forza' : Monster(287, 'sc_ai_287_Forza', [0.503, 0.180, 0.67, 0.828, 1.406, 0.027, 1.117],
    [
      ('Tackle', 511),
    ]
  ),

  'Magissa' : Monster(288, 'sc_ai_288_Magissa', [0.385, 0.359, 0.02, 0.828, 0.781, 0.270, 0.906],
    [
      ('Fire', 126),
      ('Blizzard', 127),
      ('Thunder', 128),
      ('Aero', 396),
      ('Drain', 135),
      ('Regen', 823),
    ]
  ),

  'Garula' : Monster(289, 'sc_ai_289_Garula', [0.542, 0.136, 1.17, 0.743, 1.324, 0.022, 0.921],
    [
      ('Toad', 862),
    ]
  ),

  'Shiva' : Monster(317, 'sc_ai_317_Shiva', [0.678, 1.362, 0.02, 1.980, 0.882, 0.022, 0.743],
    [
      ('Blizzara', 831),
    ]
  ),

  'Liquid Flame Human' : Monster(290, 'sc_ai_290_LiquidFlame', [1.000, 0.100, 0.01, 0.716, 0.676, 1.681, 1.014],
    [
      ('Blaze', 472),
    ]
  ),

  'Liquid Flame Hand' : Monster(291, 'sc_ai_291_LiquidFlame', [1.000, 0.100, 0.01, 0.716, 0.676, 5.042, 1.014],
    [
      ('Ray', 541),
      ('Fira', 132),
    ]
  ),

  'Liquid Flame Tornado' : Monster(292, 'sc_ai_292_LiquidFlame', [1.000, 0.100, 0.01, 0.716, 0.676, 3.361, 1.014],
    [
      ('Fira', 697),
      ('Magnet', 483),
    ]
  ),

  'Ifrit' : Monster(54, 'sc_ai_054_Ifrit', [1.000, 1.000, 1.21, 1.153, 0.811, 5.378, 1.159],
    [
      ('Blaze', 472),
      ('Fire', 132),
      ('High Kick', 975),
    ]
  ),

  'Byblos' : Monster(33, 'sc_ai_033_Byblos', [1.200, 1.000, 1.21, 1.193, 2.027, 3.361, 1.159],
    [
      ('Web', 465),
      ('Magic Hammer', 406),
      ('Confuse', 116),
      ('Wind Slash', 424),
      ('Dischord', 464),
      ('Toad', 131),
      ('Protect', 949),
      ('Drain', 135),
    ]
  ),

  # We can't easily rotate him in without breaking things w.r.t. his item drop.
  #'Ramuh' : Monster(40, 'sc_ai_040_Ramuh', [1.056, 0.237, 1.90, 0.897, 1.000, 6.849, 1.273],
  #  [
  #    ('Thundara', 134),
  #    ('Electrocute', 459),
  #    ('Flash', 392),
  #    ('Lightning', 473),
  #    ('Osmose', 143),
  #    ('Mini', 818),
  #  ]
  #),

  # TODO: The "Hole" is what casts Gravity; do we want to scale their stats though?
  'Sandworm' : Monster(294, 'sc_ai_294_Sandworm', [0.792, 7.998, 0.01, 0.831, 1.250, 0.137, 1.415],
    [
      ('Quicksand', 454),
    ]
  ),

  'Cray Claw' : Monster(364, 'sc_ai_364_CrayClaw', [0.464, 0.346, 2.08, 1.108, 0.714, 0.122, 1.114],
    [
      ('Tail Screw', 449),
      ('Slimer', 466),
    ]
  ),

  'Adamantoise' : Monster(296, 'sc_ai_296_Adamantoise', [0.464, 0.087, 2.08, 0.928, 2.143, 0.012, 0.836],
    [
      # Basic boss; no magic
    ]
  ),

  # TODO: Do we care to scale the launchers?
  # NOTE: Soul Cannon's HP is scaled a bit funny due to the 10k auto-destruct
  'Soul Cannon' : Monster(300, 'sc_ai_300_SoulCannon', [5.219, 0.693, 0.42, 0.210, 0.238, 0.122, 1.532],
    [
      ('Wave Cannon', 474),
    ]
  ),

  'Archeoavis Form 1' : Monster(301, 'sc_ai_301_Archeoaevis', [1.841, 1.234, 0.44, 1.063, 0.795, 0.110, 0.823],
    [
      ('Breath Wing', 471),
      ('Sap', 540),
    ]
  ),

  'Archeoavis Form 2' : Monster(302, 'sc_ai_302_Archeoaevis', [1.841, 1.234, 0.89, 1.063, 0.795, 0.110, 0.823],
    [
      ('Frost', 458),
      ('Sap', 540),
    ]
  ),

  'Archeoavis Form 3' : Monster(303, 'sc_ai_303_Archeoaevis', [1.841, 1.234, 1.33, 1.063, 0.795, 0.110, 0.823],
    [
      ('Blaze', 472),
      ('Tail', 492),
    ]
  ),

  'Archeoavis Form 4' : Monster(304, 'sc_ai_304_Archeoaevis', [1.841, 1.234, 1.78, 1.063, 0.795, 0.110, 0.823],
    [
      ('Lightning', 473),
      ('Claw', 493),
    ]
  ),

  'Archeoavis Form 5' : Monster(305, 'sc_ai_305_Archeoaevis', [1.841, 1.234, 2.22, 1.144, 0.795, 0.110, 0.960],
    [
      ('Breath Wing', 471),
      ('Maelstrom', 447),
      ('Tusk', 518),
      ('Entangle', 441),
      ('Blaze', 472),
      ('Lightning', 473),
      ('Frost', 458),
    ]
  ),

  'Chimera Brain' : Monster(306, 'sc_ai_306_Manticore', [0.616, 0.556, 0.67, 1.000, 0.761, 0.100, 0.946],
    [
      ('Aqua Breath', 385),
      ('Frost', 458),
    ]
  ),

  'Titan' : Monster(307, 'sc_ai_307_Titan', [0.466, 1.113, 0.67, 1.125, 0.761, 0.010, 0.676],
    [
      ('Earth Shaker', 460),
    ]
  ),

  'Purobolos' : Monster(308, 'sc_ai_308_Purobolos', [0.840, 0.056, 0.01, 1.125, 0.761, 1.000, 0.540],
    [
      ('Self-Destruct', 408),
      ('Arise', 710),
      ('Arise', 1088),
      ('Cura', 699),
    ]
  ),

}



# Boss encounters and their recommended levels
# Recommended levels are used for scaling.
# Monster Name -> [ EncounterId, RecommendedLevel, [Additional, Monsters,] ]
boss_encounters = {
  'Wing Raptor' : [ 440, 4, ['Wing Raptor Closed'] ],
  'Karlabos' : [ 441, 6, [] ],
  'Siren' : [ 442, 8, ['Siren Undead'] ],
  'Forza' : [ 443, 10, ['Magissa'] ],
  'Garula' : [ 444, 12, [] ],
  'Liquid Flame Human' : [ 445, 15, ['Liquid Flame Hand', 'Liquid Flame Tornado'] ],
  'Shiva' : [ 498, 12, [] ],
  'Ifrit' : [ 495, 15, [] ],
  'Byblos' : [ 447, 15, [] ],
  'Sandworm' : [ 448, 18, [] ],
  #'Ramuh' : [ 77, 18, [] ],
  'Cray Claw' : [ 507, 20, [] ],
  'Adamantoise' : [ 449, 20, [] ],
  'Soul Cannon' : [ 452, 20, [] ],
  'Archeoavis Form 1' : [ 453, 22, ['Archeoavis Form 2', 'Archeoavis Form 3', 'Archeoavis Form 4' , 'Archeoavis Form 5'] ],
  'Chimera Brain' : [ 454, 24, [] ],
  'Titan' : [ 455, 24, [] ],
  'Purobolos' : [ 456, 24, [] ],

}







