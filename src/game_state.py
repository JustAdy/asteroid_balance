"""
Shared engine state for Asteroid Balance.

This module holds everything the rest of the game (entities, upgrades,
UI, and the main loop) need to read or write: the display/audio setup,
balance constants, loaded assets, and all the mutable runtime game
state (score, wave, ship, bullets, menu state, ...).

Other files do `import game_state as gs` and always access state as
`gs.whatever` (never `from game_state import whatever`) so that writes
made in one file are visible everywhere else - that's the only way
plain mutable globals can be shared across separate Python modules.

Call init() once, from the entry point (game.py), before anything else
touches this module's state.
"""

import pygame
import random
import math
import os
import json

# ============================================================================
# >>> CUSTOM ASSETS - GRAFIKEN & SOUNDS HIER EINFUEGEN <<<
# >>> CUSTOM ASSETS - PUT YOUR OWN GRAPHICS & SOUNDS HERE <<<
# ============================================================================
# This is the ONE place to load your own images/sounds/music. Every spot
# in the code where you could actually USE one is marked with a banner
# comment starting with ">>> ART HOOK" or ">>> SOUND HOOK".
#
# Background music: one looping track per "section" of the game. Files
# are OPTIONAL - play_music() fails silently (and only tries once per
# track) if a file isn't there yet. Drop your own files at these paths
# to hear them; filenames/formats (mp3/ogg/wav) can be changed freely.
MUSIC_TRACKS = {
    "menu": os.path.join("assets", "music_menu.wav"),
    "weapon_select": os.path.join("assets", "music_weapon_select.wav"),
    "game": os.path.join("assets", "music_game.wav"),
}
_current_music_track = None
_failed_music_tracks = set()


def load_icon(filename):
    """Loads a weapon/upgrade card icon from assets/icons/. Returns
    None (instead of crashing) if the file isn't there yet, so cards
    just fall back to a plain placeholder until real art is added."""
    path = os.path.join("assets", "icons", filename)
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None


def play_music(track_key):
    """Switch background music to MUSIC_TRACKS[track_key] ("menu",
    "weapon_select" or "game"), looping forever. Does nothing if that
    track is already playing, and fails silently (only once per track)
    if the file isn't there yet - see MUSIC_TRACKS above."""
    global _current_music_track
    if track_key == _current_music_track:
        return
    path = MUSIC_TRACKS.get(track_key)
    if not path or track_key in _failed_music_tracks:
        _current_music_track = track_key
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1)
    except Exception:
        _failed_music_tracks.add(track_key)
    _current_music_track = track_key


# ---------------- Window / rendering ----------------
# The game is drawn onto a FIXED-size virtual canvas (`screen`), so it
# looks the same relative size on every monitor regardless of actual
# resolution. `screen` is then scaled (preserving aspect ratio, with
# letterboxing) onto the real, native-resolution full-screen `display`
# surface once per frame in present().
WIDTH, HEIGHT = 2000, 1000
FPS = 120

display = None
screen = None
clock = None

# Scale/offset from `screen` space to real `display` space, computed
# once in init() (the display size never changes at runtime).
render_scale = 1.0
render_offset_x = 0
render_offset_y = 0

# ---------------- Fonts ----------------
# Retro look: a bold monospaced "terminal/arcade" font instead of the
# default proportional one. SysFont takes a comma-separated fallback
# list and just uses whichever of these is installed on the machine.
_RETRO_FONT_NAMES = "couriernew,consolas,dejavusansmono,monospace"
FONT = SMALL_FONT = BIG_FONT = TITLE_FONT = None

# ---------------- Assets (populated in init()) ----------------
ship_img = asteroid_img = asteroid_small_img = None
BACKGROUND = None
SCANLINE_OVERLAY = None

sfx_explosion = sfx_hit = sfx_levelup = None

WEAPON_INFO = None

# ---------------- Controllers ----------------
joysticks = []
move_pad = None
aim_pad = None

# ---------------- Weapon / balance constants ----------------
# These are the BASE values. Upgrades modify the mutable globals below
# them; reset_game() restores the mutable ones from these.

BASE_BULLET_DAMAGE = 45
BASE_BULLET_COOLDOWN = 0.14
BASE_BULLET_SPREAD_COUNT = 1
BASE_BULLET_PIERCE = 0
BASE_BULLET_RANGE = 1.3       # bullet lifetime in seconds; combined with
                               # bullet speed this sets how far it travels

BASE_LASER_DPS = 200          # buffed: laser hits hard from the start
BASE_LASER_PIERCE = 0
BASE_LASER_BEAM_BONUS = 20

BASE_AIM_ROTATION_SPEED = 3.2
BASE_HIT_INVULN_TIME = 1.4

# Asteroid health scales up with wave as: 1 + wave / DIVISOR. Lower this
# to make asteroids get tankier faster as waves progress; raise it to
# slow that ramp down.
ASTEROID_HEALTH_SCALING_DIVISOR = 10

BULLET_DAMAGE = BASE_BULLET_DAMAGE
BULLET_COOLDOWN = BASE_BULLET_COOLDOWN
BULLET_SPREAD_COUNT = BASE_BULLET_SPREAD_COUNT
BULLET_PIERCE = BASE_BULLET_PIERCE
BULLET_RANGE = BASE_BULLET_RANGE

LASER_DPS = BASE_LASER_DPS
LASER_PIERCE = BASE_LASER_PIERCE
LASER_BEAM_BONUS = BASE_LASER_BEAM_BONUS

AIM_ROTATION_SPEED = BASE_AIM_ROTATION_SPEED
HIT_INVULN_TIME = BASE_HIT_INVULN_TIME

LASER_MAX_LENGTH = math.hypot(WIDTH, HEIGHT)

# ---------------- No-button menu navigation constants ----------------
# Menus are driven purely by axis tilt (no controller button required).
# Both connected controllers must lean to the SAME side to register a
# direction; holding that agreement for MENU_CONFIRM_TIME confirms it.

MENU_DIRECTION_THRESHOLD = 0.55  # how far a stick must lean to count as left/right
MENU_NEUTRAL_ZONE = 0.20         # how close to center counts as "neutral"
MENU_CONFIRM_TIME = 0.6          # seconds the agreed direction must be held

GAME_OVER_AUTO_EXIT_TIME = 10.0  # seconds before Game Over auto-returns to the menu

# ---------------- Game states ----------------
STATE_START = "start"
STATE_WEAPON_SELECT = "weapon_select"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()
LEADERBOARD_PATH = os.path.join(BASE_DIR, "asteroid_arcade_leaderboard.json")
LEADERBOARD_SIZE = 6

# ---------------- Runtime game state ----------------
state = None
weapon_type = None
leaderboard = []
high_score = 0
new_high_score = False
game_over_timer = 0.0  # seconds spent on the Game Over screen; auto-returns
                        # to the menu once it reaches GAME_OVER_AUTO_EXIT_TIME

ship = None
bullets = []
asteroids = []
particles = []

score = 0
wave = 1
spawn_timer = 0

# Progression system
xp = 0
level = 1
xp_to_next = 100
pending_level_ups = 0
leveling_up = False
upgrade_choices = []
elapsed_time = 0.0

laser_end = (0, 0)

# No-button menu navigation state
menu_hover = -1              # index of the currently agreed-on option, -1 = none
menu_progress = 0.0          # 0..1 fill of the confirm bar
menu_last_direction = None
menu_confirm_timer = 0.0

shake_timer = 0.0
shake_magnitude = 0.0

stars = []


# ---------------- One-time setup ----------------

def init():
    """Sets up pygame/display/audio, loads assets and fonts, finds
    controllers, builds the fixed-size virtual canvas, and starts the
    game in STATE_START. Must run before anything else in this module
    (or any entity class) is used."""
    global display, screen, clock, render_scale, render_offset_x, render_offset_y
    global FONT, SMALL_FONT, BIG_FONT, TITLE_FONT
    global ship_img, asteroid_img, asteroid_small_img, BACKGROUND, SCANLINE_OVERLAY
    global sfx_explosion, sfx_hit, sfx_levelup, WEAPON_INFO
    global move_pad, aim_pad
    global state, leaderboard, high_score, ship, laser_end

    pygame.init()
    pygame.joystick.init()
    pygame.mixer.init()

    # Full screen at the monitor's native resolution for `display`, but
    # everything is actually drawn onto a FIXED-size `screen` canvas
    # that gets scaled to fit `display` in present() - so the game
    # looks the same relative size no matter what monitor it runs on.
    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("Asteroid Balance")
    clock = pygame.time.Clock()

    display_w, display_h = display.get_size()
    render_scale = min(display_w / WIDTH, display_h / HEIGHT)
    render_offset_x = (display_w - WIDTH * render_scale) / 2
    render_offset_y = (display_h - HEIGHT * render_scale) / 2

    FONT = pygame.font.SysFont(_RETRO_FONT_NAMES, 34, bold=True)
    SMALL_FONT = pygame.font.SysFont(_RETRO_FONT_NAMES, 24, bold=True)
    BIG_FONT = pygame.font.SysFont(_RETRO_FONT_NAMES, 72, bold=True)
    TITLE_FONT = pygame.font.SysFont(_RETRO_FONT_NAMES, 92, bold=True)

    # Images (replace the placeholder shapes drawn with pygame.draw...):
    ship_img = pygame.image.load("assets/Ship2.png").convert_alpha()
    asteroid_img = pygame.image.load("assets/Astroid_Big.png").convert_alpha()
    asteroid_small_img = pygame.image.load("assets/Astroid.png").convert_alpha()
    #   bullet_img = pygame.image.load("assets/bullet.png").convert_alpha()
    #   (convert_alpha() keeps transparency and makes drawing much faster)

    # Sounds (played with sound.play() at the ">>> SOUND HOOK" spots):
    #   sfx_shoot    = pygame.mixer.Sound("assets/shoot.wav")
    sfx_explosion = pygame.mixer.Sound("assets/explosion.wav")
    sfx_hit = pygame.mixer.Sound("assets/ship_damage.wav")
    sfx_levelup = pygame.mixer.Sound("assets/upgrade.wav")
    #   sfx_gameover = pygame.mixer.Sound("assets/game_over.wav")

    # >>> ART HOOK: WEAPON / UPGRADE CARD ICONS <<<
    # The weapon-select and level-up cards can each show a small icon,
    # loaded via load_icon() above - OPTIONAL: it returns None (instead
    # of crashing) if the file isn't there yet, so the cards just fall
    # back to a plain placeholder until real art is added.
    WEAPON_INFO = {
        "laser": {
            "name": "Laser Cannon",
            "desc": "A continuous beam that always fires where you aim. "
                    "Hits hard right away; upgrades add damage, pierce "
                    "and beam width.",
            "icon": load_icon("weapon_laser.png"),
        },
        "bullets": {
            "name": "Blaster",
            "desc": "Rapid-fire bullets that fire automatically. Upgrades "
                    "add fire rate, damage, extra shots and pierce.",
            "icon": load_icon("weapon_blaster.png"),
        },
    }

    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks.append(js)
        print(f"Controller {i + 1}: {js.get_name()}")
    # The first two controllers found are used.
    move_pad = joysticks[0] if len(joysticks) >= 1 else None
    aim_pad = joysticks[1] if len(joysticks) >= 2 else None

    BACKGROUND = make_gradient(WIDTH, HEIGHT, (14, 10, 34), (3, 5, 16))
    # Scanlines are drawn over the real display (so they stay crisp at
    # native resolution, including over any letterbox bars).
    SCANLINE_OVERLAY = make_scanline_overlay(display_w, display_h)

    for _ in range(150):
        stars.append({
            "x": random.uniform(0, WIDTH),
            "y": random.uniform(0, HEIGHT),
            "drift": random.uniform(12, 70),
            "size": random.choice([1, 1, 1, 2, 2]),
            "phase": random.uniform(0, math.tau),
            "twinkle_speed": random.uniform(1.0, 3.2),
            "brightness": random.randint(90, 210),
        })

    state = STATE_START
    leaderboard = load_leaderboard()
    high_score = leaderboard[0]["score"] if leaderboard else 0

    # Imported here (not at module top) to dodge a circular import:
    # ship.py does `import game_state as gs`, so it can only be
    # imported once this module has finished defining everything.
    from ship import Ship
    ship = Ship()
    laser_end = (ship.x, ship.y)


# ---------------- Helper functions ----------------

def deadzone(value, size=0.18):
    if abs(value) < size:
        return 0.0
    sign = 1 if value > 0 else -1
    return sign * (abs(value) - size) / (1.0 - size)


def clamp(value, low, high):
    return max(low, min(high, value))


def draw_text(text, pos, font=None, color=(235, 240, 255), center=False):
    font = font or FONT
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    screen.blit(surf, rect)


def draw_panel(rect, fill=(10, 14, 30, 160), border=(90, 120, 190, 200), radius=0):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, border, panel.get_rect(), 2, border_radius=radius)
    screen.blit(panel, rect.topleft)


def circle_collision(x1, y1, r1, x2, y2, r2):
    return math.hypot(x1 - x2, y1 - y2) < r1 + r2


def get_virtual_mouse_pos():
    """Real mouse position converted into `screen`'s fixed virtual
    coordinate space - use this instead of pygame.mouse.get_pos()
    anywhere gameplay/UI code needs the mouse, now that `screen` is
    scaled to fit the real, native-resolution display."""
    mx, my = pygame.mouse.get_pos()
    vx = (mx - render_offset_x) / render_scale
    vy = (my - render_offset_y) / render_scale
    return vx, vy


def get_menu_direction():
    """Reads every connected controller's left/right axis and returns
    "left", "right" or "neutral" only if ALL connected pads agree.
    Returns "mixed" if they disagree (or one is in the dead zone
    between "committed" and "neutral"), and None if no pad at all is
    connected (menus then fall back to keyboard only)."""
    pads = []
    if move_pad:
        pads.append(deadzone(move_pad.get_axis(0), size=0.15))
    if aim_pad:
        pads.append(deadzone(aim_pad.get_axis(0), size=0.15))

    if not pads:
        return None

    dirs = []
    for v in pads:
        if v <= -MENU_DIRECTION_THRESHOLD:
            dirs.append("left")
        elif v >= MENU_DIRECTION_THRESHOLD:
            dirs.append("right")
        elif abs(v) <= MENU_NEUTRAL_ZONE:
            dirs.append("neutral")
        else:
            dirs.append("mid")  # committed to neither zone -> ambiguous

    if all(d == dirs[0] for d in dirs):
        return dirs[0]
    return "mixed"


def update_menu_dwell(direction, valid_directions, dt):
    """Tracks how long `direction` has continuously been one of the
    valid options. Returns (direction_or_None, progress 0..1, confirmed)."""
    global menu_last_direction, menu_confirm_timer

    if direction in valid_directions:
        if direction != menu_last_direction:
            menu_last_direction = direction
            menu_confirm_timer = 0.0

        menu_confirm_timer += dt
        progress = clamp(menu_confirm_timer / MENU_CONFIRM_TIME, 0.0, 1.0)

        if menu_confirm_timer >= MENU_CONFIRM_TIME:
            menu_last_direction = None
            menu_confirm_timer = 0.0
            return direction, 1.0, True

        return direction, progress, False

    menu_last_direction = None
    menu_confirm_timer = 0.0
    return None, 0.0, False


def reset_menu_nav():
    global menu_hover, menu_progress, menu_last_direction, menu_confirm_timer
    menu_hover = -1
    menu_progress = 0.0
    menu_last_direction = None
    menu_confirm_timer = 0.0


def load_leaderboard():
    try:
        with open(LEADERBOARD_PATH, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data[:LEADERBOARD_SIZE]
    except Exception:
        pass
    return []


def save_leaderboard(entries):
    try:
        with open(LEADERBOARD_PATH, "w") as f:
            json.dump(entries, f)
    except Exception:
        pass


def add_leaderboard_entry(run_score, run_time):
    global leaderboard, high_score
    leaderboard.append({"score": int(run_score), "time": float(run_time)})
    leaderboard.sort(key=lambda e: e["score"], reverse=True)
    del leaderboard[LEADERBOARD_SIZE:]
    save_leaderboard(leaderboard)
    high_score = leaderboard[0]["score"] if leaderboard else 0


def format_time(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


# ---------------- Background: gradient + twinkling stars ----------------

def make_gradient(width, height, top_color, bottom_color):
    surf = pygame.Surface((width, height))
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        pygame.draw.line(surf, (r, g, b), (0, y), (width, y))
    return surf


def make_scanline_overlay(width, height):
    """A grid of faint dark horizontal lines, for an old-arcade-monitor
    feel. Built once since the resolution is fixed for the window's
    lifetime."""
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 3):
        pygame.draw.line(overlay, (0, 0, 0, 40), (0, y), (width, y))
    return overlay


def update_stars(dt):
    for s in stars:
        s["y"] += s["drift"] * dt
        if s["y"] > HEIGHT:
            s["y"] -= HEIGHT
            s["x"] = random.uniform(0, WIDTH)


def draw_stars():
    t = pygame.time.get_ticks() / 1000.0
    for s in stars:
        twinkle = 0.55 + 0.45 * math.sin(t * s["twinkle_speed"] + s["phase"])
        b = clamp(int(s["brightness"] * twinkle), 0, 255)
        pygame.draw.circle(screen, (b, b, min(255, b + 30)), (int(s["x"]), int(s["y"])), s["size"])


# ---------------- Screen shake ----------------

def trigger_shake(magnitude, duration):
    global shake_timer, shake_magnitude
    shake_timer = duration
    shake_magnitude = magnitude


def present(dt):
    """Scales the fixed-size `screen` canvas (with screen-shake applied)
    onto the real, native-resolution `display` and flips it. Call once
    per frame, after all drawing onto `screen` is done."""
    global shake_timer

    if shake_timer > 0:
        shake_timer -= dt
        offset = (random.uniform(-shake_magnitude, shake_magnitude),
                  random.uniform(-shake_magnitude, shake_magnitude))
    else:
        offset = (0, 0)

    scaled_w = int(WIDTH * render_scale)
    scaled_h = int(HEIGHT * render_scale)
    scaled = pygame.transform.smoothscale(screen, (scaled_w, scaled_h))

    display.fill((0, 0, 0))
    display.blit(scaled, (render_offset_x + offset[0] * render_scale,
                           render_offset_y + offset[1] * render_scale))
    display.blit(SCANLINE_OVERLAY, (0, 0))
    pygame.display.flip()


# ---------------- Core gameplay helpers (shared by upgrades/main loop) ----

def explosion(x, y, amount=18):
    from particle import Particle
    for _ in range(amount):
        particles.append(Particle(x, y))


def gain_xp(amount):
    global xp, xp_to_next, level, pending_level_ups

    xp += amount

    while xp >= xp_to_next:
        xp -= xp_to_next
        level += 1
        xp_to_next = int(xp_to_next * 1.5) + 25
        pending_level_ups += 1


def destroy_asteroid(asteroid):
    """Handle score/xp/particles/splitting once an asteroid's health
    hits 0. Caller is responsible for removing it from `asteroids`
    first."""
    global score
    from asteroid import Asteroid

    if hasattr(asteroid, "on_death"):
        asteroid.on_death()
        sfx_explosion.play()
        return

    explosion(asteroid.x, asteroid.y)

    # >>> SOUND HOOK: play your asteroid-explosion sound effect here, e.g.
    sfx_explosion.play()

    if asteroid.size == 2:
        for _ in range(2):
            small = Asteroid(1)
            small.x = asteroid.x
            small.y = asteroid.y
            small.speed *= 0.75
            asteroids.append(small)

        score += 100
        gain_xp(65)
    else:
        score += 50
        gain_xp(30)

def end_run():
    global state, game_over_timer, new_high_score
    trigger_shake(16, 0.5)
    new_high_score = (not leaderboard) or (score > leaderboard[0]["score"])
    add_leaderboard_entry(score, elapsed_time)
    state = STATE_GAME_OVER
    game_over_timer = 0.0
    reset_menu_nav()
    play_music("menu")

def damage_ship(amount=1):
    ship.hp -= amount
    ship.invulnerable = HIT_INVULN_TIME
    explosion(ship.x, ship.y, 28)
    trigger_shake(8, 0.25)
    sfx_hit.play()
    if ship.hp <= 0:
        end_run()

def spawn_asteroid():
    from asteroid import Asteroid
    asteroids.append(Asteroid(2))


def reset_game(chosen_weapon):
    global ship, bullets, asteroids, particles
    global score, wave, spawn_timer
    global laser_end
    global xp, level, xp_to_next, pending_level_ups, leveling_up, upgrade_choices, elapsed_time
    global weapon_type
    global BULLET_DAMAGE, BULLET_COOLDOWN, BULLET_SPREAD_COUNT, BULLET_PIERCE, BULLET_RANGE
    global LASER_DPS, LASER_PIERCE, LASER_BEAM_BONUS
    global AIM_ROTATION_SPEED, HIT_INVULN_TIME

    from ship import Ship

    weapon_type = chosen_weapon

    ship = Ship()
    bullets = []
    asteroids = []
    particles = []

    score = 0
    wave = 1
    spawn_timer = 0

    xp = 0
    level = 1
    xp_to_next = 100
    pending_level_ups = 0
    leveling_up = False
    upgrade_choices = []
    elapsed_time = 0.0

    BULLET_DAMAGE = BASE_BULLET_DAMAGE
    BULLET_COOLDOWN = BASE_BULLET_COOLDOWN
    BULLET_SPREAD_COUNT = BASE_BULLET_SPREAD_COUNT
    BULLET_PIERCE = BASE_BULLET_PIERCE
    BULLET_RANGE = BASE_BULLET_RANGE

    LASER_DPS = BASE_LASER_DPS
    LASER_PIERCE = BASE_LASER_PIERCE
    LASER_BEAM_BONUS = BASE_LASER_BEAM_BONUS

    AIM_ROTATION_SPEED = BASE_AIM_ROTATION_SPEED
    HIT_INVULN_TIME = BASE_HIT_INVULN_TIME

    laser_end = (ship.x, ship.y)

    import boss
    boss.reset()

    import alien
    alien.reset()

    import energy_wave
    energy_wave.reset()


def choose_weapon(w):
    global state
    reset_game(w)
    reset_menu_nav()
    state = STATE_PLAYING

    # >>> SOUND HOOK: a good spot for a weapon-select confirm sound.
    play_music("game")

# ---------------- Jump button (balance board) ----------------
JUMP_BUTTON = 0
JUMP_FLASH_TIME = 0.5
TEST_JUMP_ONLY = True      # True = jump button ignores all menu/upgrade actions

jump_count = 0
jump_flash_timer = 0.0
jump_last_pad = None       # 1 or 2 (index in joysticks + 1), None = unknown


jump_counts = {}           # pad number -> jumps from that pad


def add_joystick(device_index):
    """Open a controller (used for hot-plug). Ignores ones already open."""
    global move_pad, aim_pad
    try:
        js = pygame.joystick.Joystick(device_index)
    except Exception:
        return
    js_id = js.get_instance_id() if hasattr(js, "get_instance_id") else js.get_id()
    for old in joysticks:
        old_id = old.get_instance_id() if hasattr(old, "get_instance_id") else old.get_id()
        if old_id == js_id:
            return
    js.init()
    joysticks.append(js)
    print(f"Controller {len(joysticks)} connected: {js.get_name()}")
    if move_pad is None:
        move_pad = js
    elif aim_pad is None:
        aim_pad = js


def register_jump(event):
    """Called when the jump button is pressed on any controller."""
    global jump_count, jump_flash_timer, jump_last_pad
    jump_count += 1
    jump_flash_timer = JUMP_FLASH_TIME

    inst = getattr(event, "instance_id", getattr(event, "joy", None))
    jump_last_pad = None
    for i, js in enumerate(joysticks):
        js_id = js.get_instance_id() if hasattr(js, "get_instance_id") else js.get_id()
        if js_id == inst:
            jump_last_pad = i + 1
            break
    jump_counts[jump_last_pad] = jump_counts.get(jump_last_pad, 0) + 1
    print(f"JUMP #{jump_count} from controller {jump_last_pad} (raw id {inst})")


def draw_jump_debug():
    surf = SMALL_FONT.render(f"Jumps: {jump_count}", True, (150, 190, 220))
    screen.blit(surf, (WIDTH - surf.get_width() - 20, HEIGHT - 40))

    # Live per-controller panel (top right)
    y = 100
    draw_text(f"Controllers found: {len(joysticks)}", (WIDTH - 560, y), SMALL_FONT, (255, 210, 80))
    for i, js in enumerate(joysticks):
        y += 26
        btn = js.get_button(JUMP_BUTTON) if js.get_numbuttons() > JUMP_BUTTON else -1
        line = (f"#{i + 1} {js.get_name()[:22]}  axis0={js.get_axis(0):+.2f}  "
                f"btn{JUMP_BUTTON}={btn}  jumps={jump_counts.get(i + 1, 0)}")
        draw_text(line, (WIDTH - 560, y), SMALL_FONT, (150, 190, 220))

    if jump_flash_timer > 0:
        pad = f"Controller {jump_last_pad}" if jump_last_pad else "unknown controller"
        draw_text(f"JUMP!  ({pad})", (WIDTH // 2, HEIGHT // 2 + 260),
                  BIG_FONT, (120, 255, 160), center=True)
