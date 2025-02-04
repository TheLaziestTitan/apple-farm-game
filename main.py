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
    cursor.execute("SELECT apple_id, image_path, points, fall_speed, spawn_rate FROM apples")
    apples_data = cursor.fetchall()
    conn.close()

    cleaned_data = []
    for data in apples_data:
        apple_id = int(data[0])
        filename = data[1].split(' ', 1)[-1].strip()
        path = os.path.join("assets", filename)
        points = int(data[2])
        speed = {"slow": 3.5, "medium": 4, "fast": 6}.get(data[3].lower(), 4)
        cleaned_data.append((apple_id, path, points, speed, float(data[4])))
    return cleaned_data


APPLE_DATA = load_apple_data()
SPAWN_WEIGHTS = [data[4] for data in APPLE_DATA]


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        try:
            self.spritesheet = pygame.image.load(os.path.join('assets', 'farmer.png')).convert_alpha()
        except:
            self.spritesheet = pygame.Surface((400, 150))
            self.spritesheet.fill((0, 255, 0))

        self.frame_width = 247
        self.frame_height = 248

        total_frames = self.spritesheet.get_width() // self.frame_width

        self.frames_right = [
            self.spritesheet.subsurface(pygame.Rect(i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(min(5, total_frames))
        ]
        self.frames_left = [pygame.transform.flip(frame, True, False) for frame in self.frames_right]

        self.current_frame = 0
        self.animation_speed = 0.1
        self.last_update = pygame.time.get_ticks()

        self.direction = 'left'
        self.image = self.frames_right[self.current_frame]
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 150))

    def update(self, keys):
        moving = False

        # Обработка движения
        if keys[pygame.K_LEFT]:
            self.rect.x -= PLAYER_SPEED
            self.direction = 'right'
            moving = True
        if keys[pygame.K_RIGHT]:
            self.rect.x += PLAYER_SPEED
            self.direction = 'left'
            moving = True

        # Анимация движения
        now = pygame.time.get_ticks()
        if moving:
            if now - self.last_update > self.animation_speed * 1000:
                self.last_update = now
                self.current_frame = (self.current_frame + 1) % len(self.frames_right)

            if self.direction == 'right':
                self.image = self.frames_right[self.current_frame]
            else:
                self.image = self.frames_left[self.current_frame]
        else:
            # Сброс анимации в первый кадр при бездействии
            self.current_frame = 0
            self.image = self.frames_right[0] if self.direction == 'right' else self.frames_left[0]

        # Ограничение движения в пределах экрана
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
            self.image = pygame.transform.scale(self.image, (50, 50))
        except:
            self.image = pygame.Surface((50, 50))
            self.image.fill((200, 0, 0))

        self.rect = self.image.get_rect(topleft=(random.randint(0, WIDTH - 50), -20))
        self.points = self.type_data[2]
        self.fall_speed = self.type_data[3]

    def update(self):
        self.rect.y += self.fall_speed
        if self.rect.top > HEIGHT:
            self.kill()
            return self.apple_id == 1
        return False


class Button(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, action):
        super().__init__()
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            self.dark_image = self.original_image.copy()
            dark_surface = pygame.Surface(self.original_image.get_size(), flags=pygame.SRCALPHA)
            dark_surface.fill((0, 0, 0, 128))
            self.dark_image.blit(dark_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except:
            self.original_image = pygame.Surface((200, 50))
            self.original_image.fill((0, 128, 0))
            self.dark_image = self.original_image.copy()
            self.dark_image.fill((0, 0, 0, 64), special_flags=pygame.BLEND_RGBA_MULT)

        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        self.action = action
        self.hovered = False

    def update(self, event):
        if event.type == pygame.MOUSEMOTION:
            # Проверяем наведение курсора
            prev_hovered = self.hovered
            self.hovered = self.rect.collidepoint(event.pos)
            if self.hovered != prev_hovered:
                self.image = self.dark_image if self.hovered else self.original_image

        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            self.action()


def start_screen():
    difficulty = [None]

    def set_easy():
        difficulty[0] = "easy"

    def set_hard():
        difficulty[0] = "hard"

    try:
        fon = pygame.transform.scale(pygame.image.load(os.path.join('assets', 'menu.png')),
                                     (WIDTH, HEIGHT))
    except:
        fon = pygame.Surface((WIDTH, HEIGHT))
        fon.fill((100, 200, 100))

    buttons = pygame.sprite.Group()
    Button(
        x=WIDTH // 2 - 150,
        y=HEIGHT // 2 + 90,
        image_path=os.path.join('assets', 'easy_btn.png'),
        action=set_easy
    ).add(buttons)

    Button(
        x=WIDTH // 2 + 150,
        y=HEIGHT // 2 + 90,
        image_path=os.path.join('assets', 'hard_btn.png'),
        action=set_hard
    ).add(buttons)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                for btn in buttons:
                    btn.update(event)

        screen.blit(fon, (0, 0))
        buttons.draw(screen)
        pygame.display.flip()

        if difficulty[0] is not None:
            return difficulty[0]


class Game:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.background = self.load_background()
        self.end_image = self.load_end_image()
        self.clock = pygame.time.Clock()
        self.reset()

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

    def reset(self):
        self.player = Player()
        self.apples = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.score = 0
        self.missed = 0
        self.running = True

    def show_text(self, text, size, y):
        font = pygame.font.Font(None, size)
        text_surface = font.render(text, True, (82, 30, 22))
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, y))

    def main_loop(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()

            if self.running:
                keys = pygame.key.get_pressed()
                self.player.update(keys)

                if random.random() < 0.02:
                    apple = Apple(self.difficulty)
                    self.apples.add(apple)
                    self.all_sprites.add(apple)

                self.missed += sum(apple.update() for apple in self.apples)

                hits = pygame.sprite.spritecollide(self.player, self.apples, True)
                self.score += sum(apple.points for apple in hits)

                if self.missed >= MAX_MISSED:
                    self.running = False

                screen.blit(self.background, (0, 0))
                self.all_sprites.draw(screen)
                self.show_text(f"Счет: {self.score}", 40, 10)
                self.show_text(f"Пропущено: {self.missed}/{MAX_MISSED}", 40, 50)


            else:
                screen.blit(self.end_image, (0, 0))
                self.show_text(f"            {self.score}", 61, HEIGHT // 2 + 70)
                if pygame.key.get_pressed()[pygame.K_r]:
                    return
            pygame.display.flip()
            self.clock.tick(60)


def terminate():
    pygame.quit()
    sys.exit()


def main():
    pygame.init()
    while True:
        difficulty = start_screen()
        game = Game(difficulty)
        game.main_loop()


if __name__ == "__main__":
    main()

# git add .
# git commit -m "Обновление функционала"
# git push
