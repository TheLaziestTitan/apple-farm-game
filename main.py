import os
import random
import sqlite3
import sys

import pygame

WIDTH, HEIGHT = 1050, 591
PLAYER_SPEED = 10
MAX_MISSED = 5

screen = pygame.display.set_mode((WIDTH, HEIGHT))


def load_apple_data():
    conn = sqlite3.connect('apple_farm.db')
    cursor = conn.cursor()
    cursor.execute("SELECT apple_id, image_path, points, fall_speed, spawn_rate, music_path FROM apples")
    apples_data = cursor.fetchall()
    conn.close()

    cleaned_data = []
    for data in apples_data:
        apple_id = int(data[0])
        filename = data[1].split(' ', 1)[-1].strip()
        image_path = os.path.join("assets", filename)
        points = int(data[2])
        speed = {"slow": 3.5, "medium": 4, "fast": 6}.get(data[3].lower(), 4)
        spawn_rate = float(data[4])

        sound_filename = data[5].strip() if data[5] else ".wav"
        sound_path = os.path.join("assets", sound_filename)

        cleaned_data.append((apple_id, image_path, points, speed, spawn_rate, sound_path))
    return cleaned_data


APPLE_DATA = load_apple_data()
SPAWN_WEIGHTS = [data[4] for data in APPLE_DATA]


class Player(pygame.sprite.Sprite):

    def __init__(self):
        super().__init__()
        try:
            self.spritesheet = pygame.image.load(os.path.join('assets', 'farmer2.png')).convert_alpha()
        except FileNotFoundError:
            self.spritesheet = pygame.Surface((400, 150))
            self.spritesheet.fill((0, 255, 0))

        self.frame_width = 210
        self.frame_height = 250
        total_frames = self.spritesheet.get_width() // self.frame_width
        self.frames_right = [
            self.spritesheet.subsurface(pygame.Rect(i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(min(5, total_frames))
        ]
        self.frames_left = [pygame.transform.flip(frame, True, False) for frame in self.frames_right]

        self.current_frame = 0
        self.animation_speed = 0.18
        self.last_update = pygame.time.get_ticks()
        self.direction = 'right'
        self.image = self.frames_right[self.current_frame]
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 150))

    def catch_apple(self, apple):
        apple.catch_sound.play()
        return apple.points

    def update(self, keys):
        moving = False
        if keys[pygame.K_LEFT]:
            self.rect.x -= PLAYER_SPEED
            self.direction = 'right'
            moving = True
        if keys[pygame.K_RIGHT]:
            self.rect.x += PLAYER_SPEED
            self.direction = 'left'
            moving = True

        now = pygame.time.get_ticks()
        if moving:
            if now - self.last_update > self.animation_speed * 1000:
                self.last_update = now
                self.current_frame = (self.current_frame + 1) % len(self.frames_right)
                self.image = self.frames_right[self.current_frame] if self.direction == 'right' else self.frames_left[
                    self.current_frame]
        else:
            self.current_frame = 0
            self.image = self.frames_right[0] if self.direction == 'right' else self.frames_left[0]

        self.rect.clamp_ip(screen.get_rect())


class Apple(pygame.sprite.Sprite):
    def __init__(self, difficulty):
        super().__init__()
        self.type_data = random.choices(APPLE_DATA, weights=SPAWN_WEIGHTS, k=1)[0]
        self.apple_id = self.type_data[0]
        speed_multiplier = 1.5 if difficulty == "hard" else 1.0
        self.fall_speed = self.type_data[3] * speed_multiplier

        try:
            self.image = pygame.image.load(self.type_data[1]).convert_alpha()
            self.image = pygame.transform.scale(self.image, (60, 60))
        except:
            self.image = pygame.Surface((50, 50))
            self.image.fill((200, 0, 0))

        self.rect = self.image.get_rect(topleft=(random.randint(0, WIDTH - 50), -20))
        self.points = self.type_data[2]
        self.catch_sound = pygame.mixer.Sound(self.type_data[5])

    def update(self):
        self.rect.y += self.fall_speed
        if self.rect.top > HEIGHT:
            self.kill()
            return self.apple_id == 1
        return False


class Button(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, action):
        super().__init__()
        self.load_images(image_path)
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        self.action = action
        self.hovered = False

    def load_images(self, image_path):
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()

            if "info_icon" in image_path:
                self.original_image = pygame.transform.scale(self.original_image, (50, 50))

            base, ext = os.path.splitext(image_path)
            hover_path = f"{base}2{ext}"

            if os.path.exists(hover_path):
                self.hover_image = pygame.image.load(hover_path).convert_alpha()
                if "info_icon" in image_path:
                    self.hover_image = pygame.transform.scale(self.hover_image, (40, 40))
            else:
                self.hover_image = self.original_image.copy()

        except:
            size = (200, 50) if "btn" in image_path else (40, 40)
            color = (0, 128, 0) if "easy" in image_path else \
                (128, 0, 0) if "hard" in image_path else \
                    (255, 200, 0) if "info" in image_path else \
                        (255, 0, 0)

            self.original_image = pygame.Surface(size)
            self.original_image.fill(color)
            self.hover_image = self.original_image.copy()
            self.hover_image.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)

    def update(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            self.image = self.hover_image if self.hovered else self.original_image

        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            self.action()


class InfoWindow:
    def __init__(self):
        self.show_info = False
        self.init_resources()

    def init_resources(self):
        try:
            self.background = pygame.image.load(os.path.join('assets', 'menu_info.png')).convert_alpha()
            self.background = pygame.transform.scale(self.background, (605, 478))
        except:
            self.background = pygame.Surface((605, 478), pygame.SRCALPHA)
            self.background.fill((30, 30, 30, 220))

        self.close_btn = Button(
            x=WIDTH // 2 + 200,
            y=HEIGHT // 2 - 150,
            image_path=os.path.join('assets', 'close_icon.png'),
            action=self.toggle_info
        )

        self.rules_text = [
            "Правила игры:",
            "1. Ловите яблоки, падающие сверху.",
            "2. Управляйте фермером стрелками ВЛЕВО и ВПРАВО.",
            "3. Не пропустите более 5 красных яблок.",
            "4. Нажмите R, чтобы перезапустить игру.",
            "P.S. Красное яблоко 2 очка",
            "     Зелёное яблоко 6 очков",
            "     Золотое яблоко 10 очков",
            "     Алмазное яблоко 20 очков",
            "     Гнилое яблоко(серое) -10 очков"
        ]

    def toggle_info(self):
        self.show_info = not self.show_info

    def draw(self, screen):
        if self.show_info:
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 180))
            screen.blit(dim, (0, 0))

            screen.blit(self.background, (WIDTH // 2 - 300, HEIGHT // 2 - 200))

            font = pygame.font.Font(None, 30)
            text_y = HEIGHT // 2 - 120
            for line in self.rules_text:
                text_surface = font.render(line, True, (0, 0, 0))
                text_x = WIDTH // 2 - text_surface.get_width() // 2
                screen.blit(text_surface, (text_x, text_y))
                text_y += 35

            screen.blit(self.close_btn.image, self.close_btn.rect)

    def handle_events(self, event):
        if self.show_info:
            self.close_btn.update(event)


def start_screen():
    pygame.mixer.init()
    pygame.mixer.music.load(os.path.join("assets", "music_1.ogg"))
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)

    if not os.path.exists('assets'):
        os.makedirs('assets')

    difficulty = [None]
    info_window = InfoWindow()

    try:
        fon = pygame.transform.scale(
            pygame.image.load(os.path.join('assets', 'menu.png')),
            (WIDTH, HEIGHT)
        )
    except:
        fon = pygame.Surface((WIDTH, HEIGHT))
        fon.fill((100, 150, 200))
        font = pygame.font.Font(None, 60)
        text = font.render("Apple Catcher Game", True, (255, 255, 255))
        fon.blit(text, (WIDTH // 2 - text.get_width() // 2, 100))

    buttons = pygame.sprite.Group()

    buttons.add(Button(
        x=WIDTH - 40,
        y=40,
        image_path=os.path.join('assets', 'info_icon.png'),
        action=info_window.toggle_info
    ))

    buttons.add(Button(
        x=WIDTH // 2 - 150,
        y=HEIGHT // 2 + 90,
        image_path=os.path.join('assets', 'easy_btn.png'),
        action=lambda: difficulty.__setitem__(0, "easy")
    ))

    buttons.add(Button(
        x=WIDTH // 2 + 150,
        y=HEIGHT // 2 + 90,
        image_path=os.path.join('assets', 'hard_btn.png'),
        action=lambda: difficulty.__setitem__(0, "hard")
    ))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()

            info_window.handle_events(event)

            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                for btn in buttons:
                    btn.update(event)

        screen.blit(fon, (0, 0))
        buttons.draw(screen)
        info_window.draw(screen)
        pygame.display.flip()

        if difficulty[0] is not None:
            return difficulty[0]


class VictoryWindow:
    def __init__(self):
        self.show_victory = False
        self.video_frames = []
        self.current_frame = 0
        self.frame_rate = 20
        self.last_update = pygame.time.get_ticks()
        self.victory_sound = None
        self.show_background = False
        self.animation_started = False
        self.video_finished = False
        self.music_stopped = False
        self.init_resources()

    def init_resources(self):
        try:
            self.background = pygame.image.load(os.path.join('assets', 'victory_bg.png')).convert_alpha()
            self.background = pygame.transform.scale(self.background, (WIDTH, HEIGHT))
        except:
            self.background = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.background.fill((30, 220, 30, 220))

        frame_index = 1
        while True:
            frame_path = os.path.join('assets', 'victory_frames', f'ezgif-frame-{frame_index:03d}.png')
            if not os.path.exists(frame_path):
                break
            frame = pygame.image.load(frame_path).convert_alpha()
            self.video_frames.append(frame)
            frame_index += 1

        try:
            self.victory_sound = pygame.mixer.Sound(os.path.join('assets', 'victory_sound.wav'))
        except:
            self.victory_sound = pygame.mixer.Sound(buffer=b'')

    def play_video(self):
        self.show_background = True
        self.animation_started = False
        self.video_finished = False
        self.current_frame = 0
        self.music_stopped = False

    def update(self, keys):
        if self.show_background and keys[pygame.K_r]:
            self.show_background = False
            self.animation_started = True
            self.victory_sound.play()
            pygame.mixer.music.fadeout(1000)
            self.music_stopped = True

        if self.animation_started:
            now = pygame.time.get_ticks()
            if now - self.last_update > 1000 // self.frame_rate:
                self.last_update = now
                if self.current_frame < len(self.video_frames) - 1:
                    self.current_frame += 1
                else:
                    self.video_finished = True

    def draw(self, screen):
        if self.show_victory:
            if self.show_background:
                screen.blit(self.background, (0, 0))
            elif self.animation_started:
                if self.video_frames:
                    current_frame = self.video_frames[self.current_frame]
                    screen.blit(current_frame, (
                        WIDTH // 2 - current_frame.get_width() // 2,
                        HEIGHT // 2 - current_frame.get_height() // 2
                    ))
                if self.video_finished:
                    font = pygame.font.Font(None, 74)
                    text = font.render("НАЖМИТЕ R ДЛЯ ВОЗВРАТА В МЕНЮ", True, (255, 215, 0))
                    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 100))


class Game:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.background = self.load_background()
        self.end_image = self.load_end_image()
        self.clock = pygame.time.Clock()
        self.info_system = InfoWindow()
        self.victory_window = VictoryWindow()
        self.ui_elements = pygame.sprite.Group()
        self.reset()
        pygame.mixer.music.set_volume(0.2)

    def load_background(self):
        try:
            path = os.path.join('assets', 'farm_bg.png')
            image = pygame.image.load(path).convert()
            return pygame.transform.scale(image, (WIDTH, HEIGHT))
        except:
            return pygame.Surface((WIDTH, HEIGHT)).convert()

    def load_end_image(self):
        try:
            path = os.path.join('assets', 'menu_end.png')
            image = pygame.image.load(path).convert()
            return pygame.transform.scale(image, (WIDTH, HEIGHT))
        except:
            return pygame.Surface((WIDTH, HEIGHT)).convert()

    def show_text(self, text, size, y):
        font = pygame.font.Font(None, size)
        text_surface = font.render(text, True, (82, 30, 22))
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, y))

    def reset(self):
        self.player = Player()
        self.apples = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.score = 0
        self.missed = 0
        self.game_state = "running"
        self.victory_window.show_victory = False
        self.victory_window.video_played = False
        self.victory_window.video_finished = False

    def main_loop(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    for btn in self.ui_elements:
                        btn.update(event)
                    self.info_system.handle_events(event)

            keys = pygame.key.get_pressed()

            if self.game_state == "running":
                self.player.update(keys)

                if random.random() < 0.02:
                    apple = Apple(self.difficulty)
                    self.apples.add(apple)
                    self.all_sprites.add(apple)

                self.missed += sum(apple.update() for apple in self.apples)

                hits = pygame.sprite.spritecollide(self.player, self.apples, True)
                for apple in hits:
                    self.score += apple.points
                    self.player.catch_apple(apple)

                if self.missed >= MAX_MISSED:
                    self.game_state = "game_over"

                if self.score >= 100:
                    self.game_state = "victory"
                    self.victory_window.show_victory = True
                    self.victory_window.play_video()

            elif self.game_state == "victory":
                self.victory_window.update(keys)
                if self.victory_window.video_finished and keys[pygame.K_r]:
                    running = False

            elif self.game_state == "game_over":
                if keys[pygame.K_r]:
                    running = False

            screen.blit(self.background, (0, 0))
            if self.game_state == "running":
                self.all_sprites.draw(screen)
                self.show_text(f"Счет: {self.score}", 40, 10)
                self.show_text(f"Пропущено: {self.missed}/{MAX_MISSED}", 40, 50)
            elif self.game_state == "victory":
                self.victory_window.draw(screen)
            elif self.game_state == "game_over":
                screen.blit(self.end_image, (0, 0))
                self.show_text(f"            {self.score}", 61, HEIGHT // 2 + 70)

            self.ui_elements.draw(screen)
            self.info_system.draw(screen)
            pygame.display.flip()
            self.clock.tick(60)


def terminate():
    pygame.quit()
    sys.exit()


def main():
    pygame.init()
    pygame.display.set_caption('Яблочная ферма')
    while True:
        difficulty = start_screen()
        game = Game(difficulty)
        game.main_loop()


if __name__ == "__main__":
    main()
