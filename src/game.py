"""
ASTEROID BALANCE - 2 CONTROLLER PYGAME

Flow: Start screen (shows high score) -> Weapon select ->
Play -> Game over -> back to the main menu.

Controller 1:
  Left stick -> Ship moves left/right

Controller 2 (single-axis controller):
  Left/right axis -> Rotates the aim direction. The ship's
  facing turns at a speed proportional to how far the stick
  is pushed (it is NOT an absolute direction, since this
  controller physically only moves left/right).
  Button 0 -> Confirm on menus.
  Button 1 -> Second menu option (e.g. pick "Blaster").

WEAPON CHOICE (picked once per run, at the start):
  [1] Laser Cannon -> a continuous beam that always fires
      where you aim. Hits hard from the start and its
      upgrades add more damage, pierce and beam width.
  [2] Blaster -> rapid-fire bullets that fire automatically,
      always aimed wherever you're pointing. Its upgrades add
      fire rate, damage, extra shots per burst and piercing
      rounds.
  Upgrades offered on level-up match whichever weapon you
  picked, plus a few generic ship upgrades.

NO-BUTTON MENU NAVIGATION:
  Neither controller needs a button for menus. TILT BOTH
  CONTROLLERS TO THE SAME SIDE and hold them there: both left
  picks the left option, both right picks the right option. A
  small bar under the highlighted card fills up while you
  hold; once it's full, that option is chosen. Every menu,
  including level-up upgrades, only ever offers 2 choices so
  this left/right gesture always works. If only one controller
  is connected, that single stick alone decides the direction.
  Start/game-over screens use the same gesture with just one
  destination: tilt either side and hold.

Keyboard/mouse as test controls:
  A/D or Left/Right arrows -> Ship movement
  Mouse -> Aim (absolute; only used as a fallback when no
           controller 2 is connected)
  1 / 2 / 3 -> Pick a menu option / an upgrade instantly
  Enter / Space -> Confirm on the start screen
  R -> Return to the main menu after Game Over

FILE LAYOUT:
  game_state.py -> shared engine state (display/audio setup,
                   constants, assets, and all mutable runtime
                   game state), imported everywhere as `gs`
  bullet.py / asteroid.py / particle.py / ship.py
                -> the entity classes
  upgrades.py   -> upgrade definitions + level-up flow
  ui.py         -> the start/weapon-select/upgrade-card screens
  game.py       -> this file: wiring + the main loop
"""

import math
import random
import pygame

import game_state as gs

gs.init()

# These build their icon surfaces via gs.load_icon(), which needs the
# display to already exist - so they're imported only after gs.init().
import upgrades  # noqa: E402
import ui  # noqa: E402
from particle import Particle  # noqa: E402
import boss  # noqa: E402
import alien  # noqa: E402

gs.play_music("menu")

# ---------------- Main loop ----------------

running = True

while running:
    dt = min(gs.clock.tick(gs.FPS) / 1000.0, 0.033)
    gs.update_stars(dt)

    gs.jump_flash_timer = max(0.0, gs.jump_flash_timer - dt)

    # ---------- Events ----------
    for event in pygame.event.get():

        if event.type == pygame.JOYBUTTONDOWN and event.button == gs.JUMP_BUTTON:
            gs.register_jump(event)
        if gs.TEST_JUMP_ONLY:
            continue   # don't let a jump also confirm menus / pick upgrades

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.JOYBUTTONDOWN:
            if gs.state == gs.STATE_START:
                gs.state = gs.STATE_WEAPON_SELECT
                gs.reset_menu_nav()
                gs.play_music("weapon_select")
            elif gs.state == gs.STATE_WEAPON_SELECT:
                if event.button == 0:
                    gs.choose_weapon("laser")
                elif event.button == 1:
                    gs.choose_weapon("bullets")
            elif gs.state == gs.STATE_PLAYING:
                if gs.leveling_up:
                    if event.button in (0, 1, 2):
                        upgrades.choose_upgrade(event.button)
            elif gs.state == gs.STATE_GAME_OVER:
                if event.button == 0:
                    gs.state = gs.STATE_START
                    gs.reset_menu_nav()
                    gs.play_music("menu")

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                running = False

            if gs.state == gs.STATE_START:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    gs.state = gs.STATE_WEAPON_SELECT
                    gs.reset_menu_nav()
                    gs.play_music("weapon_select")

            elif gs.state == gs.STATE_WEAPON_SELECT:
                if event.key == pygame.K_1:
                    gs.choose_weapon("laser")
                elif event.key == pygame.K_2:
                    gs.choose_weapon("bullets")

            elif gs.state == gs.STATE_PLAYING:
                if gs.leveling_up:
                    if event.key == pygame.K_1:
                        upgrades.choose_upgrade(0)
                    elif event.key == pygame.K_2:
                        upgrades.choose_upgrade(1)
                    elif event.key == pygame.K_3:
                        upgrades.choose_upgrade(2)

            elif gs.state == gs.STATE_GAME_OVER:
                if event.key == pygame.K_r:
                    gs.state = gs.STATE_START
                    gs.reset_menu_nav()
                    gs.play_music("menu")

    # ---------- Update ----------
    if gs.state == gs.STATE_START:
        direction = gs.get_menu_direction()
        hover, gs.menu_progress, confirmed = gs.update_menu_dwell(direction, {"left", "right"}, dt)
        if confirmed:
            gs.state = gs.STATE_WEAPON_SELECT
            gs.reset_menu_nav()
            gs.play_music("weapon_select")

    elif gs.state == gs.STATE_WEAPON_SELECT:
        direction = gs.get_menu_direction()
        hover, gs.menu_progress, confirmed = gs.update_menu_dwell(direction, {"left", "right"}, dt)
        gs.menu_hover = 0 if hover == "left" else (1 if hover == "right" else -1)
        if confirmed:
            gs.choose_weapon("laser" if hover == "left" else "bullets")

    elif gs.state == gs.STATE_GAME_OVER:
        gs.game_over_timer += dt
        direction = gs.get_menu_direction()
        hover, gs.menu_progress, confirmed = gs.update_menu_dwell(direction, {"left", "right"}, dt)
        if confirmed or gs.game_over_timer >= gs.GAME_OVER_AUTO_EXIT_TIME:
            gs.state = gs.STATE_START
            gs.reset_menu_nav()
            gs.play_music("menu")

    elif gs.state == gs.STATE_PLAYING and gs.leveling_up:
        direction = gs.get_menu_direction()
        hover, gs.menu_progress, confirmed = gs.update_menu_dwell(direction, {"left", "right"}, dt)
        gs.menu_hover = 0 if hover == "left" else (1 if hover == "right" else -1)
        if confirmed:
            upgrades.choose_upgrade(gs.menu_hover)

    elif gs.state == gs.STATE_PLAYING and not gs.leveling_up:

        gs.elapsed_time += dt
        gs.ship.update(dt)

        if gs.weapon_type == "bullets":
            gs.ship.shoot()

        # Difficulty: wave from score, PLUS a continuous ramp from
        # player level and time survived, so things keep getting
        # harder and faster the longer a run goes on.
        gs.wave = 1 + gs.score // 400

        boss.maybe_spawn_boss()
        alien.update(dt)

        gs.spawn_timer -= dt
        if gs.spawn_timer <= 0:
            gs.spawn_timer = max(
                0.15,
                0.9 - gs.wave * 0.035 - gs.level * 0.012 - gs.elapsed_time * 0.0025
            )
            if not (boss.BOSS_BLOCKS_NORMAL_SPAWNS and boss.is_boss_active()):
                gs.spawn_asteroid()

        for bullet in gs.bullets:
            bullet.update(dt)
        alien.draw_projectiles()
        for asteroid in gs.asteroids:
            asteroid.update(dt)
        for particle in gs.particles:
            particle.update(dt)

        # ---------- Continuous laser vs asteroids ----------
        if gs.weapon_type == "laser":
            dx, dy = math.cos(gs.ship.angle), math.sin(gs.ship.angle)
            hits = []

            for asteroid in gs.asteroids:
                ax = asteroid.x - gs.ship.x
                ay = asteroid.y - gs.ship.y
                t = ax * dx + ay * dy
                perp_dist = abs(ax * dy - ay * dx)
                effective_radius = asteroid.radius + gs.LASER_BEAM_BONUS

                if perp_dist <= effective_radius:
                    half_chord = math.sqrt(max(0.0, effective_radius ** 2 - perp_dist ** 2))
                    entry_t = t - half_chord
                    exit_t = t + half_chord
                    if exit_t >= 0:
                        hits.append((max(0.0, entry_t), exit_t, asteroid))

            hits.sort(key=lambda h: h[0])
            max_pierces = gs.LASER_PIERCE + 1
            damaged_this_frame = hits[:max_pierces]

            if len(hits) > max_pierces:
                beam_length = hits[max_pierces][0]
            elif hits:
                beam_length = hits[-1][1]
            else:
                beam_length = gs.LASER_MAX_LENGTH

            gs.laser_end = (gs.ship.x + dx * beam_length, gs.ship.y + dy * beam_length)

            for entry_t, exit_t, asteroid in damaged_this_frame:
                asteroid.health -= gs.LASER_DPS * dt

                if random.random() < 0.4:
                    hit_x = gs.ship.x + dx * entry_t
                    hit_y = gs.ship.y + dy * entry_t
                    gs.particles.append(Particle(hit_x, hit_y))

                if asteroid.health <= 0:
                    if asteroid in gs.asteroids:
                        gs.asteroids.remove(asteroid)
                    gs.destroy_asteroid(asteroid)

        # ---------- Bullets vs asteroids ----------
        if gs.weapon_type == "bullets":
            for asteroid in gs.asteroids[:]:
                for bullet in gs.bullets[:]:

                    if gs.circle_collision(
                        asteroid.x, asteroid.y, asteroid.radius,
                        bullet.x, bullet.y, 5
                    ):
                        gs.explosion(bullet.x, bullet.y, 6)
                        asteroid.health -= gs.BULLET_DAMAGE

                        if bullet.pierces_left > 0:
                            bullet.pierces_left -= 1
                        else:
                            if bullet in gs.bullets:
                                gs.bullets.remove(bullet)

                        if asteroid.health <= 0:
                            if asteroid in gs.asteroids:
                                gs.asteroids.remove(asteroid)
                            gs.destroy_asteroid(asteroid)

                        break

        # ---------- Asteroids hit the ship ----------
        if gs.ship.invulnerable <= 0:
            for asteroid in gs.asteroids[:]:
                if gs.circle_collision(
                    gs.ship.x, gs.ship.y, 18,
                    asteroid.x, asteroid.y, asteroid.radius
                ):
                    if not getattr(asteroid, "is_boss", False):
                        gs.asteroids.remove(asteroid)

                    gs.ship.hp -= 1
                    gs.ship.invulnerable = gs.HIT_INVULN_TIME
                    gs.explosion(gs.ship.x, gs.ship.y, 28)
                    gs.trigger_shake(8, 0.25)

                    # >>> SOUND HOOK: play your "ship got hit" sound effect
                    gs.sfx_hit.play()

                    if gs.ship.hp <= 0:
                        gs.trigger_shake(16, 0.5)
                        gs.new_high_score = (not gs.leaderboard) or (gs.score > gs.leaderboard[0]["score"])
                        gs.add_leaderboard_entry(gs.score, gs.elapsed_time)
                        gs.state = gs.STATE_GAME_OVER
                        gs.game_over_timer = 0.0
                        gs.reset_menu_nav()
                        gs.play_music("menu")

                        # >>> SOUND HOOK: play your game-over sound effect
                        #     here, e.g. sfx_gameover.play()
        
        for asteroid in gs.asteroids[:]:
            if getattr(asteroid, "is_boss", False) and asteroid.y >= gs.HEIGHT \
                    and gs.state == gs.STATE_PLAYING:
                boss.on_escape(asteroid)

        # Asteroids leaving the screen
        for asteroid in gs.asteroids[:]:
            if asteroid.y > gs.HEIGHT + 100:
                gs.asteroids.remove(asteroid)

        # Clean up bullets & particles
        gs.bullets[:] = [
            b for b in gs.bullets
            if b.life > 0
            and -50 < b.x < gs.WIDTH + 50
            and -50 < b.y < gs.HEIGHT + 50
        ]
        gs.particles[:] = [p for p in gs.particles if p.life > 0]

        if gs.pending_level_ups > 0:
            upgrades.start_level_up_selection()

    # ---------- Draw ----------
    gs.screen.blit(gs.BACKGROUND, (0, 0))
    gs.draw_stars()

    if gs.state == gs.STATE_START:
        ui.draw_start_screen()

    elif gs.state == gs.STATE_WEAPON_SELECT:
        ui.draw_weapon_select_screen()

    else:  # STATE_PLAYING or STATE_GAME_OVER: draw the game world
        for particle in gs.particles:
            particle.draw()
        for asteroid in gs.asteroids:
            asteroid.draw()
        for bullet in gs.bullets:
            bullet.draw()

        if gs.weapon_type == "laser" and gs.state == gs.STATE_PLAYING:
            nose = (
                gs.ship.x + math.cos(gs.ship.angle) * 27,
                gs.ship.y + math.sin(gs.ship.angle) * 27
            )
            # >>> ART HOOK: replace these two lines with your own beam
            #     effect (e.g. a repeating/stretched laser texture drawn
            #     between `nose` and `gs.laser_end`).
            # Line thickness scales with LASER_BEAM_BONUS - the same stat
            # that widens the actual hit area (see effective_radius above)
            # - so "Wide Beam" upgrades visibly get you a thicker beam.
            beam_outer_width = max(2, int(6 + gs.LASER_BEAM_BONUS * 0.6))
            beam_inner_width = max(1, int(2 + gs.LASER_BEAM_BONUS * 0.2))
            pygame.draw.line(gs.screen, (120, 60, 255), nose, gs.laser_end, beam_outer_width)
            pygame.draw.line(gs.screen, (230, 190, 255), nose, gs.laser_end, beam_inner_width)

        gs.ship.draw()

        # ---------- HUD ----------
        hud_rect = pygame.Rect(10, 10, gs.WIDTH - 20, 78)
        gs.draw_panel(hud_rect)

        gs.draw_text(f"HP {gs.ship.hp}", (28, 20))
        gs.draw_text(f"SCORE {gs.score}", (gs.WIDTH - 170, 20))
        gs.draw_text(f"WAVE {gs.wave}", (gs.WIDTH // 2, 20), center=True)
        gs.draw_text(f"LEVEL {gs.level}", (28, 52), gs.FONT, (170, 230, 170))

        weapon_label = gs.WEAPON_INFO[gs.weapon_type]["name"] if gs.weapon_type else ""
        gs.draw_text(f"Weapon: {weapon_label}", (gs.WIDTH // 2, 52), gs.FONT, (170, 200, 255), center=True)

        # XP bar
        xp_ratio = gs.clamp(gs.xp / gs.xp_to_next, 0, 1)
        pygame.draw.rect(gs.screen, (40, 45, 60), (0, 0, gs.WIDTH, 6))
        pygame.draw.rect(gs.screen, (120, 230, 170), (0, 0, gs.WIDTH * xp_ratio, 6))

        boss.draw_boss_ui()

        status_rect = pygame.Rect(10, gs.HEIGHT - 76, 330, 66)
        gs.draw_panel(status_rect)
        controller_1 = "Controller 1: MOVE" if gs.move_pad else "Controller 1: not found"
        controller_2 = "Controller 2: ROTATE AIM" if gs.aim_pad else "Controller 2: not found"
        gs.draw_text(controller_1, (24, gs.HEIGHT - 66), gs.SMALL_FONT, (150, 190, 220))
        gs.draw_text(controller_2, (24, gs.HEIGHT - 38), gs.SMALL_FONT, (150, 190, 220))

        if len(gs.joysticks) < 2 and gs.state == gs.STATE_PLAYING:
            gs.draw_text(
                "Fewer than 2 controllers detected - keyboard/mouse still work.",
                (gs.WIDTH // 2, 105), gs.SMALL_FONT, (255, 210, 80), center=True
            )

        if gs.state == gs.STATE_PLAYING and gs.leveling_up:
            key_labels = [f"[{i + 1}]" for i in range(len(gs.upgrade_choices))]
            ui.draw_upgrade_cards(gs.upgrade_choices, "LEVEL UP!",
                                   "Tilt BOTH controllers to the same side and hold  (or press 1 / 2)",
                                   key_labels, hover_index=gs.menu_hover, progress=gs.menu_progress)

        if gs.state == gs.STATE_GAME_OVER:
            overlay = pygame.Surface((gs.WIDTH, gs.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            gs.screen.blit(overlay, (0, 0))

            gs.draw_text("GAME OVER", (gs.WIDTH // 2, gs.HEIGHT // 2 - 90), gs.BIG_FONT, (255, 100, 100), center=True)

            if gs.new_high_score:
                gs.draw_text("NEW HIGH SCORE!", (gs.WIDTH // 2, gs.HEIGHT // 2 - 35), gs.FONT, (255, 225, 120), center=True)

            gs.draw_text(f"Score: {gs.score}   Level: {gs.level}   Time: {gs.format_time(gs.elapsed_time)}",
                         (gs.WIDTH // 2, gs.HEIGHT // 2 + 10), gs.FONT, center=True)
            gs.draw_text(f"Best Score: {gs.high_score}", (gs.WIDTH // 2, gs.HEIGHT // 2 + 42), gs.FONT, (200, 210, 230), center=True)
            gs.draw_text("Tilt controller(s) to either side and hold  -  or press R",
                         (gs.WIDTH // 2, gs.HEIGHT // 2 + 90), gs.FONT, (180, 220, 255), center=True)

            seconds_left = max(0, math.ceil(gs.GAME_OVER_AUTO_EXIT_TIME - gs.game_over_timer))
            gs.draw_text(f"Returning to menu in {seconds_left}s...",
                         (gs.WIDTH // 2, gs.HEIGHT // 2 + 122), gs.SMALL_FONT, (140, 160, 190), center=True)

            if gs.menu_progress > 0:
                bar_w, bar_h = 260, 10
                bar_x = gs.WIDTH // 2 - bar_w // 2
                bar_y = gs.HEIGHT // 2 + 148
                pygame.draw.rect(gs.screen, (50, 55, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=0)
                pygame.draw.rect(gs.screen, (255, 225, 120), (bar_x, bar_y, bar_w * gs.menu_progress, bar_h), border_radius=0)

    # ---------- Present (scaled to the real screen, with shake) ----------
    gs.draw_jump_debug()
    gs.present(dt)

pygame.quit()
