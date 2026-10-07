"""
Energy Wave - the co-op special ability for Asteroid Balance.

When BOTH players jump within JUMP_WINDOW seconds of each other, a
shockwave expands from the ship and damages/destroys everything it
touches. Then it goes on cooldown.

EDIT BALANCE VALUES IN THE CONFIG BLOCK BELOW.
"""

import math
import pygame

import game_state as gs
import alien

# ============================================================================
# CONFIG - EDIT ENERGY WAVE BALANCE HERE
# ============================================================================

# --- Activation ---
REQUIRE_BOTH_PLAYERS = True   # False = any single jump fires it (solo testing)
JUMP_WINDOW = 0.40            # sec: both jumps must land within this window

# --- Cooldown ---
COOLDOWN = 30.0               # sec between uses (ticks only while playing)
START_COOLDOWN = 10.0         # sec before the FIRST use each run (0 = ready at start)

# --- Wave behaviour ---
WAVE_SPEED = 2200             # px/sec; ~1 sec to cross the screen. Huge = instant
# Fraction of an enemy's MAX health removed when the wave hits it.
# 1.0 (or more) = instant kill. Bosses are tankier so they only take a bite.
DAMAGE_FRACTION = {
    "asteroid": 1.0,
    "alien": 1.0,
    "boss": 0.25,
}
SPLIT_ASTEROIDS = False       # True = big asteroids still split into small ones
CLEAR_ALIEN_SHOTS = True      # wipe enemy bullets when the wave fires

# --- Player bonus ---
INVULN_TIME = 0.6             # sec of invulnerability granted to the ship (0 = none)

# --- Visuals ---
WAVE_THICKNESS = 70           # px width of the ring
SHAKE_MAGNITUDE = 14
SHAKE_TIME = 0.5

# ============================================================================

MAX_RADIUS = math.hypot(gs.WIDTH, gs.HEIGHT) + WAVE_THICKNESS

cooldown_timer = START_COOLDOWN
cooldown_total = max(START_COOLDOWN, 0.001)
deny_timer = 0.0
last_jump = {1: -999.0, 2: -999.0}   # pad number -> time of last jump

active = False
radius = 0.0
origin = (0, 0)
hit_ids = set()


def _now():
    return pygame.time.get_ticks() / 1000.0


def reset():
    """Called from gs.reset_game() at the start of every run."""
    global cooldown_timer, cooldown_total, deny_timer, active, radius
    cooldown_timer = START_COOLDOWN
    cooldown_total = max(START_COOLDOWN, 0.001)
    deny_timer = 0.0
    active = False
    radius = 0.0
    hit_ids.clear()
    last_jump[1] = last_jump[2] = -999.0


def is_ready():
    return cooldown_timer <= 0 and not active


def on_jump(pad):
    """Call on every jump. `pad` is 1 or 2 (gs.jump_last_pad), or None."""
    global deny_timer
    if gs.state != gs.STATE_PLAYING or gs.leveling_up:
        return

    if REQUIRE_BOTH_PLAYERS:
        if pad not in last_jump:
            return                      # unknown controller, can't pair it
        now = _now()
        last_jump[pad] = now
        other = 2 if pad == 1 else 1
        if now - last_jump[other] > JUMP_WINDOW:
            return                      # still waiting for the partner
        last_jump[1] = last_jump[2] = -999.0

    if is_ready():
        _trigger()
    else:
        deny_timer = 0.6


def _trigger():
    global active, radius, origin, cooldown_timer, cooldown_total
    active = True
    radius = 0.0
    origin = (gs.ship.x, gs.ship.y)
    hit_ids.clear()
    cooldown_timer = cooldown_total = COOLDOWN

    gs.ship.invulnerable = max(gs.ship.invulnerable, INVULN_TIME)
    gs.trigger_shake(SHAKE_MAGNITUDE, SHAKE_TIME)
    if CLEAR_ALIEN_SHOTS:
        alien.projectiles.clear()

    # >>> SOUND HOOK: play your energy-wave sound effect here.


def _kind(a):
    if getattr(a, "is_boss", False):
        return "boss"
    if getattr(a, "is_alien", False):
        return "alien"
    return "asteroid"


def _hit(a):
    a.health -= a.max_health * DAMAGE_FRACTION[_kind(a)]
    gs.explosion(a.x, a.y, 10)
    if a.health <= 0:
        if a in gs.asteroids:
            gs.asteroids.remove(a)
        count_before = len(gs.asteroids)
        gs.destroy_asteroid(a)
        if not SPLIT_ASTEROIDS:
            del gs.asteroids[count_before:]   # drop the freshly spawned splits


def update(dt):
    """Call once per frame while playing (not during the level-up screen)."""
    global cooldown_timer, deny_timer, radius, active

    cooldown_timer = max(0.0, cooldown_timer - dt)
    deny_timer = max(0.0, deny_timer - dt)

    if not active:
        return

    radius += WAVE_SPEED * dt
    ox, oy = origin

    for a in gs.asteroids[:]:
        if id(a) in hit_ids or a.y + a.radius < 0:   # skip already hit / above screen
            continue
        if math.hypot(a.x - ox, a.y - oy) - a.radius <= radius:
            hit_ids.add(id(a))
            _hit(a)

    if radius >= MAX_RADIUS:
        active = False
        hit_ids.clear()


def draw():
    """Draw the expanding ring. Call after asteroids/bullets, before the ship."""
    if not active:
        return
    r = int(radius)
    if r < 2:
        return
    fade = 1.0 - 0.6 * min(1.0, radius / MAX_RADIUS)
    center = (int(origin[0]), int(origin[1]))
    w = min(r, WAVE_THICKNESS)
    pygame.draw.circle(gs.screen, (int(40 * fade), int(110 * fade), int(255 * fade)), center, r, w)
    pygame.draw.circle(gs.screen, (int(200 * fade), int(240 * fade), 255), center, r, max(2, min(r, w // 4)))


def draw_hud():
    """Ability indicator at bottom-centre. Call after the main HUD."""
    rect = pygame.Rect(gs.WIDTH // 2 - 190, gs.HEIGHT - 76, 380, 66)
    gs.draw_panel(rect)

    if is_ready():
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008)
        color = (int(90 * pulse) + 40, int(255 * pulse), int(150 * pulse) + 40)
        gs.draw_text("ENERGY WAVE: READY", (rect.centerx, rect.top + 20), gs.SMALL_FONT, color, center=True)

        waiting = REQUIRE_BOTH_PLAYERS and any(_now() - t <= JUMP_WINDOW for t in last_jump.values())
        hint = "Waiting for partner..." if waiting else (
            "BOTH PLAYERS JUMP!" if REQUIRE_BOTH_PLAYERS else "JUMP!")
        gs.draw_text(hint, (rect.centerx, rect.top + 46), gs.SMALL_FONT, (170, 200, 255), center=True)
    else:
        if active:
            label = "ENERGY WAVE: FIRING"
        else:
            label = f"ENERGY WAVE: {math.ceil(cooldown_timer)}s"
        gs.draw_text(label, (rect.centerx, rect.top + 20), gs.SMALL_FONT, (150, 170, 200), center=True)
        bar_x, bar_y, bar_w, bar_h = rect.left + 20, rect.top + 44, rect.width - 40, 10
        ratio = gs.clamp(1.0 - cooldown_timer / cooldown_total, 0.0, 1.0)
        pygame.draw.rect(gs.screen, (50, 55, 70), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(gs.screen, (90, 150, 255), (bar_x, bar_y, bar_w * ratio, bar_h))

    if deny_timer > 0:
        gs.draw_text("NOT READY", (rect.centerx, rect.top - 24), gs.FONT, (255, 100, 100), center=True)