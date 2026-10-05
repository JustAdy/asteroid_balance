"""
Boss system for Asteroid Balance.

Bosses are stored in gs.asteroids (flagged with is_boss = True), so the
laser, bullets, pierce and ship-collision code treat them like big
asteroids. Everything you'll want to tweak is in the CONFIG block below.
"""

import math
import pygame

import game_state as gs

# ============================================================================
# CONFIG - EDIT BOSS STATS HERE
# ============================================================================

BOSS_EVERY_N_WAVES = 10          # a boss appears at wave 10, 20, 30, ...
BOSS_BLOCKS_NORMAL_SPAWNS = False  # True = no regular asteroids while a boss is alive

# What happens if a boss reaches the bottom of the screen.
# Damage dealt to the ship's HP. Default is high enough to be instant
# game over; set to e.g. 1 for a softer penalty.
BOSS_ESCAPE_DAMAGE = 99

# Each later boss is tougher: stat * (1 + GROWTH * bosses_already_spawned)
BOSS_HEALTH_GROWTH = 0.5        # +50% health per boss
BOSS_SPEED_GROWTH = 0.10        # +10% speed per boss

# Boss variants. They are cycled in order (boss 1 -> type 1, boss 2 -> type 2,
# boss 3 -> type 1 again, ...). Add, remove or edit entries freely.
BOSS_TYPES = [
    {
        "name": "ROCK TITAN",
        "radius": 110,          # hit radius AND sprite size (px)
        "health": 2500,         # base health (see scaling above)
        "speed": 45,            # downward speed (px/sec); screen is 1000px tall
        "sway_amplitude": 250,  # how far it drifts side to side (px)
        "sway_speed": 0.8,      # how fast it sways
        "spin": 0.3,            # sprite rotation speed (rad/sec)
        "score": 1000,          # score on kill
        "xp": 400,              # XP on kill
        "tint": (255, 110, 110),  # colour multiplied over the asteroid sprite
    },
    {
        "name": "VOID BEHEMOTH",
        "radius": 140,
        "health": 4500,
        "speed": 38,
        "sway_amplitude": 400,
        "sway_speed": 0.6,
        "spin": -0.2,
        "score": 2000,
        "xp": 700,
        "tint": (170, 110, 255),
    },
]

# ============================================================================

bosses_spawned = 0
next_boss_wave = BOSS_EVERY_N_WAVES

WARNING_TIME = 2.5  # seconds the "WARNING" banner shows after a boss spawns


def reset():
    """Called from gs.reset_game() at the start of every run."""
    global bosses_spawned, next_boss_wave
    bosses_spawned = 0
    next_boss_wave = BOSS_EVERY_N_WAVES


def get_boss():
    for a in gs.asteroids:
        if getattr(a, "is_boss", False):
            return a
    return None


def is_boss_active():
    return get_boss() is not None


def maybe_spawn_boss():
    """Call every frame while playing. Spawns a boss once the wave
    threshold is reached (and none is currently alive)."""
    global bosses_spawned, next_boss_wave
    if gs.wave >= next_boss_wave and not is_boss_active():
        gs.asteroids.append(Boss(BOSS_TYPES[bosses_spawned % len(BOSS_TYPES)], bosses_spawned))
        bosses_spawned += 1
        next_boss_wave += BOSS_EVERY_N_WAVES


def on_escape(boss):
    """Boss reached the bottom of the screen."""
    gs.asteroids.remove(boss)
    gs.ship.hp -= BOSS_ESCAPE_DAMAGE
    gs.explosion(boss.x, gs.HEIGHT - 20, 40)
    gs.trigger_shake(14, 0.4)
    gs.sfx_hit.play()
    if gs.ship.hp <= 0:
        gs.end_run()


class Boss:
    is_boss = True
    size = 3  # not 1 or 2, so it never splits like a normal asteroid

    def __init__(self, cfg, index):
        self.cfg = cfg
        self.name = cfg["name"]
        self.radius = cfg["radius"]
        self.max_health = cfg["health"] * (1 + BOSS_HEALTH_GROWTH * index)
        self.health = self.max_health
        self.speed = cfg["speed"] * (1 + BOSS_SPEED_GROWTH * index)

        self.base_x = gs.WIDTH / 2
        self.x = self.base_x
        self.y = -self.radius
        self.age = 0.0
        self.rotation = 0.0

        # Pre-tinted sprite (built once)
        size = self.radius * 2
        sprite = pygame.transform.smoothscale(gs.asteroid_img, (size, size))
        sprite.fill((*cfg["tint"], 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.sprite = sprite

    def update(self, dt):
        self.age += dt
        self.y += self.speed * dt
        self.x = self.base_x + math.sin(self.age * self.cfg["sway_speed"]) * self.cfg["sway_amplitude"]
        self.x = gs.clamp(self.x, self.radius, gs.WIDTH - self.radius)
        self.rotation += self.cfg["spin"] * dt

    def draw(self):
        rotated = pygame.transform.rotate(self.sprite, math.degrees(self.rotation))
        gs.screen.blit(rotated, rotated.get_rect(center=(self.x, self.y)))

    def on_death(self):
        """Called by gs.destroy_asteroid() when health hits 0."""
        gs.explosion(self.x, self.y, 80)
        gs.trigger_shake(12, 0.4)
        gs.score += self.cfg["score"]
        gs.gain_xp(self.cfg["xp"])


def draw_boss_ui():
    """Big health bar + warning banner. Call after the HUD is drawn."""
    boss = get_boss()
    if boss is None:
        return

    bar_w, bar_h = 800, 22
    bar_x = gs.WIDTH // 2 - bar_w // 2
    bar_y = 130
    ratio = gs.clamp(boss.health / boss.max_health, 0, 1)

    gs.draw_text(boss.name, (gs.WIDTH // 2, bar_y - 20), gs.FONT, (255, 120, 120), center=True)
    pygame.draw.rect(gs.screen, (50, 30, 35), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(gs.screen, (255, 80, 80), (bar_x, bar_y, bar_w * ratio, bar_h))
    pygame.draw.rect(gs.screen, (255, 200, 200), (bar_x, bar_y, bar_w, bar_h), 2)

    if boss.age < WARNING_TIME and int(boss.age * 4) % 2 == 0:
        gs.draw_text("WARNING - BOSS APPROACHING", (gs.WIDTH // 2, gs.HEIGHT // 2 - 200),
                     gs.BIG_FONT, (255, 90, 90), center=True)
