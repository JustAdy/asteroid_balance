import math
import pygame

import game_state as gs
from bullet import Bullet


class Ship:
    def __init__(self):
        self.x = gs.WIDTH / 2
        self.y = gs.HEIGHT - 90
        self.speed = 430
        self.angle = -math.pi / 2
        self.cooldown = 0
        self.hp = 3
        self.invulnerable = 0

    def update(self, dt):
        # Controller 1: horizontal movement
        move = 0

        if gs.move_pad:
            # Default: Axis 0 = left stick horizontal
            move = gs.deadzone(gs.move_pad.get_axis(0))

        # Keyboard as an additional backup
        if abs(move) < 0.01:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                move = -1
            elif keys[pygame.K_RIGHT]:
                move = 1
            else:
                move = int(keys[pygame.K_d]) - int(keys[pygame.K_a])

        self.x += move * self.speed * dt
        self.x = gs.clamp(self.x, 35, gs.WIDTH - 35)

        # Controller 2: single-axis rotation control.
        # This controller can only move left/right, so instead of
        # pointing at an absolute direction, the axis deflection
        # sets how fast the aim direction rotates.
        if gs.aim_pad:
            aim_axis = gs.deadzone(gs.aim_pad.get_axis(0))
            if aim_axis != 0:
                self.angle += aim_axis * gs.AIM_ROTATION_SPEED * dt
                self.angle = math.fmod(self.angle, math.tau)
        else:
            # Mouse as a fallback (absolute aim) when no controller 2
            # is connected. Converted into `screen`'s fixed virtual
            # coordinate space since the real display is a different
            # (scaled, letterboxed) resolution.
            mx, my = gs.get_virtual_mouse_pos()
            aim_x = mx - self.x
            aim_y = my - self.y

            length = math.hypot(aim_x, aim_y)
            if length > 1:
                self.angle = math.atan2(aim_y, aim_x)

        self.cooldown -= dt
        self.invulnerable = max(0, self.invulnerable - dt)

    def shoot(self):
        if self.cooldown > 0:
            return False

        self.cooldown = gs.BULLET_COOLDOWN

        # >>> SOUND HOOK: play your bullet-fire sound effect here, e.g.
        #     sfx_shoot.play()

        count = max(1, gs.BULLET_SPREAD_COUNT)
        if count == 1:
            angles = [self.angle]
        else:
            total_spread = min(0.6, 0.14 * (count - 1))
            angles = [
                self.angle - total_spread / 2 + total_spread * (i / (count - 1))
                for i in range(count)
            ]

        for a in angles:
            muzzle_x = self.x + math.cos(a) * 27
            muzzle_y = self.y + math.sin(a) * 27
            gs.bullets.append(Bullet(muzzle_x, muzzle_y, a, gs.BULLET_PIERCE))

        return True

    def draw(self):
        # Blink effect after taking a hit
        if self.invulnerable > 0 and int(self.invulnerable * 15) % 2 == 0:
            return

        # >>> ART HOOK: replace the whole triangle/glow/flame drawing below
        #     with your own ship sprite. Rotate it to face self.angle, e.g.:
        #       rotated = pygame.transform.rotate(ship_img, -math.degrees(self.angle) - 90)
        #       rect = rotated.get_rect(center=(self.x, self.y))
        #       gs.screen.blit(rotated, rect)
        #     (the -90 offset is because self.angle=0 points right, but most
        #     ship art is drawn pointing "up" by default)

        rotated = pygame.transform.rotate(gs.ship_img, -math.degrees(self.angle) - 90)
        rect = rotated.get_rect(center=(self.x, self.y))
        gs.screen.blit(rotated, rect)

        # Thruster flame
        # >>> ART HOOK: swap these two circles for an animated flame/thruster
        #     sprite, positioned at (back_x, back_y).
        # flame_length = random.randint(13, 23)
        # back_x = self.x - math.cos(self.angle) * flame_length
        # back_y = self.y - math.sin(self.angle) * flame_length

        # pygame.draw.circle(gs.screen, (255, 170, 60), (int(back_x), int(back_y)), 8)
        # pygame.draw.circle(gs.screen, (255, 130, 35), (int(back_x), int(back_y)), 5)
