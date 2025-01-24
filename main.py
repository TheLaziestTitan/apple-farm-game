import os
import random
import sqlite3
import pygame

WIDTH, HEIGHT = 900, 600
PLAYER_SPEED = 15
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
        speed = {"slow": 2, "medium": 4, "fast": 6}.get(data[3].lower(), 4)
        cleaned_data.append((apple_id, path, points, speed, float(data[4])))
    return cleaned_data


APPLE_DATA = load_apple_data()
SPAWN_WEIGHTS = [data[4] for data in APPLE_DATA]


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((100, 150))
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 50))

    def update(self, keys):
        if keys[pygame.K_LEFT]: self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]: self.rect.x += PLAYER_SPEED
        self.rect.clamp_ip(screen.get_rect())


class Apple(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.type_data = random.choices(APPLE_DATA, weights=SPAWN_WEIGHTS, k=1)[0]
        self.apple_id = self.type_data[0]

        try:
            self.image = pygame.image.load(self.type_data[1]).convert_alpha()
            self.image = pygame.transform.scale(self.image, (50, 50))
        except Exception as e:
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


class Game:
    def __init__(self):
        self.background = self.load_background()
        self.clock = pygame.time.Clock()
        self.reset()

    def load_background(self):
        try:
            path = os.path.join('assets', 'farm_bg.png')
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
        text_surface = font.render(text, True, (0, 0, 0))
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, y))

    def main_loop(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            if self.running:
                keys = pygame.key.get_pressed()
                self.player.update(keys)

                if random.random() < 0.02:
                    apple = Apple()
                    self.apples.add(apple)
                    self.all_sprites.add(apple)

                self.missed += sum(apple.update() for apple in self.apples)

                hits = pygame.sprite.spritecollide(self.player, self.apples, True)
                self.score += sum(apple.points for apple in hits)

                if self.missed >= MAX_MISSED:
                    self.running = False

            screen.blit(self.background, (0, 0))
            self.all_sprites.draw(screen)

            self.show_text(f"Счет: {self.score}", 36, 10)
            self.show_text(f"Пропущено: {self.missed}/{MAX_MISSED}", 36, 50)

            if not self.running:
                if pygame.key.get_pressed()[pygame.K_r]:
                    self.reset()

            pygame.display.flip()
            self.clock.tick(60)


def main():
    pygame.init()
    game = Game()
    game.main_loop()


if __name__ == "__main__":
    main()

# git add .
# git commit -m "Обновление функционала"
# git push
