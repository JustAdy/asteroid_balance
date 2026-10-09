"""
Upgrade definitions (what each upgrade DOES) and the level-up-card
selection flow (which upgrades get offered, and applying the chosen
one). All state lives in game_state (imported as gs); this module
just mutates it.

NOTE: this module is imported only AFTER game_state.init() has run,
since building the upgrade lists below calls gs.load_icon(), which
needs the display to already exist.
"""

import random

import game_state as gs


# ---------------- Upgrades (weapon-specific + generic) ----------------

def upgrade_laser_overcharge():
    gs.LASER_DPS += 40


def upgrade_laser_pierce():
    gs.LASER_PIERCE += 1


def upgrade_laser_wide():
    gs.LASER_BEAM_BONUS += 15


def upgrade_bullet_rapid():
    gs.BULLET_COOLDOWN = max(0.05, gs.BULLET_COOLDOWN * 0.8)


def upgrade_bullet_heavy():
    gs.BULLET_DAMAGE += 18


def upgrade_bullet_multishot():
    gs.BULLET_SPREAD_COUNT += 1


def upgrade_bullet_pierce():
    gs.BULLET_PIERCE += 1


def upgrade_bullet_range():
    gs.BULLET_RANGE += 0.4


def upgrade_engine_boost():
    gs.ship.speed += 45


def upgrade_quick_turret():
    gs.AIM_ROTATION_SPEED += 0.6


def upgrade_extra_life():
    gs.ship.hp += 1


def upgrade_reinforced_hull():
    gs.HIT_INVULN_TIME += 0.4


LASER_UPGRADES = [
    {"name": "Overcharged Laser", "desc": "+35 laser damage/sec", "apply": upgrade_laser_overcharge,
     "icon": gs.load_icon("upgrade_laser_overcharge.png")},
    {"name": "Piercing Beam", "desc": "Laser passes through one more asteroid", "apply": upgrade_laser_pierce,
     "icon": gs.load_icon("upgrade_laser_pierce.png")},
    {"name": "Wide Beam", "desc": "Thicker beam, easier to hit", "apply": upgrade_laser_wide,
     "icon": gs.load_icon("upgrade_laser_wide.png")},
]

BULLET_UPGRADES = [
    {"name": "Rapid Fire", "desc": "Bullets fire ~20% faster", "apply": upgrade_bullet_rapid,
     "icon": gs.load_icon("upgrade_bullet_rapid.png")},
    {"name": "Heavy Rounds", "desc": "+18 bullet damage", "apply": upgrade_bullet_heavy,
     "icon": gs.load_icon("upgrade_bullet_heavy.png")},
    {"name": "Multi-Shot", "desc": "Fire one more bullet per shot", "apply": upgrade_bullet_multishot,
     "icon": gs.load_icon("upgrade_bullet_multishot.png")},
    {"name": "Piercing Rounds", "desc": "Bullets pierce one more asteroid", "apply": upgrade_bullet_pierce,
     "icon": gs.load_icon("upgrade_bullet_pierce.png")},
    {"name": "Extended Range", "desc": "Bullets travel farther before fading", "apply": upgrade_bullet_range,
     "icon": gs.load_icon("upgrade_bullet_range.png")},
]

GENERIC_UPGRADES = [
    {"name": "Engine Boost", "desc": "Ship moves faster", "apply": upgrade_engine_boost,
     "icon": gs.load_icon("upgrade_engine_boost.png")},
    {"name": "Quick Turret", "desc": "Aim rotates faster", "apply": upgrade_quick_turret,
     "icon": gs.load_icon("upgrade_quick_turret.png")},
    {"name": "Extra Life", "desc": "+1 hit point", "apply": upgrade_extra_life,
     "icon": gs.load_icon("upgrade_extra_life.png")},
    {"name": "Reinforced Hull", "desc": "Longer post-hit invulnerability", "apply": upgrade_reinforced_hull,
     "icon": gs.load_icon("upgrade_reinforced_hull.png")},
]


def start_level_up_selection():
    gs.leveling_up = True
    gs.pending_level_ups -= 1

    pool = (LASER_UPGRADES if gs.weapon_type == "laser" else BULLET_UPGRADES) + GENERIC_UPGRADES
    gs.upgrade_choices = random.sample(pool, min(2, len(pool)))
    gs.reset_menu_nav()

    # >>> SOUND HOOK: play your level-up sound effect here, e.g.
    gs.sfx_levelup.play()


def choose_upgrade(index):
    if not gs.leveling_up or not (0 <= index < len(gs.upgrade_choices)):
        return

    gs.upgrade_choices[index]["apply"]()
    gs.leveling_up = False

    if gs.pending_level_ups > 0:
        start_level_up_selection()
