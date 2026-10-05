"""
Aliens for Asteroid Balance.

Aliens live in gs.asteroids (flagged is_alien = True), so the laser,
bullets, pierce and ship-ramming code all treat them like asteroids.
Each type has a "behavior" that decides how it moves/attacks.

Behaviors:
  homing  - steers toward the ship and rams it
  weaver  - snakes side to side while sliding toward your column
  shooter - descends to a hover height, strafes, fires at the ship
  dasher  - hovers, flashes a warning, then dashes at where you were

EDIT STATS IN THE CONFIG BLOCK BELOW.
"""

import math
import random
import pygame

import game_state as gs
import boss

# ============================================================================
# CONFIG - EDIT ALIEN STATS HERE
# ============================================================================

ALIEN_START_WAVE = 3               # no aliens before this wave
ALIEN_SPAWN_INTERVAL = 4.0         # seconds between spawns at START_WAVE
ALIEN_SPAWN_INTERVAL_PER_WAVE = 0.15  # spawns get this much faster per wave
ALIEN_SPAWN_INTERVAL_MIN = 1.2     # never faster than this
ALIEN_MAX_ALIVE = 6                # cap on simultaneous aliens
ALIENS_DURING_BOSS = True          # False = no aliens while a boss is alive
ALIEN_HEALTH_SCALING_DIVISOR = 10  # health * (1 + wave / this), like asteroids

# "min_wave": first wave this type can appear. "weight": spawn likelihood
# relative to the other eligible types. Remove an entry to disable a type.
ALIEN_TYPES = {
    "drone": {
        "behavior": "homing", "shape": "triangle", "color": (255, 90, 90),
        "radius": 22, "health": 60, "speed": 300,
        "turn_rate": 1.6,            # rad/sec - lower = easier to dodge
        "score": 75, "xp": 35, "min_wave": 2, "weight": 4,
    },
    "weaver": {
        "behavior": "weaver", "shape": "diamond", "color": (90, 255, 150),
        "radius": 26, "health": 90, "speed": 120,
        "sway_amplitude": 220, "sway_speed": 2.2,
        "drift": 60,                 # px/sec its centre line slides toward your x
        "score": 100, "xp": 45, "min_wave": 3, "weight": 3,
    },
    "gunship": {
        "behavior": "shooter", "shape": "hex", "color": (255, 200, 70),
        "radius": 32, "health": 220, "speed": 90,
        "hover_y": 200,              # height it stops descending at
        "strafe_amplitude": 300, "strafe_speed": 0.7,
        "fire_interval": 2.0,        # seconds between shots
        "shot_speed": 380,
        "score": 150, "xp": 70, "min_wave": 4, "weight": 2,
    },
    "dasher": {
        "behavior": "dasher", "shape": "square", "color": (200, 120, 255),
        "radius": 26, "health": 120, "speed": 140,
        "hover_y_min": 150, "hover_y_max": 380,
        "windup": 1.0,               # warning flash time before the dash
        "dash_speed": 900,
        "score": 125, "xp": 55, "min_wave": 5, "weight": 2,
    },
}

SHOT_RADIUS = 8
SHOT_LIFETIME = 6.0

# ============================================================================

projectiles = []
spawn_timer = ALIEN_SPAWN_INTERVAL

_SHAPES = {
    "triangle": [(1, 0), (-0.8, 0.8), (-0.8, -0.8)],
    "diamond": [(1, 0), (0, 0.8), (-1, 0), (0, -0.8)],
    "hex": [(1, 0), (0.5, 0.87), (-0.5, 0.87), (-1, 0), (-0.5, -0.87), (0.5, -0.87)],
    "square": [(0.8, 0.8), (-0.8, 0.8), (-0.8, -0.8), (0.8, -0.8)],
}


def reset():
    """Called from gs.reset_game() at the start of every run."""
    global spawn_timer
    projectiles.clear()
    spawn_timer = ALIEN_SPAWN_INTERVAL


class AlienShot:
    def __init__(self, x, y, angle, speed):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = SHOT_LIFETIME

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        # >>> ART HOOK: replace with an enemy-bullet sprite.
        r = SHOT_RADIUS
        pygame.draw.rect(gs.screen, (255, 90, 170), (int(self.x) - r, int(self.y) - r, r * 2, r * 2))
        pygame.draw.rect(gs.screen, (255, 220, 240), (int(self.x) - r // 2, int(self.y) - r // 2, r, r))


class Alien:
    is_alien = True
    size = 4  # not 1/2 (asteroids) or 3 (boss)

    def __init__(self, key, cfg):
        self.key = key
        self.cfg = cfg
        self.behavior = cfg["behavior"]
        self.radius = cfg["radius"]

        scaling = 1 + gs.wave / ALIEN_HEALTH_SCALING_DIVISOR
        self.max_health = cfg["health"] * scaling
        self.health = self.max_health

        self.x = random.uniform(self.radius, gs.WIDTH - self.radius)
        self.y = -self.radius
        self.base_x = self.x
        self.age = 0.0
        self.phase = random.uniform(0, math.tau)
        self.heading = math.pi / 2
        self.expired = False

        self.fire_timer = cfg.get("fire_interval", 0) * random.uniform(0.5, 1.0)

        # dasher state
        self.mode = "approach"
        self.mode_timer = 0.0
        self.dash_dir = (0.0, 1.0)
        if self.behavior == "dasher":
            self.hover_y = random.uniform(cfg["hover_y_min"], cfg["hover_y_max"])

    # ---------- behaviors ----------
    def update(self, dt):
        self.age += dt
        getattr(self, "_" + self.behavior)(dt)
        if self.y > gs.HEIGHT + 150 or self.y < -400 or self.x < -200 or self.x > gs.WIDTH + 200:
            self.expired = True

    def _homing(self, dt):
        c = self.cfg
        target = math.atan2(gs.ship.y - self.y, gs.ship.x - self.x)
        diff = (target - self.heading + math.pi) % math.tau - math.pi
        step = c["turn_rate"] * dt
        self.heading += gs.clamp(diff, -step, step)
        self.x += math.cos(self.heading) * c["speed"] * dt
        self.y += math.sin(self.heading) * c["speed"] * dt

    def _weaver(self, dt):
        c = self.cfg
        self.y += c["speed"] * dt
        toward = gs.ship.x - self.base_x
        self.base_x += gs.clamp(toward, -c["drift"] * dt, c["drift"] * dt)
        self.x = self.base_x + math.sin(self.age * c["sway_speed"] + self.phase) * c["sway_amplitude"]
        self.x = gs.clamp(self.x, self.radius, gs.WIDTH - self.radius)

    def _shooter(self, dt):
        c = self.cfg
        if self.y < c["hover_y"]:
            self.y += c["speed"] * dt
        self.x = self.base_x + math.sin(self.age * c["strafe_speed"] + self.phase) * c["strafe_amplitude"]
        self.x = gs.clamp(self.x, self.radius, gs.WIDTH - self.radius)

        if self.y >= c["hover_y"] * 0.9:
            self.fire_timer -= dt
            if self.fire_timer <= 0:
                self.fire_timer = c["fire_interval"]
                angle = math.atan2(gs.ship.y - self.y, gs.ship.x - self.x)
                projectiles.append(AlienShot(self.x, self.y, angle, c["shot_speed"]))

    def _dasher(self, dt):
        c = self.cfg
        if self.mode == "approach":
            self.y += c["speed"] * dt
            if self.y >= self.hover_y:
                self.mode, self.mode_timer = "windup", c["windup"]
        elif self.mode == "windup":
            self.mode_timer -= dt
            self.heading = math.atan2(gs.ship.y - self.y, gs.ship.x - self.x)  # aim while charging
            if self.mode_timer <= 0:
                self.dash_dir = (math.cos(self.heading), math.sin(self.heading))
                self.mode = "dash"
        else:
            self.x += self.dash_dir[0] * c["dash_speed"] * dt
            self.y += self.dash_dir[1] * c["dash_speed"] * dt

    def on_death(self):
        """Called by gs.destroy_asteroid() when health hits 0."""
        gs.explosion(self.x, self.y, 20)
        gs.score += self.cfg["score"]
        gs.gain_xp(self.cfg["xp"])

    # ---------- drawing ----------
    def draw(self):
        # >>> ART HOOK: replace this polygon with an alien sprite per type
        #     (rotate by self.heading, blit centred on self.x/self.y).
        color = self.cfg["color"]
        windup = self.behavior == "dasher" and self.mode == "windup"
        if windup and int(self.age * 12) % 2 == 0:
            color = (255, 255, 255)

        cos_h, sin_h = math.cos(self.heading), math.sin(self.heading)
        pts = [
            (self.x + (px * cos_h - py * sin_h) * self.radius,
             self.y + (px * sin_h + py * cos_h) * self.radius)
            for px, py in _SHAPES[self.cfg["shape"]]
        ]
        pygame.draw.polygon(gs.screen, color, pts)
        pygame.draw.polygon(gs.screen, (20, 20, 30), pts, 3)
        pygame.draw.circle(gs.screen, (20, 20, 30), (int(self.x), int(self.y)), max(3, self.radius // 4))

        if windup:  # telegraph the dash line
            end = (self.x + cos_h * 1400, self.y + sin_h * 1400)
            pygame.draw.line(gs.screen, (255, 120, 255), (self.x, self.y), end, 2)

        if self.health < self.max_health:
            ratio = max(0.0, self.health / self.max_health)
            bar_w = self.radius * 2
            bar_x, bar_y = self.x - self.radius, self.y - self.radius - 10
            pygame.draw.rect(gs.screen, (60, 60, 60), (bar_x, bar_y, bar_w, 4))
            pygame.draw.rect(gs.screen, (255, 90, 90) if ratio < 0.4 else (255, 210, 80),
                             (bar_x, bar_y, bar_w * ratio, 4))


# ---------------- module-level hooks used by game.py ----------------

def _spawn(dt):
    global spawn_timer
    if gs.wave < ALIEN_START_WAVE:
        return
    if boss.is_boss_active() and not ALIENS_DURING_BOSS:
        return

    spawn_timer -= dt
    if spawn_timer > 0:
        return
    spawn_timer = max(
        ALIEN_SPAWN_INTERVAL_MIN,
        ALIEN_SPAWN_INTERVAL - (gs.wave - ALIEN_START_WAVE) * ALIEN_SPAWN_INTERVAL_PER_WAVE,
    )

    if sum(1 for a in gs.asteroids if getattr(a, "is_alien", False)) >= ALIEN_MAX_ALIVE:
        return

    eligible = [(k, c) for k, c in ALIEN_TYPES.items() if gs.wave >= c["min_wave"]]
    if not eligible:
        return
    key, cfg = random.choices(eligible, weights=[c["weight"] for _, c in eligible])[0]
    gs.asteroids.append(Alien(key, cfg))


def update(dt):
    """Call once per frame while playing: spawning, alien shots, cleanup."""
    _spawn(dt)

    for shot in projectiles:
        shot.update(dt)
        if gs.ship.invulnerable <= 0 and gs.circle_collision(
                gs.ship.x, gs.ship.y, 18, shot.x, shot.y, SHOT_RADIUS):
            shot.life = 0
            gs.damage_ship()

    projectiles[:] = [
        s for s in projectiles
        if s.life > 0 and -50 < s.x < gs.WIDTH + 50 and -50 < s.y < gs.HEIGHT + 50
    ]

    for a in gs.asteroids[:]:
        if getattr(a, "expired", False):
            gs.asteroids.remove(a)


def draw_projectiles():
    for shot in projectiles:
        shot.draw()
