import math
import pygame

import game_state as gs


class Bullet:
    def __init__(self, x, y, angle, pierces=0):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 720
        self.life = gs.BULLET_RANGE
        self.pierces_left = pierces

    def update(self, dt):
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        self.life -= dt

    def draw(self):
        # >>> ART HOOK: replace this square with your own bullet sprite,
        #     e.g. gs.screen.blit(bullet_img, (self.x - bullet_img.get_width()/2,
        #                                       self.y - bullet_img.get_height()/2))
        # Drawn as a blocky square (rather than a circle) for a retro,
        # pixel-art look.
        pygame.draw.rect(gs.screen, (100, 220, 255), (int(self.x) - 4, int(self.y) - 4, 8, 8))
