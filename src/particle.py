import random
import math
import pygame

import game_state as gs


class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(50, 230)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(.25, .7)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= .96
        self.vy *= .96
        self.life -= dt

    def draw(self):
        # >>> ART HOOK: replace this square with a small spark/smoke sprite
        #     for a fancier explosion effect (fade it out using self.life,
        #     e.g. by setting the sprite's alpha proportional to self.life).
        # Drawn as a blocky square (rather than a circle) for a retro,
        # pixel-art look.
        if self.life > 0:
            size = max(2, int(self.life * 10))
            pygame.draw.rect(
                gs.screen,
                (255, 170, 60),
                (int(self.x) - size // 2, int(self.y) - size // 2, size, size)
            )
