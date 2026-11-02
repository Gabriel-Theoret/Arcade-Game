#ÉQUIPE : Gabriel Théoret, Alex Gaudreau, Alexis Latour, Raphaël Piché, Charles Nicolas, Thé Tian Ngo
"""
PySmash - Menu + Jeu + Ranking + Login Arcade (SQLite)
"""

import pygame
import sys
import sqlite3
import random

pygame.init()
pygame.mixer.init()

# ---------------------------------------------------
# JOYSTICK / BORNE ARCADE : MAPPING LOGIQUE GLOBAL
# ---------------------------------------------------
pygame.joystick.init()
nbr_joystick = pygame.joystick.get_count()
print(f"{nbr_joystick} joystick(s) détecté(s)")

joystick_p1 = None
joystick_p2 = None

if nbr_joystick >= 1:
    joystick_p1 = pygame.joystick.Joystick(0)
    joystick_p1.init()
if nbr_joystick >= 2:
    joystick_p2 = pygame.joystick.Joystick(1)
    joystick_p2.init()

# MAPPING LOGIQUE POUR TOUT LE JEU
# (PC: vrai clavier, Arcade: joystick + boutons)
keys = {
    pygame.K_w: False,
    pygame.K_s: False,
    pygame.K_a: False,
    pygame.K_d: False,
    pygame.K_SPACE: False,
    pygame.K_q: False,
    pygame.K_UP: False,
    pygame.K_DOWN: False,
    pygame.K_LEFT: False,
    pygame.K_RIGHT: False,
    pygame.K_p: False,
    pygame.K_RSHIFT: False,
    pygame.K_LSHIFT: False,
    pygame.K_ESCAPE: False,
    pygame.K_RETURN: False,
}
# Anti-repeat joystick GLOBALS (initialisés à False)
prev_js_left = False
prev_js_right = False
prev_js_select = False

prev_js2_left = False
prev_js2_right = False
prev_js2_select = False

prev_btn_left = False
prev_btn_right = False
prev_btn_select = False
prev_btn_back = False


# --- ÉTATS POUR ÉVITER LE RÉPÉTAGE CONTINU (ANTI-REPEAT) ---
prev_btn_up = False
prev_btn_down = False
prev_btn_select = False

def joystick_menu_navigation(selected_index, total_buttons):
    """
    Gère navigation de menu (P1):
    - bouton0 = haut
    - bouton1 = bas
    - bouton2 = sélectionner

    selected_index : index du bouton actuellement sélectionné
    total_buttons  : nombre total de boutons dans le menu
    Retourne : (nouvel_index, validated_bool)
    """
    global prev_btn_up, prev_btn_down, prev_btn_select

    if joystick_p1 is not None:
        btn_up = joystick_p1.get_button(0)
        btn_down = joystick_p1.get_button(1)
        btn_select = joystick_p1.get_button(2)
    else:
        btn_up = btn_down = btn_select = False

    # Détection bord montante (pression, pas maintien)
    pressed_up = btn_up and not prev_btn_up
    pressed_down = btn_down and not prev_btn_down
    pressed_select = btn_select and not prev_btn_select

    if pressed_up:
        selected_index -= 1
        if selected_index < 0:
            selected_index = total_buttons - 1

    if pressed_down:
        selected_index += 1
        if selected_index >= total_buttons:
            selected_index = 0

    validated = pressed_select

    # Mémoriser l'état actuel pour le prochain appel
    prev_btn_up = btn_up
    prev_btn_down = btn_down
    prev_btn_select = btn_select

    return selected_index, validated

def getInput(in_game=False):
    """
    Lecture des entrées pour le jeu.
    - in_game = False  -> on lit seulement le clavier (menus, debug PC)
    - in_game = True   -> on mappe JOYSTICK 1 et 2 sur les touches du jeu
    """
    global keys

    # Reset
    for k in keys:
        keys[k] = False

    # Clavier (laisse-le pour debug PC)
    pressed = pygame.key.get_pressed()
    for k in keys:
        if k < len(pressed) and pressed[k]:
            keys[k] = True

    deadzone = 0.3

    # --- JOYSTICK P1 -> WASD / SPACE / LSHIFT / Q / ESC ---
    if joystick_p1 is not None and in_game:
        ax_x = joystick_p1.get_axis(0)
        ax_y = joystick_p1.get_axis(1)

        # Déplacement
        if ax_x < -deadzone:
            keys[pygame.K_a] = True
        if ax_x > deadzone:
            keys[pygame.K_d] = True
        if ax_y < -deadzone:
            keys[pygame.K_w] = True
        if ax_y > deadzone:
            keys[pygame.K_s] = True

        # Boutons 0,1,2,3
        if joystick_p1.get_button(0):  # attaque principale
            keys[pygame.K_SPACE] = True
        if joystick_p1.get_button(1):  # attaque spéciale
            keys[pygame.K_LSHIFT] = True
        if joystick_p1.get_button(2):  # autre action (ulti)
            keys[pygame.K_q] = True
        if joystick_p1.get_button(3):  # pause / retour
            keys[pygame.K_ESCAPE] = True

    # --- JOYSTICK P2 -> flèches / P / ESC (joueur 2) ---
    if joystick_p2 is not None and in_game:
        ax_x2 = joystick_p2.get_axis(0)
        ax_y2 = joystick_p2.get_axis(1)

        # Déplacement
        if ax_x2 < -deadzone:
            keys[pygame.K_LEFT] = True
        if ax_x2 > deadzone:
            keys[pygame.K_RIGHT] = True
        if ax_y2 < -deadzone:
            keys[pygame.K_UP] = True
        if ax_y2 > deadzone:
            keys[pygame.K_DOWN] = True

        # Boutons 0,1,2,3 pour P2
        if joystick_p2.get_button(0):  # attaque P2
            keys[pygame.K_p] = True
        if joystick_p2.get_button(1):
            keys[pygame.K_RSHIFT] = True  # libre si tu en as besoin ailleurs
        if joystick_p2.get_button(2):
            keys[pygame.K_RETURN] = True  # libre aussi
        if joystick_p2.get_button(3):
            keys[pygame.K_ESCAPE] = True

# Musique de fond
try:
    pygame.mixer.music.load("/home/pi/RetroPie/roms/pygame/AB/AB_music_intro.mp3")
except Exception:
    pygame.mixer.music.load("AB/AB_music_intro.mp3")
pygame.mixer.music.play(-1)

# Sons

# -----------------------------------------------
# Base de données
# -----------------------------------------------
DB_NAME = "ranking.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players(
            name TEXT PRIMARY KEY,
            country TEXT
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores(
            name TEXT,
            score INTEGER
        );
    """)
    conn.commit()
    conn.close()

country_idx = [0,0]
def player_exists(name, player_country_idx):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT country FROM players WHERE name=? AND country!=?", (name, countries[player_country_idx]))
    row = c.fetchone()

    conn.close()

    if row:
        # Le nom existe déjà dans un autre pays
        return True
    else:
        # Aucun conflit
        return False


def register_player(name, country):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO players VALUES (?, ?)", (name, country))
    conn.commit()
    conn.close()


def add_score(name, score):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT score FROM scores WHERE name=?", (name,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO scores VALUES (?, ?)", (name, score))
    else:
        old_score = row[0]
        if score > old_score:
            c.execute("UPDATE scores SET score=? WHERE name=?", (score, name))
    conn.commit()
    conn.close()

def add_win(name):
    """Ajoute 1 victoire au joueur `name` dans la table scores."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT score FROM scores WHERE name=?", (name,))
    row = c.fetchone()

    if row is None:
        # aucune entrée pour ce joueur → on crée avec 1 victoire
        c.execute("INSERT INTO scores(name, score) VALUES (?, ?)", (name, 1))
    else:
        # on incrémente le nombre de victoires
        old_score = row[0]
        c.execute("UPDATE scores SET score=? WHERE name=?", (old_score + 1, name))

    conn.commit()
    conn.close()

def delete_player(name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM players WHERE name=?", (name,))
    c.execute("DELETE FROM scores WHERE name=?", (name,))
    conn.commit()
    conn.close()


def get_top_10():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, score FROM scores ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows


init_db()

# -----------------------------------------------
# PYGAME WINDOW - AUTO FULLSCREEN
# -----------------------------------------------
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))  # S’adapte à l’écran

FPS = 60

clock = pygame.time.Clock()
pygame.display.set_caption("SUPER GOON BATTLE")

FONT = pygame.font.SysFont(None, 32)
FONT_BIG = pygame.font.SysFont(None, 60)
TITLE_FONT = pygame.font.SysFont(None, 80)  # pour les gros titres rétro
BG = (30, 30, 40)
WHITE = (240, 240, 240)
BUTTON_COLOR = (70, 70, 100)
BUTTON_HOVER = (100, 100, 150)
GRAY = (100, 100, 100)   # Pour clavier virtuel
BLUE = (50, 150, 255)    # Pour clavier virtuel

# Fond d'écran rétro néon pour tous les menus après l'intro

background_img = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_background_img1.png")

background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

# Sprite sheets pour la simulation
SPRITE_WIDTH = 35
SPRITE_HEIGHT = 74

adv_sheet = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_advnt_full.png")
ninja_sheet = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_ninja_full.png")  # prêt pour un deuxième perso plus tard


def get_adv_frame(x, y):
    rect = pygame.Rect(x, y, SPRITE_WIDTH, SPRITE_HEIGHT)
    return adv_sheet.subsurface(rect).copy()


def get_ninja_frame(x, y):
    rect = pygame.Rect(x, y, SPRITE_WIDTH, SPRITE_HEIGHT)
    return ninja_sheet.subsurface(rect).copy()


# Frames de punch au sol
adv_punch_frames = [
    get_adv_frame(222, 130),
    get_adv_frame(257, 130)
]

nin_punch_frames = [
    get_ninja_frame(222, 130),
    get_ninja_frame(257, 130)
]

# Frames de punch en saut (jump punch)
adv_jump_punch_frames = [
    get_adv_frame(222, 260),
    get_adv_frame(257, 260)
]
nin_jump_punch_frames = [
    get_ninja_frame(222, 260),
    get_ninja_frame(257, 260)
]

# Frames de base pour le personnage principal (advnt)
adv_idle = get_adv_frame(0, 0)
adv_run_frames = [get_adv_frame(35, 0), get_adv_frame(130, 0)]
adv_jump_up = get_adv_frame(222, 70)
adv_jump_down = get_adv_frame(257, 70)

nin_idle = get_ninja_frame(0, 0)
nin_run_frames = [get_ninja_frame(35, 0), get_ninja_frame(130, 0)]
nin_jump_up = get_ninja_frame(222, 70)
nin_jump_down = get_ninja_frame(257, 70)

# Images des maps pour le menu de preview

map_raw_1 = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map4.png")   # PNG
map_raw_2 = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map2.png")
map_raw_3 = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map3.png")



def scale_map(img):
    max_w, max_h = int(WIDTH * 0.9), int(HEIGHT * 0.6)
    w, h = img.get_width(), img.get_height()
    ratio = min(max_w / w, max_h / h)
    new_size = (int(w * ratio), int(h * ratio))
    return pygame.transform.smoothscale(img, new_size)


map_images = [
    scale_map(map_raw_1),
    scale_map(map_raw_2),
    scale_map(map_raw_3)
]

# -----------------------------------------------
# FONCTION TITRE RÉTRO / NÉON
# -----------------------------------------------
def draw_retro_title(text, y):
    """Dessine un titre style jeu rétro néon au centre de l'écran."""
    base_color = (255, 100, 210)    # rose/violet néon
    glow_color = (0, 255, 255)      # cyan néon
    shadow_color = (0, 0, 0)        # ombre noire

    title_surface = TITLE_FONT.render(text, True, base_color)
    x = WIDTH // 2 - title_surface.get_width() // 2

    glow_surface = TITLE_FONT.render(text, True, glow_color)
    for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        screen.blit(glow_surface, (x + dx, y + dy))

    shadow_surface = TITLE_FONT.render(text, True, shadow_color)
    screen.blit(shadow_surface, (x + 4, y + 4))

    screen.blit(title_surface, (x, y))


# -----------------------------------------------
# BUTTON CLASS (style arcade / néon)
# -----------------------------------------------
class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text

    def draw(self):
        mouse = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse)

        base_color = (90, 40, 140)
        hover_color = (150, 70, 240)
        glow_color = (0, 255, 255)
        shadow_color = (5, 5, 20)

        inner_color = hover_color if is_hover else base_color

        shadow_rect = self.rect.move(0, 6)
        pygame.draw.rect(screen, shadow_color, shadow_rect)

        glow_rect = self.rect.inflate(10, 10)
        pygame.draw.rect(screen, glow_color, glow_rect)

        pygame.draw.rect(screen, inner_color, self.rect)

        highlight_rect = pygame.Rect(
            self.rect.x + 6,
            self.rect.y + 6,
            self.rect.w - 12,
            self.rect.h // 2 - 4
        )
        hl_r = min(inner_color[0] + 40, 255)
        hl_g = min(inner_color[1] + 40, 255)
        hl_b = min(inner_color[2] + 40, 255)
        highlight_color = (hl_r, hl_g, hl_b)
        pygame.draw.rect(screen, highlight_color, highlight_rect)

        text_surface = FONT.render(self.text, True, WHITE)
        outline_surface = FONT.render(self.text, True, (0, 0, 0))

        text_x = self.rect.centerx - text_surface.get_width() // 2
        text_y = self.rect.centery - text_surface.get_height() // 2

        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            screen.blit(outline_surface, (text_x + dx, text_y + dy))

        screen.blit(text_surface, (text_x, text_y))

    def clicked(self):
        return self.rect.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]


# -----------------------------------------------
# POLYGON HITBOX SUPPORT (ray-casting)
# -----------------------------------------------
def point_in_polygon(x, y, poly):
    """Return True if point is inside a polygon. Works for any shape."""
    inside = False
    p1x, p1y = poly[0]
    n = len(poly)

    for i in range(n + 1):
        p2x, p2y = poly[i % n]

        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside

        p1x, p1y = p2x, p2y

    return inside


# -----------------------------------------------
# COUNTRIES
# -----------------------------------------------
countries = [
    "Canada","USA","Italie","Mexique","Russie","Kiribati"
]
#images drapeaux

img_canada = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_canada.bmp")
img_usa = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_usa.bmp")
img_italie = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_italie.bmp")
img_mexique = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_mexique.bmp")
img_russie = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_russie.bmp")
img_kiribati = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_drapeau_kiribati.bmp")

liste_flags = [img_canada,img_usa,img_italie,img_mexique,img_russie,img_kiribati]
for i, drapeau in enumerate(liste_flags):
    liste_flags[i] = pygame.transform.scale(drapeau,(30,30))








# -----------------------------------------------
# INTRO MENU
# -----------------------------------------------
def intro_menu():

    img_accueil = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_img_accueuil.png")

    img_accueil = pygame.transform.scale(img_accueil, (WIDTH, HEIGHT))

    btn_start = Button(WIDTH // 2 - 250, HEIGHT // 2 + 150, 500, 60,
                       "APPUYEZ SUR START POUR COMMENCER")

    credits_text = [
        "Alexis Latour",
        "Gabriel Theoret",
        "Charles Nicolas",
        "Raphael Piche",
        "Alex Gaudreau",
        "The Tian Ngo"
    ]

    credit_font = pygame.font.SysFont(None, 26)

    selected_index = 0  # un seul bouton, mais on garde la logique de menu

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Option clavier: ENTER / ESPACE pour tester sur PC
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):

                    return

        # Navigation joystick (même si un seul bouton)
        selected_index, validated = joystick_menu_navigation(selected_index, 1)

        # bouton3 = quitter le jeu depuis l'écran d'accueil
        if joystick_p1 is not None and joystick_p1.get_button(9):
            pygame.quit()
            sys.exit()

        screen.blit(img_accueil, (0, 0))
        btn_start.draw()

        # Affichage crédits bas droite
        y_offset = HEIGHT - (len(credits_text) * 22) - 20
        for i, line in enumerate(credits_text):
            text_surface = credit_font.render(line, True, (255, 255, 255))
            x = WIDTH - text_surface.get_width() - 20
            y = y_offset + i * 22
            screen.blit(text_surface, (x, y))

        # Highlight du bouton sélectionné (joystick)
        if selected_index == 0:
            highlight_rect = btn_start.rect.inflate(14, 14)
            pygame.draw.rect(screen, (255, 255, 0), highlight_rect, 3)

        # Validation avec bouton2 (C)
        if joystick_p1 is not None and joystick_p1.get_button(8):
            main_menu()
            return

        pygame.display.flip()
        clock.tick(FPS)
player_names = ["",""]
# -----------------------------------------------
# LOGIN MENU ARCADE (CLAVIER VIRTUEL) - 1v1
# -----------------------------------------------
def login_menu_arcade():
            global player_names


            player_names = ["", ""]
            selected_rows = [0, 0]
            selected_cols = [0, 0]
            ready = [False, False]

            kbd = [
                list("ABCDEFGHIJKLM"),
                list("NOPQRSTUVWXYZ"),
                list("0123456789"),
                ["<", " ", "READY"]
            ]

            btn_back = Button(20, 20, 120, 50, "Retour")

            default_idx = countries.index("Canada") if "Canada" in countries else 0
            country_idx = [default_idx, default_idx]

            # Anti-repeat locaux joystick
            js1_prev_up = js1_prev_down = js1_prev_left = js1_prev_right = False
            js1_prev_select = False
            js1_prev_country_prev = js1_prev_country_next = False

            js2_prev_up = js2_prev_down = js2_prev_left = js2_prev_right = False
            js2_prev_select = False
            js2_prev_country_prev = js2_prev_country_next = False

            deadzone = 0.4

            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                # ---------- P1 JOYSTICK ----------
                if joystick_p1 is not None and not ready[0]:
                    ax_x = joystick_p1.get_axis(0)
                    ax_y = joystick_p1.get_axis(1)

                    up = ax_y < -deadzone
                    down = ax_y > deadzone
                    left = ax_x < -deadzone
                    right = ax_x > deadzone

                    select = joystick_p1.get_button(2)
                    country_prev = joystick_p1.get_button(0)
                    country_next = joystick_p1.get_button(1)
                    back = joystick_p1.get_button(3)

                    # Déplacement clavier virtuel P1 (bord montante)
                    if up and not js1_prev_up:
                        selected_rows[0] = (selected_rows[0] - 1) % len(kbd)
                        selected_cols[0] = min(
                            selected_cols[0],
                            len(kbd[selected_rows[0]]) - 1
                        )

                    if down and not js1_prev_down:
                        selected_rows[0] = (selected_rows[0] + 1) % len(kbd)
                        selected_cols[0] = min(
                            selected_cols[0],
                            len(kbd[selected_rows[0]]) - 1
                        )

                    if left and not js1_prev_left:
                        selected_cols[0] = (selected_cols[0] - 1) % len(kbd[selected_rows[0]])

                    if right and not js1_prev_right:
                        selected_cols[0] = (selected_cols[0] + 1) % len(kbd[selected_rows[0]])


                    # Pays P1
                    if country_prev and not js1_prev_country_prev:
                        country_idx[0] = (country_idx[0] - 1) % len(countries)

                    if country_next and not js1_prev_country_next:
                        country_idx[0] = (country_idx[0] + 1) % len(countries)


                    # Validation / écriture P1
                    if select and not js1_prev_select:

                        char = kbd[selected_rows[0]][selected_cols[0]]
                        if char == "READY":
                            if player_names[0] != "":
                                ready[0] = True
                        elif char == "<":
                            player_names[0] = player_names[0][:-1]
                        else:
                            if len(player_names[0]) < 12:
                                player_names[0] += char

                    # Retour général
                    if back:

                        return None

                    js1_prev_up, js1_prev_down = up, down
                    js1_prev_left, js1_prev_right = left, right
                    js1_prev_select = select
                    js1_prev_country_prev = country_prev
                    js1_prev_country_next = country_next

                # ---------- P2 JOYSTICK ----------
                if joystick_p2 is not None and not ready[1]:
                    ax_x2 = joystick_p2.get_axis(0)
                    ax_y2 = joystick_p2.get_axis(1)

                    up2 = ax_y2 < -deadzone
                    down2 = ax_y2 > deadzone
                    left2 = ax_x2 < -deadzone
                    right2 = ax_x2 > deadzone

                    select2 = joystick_p2.get_button(2)
                    country_prev2 = joystick_p2.get_button(0)
                    country_next2 = joystick_p2.get_button(1)

                    # Déplacement clavier virtuel P2
                    if up2 and not js2_prev_up:
                        selected_rows[1] = (selected_rows[1] - 1) % len(kbd)
                        selected_cols[1] = min(
                            selected_cols[1],
                            len(kbd[selected_rows[1]]) - 1
                        )

                    if down2 and not js2_prev_down:
                        selected_rows[1] = (selected_rows[1] + 1) % len(kbd)
                        selected_cols[1] = min(
                            selected_cols[1],
                            len(kbd[selected_rows[1]]) - 1
                        )

                    if left2 and not js2_prev_left:
                        selected_cols[1] = (selected_cols[1] - 1) % len(kbd[selected_rows[1]])

                    if right2 and not js2_prev_right:
                        selected_cols[1] = (selected_cols[1] + 1) % len(kbd[selected_rows[1]])


                    # Pays P2
                    if country_prev2 and not js2_prev_country_prev:
                        country_idx[1] = (country_idx[1] - 1) % len(countries)

                    if country_next2 and not js2_prev_country_next:
                        country_idx[1] = (country_idx[1] + 1) % len(countries)


                    # Validation / écriture P2
                    if select2 and not js2_prev_select:

                        char = kbd[selected_rows[1]][selected_cols[1]]
                        if char == "READY":
                            if player_names[1] != "":
                                ready[1] = True
                        elif char == "<":
                            player_names[1] = player_names[1][:-1]
                        else:
                            if len(player_names[1]) < 12:
                                player_names[1] += char

                    js2_prev_up, js2_prev_down = up2, down2
                    js2_prev_left, js2_prev_right = left2, right2
                    js2_prev_select = select2
                    js2_prev_country_prev = country_prev2
                    js2_prev_country_next = country_next2
                error_message =""
                # Quand les deux joueurs sont prêts : enregistre en BD
                if ready[0] and ready[1]:
                    can_register = True
                    for i, name in enumerate(player_names):
                        if name:

                            existing = player_exists(name, country_idx[i])  # <- prend maintenant le pays en compte
                            if not existing:
                                register_player(name, countries[country_idx[i]])
                            else:
                                error_message = f"Le joueur '{name}' existe déjà pour un autre pays. C POUR RÉASSAYER"
                                can_register = False
                                break  # arrête l'enregistrement si conflit
                    if can_register:
                        return player_names

                    if can_register:
                        return player_names

                # ---------- DESSIN ----------
                screen.blit(background_img, (0, 0))
                draw_retro_title("IDENTIFICATION 1 vs 1", 50)

                # P1 nom + pays
                pygame.draw.rect(screen, (60, 60, 80), (50, 120, 400, 50))
                label1 = player_names[0] + ("  [READY]" if ready[0] else "")
                txt1 = FONT.render(label1, True, WHITE)
                screen.blit(txt1, (60, 135))

                txt1_country = FONT.render(
                    "Pays : " + countries[country_idx[0]],
                    True,
                    WHITE
                )
                screen.blit(txt1_country, (60, 190))
                screen.blit(liste_flags[country_idx[0]],(60,250))

                # P2 nom + pays
                pygame.draw.rect(screen, (60, 60, 80),
                                 (WIDTH - 450, 120, 400, 50))
                label2 = player_names[1] + ("  [READY]" if ready[1] else "")
                txt2 = FONT.render(label2, True, WHITE)
                screen.blit(txt2, (WIDTH - 440, 135))

                txt2_country = FONT.render(
                    "Pays : " + countries[country_idx[1]],
                    True,
                    WHITE
                )
                screen.blit(txt2_country, (WIDTH - 440, 190))
                screen.blit(liste_flags[country_idx[1]], (WIDTH-50, 250))

                # Aide contrôles borne
                h1 = FONT.render("P1 (Joystick 1) : axes pour bouger, 2=OK, 0/1=pays, 3=Retour", True, WHITE)
                h2 = FONT.render("P2 (Joystick 2) : axes pour bouger, 2=OK, 0/1=pays", True, WHITE)
                screen.blit(h1, (WIDTH // 2 - h1.get_width() // 2, 230))
                screen.blit(h2, (WIDTH // 2 - h2.get_width() // 2, 260))

                # Clavier virtuel
                start_y = 300
                key_w, key_h, spacing = 52, 52, 8

                for r, row in enumerate(kbd):
                    row_width = len(row) * (key_w + spacing) - spacing
                    start_x = WIDTH // 2 - row_width // 2

                    for c, key_char in enumerate(row):
                        x = start_x + c * (key_w + spacing)
                        y = start_y + r * (key_h + spacing)

                        selected1 = (not ready[0] and r == selected_rows[0] and c == selected_cols[0])
                        selected2 = (not ready[1] and r == selected_rows[1] and c == selected_cols[1])

                        color = (20, 25, 60)
                        if selected1 and not selected2:
                            color = (255, 90, 120)
                        elif selected2 and not selected1:
                            color = (90, 255, 120)
                        elif selected1 and selected2:
                            color = (255, 200, 0)

                        shadow_rect = pygame.Rect(x, y + 4, key_w, key_h)
                        pygame.draw.rect(screen, (5, 5, 20), shadow_rect)
                        pygame.draw.rect(screen, color,
                                         pygame.Rect(x, y, key_w, key_h))

                        label = FONT.render(key_char, True, WHITE)
                        screen.blit(label, (
                            x + key_w // 2 - label.get_width() // 2,
                            y + key_h // 2 - label.get_height() // 2
                        ))

                # Visuel bouton retour (mais déclenché par bouton 3)
                btn_back.draw()
                if error_message:
                    font_error = pygame.font.Font(None, 36)
                    text_surf = font_error.render(error_message, True, (255, 0, 0))  # rouge
                    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, HEIGHT - 100))
                    if joystick_p1.get_button(2):
                        login_menu_arcade()
                        return



                pygame.display.flip()
                clock.tick(FPS)

                # -----------------------------------------------
# LOGIN MENU VS AI
# -----------------------------------------------

def login_menu_vs_ai():
    input_name = ""
    ai_name = "ORDI"
    selected_row = 0
    selected_col = 0
    ready = False

    kbd = [
        list("ABCDEFGHIJKLM"),
        list("NOPQRSTUVWXYZ"),
        list("0123456789"),
        ["<", " ", "READY"]
    ]

    btn_back = Button(20, 20, 120, 50, "Retour")

    default_idx = countries.index("Canada") if "Canada" in countries else 0
    country_idx = default_idx

    js_prev_up = js_prev_down = js_prev_left = js_prev_right = False
    js_prev_select = False
    js_prev_country_prev = js_prev_country_next = False

    deadzone = 0.4

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if joystick_p1 is not None and not ready:
            ax_x = joystick_p1.get_axis(0)
            ax_y = joystick_p1.get_axis(1)

            up = ax_y < -deadzone
            down = ax_y > deadzone
            left = ax_x < -deadzone
            right = ax_x > deadzone

            select = joystick_p1.get_button(2)
            country_prev = joystick_p1.get_button(0)
            country_next = joystick_p1.get_button(1)
            back = joystick_p1.get_button(3)

            if up and not js_prev_up:
                selected_row = (selected_row - 1) % len(kbd)
                selected_col = min(selected_col, len(kbd[selected_row]) - 1)

            if down and not js_prev_down:
                selected_row = (selected_row + 1) % len(kbd)
                selected_col = min(selected_col, len(kbd[selected_row]) - 1)

            if left and not js_prev_left:
                selected_col = (selected_col - 1) % len(kbd[selected_row])

            if right and not js_prev_right:
                selected_col = (selected_col + 1) % len(kbd[selected_row])


            if country_prev and not js_prev_country_prev:
                country_idx = (country_idx - 1) % len(countries)

            if country_next and not js_prev_country_next:
                country_idx = (country_idx + 1) % len(countries)


            if select and not js_prev_select:

                char = kbd[selected_row][selected_col]
                if char == "READY":
                    if input_name != "":
                        ready = True
                elif char == "<":
                    input_name = input_name[:-1]
                else:
                    if len(input_name) < 12:
                        input_name += char

            if back:

                return None

            js_prev_up, js_prev_down = up, down
            js_prev_left, js_prev_right = left, right
            js_prev_select = select
            js_prev_country_prev = country_prev
            js_prev_country_next = country_next

        if ready:
            if input_name:
                existing = player_exists(input_name,country_idx[i])
                if existing is None:
                    register_player(input_name, countries[country_idx[i]])
                else:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("UPDATE players SET country=? WHERE name=?",
                              (countries[country_idx[i]], input_name))
                    conn.commit()
                    conn.close()

            if player_exists(ai_name,country_idx[i]) is None:
                register_player(ai_name, "AI")

            return [input_name, ai_name]

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("IDENTIFICATION VS ORDI", 50)

        pygame.draw.rect(screen, (60, 60, 80),
                         (WIDTH//2 - 200, 120, 400, 50))
        label = input_name + ("  [READY]" if ready else "")
        txt = FONT.render(label, True, WHITE)
        screen.blit(txt, (WIDTH//2 - 180, 135))

        txt_country = FONT.render("Pays : " + countries[country_idx[i]], True, WHITE)
        screen.blit(txt_country, (WIDTH//2 - 180, 190))
        screen.blit(liste_flags[country_idx], (200,200))

        h = FONT.render("Joystick 1 : axes=lettres, 2=OK, 0/1=pays, 3=Retour", True, WHITE)
        screen.blit(h, (WIDTH//2 - h.get_width()//2, 230))

        start_y = 260
        key_w, key_h, spacing = 52, 52, 8

        for r, row in enumerate(kbd):
            row_width = len(row) * (key_w + spacing) - spacing
            start_x = WIDTH // 2 - row_width // 2

            for c, key_char in enumerate(row):
                x = start_x + c * (key_w + spacing)
                y = start_y + r * (key_h + spacing)

                selected = (not ready and r == selected_row and c == selected_col)

                color = (20, 25, 60)
                if selected:
                    color = (255, 120, 150)

                shadow_rect = pygame.Rect(x, y + 4, key_w, key_h)
                pygame.draw.rect(screen, (5, 5, 20), shadow_rect)
                pygame.draw.rect(screen, color,
                                 pygame.Rect(x, y, key_w, key_h))

                label_key = FONT.render(key_char, True, WHITE)
                screen.blit(label_key, (
                    x + key_w//2 - label_key.get_width()//2,
                    y + key_h//2 - label_key.get_height()//2
                ))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# MAIN MENU
# -----------------------------------------------
def main_menu():
    btn_partie = Button(50, 190, 240, 60, "PARTIE")
    btn_rank   = Button(50, 260, 240, 60, "RANKING")
    btn_arme   = Button(50, 330, 240, 60, "ARMES")
    btn_char   = Button(50, 400, 240, 60, "CHARACTER")
    btn_maps   = Button(50, 470, 240, 60, "MAPS")
    btn_quit   = Button(WIDTH - 160, 20, 140, 50, "QUITTER")

    font = pygame.font.Font(None,30)

    buttons = [btn_partie, btn_rank, btn_maps, btn_quit]
    selected_index = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Option clavier pour tests : flèches + ENTER
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(buttons)
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(buttons)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    choice = selected_index

                    if choice == 0:
                        return "partie"
                    elif choice == 1:
                        ranking_menu()
                    elif choice == 2:
                        map_preview_menu()
                    elif choice == 3:
                        pygame.quit()
                        sys.exit()

        # Navigation joystick
        selected_index, validated = joystick_menu_navigation(selected_index, len(buttons))

        # bouton3 = quitter directement depuis le main menu
        if joystick_p1 is not None and (joystick_p1.get_button(9)):
            pygame.quit()
            sys.exit()

        screen.blit(background_img, (0, 0))
        draw_retro_title("SUPER GOON BATTLE", 60)

        # Dessin des boutons
        for i, btn in enumerate(buttons):
            btn.draw()
            if i == selected_index:
                # Highlight du bouton sélectionné
                highlight_rect = btn.rect.inflate(14, 14)
                pygame.draw.rect(screen, (255, 255, 0), highlight_rect, 3)

        # Validation joystick (bouton2)
        if validated:

            if selected_index == 0:
                return "partie"
            elif selected_index == 1:
                ranking_menu()
            elif selected_index == 2:
                map_preview_menu()
            elif selected_index == 3:
                pygame.quit()
                sys.exit()


        text_commandes_menu = font.render("COMMANDES DU MENU : A/B HAUT/BAS,C SELECTIONNER, SELECT/START QUITTER  ",True,(255,255,255))
        screen.blit(text_commandes_menu,(400,200))
        text_commandes_jeu = font.render("COMMANDES DU JEU: A SAUTER, C ATTAQUER, JOYSTICK BOUGER",True,(255,255,255))
        screen.blit(text_commandes_jeu,(400,300))
        text_regles = font.render("RÈGLES : ENVOYEZ VOTRE ADVERSAIRE DANS LE VIDE 3 FOIS ! LE PREMIER À 0 VIES MEURT!", True,(255,255,255))
        screen.blit(text_regles,(400,400))

        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# PARTIE MENU
# -----------------------------------------------
def partie_menu():
    btn_1v1 = Button(WIDTH // 2 - 120, 260, 240, 60, "1 vs 1")
    btn_ai = Button(WIDTH // 2 - 120, 350, 240, 60, "Contre ORDI")
    btn_back = Button(20, 20, 120, 50, "Retour")

    buttons = [btn_1v1, btn_ai, btn_back]
    selected_index = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Navigation joystick
        selected_index, validated = joystick_menu_navigation(selected_index, len(buttons))

        # Bouton 3 → Retour direct
        if joystick_p1 is not None and joystick_p1.get_button(3):

            return "back"

        screen.blit(background_img, (0, 0))
        draw_retro_title("PARTIE", 100)
        draw_retro_title("D:RETOUR",155)

        for i, btn in enumerate(buttons):
            btn.draw()

            # highlight du bouton sélectionné
            if i == selected_index:
                hrect = btn.rect.inflate(14, 14)
                pygame.draw.rect(screen, (255, 255, 0), hrect, 3)

        # Bouton 2 → Valider
        if validated:

            if selected_index == 0:
                return "1v1"
            elif selected_index == 1:
                return "ai"
            elif selected_index == 2:
                return "back"
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 1 = left click, 3 = right
                    return "1v1"
        pygame.display.flip()
        clock.tick(FPS)
# -----------------------------------------------
# UTILITAIRE RECT RELATIF
# -----------------------------------------------
def rel_rect(rx, ry, rw, rh, sw, sh):
    return pygame.Rect(rx*sw, ry*sh, rw*sw, rh*sh)
sw, sh = WIDTH, HEIGHT
# -----------------------------------------------
# SELECT PERSONNAGE 1v1 (réutilisé)
# -----------------------------------------------
def character_select_menu(player_names):
    """
    Écran de sélection de personnage style Smash :
    - player_names[0] = nom P1
    - player_names[1] = nom P2
    - P1 bouge avec A/D, confirme avec LSHIFT
    - P2 bouge avec LEFT/RIGHT, confirme avec P
    Retourne (char_p1, char_p2) où chaque char est 'ADV' ou 'NINJA'.
    """
    adv_preview_raw = adv_idle
    ninja_preview_raw = get_ninja_frame(0, 0)
    preview_h = int(HEIGHT * 0.28)
    preview_w = int(preview_h * (SPRITE_WIDTH / SPRITE_HEIGHT))
    adv_preview = pygame.transform.scale(adv_preview_raw, (preview_w, preview_h))
    ninja_preview = pygame.transform.scale(ninja_preview_raw, (preview_w, preview_h))
    characters = [
        {"key": "ADV", "name": "ADVENTURER", "image": adv_preview},
        {"key": "NINJA", "name": "NINJA", "image": ninja_preview},
    ]
    p1_index = 0
    p2_index = 1
    p1_locked = False
    p2_locked = False
    btn_back = Button(20, 20, 120, 50, "Retour")
    btn_confirm_p1 = Button(WIDTH//4 - 100, HEIGHT - 100, 200, 60, "CONFIRMER P1")
    btn_confirm_p2 = Button(3*WIDTH//4 - 100, HEIGHT - 100, 200, 60, "CONFIRMER P2")
    while True:
        for event in pygame.event.get():
            # --- JOYSTICK P1 ---
            # --- JOYSTICK P2 ---
            if joystick_p2:
                ax2 = joystick_p2.get_axis(0)
                deadzone = 0.4

                move_left2 = ax2 < -deadzone
                move_right2 = ax2 > deadzone
                select2 = joystick_p2.get_button(2)
                back2 = joystick_p2.get_button(3)

                global prev_js2_left, prev_js2_right, prev_js2_select

                if move_left2 and not prev_js2_left and not p2_locked:
                    p2_index = (p2_index - 1) % len(characters)

                if move_right2 and not prev_js2_right and not p2_locked:
                    p2_index = (p2_index + 1) % len(characters)

                if select2 and not prev_js2_select:
                    p2_locked = not p2_locked

                if back2:
                    return None

                prev_js2_left = move_left2
                prev_js2_right = move_right2
                prev_js2_select = select2

            if joystick_p1:
                ax = joystick_p1.get_axis(0)
                deadzone = 0.4
                move_left = ax < -deadzone
                move_right = ax > deadzone
                select = joystick_p1.get_button(2)
                back = joystick_p1.get_button(3)

                global prev_js_left, prev_js_right, prev_js_select

                if move_left and not prev_js_left and not p1_locked:
                    p1_index = (p1_index - 1) % len(characters)

                if move_right and not prev_js_right and not p1_locked:
                    p1_index = (p1_index + 1) % len(characters)

                if select and not prev_js_select:
                    p1_locked = not p1_locked

                if back:
                    return None

                prev_js_left = move_left
                prev_js_right = move_right
                prev_js_select = select

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    return None
                if not p1_locked:
                    if event.key == pygame.K_a:
                        p1_index = (p1_index - 1) % len(characters)
                    elif event.key == pygame.K_d:
                        p1_index = (p1_index + 1) % len(characters)
                if event.key == pygame.K_LSHIFT:
                    p1_locked = not p1_locked
                if not p2_locked:
                    if event.key == pygame.K_LEFT:
                        p2_index = (p2_index - 1) % len(characters)
                    elif event.key == pygame.K_RIGHT:
                        p2_index = (p2_index + 1) % len(characters)
                if event.key == pygame.K_p:
                    p2_locked = not p2_locked
        if btn_back.clicked():

            return None
        if btn_confirm_p1.clicked():

            p1_locked = not p1_locked
        if btn_confirm_p2.clicked():

            p2_locked = not p2_locked
        if p1_locked and p2_locked:
            return (characters[p1_index]["key"], characters[p2_index]["key"])
        # DESSIN
        screen.blit(background_img, (0, 0))
        draw_retro_title("SELECTION PERSONNAGE", 50)
        panel_h = int(HEIGHT * 0.35)
        panel_y = HEIGHT - panel_h - 20
        panel_p1 = pygame.Rect(0, panel_y, WIDTH//2, panel_h)
        pygame.draw.rect(screen, (180, 40, 70), panel_p1)
        pygame.draw.rect(screen, (255, 255, 255), panel_p1, 3)
        label_p1 = FONT_BIG.render(f"{player_names[0]}", True, WHITE)
        screen.blit(label_p1,
                    (panel_p1.centerx - label_p1.get_width()//2, panel_p1.top + 10))
        panel_p2 = pygame.Rect(WIDTH//2, panel_y, WIDTH//2, panel_h)
        pygame.draw.rect(screen, (40, 100, 200), panel_p2)
        pygame.draw.rect(screen, (255, 255, 255), panel_p2, 3)
        label_p2 = FONT_BIG.render(f"{player_names[1]}", True, WHITE)
        screen.blit(label_p2,
                    (panel_p2.centerx - label_p2.get_width()//2, panel_p2.top + 10))

        mid_y = int(HEIGHT * 0.35)
        for i, char in enumerate(characters):
            center_x = WIDTH//2 + (i - 0.5) * 220
            img = char["image"]
            img_rect = img.get_rect(center=(center_x, mid_y))
            screen.blit(img, img_rect.topleft)
            name_surf = FONT.render(char["name"], True, WHITE)
            screen.blit(name_surf,
                        (center_x - name_surf.get_width()//2, img_rect.bottom + 5))
            if p1_index == i:
                pygame.draw.rect(screen, (255, 220, 220),
                                 img_rect.inflate(18, 18), 3)
                tag = FONT.render("P1", True, (255, 220, 220))
                screen.blit(tag, (img_rect.left - 10, img_rect.top - 25))
            if p2_index == i:
                pygame.draw.rect(screen, (200, 220, 255),
                                 img_rect.inflate(10, 10), 3)
                tag = FONT.render("P2", True, (200, 220, 255))
                screen.blit(tag,
                            (img_rect.right - tag.get_width() + 10, img_rect.top - 25))
        btn_back.draw()
        btn_confirm_p1.draw()
        btn_confirm_p2.draw()
        status_p1 = "LOCKED" if p1_locked else "CHOIX..."
        status_p2 = "LOCKED" if p2_locked else "CHOIX..."
        st1 = FONT.render(status_p1, True, WHITE)
        st2 = FONT.render(status_p2, True, WHITE)
        screen.blit(st1, (panel_p1.centerx - st1.get_width()//2, panel_p1.bottom - 40))
        screen.blit(st2, (panel_p2.centerx - st2.get_width()//2, panel_p2.bottom - 40))
        pygame.display.flip()
        clock.tick(FPS)
def character_select_1v1(player_names):
    return character_select_menu(player_names)
# -----------------------------------------------
# PLAY TEST – SIM MAP (avec getInput + joystick)
# -----------------------------------------------
def play_map_sim(map_index):
    # Platformes
    if map_index == 0:
        platforms = [
            rel_rect(0.2448, 0.4537, 0.2188, 0.3056, sw, sh),
            rel_rect(0.5443, 0.5370, 0.2239, 0.3056, sw, sh),
            rel_rect(0.5630, 0.3481, 0.1375, 0.0278, sw, sh)
        ]
    elif map_index == 1:
        platforms = [
            rel_rect(0.2656, 0.4676, 0.4661, 0.3241, sw, sh),
            rel_rect(0.2750, 0.2528, 0.1495, 0.0278, sw, sh),
            rel_rect(0.5693, 0.2528, 0.1495, 0.0278, sw, sh)  ]
    else:
        platforms = [
            rel_rect(0.2901, 0.6481, 0.3844, 0.2129, sw, sh),
            rel_rect(0.2698, 0.4444, 0.1323, 0.0185, sw, sh),
            rel_rect(0.6224, 0.2685, 0.1083, 0.1389, sw, sh)   ]
    # Background
    if map_index == 0:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map4.png")

    elif map_index == 1:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map2.png")

    else:


        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map3.png")

    background = pygame.transform.smoothscale(background, (sw, sh))
    # Spawn
    if map_index == 0:
        base_plat = platforms[0]
        spawn_x = base_plat.centerx - 25
        spawn_y = base_plat.top - 100
    else:
        spawn_x = sw // 2 - 25
        spawn_y = 200

    player = pygame.Rect(spawn_x, spawn_y, 50, 100)
    x_player = float(player.x)
    y_player = float(player.y)
    # sprite plus grand que hitbox
    scale_factor = 1.5
    sprite_w = int(player.width * scale_factor)
    sprite_h = int(player.height * scale_factor)
    sprite_offset_y = 18

    animation_timer = 0.0
    run_frame_index = 0
    facing_right = True

    # Punch
    is_punching = False
    punch_index = 0
    punch_timer = 0.0
    PUNCH_FRAME_TIME = 0.07
    # Physique
    vitesse_x = 0
    vitesse_y = 0
    gravite = 70
    gravite_up = 45
    gravite_down = 130
    friction = 80
    double_jump = 2
    prev_jump = False
    prev_punch = False
    local_clock = pygame.time.Clock()
    def death_animation(player_center):
        duration = 700
        start_time = pygame.time.get_ticks()
        max_radius = int(120 * (sw / 1366.0))
        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_time
            if elapsed > duration:
                break
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return
            t = elapsed / duration
            radius = int(max_radius * t)
            alpha = max(0, 255 - int(255 * t))
            screen.blit(background, (0, 0))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(180 * t)))
            screen.blit(overlay, (0, 0))
            s = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 80, 180, alpha), player_center, radius)
            pygame.draw.circle(s,(0, 255, 255, max(0, alpha - 80)),player_center,int(radius * 1.3),4)
            screen.blit(s, (0, 0))

            pygame.display.flip()
            local_clock.tick(60)

    def respawn_animation(player_rect):
        duration = 700
        start_time = pygame.time.get_ticks()

        idle_frame = adv_idle
        frame_w = int(player_rect.width * 1.15)
        frame_h = int(player_rect.height * 1.15)
        idle_sprite = pygame.transform.smoothscale(idle_frame, (frame_w, frame_h))

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_time
            if elapsed > duration:
                break

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return

            t = elapsed / duration
            alpha_sprite = int(255 * t)
            alpha_glow = int(180 * (1 - t))

            screen.blit(background, (0, 0))

            glow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (0, 255, 255, alpha_glow),
                player_rect.inflate(25, 25)

            )
            screen.blit(glow, (0, 0))

            sprite_surf = idle_sprite.copy()
            sprite_surf.set_alpha(alpha_sprite)

            draw_x = player_rect.centerx - frame_w // 2
            draw_y = player_rect.bottom - frame_h + 18
            screen.blit(sprite_surf, (draw_x, draw_y))

            pygame.display.flip()
            local_clock.tick(60)

    # Première anim de spawn
    respawn_animation(player)

    LANCEMENT = True
    while LANCEMENT:
        # Update entrée logique (clavier + joystick)
        dt = clock.tick(FPS) / 1000.0

        # Entrées ARCADE (joystick -> touches logiques du jeu)
        getInput(in_game=True)

        # Bouton 3 du joystick = quitter la simulation (PLAY TEST)
        if joystick_p1 is not None and joystick_p1.get_button(3):
            return


        # Timer punch
        if is_punching:
            punch_timer += dt
            if punch_timer >= PUNCH_FRAME_TIME:
                punch_timer = 0.0
                punch_index += 1
                if punch_index >= len(adv_punch_frames):
                    punch_index = 0
                    is_punching = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        # KEYDOWN logiques via getInput
        jump_pressed = keys[pygame.K_w] and not prev_jump
        punch_pressed = keys[pygame.K_SPACE] and not prev_punch

        if jump_pressed and double_jump > 0:
            double_jump -= 1
            vitesse_y = -20

        if punch_pressed and not is_punching:
            is_punching = True
            punch_index = 0
            punch_timer = 0.0

        prev_jump = keys[pygame.K_w]
        prev_punch = keys[pygame.K_SPACE]

        # Mouvements horizontaux
        if keys[pygame.K_a] and not keys[pygame.K_d]:
            vitesse_x = -12
            facing_right = False
        elif keys[pygame.K_d] and not keys[pygame.K_a]:
            vitesse_x = 12
            facing_right = True
        else:
            if vitesse_x > 0:
                vitesse_x -= friction * dt
                if vitesse_x < 0:
                    vitesse_x = 0
            elif vitesse_x < 0:
                vitesse_x += friction * dt
                if vitesse_x > 0:
                    vitesse_x = 0

        # Gravité
        if keys[pygame.K_w]:
            vitesse_y += gravite_up * dt
        elif keys[pygame.K_s]:
            if vitesse_y < 20:
                vitesse_y = 23
            else:
                vitesse_y += gravite_down * dt
        else:
            vitesse_y += gravite * dt

        # Déplacement X
        x_player += vitesse_x
        player.x = int(x_player)
        for p in platforms:
            if player.colliderect(p):
                if vitesse_x > 0:
                    player.right = p.left
                elif vitesse_x < 0:
                    player.left = p.right

                if not (player.top == p.bottom) and not (player.bottom == p.top):
                    double_jump = 1
                    if not (vitesse_y <= 7):
                        vitesse_y = 8
                x_player = player.x
                vitesse_x = 0

        # Déplacement Y
        y_player += vitesse_y
        player.y = int(y_player)
        on_ground = False
        for p in platforms:
            if player.colliderect(p):
                if vitesse_y > 0:
                    player.bottom = p.top
                    y_player = player.y
                    vitesse_y = 0
                    double_jump = 2
                    on_ground = True
                elif vitesse_y < 0:
                    player.top = p.bottom
                    y_player = player.y
                    vitesse_y = 0

        # Mort (void)
        if player.top > sh:

            death_animation(player.center)

            x_player = float(spawn_x)
            y_player = float(spawn_y)
            player.x = int(x_player)
            player.y = int(y_player)
            vitesse_x = 0
            vitesse_y = 0
            double_jump = 2

            respawn_animation(player)

        # Choix de frame
        animation_timer += dt
        in_air = abs(vitesse_y) > 1 and not on_ground

        if in_air:
            if is_punching:
                base_frame = adv_jump_punch_frames[punch_index % len(adv_jump_punch_frames)]
            else:
                base_frame = adv_jump_up if vitesse_y < 0 else adv_jump_down
        else:
            if is_punching:
                base_frame = adv_punch_frames[punch_index % len(adv_punch_frames)]
            elif abs(vitesse_x) > 1:
                if animation_timer >= 0.10:
                    animation_timer = 0.0
                    run_frame_index = (run_frame_index + 1) % len(adv_run_frames)
                base_frame = adv_run_frames[run_frame_index]
            else:
                base_frame = adv_idle

        frame_to_draw = base_frame
        if not facing_right:
            frame_to_draw = pygame.transform.flip(base_frame, True, False)

        player_image = pygame.transform.smoothscale(frame_to_draw, (sprite_w, sprite_h))

        # DRAW
        screen.blit(background, (0, 0))
        draw_x = player.centerx - sprite_w // 2
        draw_y = player.bottom - sprite_h + sprite_offset_y
        screen.blit(player_image, (draw_x, draw_y))

        pygame.display.flip()


# -----------------------------------------------
# MAP PREVIEW MENU
# -----------------------------------------------
def map_preview_menu():
    btn_back = Button(20, 20, 120, 50, "Retour")
    btn_m1   = Button(WIDTH//2 - 330, HEIGHT - 90, 200, 60, "MAP 1")
    btn_m2   = Button(WIDTH//2 - 100, HEIGHT - 90, 200, 60, "MAP 2")
    btn_m3   = Button(WIDTH//2 + 130, HEIGHT - 90, 200, 60, "MAP 3")
    btn_test = Button(WIDTH - 260, 90, 210, 50, "PLAY TEST")

    # ordre logique des boutons pour la navigation au joystick
    buttons = [btn_m1, btn_m2, btn_m3, btn_test, btn_back]

    selected_index = 0      # bouton surligné au début
    current_index  = 0      # map actuellement affichée (0,1,2)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Navigation via joystick (bouton0 = haut, bouton1 = bas, bouton2 = valider)
        selected_index, validated = joystick_menu_navigation(selected_index, len(buttons))

        # Bouton 3 = retour direct
        if joystick_p1 is not None and joystick_p1.get_button(3):

            return

        # ----------- DESSIN ÉCRAN -----------
        screen.blit(background_img, (0, 0))
        draw_retro_title("MAP PREVIEW", 50)

        # Affichage de la map sélectionnée
        img = map_images[current_index]
        img_x = WIDTH // 2 - img.get_width() // 2
        img_y = int(HEIGHT * 0.2)
        screen.blit(img, (img_x, img_y))

        # Dessin des boutons + highlight visuel
        for i, btn in enumerate(buttons):
            btn.draw()
            if i == selected_index:
                hrect = btn.rect.inflate(14, 14)
                pygame.draw.rect(screen, (255, 255, 0), hrect, 3)

        # Si on valide avec bouton 2
        if validated:

            if selected_index == 0:
                # MAP 1
                current_index = 0
            elif selected_index == 1:
                # MAP 2
                current_index = 1
            elif selected_index == 2:
                # MAP 3
                current_index = 2
            elif selected_index == 3:
                # PLAY TEST sur la map courante
                play_map_sim(current_index)
            elif selected_index == 4:
                # RETOUR
                return

        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# RANKING MENU
# -----------------------------------------------
def ranking_menu():
    btn_back = Button(20, 20, 120, 50, "Retour")

    # index de sélection (0..len(scores) pour Retour)
    selected_index = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.blit(background_img, (0, 0))
        draw_retro_title("RANKING TOP 10", 60)

        # jointure scores + players pour récupérer le pays
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT s.name,
                   COALESCE(p.country, 'Inconnu') AS country,
                   s.score
            FROM scores s
            LEFT JOIN players p ON s.name = p.name
            ORDER BY s.score DESC
            LIMIT 10
        """)
        scores = c.fetchall()
        conn.close()

        # nombre total d'items sélectionnables : chaque joueur + 1 pour "Retour"
        total_items = len(scores) + 1  # le dernier index = bouton Retour

        # Navigation via joystick
        selected_index, validated = joystick_menu_navigation(selected_index, total_items)

        # Bouton 3 = retour direct
        if joystick_p1 is not None and joystick_p1.get_button(3):

            return

        y = 160
        rank = 1

        # Affichage des scores
        for i, (name, country, score) in enumerate(scores):
            txt = FONT.render(f"{rank}. {name} ({country}) — {score}", True, WHITE)
            screen.blit(txt, (WIDTH // 2 - 260, y))

            # Encadrer la ligne si elle est sélectionnée
            if i == selected_index:
                highlight_rect = pygame.Rect(WIDTH // 2 - 270, y - 5, 540, 40)
                pygame.draw.rect(screen, (255, 255, 0), highlight_rect, 3)

            y += 50
            rank += 1

        if len(scores) == 0:
            msg = FONT.render("Aucun score enregistré.", True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 260))

        # Dessin du bouton Retour
        btn_back.draw()

        # highlight du bouton Retour si sélectionné
        if selected_index == len(scores):
            hrect = btn_back.rect.inflate(10, 10)
            pygame.draw.rect(screen, (255, 255, 0), hrect, 3)

        # Action quand on valide (bouton 2)
        if validated:

            if selected_index < len(scores):
                # suppression du joueur sélectionné
                name_to_delete = scores[selected_index][0]
                delete_player(name_to_delete)
            else:
                # dernier item = Retour
                return

        pygame.display.flip()
        clock.tick(FPS)



# -----------------------------------------------
# CHARGEMENT DES IMAGES D'ARMES
# -----------------------------------------------
def load_weapon_images(max_h):

    pistol_raw  = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_pistolet_droite.png")
    sniper_raw  = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_sniper_droite.png")
    shotgun_raw = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_shotgun_droite.png")

    def scale_weapon(img):
        w, h = img.get_width(), img.get_height()
        ratio = max_h / h
        return pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))

    pistol_img  = scale_weapon(pistol_raw)
    sniper_img  = scale_weapon(sniper_raw)
    shotgun_img = scale_weapon(shotgun_raw)

    weapons = [
        {"key": "PISTOL",  "name": "Pistolet", "image": pistol_img},
        {"key": "SNIPER",  "name": "Sniper",   "image": sniper_img},
        {"key": "SHOTGUN", "name": "Shotgun",  "image": shotgun_img},
    ]
    return weapons


# -----------------------------------------------
# MENU ARMES (visuel)
# -----------------------------------------------

# -----------------------------------------------
# MENU CHARACTERS (placeholder)
# -----------------------------------------------
def character_menu():
    btn_back = Button(20, 20, 120, 50, "Retour")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Bouton 3 = retour
        if joystick_p1 and joystick_p1.get_button(3):

            return

        screen.blit(background_img, (0, 0))
        draw_retro_title("CHARACTERS", 60)

        msg = FONT.render("Menu CHARACTERS à venir...", True, WHITE)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2))

        btn_back.draw()
        if btn_back.clicked():

            return

        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# SELECT PERSO VS ORDI
# -----------------------------------------------
def character_select_vs_ai(player_names):
    adv_preview_raw = adv_idle
    ninja_preview_raw = nin_idle

    preview_h = int(HEIGHT * 0.28)
    preview_w = int(preview_h * (SPRITE_WIDTH / SPRITE_HEIGHT))

    adv_preview = pygame.transform.smoothscale(adv_preview_raw, (preview_w, preview_h))
    ninja_preview = pygame.transform.smoothscale(ninja_preview_raw, (preview_w, preview_h))

    characters = [
        {"key": "ADV", "name": "ADVENTURER", "image": adv_preview},
        {"key": "NINJA", "name": "NINJA", "image": ninja_preview},
    ]

    p1_index = 0
    p1_locked = False

    btn_back = Button(20, 20, 120, 50, "Retour")

    deadzone = 0.4
    js_prev_left = js_prev_right = False
    js_prev_select = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # clavier en backup (optionnel)
            if event.type == pygame.KEYDOWN:


                if event.key == pygame.K_ESCAPE:
                    return None, None

                if not p1_locked:
                    if event.key == pygame.K_a:
                        p1_index = (p1_index - 1) % len(characters)
                    elif event.key == pygame.K_d:
                        p1_index = (p1_index + 1) % len(characters)

                    if event.key == pygame.K_LSHIFT:
                        p1_locked = True

        # JOYSTICK 1
        if joystick_p1 is not None:
            ax = joystick_p1.get_axis(0)
            left = ax < -deadzone
            right = ax > deadzone
            select = joystick_p1.get_button(2)
            back = joystick_p1.get_button(3)

            if left and not js_prev_left and not p1_locked:
                p1_index = (p1_index - 1) % len(characters)

            if right and not js_prev_right and not p1_locked:
                p1_index = (p1_index + 1) % len(characters)


            if select and not js_prev_select and not p1_locked:
                p1_locked = True


            if back:

                return None, None

            js_prev_left, js_prev_right = left, right
            js_prev_select = select

        if p1_locked:
            char_p1 = characters[p1_index]["key"]
            char_ai = "NINJA" if char_p1 == "ADV" else "ADV"
            return char_p1, char_ai

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("CHOIX DU PERSONNAGE", 50)

        label_p1 = FONT_BIG.render(f"{player_names[0]} (P1)", True, WHITE)
        label_ai = FONT_BIG.render(f"{player_names[1]} (ORDI)", True, WHITE)
        screen.blit(label_p1, (WIDTH//4 - label_p1.get_width()//2, 120))
        screen.blit(label_ai, (3*WIDTH//4 - label_ai.get_width()//2, 120))

        current_char = characters[p1_index]
        p1_img = current_char["image"]

        p1_x = WIDTH//4 - p1_img.get_width()//2
        p1_y = HEIGHT//2 - p1_img.get_height()//2
        screen.blit(p1_img, (p1_x, p1_y))
        name_p1 = FONT.render(current_char["name"], True, WHITE)
        screen.blit(name_p1,
                    (WIDTH//4 - name_p1.get_width()//2,
                     p1_y + p1_img.get_height() + 10))

        if current_char["key"] == "ADV":
            ai_char = characters[1]
        else:
            ai_char = characters[0]

        ai_img = ai_char["image"]
        ai_x = 3*WIDTH//4 - ai_img.get_width()//2
        ai_y = HEIGHT//2 - ai_img.get_height()//2
        screen.blit(ai_img, (ai_x, ai_y))
        name_ai = FONT.render(ai_char["name"], True, WHITE)
        screen.blit(name_ai,
                    (3*WIDTH//4 - name_ai.get_width()//2,
                     ai_y + ai_img.get_height() + 10))

        hint1 = FONT.render("Joystick 1 : gauche/droite, 2=CONFIRMER, 3=Retour", True, WHITE)
        screen.blit(hint1, (WIDTH//2 - hint1.get_width()//2, HEIGHT - 80))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# MAP SELECT VS ORDI
# -----------------------------------------------
def map_select_vs_ai(player_names):
    btn_back = Button(20, 20, 120, 50, "Retour")

    current_index = 0
    map_names = ["MAP 1", "MAP 2", "MAP 3"]

    deadzone = 0.4
    js_prev_left = js_prev_right = False
    js_prev_select = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if joystick_p1 is not None:
            ax = joystick_p1.get_axis(0)
            left = ax < -deadzone
            right = ax > deadzone
            select = joystick_p1.get_button(2)
            back = joystick_p1.get_button(3)

            if left and not js_prev_left:
                current_index = (current_index - 1) % len(map_images)

            if right and not js_prev_right:
                current_index = (current_index + 1) % len(map_images)


            if select and not js_prev_select:

                return current_index

            if back:

                return None

            js_prev_left, js_prev_right = left, right
            js_prev_select = select

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("CHOIX DE LA MAP (VS ORDI)", 50)

        label_p1 = FONT.render(f"{player_names[0]} (P1)", True, WHITE)
        label_ai = FONT.render(f"{player_names[1]} (ORDI)", True, WHITE)
        screen.blit(label_p1, (WIDTH//4 - label_p1.get_width()//2, 120))
        screen.blit(label_ai, (3*WIDTH//4 - label_ai.get_width()//2, 120))

        thumb_max_h = int(HEIGHT * 0.35)
        thumb_max_w = int(WIDTH * 0.25)
        center_y = HEIGHT // 2 + 20

        for i, img in enumerate(map_images):
            w, h = img.get_width(), img.get_height()
            ratio = min(thumb_max_w / w, thumb_max_h / h)
            thumb = pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))

            if i == 0:
                cx = WIDTH // 4
            elif i == 1:
                cx = WIDTH // 2
            else:
                cx = 3 * WIDTH // 4

            x = cx - thumb.get_width() // 2
            y = center_y - thumb.get_height() // 2

            frame_rect = pygame.Rect(
                x - 10,
                y - 10,
                thumb.get_width() + 20,
                thumb.get_height() + 20
            )

            if i == current_index:
                pygame.draw.rect(screen, (0, 255, 255), frame_rect
                                )
            else:
                pygame.draw.rect(screen, (50, 50, 80), frame_rect
                                )

            screen.blit(thumb, (x, y))

            label = FONT.render(map_names[i], True, WHITE)
            screen.blit(label, (cx - label.get_width()//2,
                                y + thumb.get_height() + 15))

        hint = FONT.render("Joystick 1 : gauche/droite, 2=CONFIRMER, 3=Retour",
                           True, WHITE)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 80))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)


# -----------------------------------------------
# WEAPON SELECT VS ORDI
# -----------------------------------------------
def weapon_select_vs_ai(player_names):
    btn_back = Button(20, 20, 120, 50, "Retour")

    max_h = int(HEIGHT * 0.25)
    weapons = load_weapon_images(max_h)

    p1_index = 0
    p1_ready = False

    deadzone = 0.4
    js_prev_left = js_prev_right = False
    js_prev_select = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if joystick_p1 is not None:
            ax = joystick_p1.get_axis(0)
            left = ax < -deadzone
            right = ax > deadzone
            select = joystick_p1.get_button(2)
            back = joystick_p1.get_button(3)

            if not p1_ready:
                if left and not js_prev_left:
                    p1_index = (p1_index - 1) % len(weapons)

                if right and not js_prev_right:
                    p1_index = (p1_index + 1) % len(weapons)

                if select and not js_prev_select:
                    p1_ready = True


            if back:

                return None, None

            js_prev_left, js_prev_right = left, right
            js_prev_select = select

        if p1_ready:
            weapon_p1 = weapons[p1_index]["key"]
            weapon_ai = random.choice(weapons)["key"]
            return weapon_p1, weapon_ai

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("CHOIX DE L'ARME (VS ORDI)", 50)

        label_p1 = FONT.render(f"{player_names[0]} (P1)", True, WHITE)
        label_ai = FONT.render(f"{player_names[1]} (ORDI)", True, WHITE)
        screen.blit(label_p1, (WIDTH//4 - label_p1.get_width()//2, 120))
        screen.blit(label_ai, (3*WIDTH//4 - label_ai.get_width()//2, 120))

        center_y = HEIGHT // 2 + 20
        positions = [WIDTH // 4, WIDTH // 2, 3 * WIDTH // 4]

        for i, weapon in enumerate(weapons):
            img = weapon["image"]
            cx = positions[i]
            x = cx - img.get_width() // 2
            y = center_y - img.get_height() // 2

            frame_rect = pygame.Rect(
                x - 10, y - 10,
                img.get_width() + 20,
                img.get_height() + 20
            )

            if i == p1_index:
                border_color = (255, 120, 150)
                border_width = 5
            else:
                border_color = (50, 50, 80)
                border_width = 2

            pygame.draw.rect(screen, border_color, frame_rect)
            screen.blit(img, (x, y))

            name_surf = FONT.render(weapon["name"], True, WHITE)
            screen.blit(name_surf, (cx - name_surf.get_width()//2,
                                    y + img.get_height() + 10))

        hint = FONT.render("Joystick 1 : gauche/droite, 2=READY, 3=Retour",
                           True, WHITE)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 80))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)



# -----------------------------------------------
# WEAPON SELECT 1v1
# -----------------------------------------------
def weapon_select_1v1(player_names):
    btn_back = Button(20, 20, 120, 50, "Retour")

    max_h = int(HEIGHT * 0.25)
    weapons = load_weapon_images(max_h)

    p1_index = 0
    p2_index = 1
    p1_ready = False
    p2_ready = False

    deadzone = 0.4

    js1_prev_left = js1_prev_right = False
    js1_prev_select = False

    js2_prev_left = js2_prev_right = False
    js2_prev_select = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # JOYSTICK P1
        if joystick_p1 is not None:
            ax1 = joystick_p1.get_axis(0)
            left1 = ax1 < -deadzone
            right1 = ax1 > deadzone
            select1 = joystick_p1.get_button(2)
            back1 = joystick_p1.get_button(3)

            if not p1_ready:
                if left1 and not js1_prev_left:
                    p1_index = (p1_index - 1) % len(weapons)

                if right1 and not js1_prev_right:
                    p1_index = (p1_index + 1) % len(weapons)

                if select1 and not js1_prev_select:
                    p1_ready = True


            if back1:

                return None, None

            js1_prev_left, js1_prev_right = left1, right1
            js1_prev_select = select1

        # JOYSTICK P2
        if joystick_p2 is not None:
            ax2 = joystick_p2.get_axis(0)
            left2 = ax2 < -deadzone
            right2 = ax2 > deadzone
            select2 = joystick_p2.get_button(2)

            if not p2_ready:
                if left2 and not js2_prev_left:
                    p2_index = (p2_index - 1) % len(weapons)

                if right2 and not js2_prev_right:
                    p2_index = (p2_index + 1) % len(weapons)

                if select2 and not js2_prev_select:
                    p2_ready = True


            js2_prev_left, js2_prev_right = left2, right2
            js2_prev_select = select2

        if p1_ready and p2_ready:
            weapon_p1 = weapons[p1_index]["key"]
            weapon_p2 = weapons[p2_index]["key"]
            return weapon_p1, weapon_p2

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("CHOIX DES ARMES (1 vs 1)", 50)

        label_p1 = FONT.render(
            f"{player_names[0]} (P1) {'[READY]' if p1_ready else ''}", True, WHITE
        )
        label_p2 = FONT.render(
            f"{player_names[1]} (P2) {'[READY]' if p2_ready else ''}", True, WHITE
        )
        screen.blit(label_p1, (WIDTH//4 - label_p1.get_width()//2, 120))
        screen.blit(label_p2, (3*WIDTH//4 - label_p2.get_width()//2, 120))

        center_y = HEIGHT // 2 + 20
        positions = [WIDTH // 4, WIDTH // 2, 3 * WIDTH // 4]

        for i, weapon in enumerate(weapons):
            img = weapon["image"]
            cx = positions[i]
            x = cx - img.get_width() // 2
            y = center_y - img.get_height() // 2

            frame_rect = pygame.Rect(
                x - 10, y - 10,
                img.get_width() + 20,
                img.get_height() + 20
            )

            selected_by_p1 = (i == p1_index)
            selected_by_p2 = (i == p2_index)

            if selected_by_p1 and selected_by_p2:
                border_color = (255, 215, 0)
                border_width = 6
            elif selected_by_p1:
                border_color = (255, 120, 150)
                border_width = 4
            elif selected_by_p2:
                border_color = (120, 180, 255)
                border_width = 4
            else:
                border_color = (50, 50, 80)
                border_width = 2

            pygame.draw.rect(screen, border_color, frame_rect
                             )
            screen.blit(img, (x, y))

            name_surf = FONT.render(weapon["name"], True, WHITE)
            screen.blit(name_surf, (cx - name_surf.get_width()//2,
                                    y + img.get_height() + 10))

        hint1 = FONT.render("P1 (Joystick 1) : gauche/droite + 2=READY, 3=Retour", True, WHITE)
        hint2 = FONT.render("P2 (Joystick 2) : gauche/droite + 2=READY", True, WHITE)
        screen.blit(hint1, (WIDTH//2 - hint1.get_width()//2, HEIGHT - 110))
        screen.blit(hint2, (WIDTH//2 - hint2.get_width()//2, HEIGHT - 80))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)

# -----------------------------------------------
# MAP SELECT 1v1
# -----------------------------------------------
def map_select_1v1(player_names):
    btn_back = Button(20, 20, 120, 50, "Retour")

    map_names = ["MAP 1", "MAP 2", "MAP 3"]

    map_index_p1 = 0
    map_index_p2 = 1
    p1_ready = False
    p2_ready = False

    deadzone = 0.4

    js1_prev_left = js1_prev_right = False
    js1_prev_select = False

    js2_prev_left = js2_prev_right = False
    js2_prev_select = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # JOYSTICK P1
        if joystick_p1 is not None:
            ax1 = joystick_p1.get_axis(0)
            left1 = ax1 < -deadzone
            right1 = ax1 > deadzone
            select1 = joystick_p1.get_button(2)
            back1 = joystick_p1.get_button(3)

            if not p1_ready:
                if left1 and not js1_prev_left:
                    map_index_p1 = (map_index_p1 - 1) % len(map_images)

                if right1 and not js1_prev_right:
                    map_index_p1 = (map_index_p1 + 1) % len(map_images)

                if select1 and not js1_prev_select:
                    p1_ready = True


            if back1:

                return None

            js1_prev_left, js1_prev_right = left1, right1
            js1_prev_select = select1

        # JOYSTICK P2
        if joystick_p2 is not None:
            ax2 = joystick_p2.get_axis(0)
            left2 = ax2 < -deadzone
            right2 = ax2 > deadzone
            select2 = joystick_p2.get_button(2)

            if not p2_ready:
                if left2 and not js2_prev_left:
                    map_index_p2 = (map_index_p2 - 1) % len(map_images)

                if right2 and not js2_prev_right:
                    map_index_p2 = (map_index_p2 + 1) % len(map_images)

                if select2 and not js2_prev_select:
                    p2_ready = True


            js2_prev_left, js2_prev_right = left2, right2
            js2_prev_select = select2

        if p1_ready and p2_ready:
            chosen_index = random.choice([map_index_p1, map_index_p2])
            return chosen_index

        # ----- DESSIN -----
        screen.blit(background_img, (0, 0))
        draw_retro_title("CHOIX DE LA MAP (1 vs 1)", 50)

        label_p1 = FONT.render(
            f"{player_names[0]} (P1) {'[READY]' if p1_ready else ''}",
            True, WHITE
        )
        label_p2 = FONT.render(
            f"{player_names[1]} (P2) {'[READY]' if p2_ready else ''}",
            True, WHITE
        )
        screen.blit(label_p1, (WIDTH//4 - label_p1.get_width()//2, 120))
        screen.blit(label_p2, (3*WIDTH//4 - label_p2.get_width()//2, 120))

        thumb_max_h = int(HEIGHT * 0.35)
        thumb_max_w = int(WIDTH * 0.25)
        center_y = HEIGHT // 2 + 20

        for i, img in enumerate(map_images):
            w, h = img.get_width(), img.get_height()
            ratio = min(thumb_max_w / w, thumb_max_h / h)
            thumb = pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))

            if i == 0:
                cx = WIDTH // 4
            elif i == 1:
                cx = WIDTH // 2
            else:
                cx = 3 * WIDTH // 4

            x = cx - thumb.get_width() // 2
            y = center_y - thumb.get_height() // 2

            frame_rect = pygame.Rect(
                x - 10,
                y - 10,
                thumb.get_width() + 20,
                thumb.get_height() + 20
            )

            selected_by_p1 = (i == map_index_p1)
            selected_by_p2 = (i == map_index_p2)

            if selected_by_p1 and selected_by_p2:
                border_color = (255, 215, 0)
                border_width = 6
            elif selected_by_p1:
                border_color = (255, 120, 150)
                border_width = 4
            elif selected_by_p2:
                border_color = (120, 180, 255)
                border_width = 4
            else:
                border_color = (50, 50, 80)
                border_width = 2

            pygame.draw.rect(screen, border_color, frame_rect)

            screen.blit(thumb, (x, y))

            label = FONT.render(map_names[i], True, WHITE)
            screen.blit(label, (cx - label.get_width()//2,
                                y + thumb.get_height() + 15))

        hint1 = FONT.render("P1 (Joystick 1) : gauche/droite + 2=READY, 3=Retour", True, WHITE)
        hint2 = FONT.render("P2 (Joystick 2) : gauche/droite + 2=READY", True, WHITE)
        screen.blit(hint1, (WIDTH//2 - hint1.get_width()//2, HEIGHT - 110))
        screen.blit(hint2, (WIDTH//2 - hint2.get_width()//2, HEIGHT - 80))

        btn_back.draw()
        pygame.display.flip()
        clock.tick(FPS)



def play_ordi(map_index, char_p1, player_names):
    """
    Match 1 vs ORDI (AI) avec stocks, HP et compte à rebours.
    Utilise la même physique que play_map_sim.
    player_names[0] = nom du joueur humain
    player_names[1] = "ORDI"
    """

    # --- Platformes (copie de play_map_sim) ---
    if map_index == 0:
        platforms = [
            rel_rect(0.2448, 0.4537, 0.2188, 0.3056, sw, sh),
            rel_rect(0.5443, 0.5370, 0.2239, 0.3056, sw, sh),
            rel_rect(0.5630, 0.3481, 0.1375, 0.0278, sw, sh)
        ]
    elif map_index == 1:
        platforms = [
            rel_rect(0.2656, 0.4676, 0.4661, 0.3241, sw, sh),
            rel_rect(0.2750, 0.2528, 0.1495, 0.0278, sw, sh),
            rel_rect(0.5693, 0.2528, 0.1495, 0.0278, sw, sh)
        ]
    else:
        platforms = [
            rel_rect(0.2901, 0.6481, 0.3844, 0.2129, sw, sh),
            rel_rect(0.2698, 0.4444, 0.1323, 0.0185, sw, sh),
            rel_rect(0.6224, 0.2685, 0.1083, 0.1389, sw, sh)
        ]

    # --- Background (copie de play_map_sim) ---
    if map_index == 0:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map4.png")

    elif map_index == 1:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map2.png")

    else:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map3.png")


    background = pygame.transform.smoothscale(background, (sw, sh))

    # --- Spawn des persos (sur la plateforme principale) ---
    base_plat = platforms[0]
    spawn_y = base_plat.top - 100
    spawn_p1_x = base_plat.left + 60
    spawn_ai_x = base_plat.right - 110

    p1 = pygame.Rect(spawn_p1_x, spawn_y, 50, 100)
    ai = pygame.Rect(spawn_ai_x, spawn_y, 50, 100)

    x_p1, y_p1 = float(p1.x), float(p1.y)
    x_ai, y_ai = float(ai.x), float(ai.y)

    # --- Sprite et anim (copie de play_map_sim, pour 2 persos) ---
    scale_factor = 1.5
    sprite_w = int(p1.width * scale_factor)
    sprite_h = int(p1.height * scale_factor)
    sprite_offset_y = 18

    # P1 anim
    anim_timer_p1 = 0.0
    run_frame_idx_p1 = 0
    facing_right_p1 = True

    is_punching_p1 = False
    punch_idx_p1 = 0
    punch_timer_p1 = 0.0

    # AI anim
    anim_timer_ai = 0.0
    run_frame_idx_ai = 0
    facing_right_ai = False

    is_punching_ai = False
    punch_idx_ai = 0
    punch_timer_ai = 0.0

    PUNCH_FRAME_TIME = 0.07

    # cooldown + one-hit-per-punch
    PUNCH_COOLDOWN = 0.35  # secondes entre deux coups
    punch_cooldown_p1 = 0.0
    punch_cooldown_ai = 0.0
    can_hit_p1 = True
    can_hit_ai = True

    # --- Physique ---
    vitesse_x_p1 = 0.0
    vitesse_y_p1 = 0.0
    vitesse_x_ai = 0.0
    vitesse_y_ai = 0.0

    gravite = 90
    gravite_up = 45
    gravite_down = 130
    friction = 80
    double_jump_p1 = 2
    double_jump_ai = 2

    prev_jump_p1 = False
    prev_punch_p1 = False

    # --- HP & Stocks ---
    MAX_HP = 100
    hp_p1 = MAX_HP
    hp_ai = MAX_HP
    stocks_p1 = 3
    stocks_ai = 3

    winner = None  # "P1" ou "ORDI"

    # état pour le recover AI
    ai_recovering = False

    def ai_recover_platform():
        """
        Quand l'ORDI glisse / tombe sous les plateformes, essaie de revenir
        vers la plateforme la plus proche et saute pour remonter.
        """
        nonlocal vitesse_x_ai, vitesse_y_ai, double_jump_ai, ai_recovering, facing_right_ai

        if double_jump_ai <= 0 or ai_recovering:
            return

        target_plat = min(platforms, key=lambda p: abs(p.centerx - ai.centerx))

        if ai.centerx < target_plat.centerx:
            vitesse_x_ai = 6
            facing_right_ai = True
        else:
            vitesse_x_ai = -6
            facing_right_ai = False

        double_jump_ai -= 1
        vitesse_y_ai = -23
        ai_recovering = True

    # --- Compte à rebours 3-2-1-GO ---
    countdown_labels = ["3", "2", "1", "GO!"]
    for label in countdown_labels:
        start = pygame.time.get_ticks()
        while True:
            dt = clock.tick(FPS) / 1000.0
            now = pygame.time.get_ticks()
            if now - start >= 1000:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            screen.blit(background, (0, 0))
            if char_p1 == "ADV":
                frame_idle_p1 = adv_idle
                frame_idle_ai = nin_idle
            else:
                frame_idle_p1 = nin_idle
                frame_idle_ai = adv_idle

            sprite_p1 = pygame.transform.smoothscale(frame_idle_p1, (sprite_w, sprite_h))
            sprite_ai = pygame.transform.smoothscale(frame_idle_ai, (sprite_w, sprite_h))

            draw_x_p1 = p1.centerx - sprite_w // 2
            draw_y_p1 = p1.bottom - sprite_h + sprite_offset_y
            draw_x_ai = ai.centerx - sprite_w // 2
            draw_y_ai = ai.bottom - sprite_h + sprite_offset_y

            screen.blit(sprite_p1, (draw_x_p1, draw_y_p1))
            screen.blit(sprite_ai, (draw_x_ai, draw_y_ai))

            hp_text_p1 = FONT.render(f"P1 HP: {hp_p1}", True, (255, 255, 255))
            hp_text_ai = FONT.render(f"ORDI HP: {hp_ai}", True, (255, 255, 255))
            stock_text_p1 = FONT.render(f"Stocks: {stocks_p1}", True, (255, 255, 0))
            stock_text_ai = FONT.render(f"Stocks: {stocks_ai}", True, (255, 255, 0))

            screen.blit(hp_text_p1, (40, 40))
            screen.blit(stock_text_p1, (40, 70))
            screen.blit(hp_text_ai, (sw - hp_text_ai.get_width() - 40, 40))
            screen.blit(stock_text_ai, (sw - stock_text_ai.get_width() - 40, 70))

            label_surf = TITLE_FONT.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=(sw // 2, sh // 2))
            screen.blit(label_surf, label_rect)

            pygame.display.flip()

    def respawn_animation(player_rect):
        duration = 100
        start_time = pygame.time.get_ticks()

        idle_frame = adv_idle
        frame_w = int(player_rect.width * 1.15)
        frame_h = int(player_rect.height * 1.15)
        idle_sprite = pygame.transform.smoothscale(idle_frame, (frame_w, frame_h))

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_time
            if elapsed > duration:
                break

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return

            t = elapsed / duration
            alpha_sprite = int(255 * t)
            alpha_glow = int(180 * (1 - t))

            screen.blit(background, (0, 0))

            glow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (0, 255, 255, alpha_glow),
                player_rect.inflate(25, 25),

            )
            screen.blit(glow, (0, 0))

            sprite_surf = idle_sprite.copy()
            sprite_surf.set_alpha(alpha_sprite)

            draw_x = player_rect.centerx - frame_w // 2
            draw_y = player_rect.bottom - frame_h + 18
            screen.blit(sprite_surf, (draw_x, draw_y))

            pygame.display.flip()
            clock.tick(60)

    # --- Boucle principale de match ---
    running = True
    while running:
        dt = clock.tick(FPS) / 1500

        getInput(in_game=True)

        if punch_cooldown_p1 > 0:
            punch_cooldown_p1 -= dt
        if punch_cooldown_ai > 0:
            punch_cooldown_ai -= dt

        if is_punching_p1:
            punch_timer_p1 += dt
            if punch_timer_p1 >= PUNCH_FRAME_TIME:
                punch_timer_p1 = 0.0
                punch_idx_p1 += 1
                if punch_idx_p1 >= len(adv_punch_frames):
                    punch_idx_p1 = 0
                    is_punching_p1 = False
                    can_hit_p1 = True

        if is_punching_ai:
            punch_timer_ai += dt
            if punch_timer_ai >= PUNCH_FRAME_TIME:
                punch_timer_ai = 0.0
                punch_idx_ai += 1
                if punch_idx_ai >= len(adv_punch_frames):
                    punch_idx_ai = 0
                    is_punching_ai = False
                    can_hit_ai = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        # --- Entrées P1 ---
        jump_pressed_p1 = keys[pygame.K_w] and not prev_jump_p1
        punch_pressed_p1 = keys[pygame.K_SPACE] and not prev_punch_p1

        if jump_pressed_p1 and double_jump_p1 > 0:
            double_jump_p1 -= 1
            vitesse_y_p1 = -20

        if punch_pressed_p1 and not is_punching_p1 and punch_cooldown_p1 <= 0:
            is_punching_p1 = True
            punch_idx_p1 = 0
            punch_timer_p1 = 0.0
            punch_cooldown_p1 = PUNCH_COOLDOWN
            can_hit_p1 = True

        prev_jump_p1 = keys[pygame.K_w]
        prev_punch_p1 = keys[pygame.K_SPACE]

        if keys[pygame.K_a] and not keys[pygame.K_d]:
            vitesse_x_p1 = -12
            facing_right_p1 = False
        elif keys[pygame.K_d] and not keys[pygame.K_a]:
            vitesse_x_p1 = 12
            facing_right_p1 = True
        else:
            if vitesse_x_p1 > 0:
                vitesse_x_p1 -= friction * dt
                if vitesse_x_p1 < 0:
                    vitesse_x_p1 = 0
            elif vitesse_x_p1 < 0:
                vitesse_x_p1 += friction * dt
                if vitesse_x_p1 > 0:
                    vitesse_x_p1 = 0

        if keys[pygame.K_w]:
            vitesse_y_p1 += gravite_up * dt
        elif keys[pygame.K_s]:
            if vitesse_y_p1 < 20:
                vitesse_y_p1 = 23
            else:
                vitesse_y_p1 += gravite_down * dt
        else:
            vitesse_y_p1 += gravite * dt

        # --- IA ORDI ---
        ai_speed = 6
        if abs(ai.centerx - p1.centerx) > 15:
            if ai.centerx < p1.centerx:
                vitesse_x_ai = ai_speed
                facing_right_ai = True
            else:
                vitesse_x_ai = -ai_speed
                facing_right_ai = False
        else:
            vitesse_x_ai = random.randint(-ai_speed, ai_speed)

        vitesse_y_ai += gravite * dt

        if double_jump_ai > 0 and random.random() < 0.0085:
            double_jump_ai -= 1
            vitesse_y_ai = -20

        close_x = abs(ai.centerx - p1.centerx) < 60
        close_y = abs(ai.bottom - p1.bottom) < 40
        if ((not is_punching_ai) and close_x and close_y
                and punch_cooldown_ai <= 0 and random.random() < 0.4):
            is_punching_ai = True
            punch_idx_ai = 0
            punch_timer_ai = 0.0
            punch_cooldown_ai = PUNCH_COOLDOWN + 0.15
            can_hit_ai = True

        # --- Mouvements + collisions P1 ---
        x_p1 += vitesse_x_p1
        p1.x = int(x_p1)
        for plat in platforms:
            if p1.colliderect(plat):
                if vitesse_x_p1 > 0:
                    p1.right = plat.left
                elif vitesse_x_p1 < 0:
                    p1.left = plat.right

                if not (p1.top == plat.bottom) and not (p1.bottom == plat.top):
                    double_jump_p1 = 1
                    if not (vitesse_y_p1 <= 7):
                        vitesse_y_p1 = 8
                x_p1 = p1.x
                vitesse_x_p1 = 0

        y_p1 += vitesse_y_p1
        p1.y = int(y_p1)
        on_ground_p1 = False
        for plat in platforms:
            if p1.colliderect(plat):
                if vitesse_y_p1 > 0:
                    p1.bottom = plat.top
                    y_p1 = p1.y
                    vitesse_y_p1 = 0
                    double_jump_p1 = 2
                    on_ground_p1 = True
                elif vitesse_y_p1 < 0:
                    p1.top = plat.bottom
                    y_p1 = p1.y
                    vitesse_y_p1 = 0

        # --- Mouvements + collisions AI ---
        x_ai += vitesse_x_ai
        ai.x = int(x_ai)
        for plat in platforms:
            if ai.colliderect(plat):
                if vitesse_x_ai > 0:
                    ai.right = plat.left
                elif vitesse_x_ai < 0:
                    ai.left = plat.right
                x_ai = ai.x
                vitesse_x_ai = 0

        y_ai += vitesse_y_ai
        ai.y = int(y_ai)
        on_ground_ai = False
        for plat in platforms:
            if ai.colliderect(plat):
                if vitesse_y_ai > 0:
                    ai.bottom = plat.top
                    y_ai = ai.y
                    vitesse_y_ai = 0
                    double_jump_ai = 2
                    on_ground_ai = True
                    ai_recovering = False
                elif vitesse_y_ai < 0:
                    ai.top = plat.bottom
                    y_ai = ai.y
                    vitesse_y_ai = 0

        if (not on_ground_ai) and vitesse_y_ai > 0 and ai.bottom > sh * 0.75:
            ai_recover_platform()

        # --- Chute dans le vide (stocks) ---
        if p1.top > sh:

            stocks_p1 -= 1
            respawn_animation(p1)
            if stocks_p1 <= 0:
                winner = "ORDI"
                running = False
            else:
                x_p1 = float(spawn_p1_x)
                y_p1 = float(spawn_y)
                p1.x = int(x_p1)
                p1.y = int(y_p1)
                vitesse_x_p1 = 0
                vitesse_y_p1 = 0
                double_jump_p1 = 2
                hp_p1 = MAX_HP

        if ai.top > sh:

            stocks_ai -= 1
            respawn_animation(ai)
            if stocks_ai <= 0:
                winner = "P1"
                running = False
            else:
                x_ai = float(spawn_ai_x)
                y_ai = float(spawn_y)
                ai.x = int(x_ai)
                ai.y = int(y_ai)
                vitesse_x_ai = 0
                vitesse_y_ai = 0
                double_jump_ai = 2
                hp_ai = MAX_HP
                ai_recovering = False

        if not running:
            break

        # --- Dégâts des punches ---
        if is_punching_p1 and can_hit_p1:
            if facing_right_p1:
                hitbox_p1 = pygame.Rect(p1.right, p1.y + 20, 40, 40)
            else:
                hitbox_p1 = pygame.Rect(p1.left - 40, p1.y + 20, 40, 40)
            if hitbox_p1.colliderect(ai):
                can_hit_p1 = False
                hp_ai -= 8
                if facing_right_p1:
                    x_ai += 12
                else:
                    x_ai -= 12
                y_ai -= 10
                ai.x = int(x_ai)
                ai.y = int(y_ai)
                vitesse_y_ai = -10

        if is_punching_ai and can_hit_ai:
            if facing_right_ai:
                hitbox_ai = pygame.Rect(ai.right, ai.y + 20, 40, 40)
            else:
                hitbox_ai = pygame.Rect(ai.left - 40, ai.y + 20, 40, 40)
            if hitbox_ai.colliderect(p1):
                can_hit_ai = False
                hp_p1 -= 8
                if facing_right_ai:
                    x_p1 += 12
                else:
                    x_p1 -= 12
                y_p1 -= 10
                p1.x = int(x_p1)
                p1.y = int(y_p1)
                vitesse_y_p1 = -10

        if hp_p1 <= 0:
            stocks_p1 -= 1
            respawn_animation(p1)
            if stocks_p1 <= 0:
                winner = "ORDI"
                running = False
            else:
                hp_p1 = MAX_HP
                x_p1 = float(spawn_p1_x)
                y_p1 = float(spawn_y)
                p1.x = int(x_p1)
                p1.y = int(y_p1)
                vitesse_x_p1 = 0
                vitesse_y_p1 = 0
                double_jump_p1 = 2

        if hp_ai <= 0:
            stocks_ai -= 1
            respawn_animation(ai)
            if stocks_ai <= 0:
                winner = "P1"
                running = False
            else:
                hp_ai = MAX_HP
                x_ai = float(spawn_ai_x)
                y_ai = float(spawn_y)
                ai.x = int(x_ai)
                ai.y = int(y_ai)
                vitesse_x_ai = 0
                vitesse_y_ai = 0
                double_jump_ai = 2
                ai_recovering = False

        if not running:
            break

        # --- Animation P1 ---
        anim_timer_p1 += dt
        in_air_p1 = abs(vitesse_y_p1) > 1 and not on_ground_p1
        if char_p1 == "ADV":
            if in_air_p1:
                if is_punching_p1:
                    base_frame_p1 = adv_jump_punch_frames[punch_idx_p1 % len(adv_jump_punch_frames)]
                else:
                    base_frame_p1 = adv_jump_up if vitesse_y_p1 < 0 else adv_jump_down
            else:
                if is_punching_p1:
                    base_frame_p1 = adv_punch_frames[punch_idx_p1 % len(adv_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(adv_run_frames)
                    base_frame_p1 = adv_run_frames[run_frame_idx_p1]
                else:
                    base_frame_p1 = adv_idle
        else:
            if in_air_p1:
                if is_punching_p1:
                    base_frame_p1 = nin_jump_punch_frames[punch_idx_p1 % len(nin_jump_punch_frames)]
                else:
                    base_frame_p1 = nin_jump_up if vitesse_y_p1 < 0 else nin_jump_down
            else:
                if is_punching_p1:
                    base_frame_p1 = nin_punch_frames[punch_idx_p1 % len(nin_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(nin_run_frames)
                    base_frame_p1 = nin_run_frames[run_frame_idx_p1]
                else:
                    base_frame_p1 = nin_idle

        frame_p1 = base_frame_p1
        if not facing_right_p1:
            frame_p1 = pygame.transform.flip(base_frame_p1, True, False)
        sprite_p1 = pygame.transform.smoothscale(frame_p1, (sprite_w, sprite_h))

        # --- Animation AI ---
        anim_timer_ai += dt
        in_air_ai = abs(vitesse_y_ai) > 1 and not on_ground_ai
        if char_p1 == "NINJA":
            if in_air_ai:
                if is_punching_p1:
                    base_frame_ai = adv_jump_punch_frames[punch_idx_p1 % len(adv_jump_punch_frames)]
                else:
                    base_frame_ai = adv_jump_up if vitesse_y_p1 < 0 else adv_jump_down
            else:
                if is_punching_p1:
                    base_frame_ai = adv_punch_frames[punch_idx_p1 % len(adv_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(adv_run_frames)
                    base_frame_ai = adv_run_frames[run_frame_idx_p1]
                else:
                    base_frame_ai = adv_idle
        else:
            if in_air_ai:
                if is_punching_p1:
                    base_frame_ai = nin_jump_punch_frames[punch_idx_p1 % len(nin_jump_punch_frames)]
                else:
                    base_frame_ai = nin_jump_up if vitesse_y_p1 < 0 else nin_jump_down
            else:
                if is_punching_p1:
                    base_frame_ai = nin_punch_frames[punch_idx_p1 % len(nin_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(nin_run_frames)
                    base_frame_ai = nin_run_frames[run_frame_idx_p1]
                else:
                    base_frame_ai = nin_idle

        frame_ai = base_frame_ai
        if not facing_right_ai:
            frame_ai = pygame.transform.flip(base_frame_ai, True, False)
        sprite_ai = pygame.transform.smoothscale(frame_ai, (sprite_w, sprite_h))

        screen.blit(background, (0, 0))

        draw_x_p1 = p1.centerx - sprite_w // 2
        draw_y_p1 = p1.bottom - sprite_h + sprite_offset_y
        draw_x_ai = ai.centerx - sprite_w // 2
        draw_y_ai = ai.bottom - sprite_h + sprite_offset_y

        screen.blit(sprite_p1, (draw_x_p1, draw_y_p1))
        screen.blit(sprite_ai, (draw_x_ai, draw_y_ai))

        name_p1 = FONT.render("P1", True, (255, 220, 220))
        name_ai = FONT.render("ORDI", True, (200, 220, 255))
        screen.blit(name_p1, (p1.centerx - name_p1.get_width()//2, p1.top - 25))
        screen.blit(name_ai, (ai.centerx - name_ai.get_width()//2, ai.top - 25))

        hp_text_p1 = FONT.render(f"HP: {hp_p1}", True, (255, 255, 255))
        hp_text_ai = FONT.render(f"HP: {hp_ai}", True, (255, 255, 255))
        stock_text_p1 = FONT.render(f"Stocks: {stocks_p1}", True, (255, 255, 0))
        stock_text_ai = FONT.render(f"Stocks: {stocks_ai}", True, (255, 255, 0))

        screen.blit(hp_text_p1, (40, 40))
        screen.blit(stock_text_p1, (40, 70))
        screen.blit(hp_text_ai, (sw - hp_text_ai.get_width() - 40, 40))
        screen.blit(stock_text_ai, (sw - stock_text_ai.get_width() - 40, 70))

        pygame.display.flip()

    # --- Mise à jour du ranking si le joueur humain gagne ---


    if winner == "P1":
        add_win(player_names[0])
        # (Optionnel : compter aussi les victoires de l'ORDI)
        # elif winner == "ORDI":
        #     add_win(player_names[1])

        # --- Écran de fin : affiche le vainqueur + retour au lobby (JOYSTICK) ---
    if winner is not None:
        btn_back = Button(WIDTH // 2 - 150, HEIGHT - 120, 300, 70, "Retour au lobby")

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Validation avec le joystick (borne arcade)
            if joystick_p1 is not None:
                # bouton 2 = OK / bouton 3 = retour
                if joystick_p1.get_button(2) or joystick_p1.get_button(3):

                    return ranking_menu()

            screen.blit(background_img, (0, 0))
            draw_retro_title("VICTOIRE !", 100)

            if winner == "P1":
                txt = "Le joueur 1 gagne !"
            else:
                txt = "L'ORDI gagne !"

            win_text = FONT_BIG.render(txt, True, WHITE)
            screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - 40))

            # Bouton visuel (toujours dessiné, mais plus besoin de souris)
            btn_back.draw()

            pygame.display.flip()
            clock.tick(FPS)

def play_players(map_index, char_p1, char_p2, player_names=player_names):
    """
    Match 1 vs 1 avec stocks, % de dégâts et compte à rebours.
    Compatible borne arcade : 2 joysticks (joystick_p1, joystick_p2)
    - P1 : joystick 0
    - P2 : joystick 1
    Boutons :
      0 = Jump
      2 = Punch
      3 = Quitter / Retour au lobby
    """

    # --- Platformes (copie de play_map_sim) ---
    if map_index == 0:
        platforms = [
            rel_rect(0.2448, 0.4537, 0.2188, 0.3056, sw, sh),
            rel_rect(0.5443, 0.5370, 0.2239, 0.3056, sw, sh),
            rel_rect(0.5630, 0.3481, 0.1375, 0.0278, sw, sh)
        ]
    elif map_index == 1:
        platforms = [
            rel_rect(0.2656, 0.4676, 0.4661, 0.3241, sw, sh),
            rel_rect(0.2750, 0.2528, 0.1495, 0.0278, sw, sh),
            rel_rect(0.5693, 0.2528, 0.1495, 0.0278, sw, sh)
        ]
    else:
        platforms = [
            rel_rect(0.2901, 0.6481, 0.3844, 0.2129, sw, sh),
            rel_rect(0.2698, 0.4444, 0.1323, 0.0185, sw, sh),
            rel_rect(0.6224, 0.2685, 0.1083, 0.1389, sw, sh)
        ]

    # --- Background (copie de play_map_sim) ---
    if map_index == 0:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map4.png")


    elif map_index == 1:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map2.png")


    else:

        background = pygame.image.load("/home/pi/RetroPie/roms/pygame/AB/AB_map3.png")


    background = pygame.transform.smoothscale(background, (sw, sh))

    # --- Spawn des persos (sur la plateforme principale) ---
    base_plat = platforms[0]
    spawn_y = base_plat.top - 100
    spawn_p1_x = base_plat.left + 60
    spawn_p2_x = base_plat.right - 110

    p1 = pygame.Rect(spawn_p1_x, spawn_y, 50, 100)
    p2 = pygame.Rect(spawn_p2_x, spawn_y, 50, 100)

    x_p1, y_p1 = float(p1.x), float(p1.y)
    x_p2, y_p2 = float(p2.x), float(p2.y)

    # --- Sprite / anim pour 2 persos ---
    scale_factor = 1.5
    sprite_w = int(p1.width * scale_factor)
    sprite_h = int(p1.height * scale_factor)
    sprite_offset_y = 18

    # Anim P1
    anim_timer_p1 = 0.0
    run_frame_idx_p1 = 0
    facing_right_p1 = True

    is_punching_p1 = False
    punch_idx_p1 = 0
    punch_timer_p1 = 0.0

    # Anim P2
    anim_timer_p2 = 0.0
    run_frame_idx_p2 = 0
    facing_right_p2 = False

    is_punching_p2 = False
    punch_idx_p2 = 0
    punch_timer_p2 = 0.0

    local_clock = pygame.time.Clock()
    PUNCH_FRAME_TIME = 0.07

    # cooldown + one-hit-per-punch
    PUNCH_COOLDOWN = 0.35
    punch_cooldown_p1 = 0.0
    punch_cooldown_p2 = 0.0
    can_hit_p1 = True
    can_hit_p2 = True

    # --- Physique ---
    vitesse_x_p1 = 0.0
    vitesse_y_p1 = 0.0
    vitesse_x_p2 = 0.0
    vitesse_y_p2 = 0.0

    gravite = 50
    gravite_up = 35
    gravite_down = 130
    friction = 80
    double_jump_p1 = 2
    double_jump_p2 = 2

    prev_jump_p1 = False
    prev_punch_p1 = False
    prev_jump_p2 = False
    prev_punch_p2 = False

    # --- HP & Stocks façon Smash (0% au départ, augmente avec les coups) ---
    MAX_HP = 0
    hp_p1 = MAX_HP
    hp_p2 = MAX_HP
    basic_degat = 10
    degat_coup = 10
    stocks_p1 = 3
    stocks_p2 = 3

    winner = None  # "P1" ou "P2"

    # --- Compte à rebours 3-2-1-GO ---
    countdown_labels = ["3", "2", "1", "GO!"]
    for label in countdown_labels:
        start = pygame.time.get_ticks()
        while True:
            dt = clock.tick(FPS) / 1000
            now = pygame.time.get_ticks()
            if now - start >= 1000:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            screen.blit(background, (0, 0))

            # frames idle
            frame_idle_p1 = adv_idle if char_p1 == "ADV" else nin_idle
            frame_idle_p2 = adv_idle if char_p2 == "ADV" else nin_idle

            sprite_p1 = pygame.transform.smoothscale(frame_idle_p1, (sprite_w, sprite_h))
            sprite_p2 = pygame.transform.smoothscale(frame_idle_p2, (sprite_w, sprite_h))

            draw_x_p1 = p1.centerx - sprite_w // 2
            draw_y_p1 = p1.bottom - sprite_h + sprite_offset_y
            draw_x_p2 = p2.centerx - sprite_w // 2
            draw_y_p2 = p2.bottom - sprite_h + sprite_offset_y

            screen.blit(sprite_p1, (draw_x_p1, draw_y_p1))
            screen.blit(sprite_p2, (draw_x_p2, draw_y_p2))

            hp_text_p1 = FONT.render(f"{player_names[0]}: {hp_p1} %", True, (255, 255, 255))
            hp_text_p2 = FONT.render(f"{player_names[1]}: {hp_p2} %", True, (255, 255, 255))
            stock_text_p1 = FONT.render(f"VIES: {stocks_p1}", True, (255, 255, 0))
            stock_text_p2 = FONT.render(f"VIES: {stocks_p2}", True, (255, 255, 0))

            screen.blit(hp_text_p1, (40, 40))
            screen.blit(stock_text_p1, (40, 70))
            screen.blit(hp_text_p2, (sw - hp_text_p2.get_width() - 40, 40))
            screen.blit(stock_text_p2, (sw - stock_text_p2.get_width() - 40, 70))

            label_surf = TITLE_FONT.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=(sw // 2, sh // 2))
            screen.blit(label_surf, label_rect)

            pygame.display.flip()

    def respawn_animation(player_rect, spawn_pos):
        """
        Animation simple de respawn : flash bleu à la position de spawn.
        (Sans border_radius pour compat borne)
        """

        duration = 100
        start_time = pygame.time.get_ticks()

        idle_frame = adv_idle
        frame_w = int(player_rect.width * 1.15)
        frame_h = int(player_rect.height * 1.15)
        idle_sprite = pygame.transform.smoothscale(idle_frame, (frame_w, frame_h))

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_time
            if elapsed > duration:
                break

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return

            t = elapsed / duration
            alpha_sprite = int(255 * t)
            alpha_glow = int(180 * (1 - t))

            screen.blit(background, (0, 0))

            # Flash bleu sur le point de spawn
            spawn_flash = pygame.Surface((80, 80), pygame.SRCALPHA)
            size = int(40 * (1 + 0.6 * (1 - t)))
            flash_alpha = int(255 * (1 - t))
            pygame.draw.circle(
                spawn_flash,
                (0, 140, 255, flash_alpha),
                (40, 40),
                size
            )
            screen.blit(spawn_flash, (spawn_pos[0] - 40, spawn_pos[1] - 40))

            # Glow rectangulaire (sans border_radius)
            glow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (0, 255, 255, alpha_glow),
                player_rect.inflate(25, 25)
            )
            screen.blit(glow, (0, 0))

            sprite_surf = idle_sprite.copy()
            sprite_surf.set_alpha(alpha_sprite)

            draw_x = player_rect.centerx - frame_w // 2
            draw_y = player_rect.bottom - frame_h + 18
            screen.blit(sprite_surf, (draw_x, draw_y))

            pygame.display.flip()
            clock.tick(60)

    def hit(player_rect, duration=120):
        """
        Réaction au coup :
        - son "ouch"
        - flash rouge rectangulaire sur le joueur (sans border_radius)
        """

        start = pygame.time.get_ticks()

        while True:
            now = pygame.time.get_ticks()
            if now - start > duration:
                break

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            t = (now - start) / duration
            alpha = int(220 * (1 - t))

            screen.blit(background, (0, 0))

            flash = pygame.Surface((player_rect.width, player_rect.height), pygame.SRCALPHA)
            flash.fill((255, 40, 40, alpha))
            screen.blit(flash, player_rect.topleft)

            pygame.display.flip()
            clock.tick(60)

    # --- Boucle principale du match ---
    running = True
    while running:
        dt = clock.tick(FPS) / 1000

        # Lecture clavier (backup PC)
        keys = pygame.key.get_pressed()

        # --- LECTURE DES JOYSTICKS (borne arcade) ---
        jx1 = joystick_p1.get_axis(0) if joystick_p1 else 0
        jy1 = joystick_p1.get_axis(1) if joystick_p1 else 0
        b0_1 = joystick_p1.get_button(0) if joystick_p1 else 0  # jump
        b1_1 = joystick_p1.get_button(1) if joystick_p1 else 0  # (libre)
        b2_1 = joystick_p1.get_button(2) if joystick_p1 else 0  # punch
        b3_1 = joystick_p1.get_button(3) if joystick_p1 else 0  # back
        b9_1 = joystick_p1.get_button(9) if joystick_p1 else 0  # back

        jx2 = joystick_p2.get_axis(0) if joystick_p2 else 0
        jy2 = joystick_p2.get_axis(1) if joystick_p2 else 0
        b0_2 = joystick_p2.get_button(0) if joystick_p2 else 0  # jump
        b1_2 = joystick_p2.get_button(1) if joystick_p2 else 0  # (libre)
        b2_2 = joystick_p2.get_button(2) if joystick_p2 else 0  # punch
        b3_2 = joystick_p2.get_button(3) if joystick_p2 else 0  # back
        b9_2 = joystick_p2.get_button(9) if joystick_p2 else 0  # back

        # DEADZONE
        dz = 0.25
        if abs(jx1) < dz: jx1 = 0
        if abs(jy1) < dz: jy1 = 0
        if abs(jx2) < dz: jx2 = 0
        if abs(jy2) < dz: jy2 = 0

        # --- Gestion événements généraux ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        # Bouton 3 d'un des deux joueurs = quitter le match
        if (joystick_p1 and b9_1) or (joystick_p2 and b9_2):
            return

        # --- COOLDOWNS & ANIM PUNCH ---
        if punch_cooldown_p1 > 0:
            punch_cooldown_p1 -= dt
        if punch_cooldown_p2 > 0:
            punch_cooldown_p2 -= dt

        if is_punching_p1:
            punch_timer_p1 += dt
            if punch_timer_p1 >= PUNCH_FRAME_TIME:
                punch_timer_p1 = 0.0
                punch_idx_p1 += 1
                if punch_idx_p1 >= len(adv_punch_frames):
                    punch_idx_p1 = 0
                    is_punching_p1 = False
                    can_hit_p1 = True

        if is_punching_p2:
            punch_timer_p2 += dt
            if punch_timer_p2 >= PUNCH_FRAME_TIME:
                punch_timer_p2 = 0.0
                punch_idx_p2 += 1
                if punch_idx_p2 >= len(adv_punch_frames):
                    punch_idx_p2 = 0
                    is_punching_p2 = False
                    can_hit_p2 = True

        # --- Entrées P1 & P2 (jump/punch avec joystick + fallback clavier) ---
        jump_pressed_p1 = (b0_1 or keys[pygame.K_w]) and not prev_jump_p1
        punch_pressed_p1 = (b2_1 or keys[pygame.K_SPACE]) and not prev_punch_p1

        jump_pressed_p2 = (b0_2 or keys[pygame.K_UP]) and not prev_jump_p2
        punch_pressed_p2 = (b2_2 or keys[pygame.K_p]) and not prev_punch_p2

        if jump_pressed_p1 and double_jump_p1 > 0:
            double_jump_p1 -= 1
            vitesse_y_p1 = -20

        if jump_pressed_p2 and double_jump_p2 > 0:
            double_jump_p2 -= 1
            vitesse_y_p2 = -20

        if punch_pressed_p1 and not is_punching_p1 and punch_cooldown_p1 <= 0:
            is_punching_p1 = True
            punch_idx_p1 = 0
            punch_timer_p1 = 0.0
            punch_cooldown_p1 = PUNCH_COOLDOWN
            can_hit_p1 = True

        if punch_pressed_p2 and not is_punching_p2 and punch_cooldown_p2 <= 0:
            is_punching_p2 = True
            punch_idx_p2 = 0
            punch_timer_p2 = 0.0
            punch_cooldown_p2 = PUNCH_COOLDOWN
            can_hit_p2 = True

        prev_jump_p1 = (b0_1 or keys[pygame.K_w])
        prev_punch_p1 = (b2_1 or keys[pygame.K_SPACE])
        prev_jump_p2 = (b0_2 or keys[pygame.K_UP])
        prev_punch_p2 = (b2_2 or keys[pygame.K_p])

        # --- Déplacements horizontaux P1 ---
        if jx1 < 0 or keys[pygame.K_a]:
            vitesse_x_p1 = -12
            facing_right_p1 = False
        elif jx1 > 0 or keys[pygame.K_d]:
            vitesse_x_p1 = 12
            facing_right_p1 = True
        else:
            if vitesse_x_p1 > 0:
                vitesse_x_p1 -= friction * dt
                if vitesse_x_p1 < 0:
                    vitesse_x_p1 = 0
            elif vitesse_x_p1 < 0:
                vitesse_x_p1 += friction * dt
                if vitesse_x_p1 > 0:
                    vitesse_x_p1 = 0

        # --- Déplacements horizontaux P2 ---
        if jx2 < 0 or keys[pygame.K_LEFT]:
            vitesse_x_p2 = -12
            facing_right_p2 = False
        elif jx2 > 0 or keys[pygame.K_RIGHT]:
            vitesse_x_p2 = 12
            facing_right_p2 = True
        else:
            if vitesse_x_p2 > 0:
                vitesse_x_p2 -= friction * dt
                if vitesse_x_p2 < 0:
                    vitesse_x_p2 = 0
            elif vitesse_x_p2 < 0:
                vitesse_x_p2 += friction * dt
                if vitesse_x_p2 > 0:
                    vitesse_x_p2 = 0

        # --- Gravité P1 ---
        if jy1 < -0.5 or keys[pygame.K_w]:
            vitesse_y_p1 += gravite_up * dt
        elif jy1 > 0.5 or keys[pygame.K_s]:
            if vitesse_y_p1 < 20:
                vitesse_y_p1 = 23
            else:
                vitesse_y_p1 += gravite_down * dt
        else:
            vitesse_y_p1 += gravite * dt

        # --- Gravité P2 ---
        if jy2 < -0.5 or keys[pygame.K_UP]:
            vitesse_y_p2 += gravite_up * dt
        elif jy2 > 0.5 or keys[pygame.K_DOWN]:
            if vitesse_y_p2 < 20:
                vitesse_y_p2 = 23
            else:
                vitesse_y_p2 += gravite_down * dt
        else:
            vitesse_y_p2 += gravite * dt

        # --- Mouvements + collisions P1 ---
        x_p1 += vitesse_x_p1
        p1.x = int(x_p1)
        for plat in platforms:
            if p1.colliderect(plat):
                if vitesse_x_p1 > 0:
                    p1.right = plat.left
                elif vitesse_x_p1 < 0:
                    p1.left = plat.right

                if not (p1.top == plat.bottom) and not (p1.bottom == plat.top):
                    double_jump_p1 = 1
                    if not (vitesse_y_p1 <= 7):
                        vitesse_y_p1 = 8
                x_p1 = p1.x
                vitesse_x_p1 = 0

        y_p1 += vitesse_y_p1
        p1.y = int(y_p1)
        on_ground_p1 = False
        for plat in platforms:
            if p1.colliderect(plat):
                if vitesse_y_p1 > 0:
                    p1.bottom = plat.top
                    y_p1 = p1.y
                    vitesse_y_p1 = 0
                    double_jump_p1 = 2
                    on_ground_p1 = True
                elif vitesse_y_p1 < 0:
                    p1.top = plat.bottom
                    y_p1 = p1.y
                    vitesse_y_p1 = 0

        # --- Mouvements + collisions P2 ---
        x_p2 += vitesse_x_p2
        p2.x = int(x_p2)
        for plat in platforms:
            if p2.colliderect(plat):
                if vitesse_x_p2 > 0:
                    p2.right = plat.left
                elif vitesse_x_p2 < 0:
                    p2.left = plat.right

                if not (p2.top == plat.bottom) and not (p2.bottom == plat.top):
                    double_jump_p2 = 1
                    if not (vitesse_y_p2 <= 7):
                        vitesse_y_p2 = 8
                x_p2 = p2.x
                vitesse_x_p2 = 0

        y_p2 += vitesse_y_p2
        p2.y = int(y_p2)
        on_ground_p2 = False
        for plat in platforms:
            if p2.colliderect(plat):
                if vitesse_y_p2 > 0:
                    p2.bottom = plat.top
                    y_p2 = p2.y
                    vitesse_y_p2 = 0
                    double_jump_p2 = 2
                    on_ground_p2 = True
                elif vitesse_y_p2 < 0:
                    p2.top = plat.bottom
                    y_p2 = p2.y
                    vitesse_y_p2 = 0

        # --- Chute dans le vide (stocks) ---
        if p1.top > sh:
            stocks_p1 -= 1
            respawn_animation(p1, (spawn_p1_x, spawn_y))
            if stocks_p1 <= 0:
                winner = "P2"
                running = False
            else:
                x_p1 = float(spawn_p1_x)
                y_p1 = float(spawn_y)
                p1.x = int(x_p1)
                p1.y = int(y_p1)
                vitesse_x_p1 = 0
                vitesse_y_p1 = 0
                double_jump_p1 = 2
                hp_p1 = 0

        if p2.top > sh:
            stocks_p2 -= 1
            respawn_animation(p2, (spawn_p2_x, spawn_y))
            if stocks_p2 <= 0:
                winner = "P1"
                running = False
            else:
                x_p2 = float(spawn_p2_x)
                y_p2 = float(spawn_y)
                p2.x = int(x_p2)
                p2.y = int(y_p2)
                vitesse_x_p2 = 0
                vitesse_y_p2 = 0
                double_jump_p2 = 2
                hp_p2 = 0

        if not running:
            break

        # --- Dégâts & knockback P1 -> P2 ---
        if is_punching_p1 and can_hit_p1:
            if facing_right_p1:
                hitbox_p1 = pygame.Rect(p1.right - 5, p1.y + 20, 40, 40)
            else:
                hitbox_p1 = pygame.Rect(p1.left - 40, p1.y + 20, 40, 45)
            if hitbox_p1.colliderect(p2):
                hit(p2)
                can_hit_p1 = False
                hp_p2 += random.randint(10, 60)
                if facing_right_p1:
                    vitesse_x_p2 += basic_degat + (hp_p2 / 50) * degat_coup
                else:
                    vitesse_x_p2 -= basic_degat + (hp_p2 / 50) * degat_coup
                vitesse_y_p2 -= basic_degat + (hp_p2 / 100) * degat_coup

        # --- Dégâts & knockback P2 -> P1 ---
        if is_punching_p2 and can_hit_p2:
            if facing_right_p2:
                hitbox_p2 = pygame.Rect(p2.right - 5, p2.y + 20, 40, 40)
            else:
                hitbox_p2 = pygame.Rect(p2.left - 40, p2.y + 20, 40, 45)
            if hitbox_p2.colliderect(p1):
                hit(p1)
                can_hit_p2 = False
                hp_p1 += random.randint(10, 60)
                if facing_right_p2:
                    vitesse_x_p1 += basic_degat + (hp_p1 / 50) * degat_coup
                else:
                    vitesse_x_p1 -= basic_degat + (hp_p1 / 50) * degat_coup
                vitesse_y_p1 -= basic_degat + (hp_p1 / 100) * degat_coup

        if not running:
            break

        # --- Animation P1 ---
        anim_timer_p1 += dt
        in_air_p1 = abs(vitesse_y_p1) > 1 and not on_ground_p1
        if char_p1 == "ADV":
            if in_air_p1:
                if is_punching_p1:
                    base_frame_p1 = adv_jump_punch_frames[punch_idx_p1 % len(adv_jump_punch_frames)]
                else:
                    base_frame_p1 = adv_jump_up if vitesse_y_p1 < 0 else adv_jump_down
            else:
                if is_punching_p1:
                    base_frame_p1 = adv_punch_frames[punch_idx_p1 % len(adv_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(adv_run_frames)
                    base_frame_p1 = adv_run_frames[run_frame_idx_p1]
                else:
                    base_frame_p1 = adv_idle
        else:
            if in_air_p1:
                if is_punching_p1:
                    base_frame_p1 = nin_jump_punch_frames[punch_idx_p1 % len(nin_jump_punch_frames)]
                else:
                    base_frame_p1 = nin_jump_up if vitesse_y_p1 < 0 else nin_jump_down
            else:
                if is_punching_p1:
                    base_frame_p1 = nin_punch_frames[punch_idx_p1 % len(nin_punch_frames)]
                elif abs(vitesse_x_p1) > 1:
                    if anim_timer_p1 >= 0.10:
                        anim_timer_p1 = 0.0
                        run_frame_idx_p1 = (run_frame_idx_p1 + 1) % len(nin_run_frames)
                    base_frame_p1 = nin_run_frames[run_frame_idx_p1]
                else:
                    base_frame_p1 = nin_idle

        frame_p1 = base_frame_p1
        if not facing_right_p1:
            frame_p1 = pygame.transform.flip(base_frame_p1, True, False)
        sprite_p1 = pygame.transform.smoothscale(frame_p1, (sprite_w, sprite_h))

        # --- Animation P2 ---
        anim_timer_p2 += dt
        in_air_p2 = abs(vitesse_y_p2) > 1 and not on_ground_p2
        if char_p2 == "ADV":
            if in_air_p2:
                if is_punching_p2:
                    base_frame_p2 = adv_jump_punch_frames[punch_idx_p2 % len(adv_jump_punch_frames)]
                else:
                    base_frame_p2 = adv_jump_up if vitesse_y_p2 < 0 else adv_jump_down
            else:
                if is_punching_p2:
                    base_frame_p2 = adv_punch_frames[punch_idx_p2 % len(adv_punch_frames)]
                elif abs(vitesse_x_p2) > 1:
                    if anim_timer_p2 >= 0.10:
                        anim_timer_p2 = 0.0
                        run_frame_idx_p2 = (run_frame_idx_p2 + 1) % len(adv_run_frames)
                    base_frame_p2 = adv_run_frames[run_frame_idx_p2]
                else:
                    base_frame_p2 = adv_idle
        else:
            if in_air_p2:
                if is_punching_p2:
                    base_frame_p2 = nin_jump_punch_frames[punch_idx_p2 % len(nin_jump_punch_frames)]
                else:
                    base_frame_p2 = nin_jump_up if vitesse_y_p2 < 0 else nin_jump_down
            else:
                if is_punching_p2:
                    base_frame_p2 = nin_punch_frames[punch_idx_p2 % len(nin_punch_frames)]
                elif abs(vitesse_x_p2) > 1:
                    if anim_timer_p2 >= 0.10:
                        anim_timer_p2 = 0.0
                        run_frame_idx_p2 = (run_frame_idx_p2 + 1) % len(nin_run_frames)
                    base_frame_p2 = nin_run_frames[run_frame_idx_p2]
                else:
                    base_frame_p2 = nin_idle

        frame_p2 = base_frame_p2
        if not facing_right_p2:
            frame_p2 = pygame.transform.flip(base_frame_p2, True, False)
        sprite_p2 = pygame.transform.smoothscale(frame_p2, (sprite_w, sprite_h))

        # --- DRAW ---
        screen.blit(background, (0, 0))

        draw_x_p1 = p1.centerx - sprite_w // 2
        draw_y_p1 = p1.bottom - sprite_h + sprite_offset_y
        draw_x_p2 = p2.centerx - sprite_w // 2
        draw_y_p2 = p2.bottom - sprite_h + sprite_offset_y

        screen.blit(sprite_p1, (draw_x_p1, draw_y_p1))
        screen.blit(sprite_p2, (draw_x_p2, draw_y_p2))

        name_p1 = FONT.render(f"{player_names[0]} ({hp_p1}%)", True, (255, 220, 220))
        name_p2 = FONT.render(f"{player_names[1]} ({hp_p2}%)", True, (200, 220, 255))
        screen.blit(name_p1, (p1.centerx - name_p1.get_width() // 2, p1.top - 25))
        screen.blit(name_p2, (p2.centerx - name_p2.get_width() // 2, p2.top - 25))

        hp_text_p1 = FONT.render(f"{player_names[0]}: {hp_p1} %", True, (255, 255, 255))
        hp_text_p2 = FONT.render(f"{player_names[1]}: {hp_p2} %", True, (255, 255, 255))
        stock_text_p1 = FONT.render(f"VIES: {stocks_p1}", True, (255, 255, 0))
        stock_text_p2 = FONT.render(f"VIES: {stocks_p2}", True, (255, 255, 0))

        screen.blit(hp_text_p1, (40, 40))
        screen.blit(stock_text_p1, (40, 70))
        screen.blit(hp_text_p2, (sw - hp_text_p2.get_width() - 40, 40))
        screen.blit(stock_text_p2, (sw - stock_text_p2.get_width() - 40, 70))

        pygame.display.flip()

    # --- Mise à jour du ranking : on compte les victoires du gagnant ---
    if winner == "P1":
        add_win(player_names[0])
    elif winner == "P2":
        add_win(player_names[1])

    # --- Écran de fin : affiche le vainqueur + retour lobby ---
    if winner is not None:
        btn_back = Button(WIDTH // 2 - 150, HEIGHT - 120, 300, 70, "Retour au lobby")

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            # Joystick : bouton 2 ou 3 pour revenir
            if (joystick_p1 and (joystick_p1.get_button(2) or joystick_p1.get_button(3))) or \
               (joystick_p2 and (joystick_p2.get_button(2) or joystick_p2.get_button(3))):

                return

            screen.blit(background_img, (0, 0))
            draw_retro_title("VICTOIRE !", 100)

            if winner == "P1":
                txt = f"{player_names[0]} gagne !"
            else:
                txt = f"{player_names[1]} gagne !"

            win_text = FONT_BIG.render(txt, True, WHITE)
            screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - 40))

            btn_back.draw()
            if btn_back.clicked():

                return

            pygame.display.flip()
            clock.tick(FPS)

# -----------------------------------------------
# MAIN LOOP
# -----------------------------------------------
def main():
    intro_menu()

    while True:
        choice = main_menu()
        if choice == "partie":
            mode = partie_menu()

            # MODE 1v1
            if mode == "1v1":
                names = login_menu_arcade()
                if names is not None:
                    char_p1, char_p2 = character_select_1v1(names)
                    if char_p1 is not None:
                        map_index = map_select_1v1(names)
                        if map_index is not None:
                            weapon_p1, weapon_p2 = weapon_select_1v1(names)
                            if weapon_p1 is not None:
                                play_players(map_index,char_p1,char_p2,player_names)

            # MODE VS ORDI
            elif mode == "ai":
                names = login_menu_vs_ai()
                if names is not None:
                    char_p1, char_ai = character_select_vs_ai(names)
                    if char_p1 is not None:
                        map_index = map_select_vs_ai(names)
                        if map_index is not None:
                            weapon_p1, weapon_ai = weapon_select_vs_ai(names)
                            if weapon_p1 is not None:
                                # appel modifié : on passe aussi names
                                play_ordi(map_index, char_p1, names)

        else:
            pygame.quit()
            sys.exit()


if __name__ == "__main__":
    main()
