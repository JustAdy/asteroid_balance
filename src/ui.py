"""
Non-gameplay screens: the weapon-select / level-up card layout, the
start screen, and the leaderboard panel. All read from game_state
(imported as gs) and draw onto gs.screen.
"""

import math
import pygame

import game_state as gs


def draw_upgrade_cards(cards, title, subtitle, key_labels, hover_index=-1, progress=0.0):
    screen = gs.screen

    overlay = pygame.Surface((gs.WIDTH, gs.HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 5, 15, 200))
    screen.blit(overlay, (0, 0))

    title_y = gs.HEIGHT // 2 - 170
    subtitle_y = gs.HEIGHT // 2 - 110
    gs.draw_text(title, (gs.WIDTH // 2, title_y), gs.BIG_FONT, (255, 225, 120), center=True)
    gs.draw_text(subtitle, (gs.WIDTH // 2, subtitle_y), gs.FONT, (200, 210, 230), center=True)

    # Cards scale up a bit on big/high-res full-screen monitors (never
    # smaller than the original design). Card height is computed from the
    # ACTUAL wrapped text for each card below, so nothing is ever clipped
    # or spills out of the box; the card block is anchored a fixed gap
    # below the subtitle so enlarged cards can never cover it.
    card_scale = max(1.0, gs.HEIGHT / 900)
    card_w = int(300 * card_scale)
    gap = int(30 * card_scale)
    padding = int(18 * card_scale)
    section_gap = int(10 * card_scale)
    icon_size = int(44 * card_scale)
    key_line_h = gs.FONT.get_linesize()
    name_line_h = gs.FONT.get_linesize()
    desc_line_h = gs.SMALL_FONT.get_linesize()

    def wrap(text, font):
        words = text.split(" ")
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if font.size(test)[0] > card_w - padding * 2:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    # Pre-wrap every card's text so we know exactly how tall each one
    # needs to be, then use the tallest as the shared card height.
    per_card = []
    for card in cards:
        name_lines = wrap(card["name"], gs.FONT)
        desc_lines = wrap(card["desc"], gs.SMALL_FONT)
        needed_h = (
            padding + key_line_h + section_gap + icon_size + section_gap
            + len(name_lines) * name_line_h + section_gap
            + len(desc_lines) * desc_line_h + padding
        )
        per_card.append((name_lines, desc_lines, needed_h))

    card_h = max(h for _, _, h in per_card)
    total_w = card_w * len(cards) + gap * (len(cards) - 1)
    start_x = gs.WIDTH // 2 - total_w // 2
    card_y = subtitle_y + gs.FONT.get_linesize() // 2 + int(30 * card_scale)

    for i, card in enumerate(cards):
        name_lines, desc_lines, _ = per_card[i]
        card_x = start_x + i * (card_w + gap)
        rect = pygame.Rect(card_x, card_y, card_w, card_h)
        is_hovered = (i == hover_index)

        pygame.draw.rect(screen, (34, 40, 60) if is_hovered else (25, 30, 48), rect, border_radius=0)
        border_color = (255, 225, 120) if is_hovered else (110, 160, 255)
        pygame.draw.rect(screen, border_color, rect, 4 if is_hovered else 3, border_radius=0)

        cx = rect.centerx
        cursor = rect.top + padding

        key_surf = gs.FONT.render(key_labels[i], True, (255, 225, 120))
        screen.blit(key_surf, key_surf.get_rect(midtop=(cx, cursor)))
        cursor += key_line_h + section_gap

        # >>> ART HOOK: card icon. If card["icon"] was loaded successfully
        # (see gs.load_icon() / assets/icons/...), draw it here; otherwise
        # fall back to a plain placeholder square so the layout still
        # looks intentional with no art installed.
        icon = card.get("icon")
        if icon:
            icon_scaled = pygame.transform.smoothscale(icon, (icon_size, icon_size))
            screen.blit(icon_scaled, icon_scaled.get_rect(midtop=(cx, cursor)))
        else:
            placeholder_rect = pygame.Rect(0, 0, icon_size, icon_size)
            placeholder_rect.midtop = (cx, cursor)
            pygame.draw.rect(screen, (45, 52, 78), placeholder_rect, border_radius=0)
            pygame.draw.rect(screen, (90, 110, 160), placeholder_rect, 2, border_radius=0)
        cursor += icon_size + section_gap

        for line in name_lines:
            surf = gs.FONT.render(line, True, (235, 240, 255))
            screen.blit(surf, surf.get_rect(midtop=(cx, cursor)))
            cursor += name_line_h
        cursor += section_gap

        for line in desc_lines:
            surf = gs.SMALL_FONT.render(line, True, (170, 190, 220))
            screen.blit(surf, surf.get_rect(midtop=(cx, cursor)))
            cursor += desc_line_h

        if is_hovered and progress > 0:
            bar_w = card_w - 30
            bar_x = rect.left + 15
            bar_y = rect.bottom - int(16 * card_scale)
            pygame.draw.rect(screen, (50, 55, 70), (bar_x, bar_y, bar_w, 8), border_radius=0)
            pygame.draw.rect(screen, (255, 225, 120), (bar_x, bar_y, bar_w * progress, 8), border_radius=0)


def draw_start_screen():
    screen = gs.screen

    gs.draw_text("ASTEROID BALANCE", (gs.WIDTH // 2 + 3, gs.HEIGHT // 2 - 177), gs.TITLE_FONT, (35, 55, 110), center=True)
    gs.draw_text("ASTEROID BALANCE", (gs.WIDTH // 2, gs.HEIGHT // 2 - 180), gs.TITLE_FONT, (150, 200, 255), center=True)
    gs.draw_text("2-Controller Edition", (gs.WIDTH // 2, gs.HEIGHT // 2 - 118), gs.FONT, (160, 180, 210), center=True)

    pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.004)
    prompt_color = (int(200 * pulse) + 55, int(210 * pulse) + 45, 255)
    gs.draw_text("Tilt controller(s) to either side and hold  -  or press ENTER / SPACE",
                 (gs.WIDTH // 2, gs.HEIGHT // 2 - 60), gs.FONT, prompt_color, center=True)

    if gs.menu_progress > 0:
        bar_w, bar_h = 260, 10
        bar_x = gs.WIDTH // 2 - bar_w // 2
        bar_y = gs.HEIGHT // 2 - 30
        pygame.draw.rect(screen, (50, 55, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=0)
        pygame.draw.rect(screen, (255, 225, 120), (bar_x, bar_y, bar_w * gs.menu_progress, bar_h), border_radius=0)

    lines = [
        "Controller 1: move left/right   |   Controller 2: rotate aim",
        "Keyboard: A/D or arrows to move, mouse to aim",
        "Escape to quit",
    ]
    for i, line in enumerate(lines):
        gs.draw_text(line, (gs.WIDTH // 2 - 130, gs.HEIGHT - 90 + i * 26), gs.SMALL_FONT, (150, 165, 195), center=True)

    draw_leaderboard_panel()


def draw_leaderboard_panel():
    screen = gs.screen

    panel_w = 300
    panel_h = 50 + gs.LEADERBOARD_SIZE * 30
    panel_x = gs.WIDTH - panel_w - 20
    panel_y = gs.HEIGHT // 2 - panel_h // 2
    rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    gs.draw_panel(rect)
    gs.draw_text("TOP RUNS", (rect.centerx, rect.top + 22), gs.FONT, (255, 225, 120), center=True)

    if not gs.leaderboard:
        gs.draw_text("No runs yet -", (rect.centerx, rect.top + 58), gs.SMALL_FONT, (170, 190, 220), center=True)
        gs.draw_text("be the first!", (rect.centerx, rect.top + 80), gs.SMALL_FONT, (170, 190, 220), center=True)
        return

    for i, entry in enumerate(gs.leaderboard):
        y = rect.top + 48 + i * 30
        color = (255, 225, 120) if i == 0 else (200, 210, 230)

        gs.draw_text(f"{i + 1}.", (rect.left + 16, y), gs.SMALL_FONT, color)
        gs.draw_text(f"{entry['score']} pts", (rect.left + 46, y), gs.SMALL_FONT, color)

        time_str = gs.format_time(entry["time"])
        time_surf = gs.SMALL_FONT.render(time_str, True, color)
        screen.blit(time_surf, (rect.right - 16 - time_surf.get_width(), y))


def draw_weapon_select_screen():
    cards = [gs.WEAPON_INFO["laser"], gs.WEAPON_INFO["bullets"]]
    draw_upgrade_cards(cards, "CHOOSE YOUR WEAPON",
                        "Tilt BOTH controllers left = Laser, right = Blaster, and hold  (or press 1 / 2)",
                        ["[1]", "[2]"], hover_index=gs.menu_hover, progress=gs.menu_progress)
