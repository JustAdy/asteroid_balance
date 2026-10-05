import random
import math
import pygame

import game_state as gs


class Asteroid:
    def __init__(self, size=2):
        self.size = size
        self.radius = 50 if size == 2 else 25
        self.x = random.randint(self.radius, gs.WIDTH - self.radius)
        self.y = -self.radius - random.randint(0, 250)

        # Speed scales with wave, player level, AND survival time so
        # the game keeps getting harder and faster the longer you play.
        self.speed = (
            random.uniform(90, 170)
            + gs.wave * 7
            + gs.level * 4
            + gs.elapsed_time * 1.1
        )
        self.vx = random.uniform(-35, 35)

        self.rotation = random.uniform(0, math.tau)
        self.spin = random.uniform(-2.0, 2.0)

        # Asteroids have health instead of dying in one hit.
        health_scaling = 1 + gs.wave / gs.ASTEROID_HEALTH_SCALING_DIVISOR
        self.max_health = 120 * health_scaling if size == 2 else 55 * health_scaling
        self.health = self.max_health

        self.points = []
        for i in range(9):
            angle = math.tau * i / 9
            radius = self.radius * random.uniform(0.75, 1.15)
            self.points.append((angle, radius))

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.speed * dt
        self.rotation += self.spin * dt

    def draw(self):
        # >>> ART HOOK: replace the two polygon lines just below with your
        #     own rock sprite instead (rotate it with pygame.transform.rotate
        #     using math.degrees(self.rotation), then blit it centered on
        #     self.x/self.y). You'll probably want a small sprite and a big
        #     one, picked based on self.size (2 = large, 1 = small).
        points = []

        for angle, radius in self.points:
            a = angle + self.rotation
            points.append((
                int(self.x + math.cos(a) * radius),
                int(self.y + math.sin(a) * radius)
            ))

        if self.size == 2:
            rotated = pygame.transform.rotate(gs.asteroid_img, math.degrees(self.rotation))
        else:
            rotated = pygame.transform.rotate(gs.asteroid_small_img, math.degrees(self.rotation))
        rect = rotated.get_rect(center=(self.x, self.y))
        gs.screen.blit(rotated, rect)

        # Health bar, only shown once the asteroid has taken damage.
        if self.health < self.max_health:
            ratio = max(0.0, self.health / self.max_health)
            bar_w = self.radius * 2
            bar_x = self.x - self.radius
            bar_y = self.y - self.radius - 10

            pygame.draw.rect(gs.screen, (60, 60, 60), (bar_x, bar_y, bar_w, 4))
            bar_color = (255, 90, 90) if ratio < 0.4 else (255, 210, 80)
            pygame.draw.rect(gs.screen, bar_color, (bar_x, bar_y, bar_w * ratio, 4))
