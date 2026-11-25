"""블록 피하기 (pygame-ce). 실행: python game.py
조작: 스페이스 = 시작/다시 시작, ← → = 차선 이동. 숫자와 규칙은 index.html과 같다."""
import array
import math
import pathlib
import random
from types import SimpleNamespace

import pygame

W, H, CX, PZ = 500, 420, 250, 0.88
BEST_FILE = pathlib.Path(__file__).with_name("best.txt")
RATE, VOL = 22050, 0.15


# 원근: z는 0(먼 곳, 위) ~ 1(가까운 곳, 아래). 제곱이라 가까울수록 빨라 보인다.
def z_to_y(z): return H * z * z
def half_w(y): return 100 + 160 * y / H   # 도로 반폭: 위 100px → 아래 260px
def lane_w(y): return half_w(y) * 2 / 3
def lane_x(lane, y): return CX + (lane - 1) * lane_w(y)


PY = z_to_y(PZ)


def level_params(L):
    """(낙하 속도 z/초, 줄 간격 초, 한 줄에 2개 나올 확률)"""
    return (min(0.90, 0.40 + 0.05 * (L - 1)),
            max(0.45, 1.10 - 0.08 * (L - 1)),
            0 if L < 3 else min(0.60, 0.25 + 0.05 * (L - 3)))


def hit(px, lane, z):
    return abs(px - lane) < 0.6 and PZ - 0.06 < z < PZ + 0.04


def make_row(two):
    open_lane = random.randrange(3)
    return [l for l in range(3) if l != open_lane] if two else [open_lane]  # 3개(길 막힘)는 만들지 않는다


def load_best():
    try:
        return int(BEST_FILE.read_text())
    except (OSError, ValueError):
        return 0


# 초기화
pygame.mixer.pre_init(RATE, -16, 1)
pygame.init()
pygame.display.set_caption("블록 피하기")
screen = pygame.display.set_mode((W, H))
world = pygame.Surface((W, H))  # 흔들림을 위해 도로·블록·캐릭터는 여기 그린 뒤 옮겨 붙인다
fonts = {}


def font(size):
    if size not in fonts:
        fonts[size] = pygame.font.SysFont("malgungothic", size, bold=True)
    return fonts[size]


def tone(freq, dur, wave, vol):
    """freq(t)를 따라가는 소리를 직접 만든다. 소리 파일이 필요 없다."""
    buf, ph = array.array("h"), 0.0
    for i in range(int(RATE * dur)):
        t = i / RATE
        ph += freq(t) / RATE
        s = {"sine": math.sin(2 * math.pi * ph), "square": 1 if ph % 1 < 0.5 else -1, "saw": 2 * (ph % 1) - 1}[wave]
        buf.append(int(32767 * vol * 0.001 ** (t / dur) * s))
    return pygame.mixer.Sound(buffer=buf.tobytes())


try:
    SOUNDS = {"move": tone(lambda t: 600, 0.05, "sine", VOL),
              "hit": tone(lambda t: 150 * (40 / 150) ** (t / 0.3), 0.3, "saw", VOL * 2),
              "up": tone(lambda t: 500 if t < 0.1 else 800, 0.25, "square", VOL)}
except pygame.error:  # 소리 장치가 없는 PC에서도 게임은 돌게 한다
    SOUNDS = {}


def sfx(name):
    if name in SOUNDS:
        SOUNDS[name].play()


sky = pygame.Surface((W, H))
for y in range(H):
    k = y / H
    sky.fill((int(15 + 16 * k), int(42 + 37 * k), int(138 + 78 * k)), (0, y, W, 1))

lights = []
for _ in range(60):
    y = 40 + random.random() * 280
    side, edge = random.choice((-1, 1)), half_w(y) + 14
    lights.append((CX + side * (edge + random.random() * max(0, CX - edge)), y, random.random() * 6))

S = SimpleNamespace(state="ready", t=0.0, score=0.0, level=1, lane=1, px=1.0, blocks=[], spawn=0.0,
                    dash=0.0, shake=0.0, flash=0.0, over_t=0.0, parts=[], new_best=False, best=load_best())


def reset():
    S.score, S.level, S.lane, S.px, S.blocks, S.spawn = 0.0, 1, 1, 1.0, [], 0.5
    S.parts, S.new_best, S.over_t, S.state = [], False, 0.0, "playing"


def crash(b):
    S.state, S.shake, S.flash = "over", 0.3, 0.5
    y = z_to_y(b["z"])
    x = lane_x(b["lane"], y)
    for _ in range(20):
        a, sp = random.random() * math.tau, 100 + random.random() * 200
        S.parts.append({"x": x, "y": y - 10, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 150, "life": 0.8})
    sfx("hit")
    if int(S.score) > S.best:
        S.best, S.new_best = int(S.score), True
        BEST_FILE.write_text(str(S.best))


def update(dt):
    S.t += dt
    S.px += (S.lane - S.px) * min(1, dt * 20)   # 약 0.15초에 목표 차선 도착
    S.shake = max(0, S.shake - dt)
    S.flash = max(0, S.flash - dt)
    for p in S.parts:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["vy"] += 600 * dt
        p["life"] -= dt
    S.parts = [p for p in S.parts if p["life"] > 0]
    if S.state == "over":
        S.over_t += dt
    if S.state != "playing":
        return

    S.score += dt * 10
    L = 1 + int(S.score // 100)
    if L > S.level:
        S.level = L
        sfx("up")
    v, gap, two = level_params(S.level)
    S.dash = (S.dash + v * dt * 8) % 1

    S.spawn -= dt
    if S.spawn <= 0:
        S.spawn = gap
        S.blocks += [{"lane": l, "z": 0.0} for l in make_row(random.random() < two)]
    for b in S.blocks:
        b["z"] += v * dt
        if hit(S.px, b["lane"], b["z"]):
            return crash(b)
    S.blocks = [b for b in S.blocks if b["z"] < 1.1]


def handle_key(key):
    if key == pygame.K_SPACE:
        if S.state == "playing" or (S.state == "over" and S.over_t < 0.4):
            return
        reset()
        return
    d = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1}.get(key, 0)
    if d and S.state == "playing" and 0 <= S.lane + d <= 2:
        S.lane += d
        sfx("move")


# 그리기
def draw_scene():
    world.blit(sky, (0, 0))
    for x, y, ph in lights:
        a = 0.5 + 0.4 * math.sin(S.t * 2 + ph)
        world.fill((int(60 + 60 * a), int(105 + 105 * a), int(128 + 127 * a)), (x, y, 5, 5))
    pygame.draw.polygon(world, (28, 33, 66), [(CX - 100, 0), (CX + 100, 0), (CX + 260, H), (CX - 260, H)])
    for s in (-1, 1):
        pygame.draw.line(world, (73, 168, 255), (CX + s * 100, 0), (CX + s * 260, H), 6)
    n = 8   # 흐르는 차선 점선
    for k in range(n):
        y0, y1 = z_to_y((k + S.dash) / n), z_to_y((k + S.dash + 0.5) / n)
        for s in (-1, 1):
            pygame.draw.line(world, (90, 97, 132), (CX + s * half_w(y0) / 3, y0), (CX + s * half_w(y1) / 3, y1),
                             int(1 + 3 * y0 / H))


def draw_block(b):
    y = z_to_y(b["z"])
    s, x, w = half_w(y) / 260, lane_x(b["lane"], y), lane_w(y) * 0.45
    h, top, r = w * 0.32, w * 0.14, max(1, int(4 * s))
    pygame.draw.ellipse(world, (18, 21, 44), (x - w * 0.55, y + 3 * s - 5 * s, w * 1.1, 10 * s))
    pygame.draw.rect(world, (216, 31, 69), (x - w / 2, y - h, w, h), border_radius=r)
    pygame.draw.rect(world, (255, 77, 109), (x - w / 2, y - h - top, w, top + 4 * s), border_radius=r)


def draw_player():
    x = lane_x(S.px, PY)
    bob = abs(math.sin(S.t * 12)) * 5 if S.state == "playing" else 0
    pygame.draw.ellipse(world, (18, 21, 44), (x - (22 - bob), PY - 2, 2 * (22 - bob), 12))
    spr = pygame.Surface((80, 80), pygame.SRCALPHA)   # 발 위치가 (40, 64)
    for s in (-1, 1):
        pygame.draw.ellipse(spr, (13, 62, 168), (40 + s * 8 - 7, 55, 14, 10))
    pygame.draw.rect(spr, (30, 100, 230), (26, 36, 28, 24), border_radius=10)
    pygame.draw.circle(spr, (40, 115, 240), (40, 26), 17)
    pygame.draw.ellipse(spr, (140, 195, 255), (28, 16, 10, 6))
    for s in (-1, 1):
        pygame.draw.circle(spr, (255, 255, 255), (40 + s * 19, 46), 5)
    spr = pygame.transform.rotate(spr, -math.degrees((S.lane - S.px) * 0.5))  # 옮겨 가는 방향으로 기울기
    world.blit(spr, spr.get_rect(center=(x, PY - bob - 24)))


def text(surf, s, size, color, **pos):
    img = font(size).render(s, True, color)
    surf.blit(img, img.get_rect(**pos))


def draw_box(x, label, value, blink):
    box = pygame.Surface((104, 48), pygame.SRCALPHA)
    pygame.draw.rect(box, (10, 20, 60, 217), box.get_rect(), border_radius=10)
    screen.blit(box, (x, 10))
    left = x < CX
    key = "topleft" if left else "topright"
    tx = x + 12 if left else x + 92
    text(screen, label, 11, (255, 255, 255), **{key: (tx, 15)})
    if not blink:
        text(screen, f"{value:04d}", 26, (255, 255, 255), **{key: (tx, 24)})


def draw_hud():
    draw_box(10, "SCORE", int(S.score), S.flash > 0 and int(S.flash * 12) % 2 == 0)
    draw_box(386, "BEST", S.best, False)
    text(screen, f"LEVEL {S.level}", 12, (156, 200, 255), topleft=(16, 63))
    pill = pygame.Surface((280, 30), pygame.SRCALPHA)
    pygame.draw.rect(pill, (10, 20, 60, 204), pill.get_rect(), border_radius=15)
    screen.blit(pill, (CX - 140, 382))
    text(screen, "←   좌우로 움직여 블록을 피하세요!   →", 14, (255, 255, 255), center=(CX, 397))


def draw_overlay(lines):
    dim = pygame.Surface((W, H), pygame.SRCALPHA)
    dim.fill((5, 10, 40, 153))
    screen.blit(dim, (0, 0))
    for i, (s, size, color) in enumerate(lines):
        if s:
            text(screen, s, size, color, center=(CX, 140 + i * 42))


def draw():
    draw_scene()
    S.blocks.sort(key=lambda b: b["z"])
    for b in S.blocks:
        if b["z"] <= PZ:
            draw_block(b)       # 플레이어 뒤쪽 블록
    draw_player()
    for b in S.blocks:
        if b["z"] > PZ:
            draw_block(b)       # 플레이어 앞쪽 블록
    for p in S.parts:
        size = max(1, int(6 * p["life"] / 0.8))
        world.fill((255, 77, 109), (p["x"] - size / 2, p["y"] - size / 2, size, size))
    a = 8 * S.shake / 0.3
    screen.fill((11, 16, 48))
    screen.blit(world, (random.uniform(-a, a), random.uniform(-a, a)) if a else (0, 0))
    draw_hud()
    if S.state == "ready":
        draw_overlay([("블록 피하기", 34, (255, 255, 255)), ("스페이스바로 시작", 18, (156, 200, 255))])
    if S.state == "over" and S.over_t > 0.4:
        draw_overlay([("GAME OVER", 34, (255, 77, 109)), (f"점수 {int(S.score)}", 20, (255, 255, 255)),
                      ("NEW BEST!" if S.new_best else "", 20, (255, 213, 74)),
                      ("스페이스로 다시 시작", 16, (156, 200, 255))])


# 자체 검사: 실행할 때마다 핵심 규칙을 확인한다
assert hit(1, 1, PZ) and not hit(0, 1, PZ) and hit(1.5, 1, PZ) and hit(1.5, 2, PZ) and not hit(1, 1, 0.5)
assert all(abs(a - b) < 1e-9 for a, b in zip(level_params(5) + level_params(10), (0.6, 0.78, 0.35, 0.85, 0.45, 0.6)))
for i in range(200):
    r = make_row(i % 2 == 0)
    assert len(r) == (2 if i % 2 == 0 else 1) and len(set(r)) == len(r) and all(0 <= l <= 2 for l in r)


def main():
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                handle_key(e.key)
        update(min(0.05, clock.tick(60) / 1000))   # 창을 옮기거나 멈춰도 순간이동하지 않게
        draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
