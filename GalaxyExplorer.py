import pygame, sys
import random, math

# ---------- CONFIG -----------------------------------------------------------
SCREEN_W, SCREEN_H = 800, 600
CELL_SIZE        = 50
GRID_W, GRID_H   = SCREEN_W // CELL_SIZE, SCREEN_H // CELL_SIZE
HALF_W, HALF_H   = GRID_W // 2, GRID_H // 2
FONT_SIZE        = 18

# MAP movement (numpad)
NUMPAD_DIRS = {
    pygame.K_KP1:(-1,  1), pygame.K_KP2:( 0,  1), pygame.K_KP3:( 1,  1),
    pygame.K_KP4:(-1,  0), pygame.K_KP5:( 0,  0), pygame.K_KP6:( 1,  0),
    pygame.K_KP7:(-1, -1), pygame.K_KP8:( 0, -1), pygame.K_KP9:( 1, -1),
}

# Star & planet palettes & features
STAR_TYPES = {
    "Red Dwarf":    (180, 50,  50),
    "Yellow Dwarf": (240,240,100),
    "Blue Giant":   (100,150,255),
    "Neutron Star": (200,180,255),
    "White Dwarf":  (255,255,255),
}
PLANET_TYPES = {
    "Rocky":       (100,100,100),
    "Gas Giant":   (255,150, 50),
    "Ice World":   (150,200,255),
    "Ocean World": ( 50,100,255),
    "Desert":      (210,180,100),
}
PLANET_FEATS = ["Rings","Life","Volcanic","High Gravity","Magnetic Storms"]

# Resources & inventory
RESOURCE_TYPES = ["Iron", "Gold", "Water", "Silicon", "Uranium"]
RESOURCE_RATIOS = {
    "Rocky":    [0.30, 0.05, 0.05, 0.50, 0.10],
    "Gas Giant":[0.05, 0.01, 0.70, 0.10, 0.14],
    "Ice World":[0.10, 0.02, 0.80, 0.05, 0.03],
    "Ocean World":[0.05,0.01,0.85,0.05,0.04],
    "Desert":   [0.20, 0.10, 0.05, 0.50, 0.15],
}
inventory = {r: 0 for r in RESOURCE_TYPES}

def pick_resource(planet_type, rng):
    return rng.choices(RESOURCE_TYPES, weights=RESOURCE_RATIOS[planet_type], k=1)[0]

# ---------- PROC‑GEN HELPERS ------------------------------------------------
def system_seed(x,y):
    return x*73856093 ^ y*19349663

def has_star(x,y, chance=0.2):
    return random.Random(system_seed(x,y)).random() < chance

def generate_system(x,y):
    """Return (star_type, planets) or None if empty."""
    if not has_star(x,y):
        return None
    rng = random.Random(system_seed(x,y))
    star = rng.choice(list(STAR_TYPES))
    planets = []
    for i in range(rng.randint(1,5)):
        planets.append({
            "type":   rng.choice(list(PLANET_TYPES)),
            "feats":  rng.sample(PLANET_FEATS, rng.randint(0,2)),
            "orbit":  80 + i*50,
            "angle":  rng.random()*2*math.pi,
            "radius": 12 if i==0 else 8,
        })
    return star, planets

# ---------- PYGAME INIT ------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Galaxy Rogue‑Lite Demo")
font  = pygame.font.SysFont("Consolas", FONT_SIZE)
clock = pygame.time.Clock()

# ---------- GAME STATE ------------------------------------------------------
mode             = "MAP"   # MAP, SYS, PLANET_INFO, SURFACE, INVENTORY
prev_mode        = None
px = py          = 0       # galaxy coords
current_sys      = None
sel_planet_idx   = None    # for PLANET_INFO & SURFACE

# --- space‑flight physics
ship_pos   = (0,0)
ship_vel   = [0.0, 0.0]
ship_ang   = 0.0
SHIP_RAD   = 10
THRUST     = 0.15
ROT_SPEED  = 0.08
DRAG       = 0.995

# --- surface state
surface_pos  = [0,0]
SURF_SPEED   = 4
surface_orbs = []
orb_count    = 0
total_orbs   = 0

# ---------- UTILITY ---------------------------------------------------------
def collide(p1, p2, r):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 < r*r

# ---------- DRAW FUNCTIONS -------------------------------------------------
def draw_map():
    screen.fill((10,10,30))
    for gx in range(GRID_W):
        for gy in range(GRID_H):
            sx, sy = gx*CELL_SIZE, gy*CELL_SIZE
            pygame.draw.rect(screen, (40,40,60),
                             (sx,sy,CELL_SIZE,CELL_SIZE), 1)
            wx, wy = px + (gx-HALF_W), py + (gy-HALF_H)
            if has_star(wx,wy):
                pygame.draw.circle(screen, (255,255,100),
                                   (sx+CELL_SIZE//2, sy+CELL_SIZE//2), 5)
    # ship in center cell
    cx = HALF_W*CELL_SIZE + CELL_SIZE//2
    cy = HALF_H*CELL_SIZE + CELL_SIZE//2
    pts = [(cx,cy-12),(cx-8,cy+8),(cx+8,cy+8)]
    pygame.draw.polygon(screen, (255,255,255), pts)
    screen.blit(font.render(f"Map Mode | Sector: ({px},{py})",
                           True,(255,255,255)), (10,10))
    screen.blit(font.render(
        "Move: Numpad 1-9  |  Explore: E  |  Inventory: I  |  Quit: X",
        True,(200,200,200)), (10,40))

def draw_system():
    star, planets = current_sys
    cx, cy = SCREEN_W//2, SCREEN_H//2
    screen.fill((0,0,20))
    # orbits & star
    for p in planets:
        pygame.draw.circle(screen, (60,60,80), (cx,cy), p["orbit"], 1)
    pygame.draw.circle(screen, STAR_TYPES[star], (cx,cy), 30)
    # planets
    planet_rects = []
    for p in planets:
        pxp = cx + math.cos(p["angle"])*p["orbit"]
        pyp = cy + math.sin(p["angle"])*p["orbit"]
        pygame.draw.circle(screen, PLANET_TYPES[p["type"]],
                           (int(pxp),int(pyp)), p["radius"])
        planet_rects.append(((pxp,pyp), p["radius"]))
    # ship
    sx, sy = ship_pos
    tip   = (sx + math.cos(ship_ang)*15, sy + math.sin(ship_ang)*15)
    left  = (sx + math.cos(ship_ang+2.5)*12, sy + math.sin(ship_ang+2.5)*12)
    right = (sx + math.cos(ship_ang-2.5)*12, sy + math.sin(ship_ang-2.5)*12)
    pygame.draw.polygon(screen, (255,255,255), [tip,left,right])
    screen.blit(font.render("System Mode (↑←→ to fly, B=back, I=inv)",
                           True,(200,200,200)), (10,10))
    screen.blit(font.render(f"Star: {star}", True,(255,255,255)), (10,34))

def draw_planet_info():
    p = current_sys[1][sel_planet_idx]
    screen.fill((20,20,30))
    # big scan circle
    big_center = (SCREEN_W//2, SCREEN_H//2 + 40)
    big_radius = max(40, p["radius"] * 4)
    pygame.draw.circle(screen, PLANET_TYPES[p["type"]],
                       big_center, big_radius)
    # info text
    screen.blit(font.render(
        f"Planet {sel_planet_idx+1} Info (L=land, B=back, I=inv)",
        True,(255,255,255)), (10,10))
    screen.blit(font.render(f"Type: {p['type']}", True,(220,220,220)),
                (10,50))
    feats = ", ".join(p['feats']) if p['feats'] else "None"
    screen.blit(font.render("Features: " + feats, True,(220,220,220)),
                (10,80))

def draw_surface():
    # background = planet color
    p = current_sys[1][sel_planet_idx]
    screen.fill(PLANET_TYPES[p["type"]])
    # draw orbs
    for ox, oy, res in surface_orbs:
        pygame.draw.circle(screen, (200,200,50), (int(ox),int(oy)), 8)
    # draw player
    pygame.draw.circle(screen, (255,255,255),
                       (int(surface_pos[0]), int(surface_pos[1])), 10)
    screen.blit(font.render(
        f"Surface Mode | Minerals: {orb_count}/{total_orbs}  B=back  I=inv",
        True,(255,255,255)), (10,10))
    if orb_count >= total_orbs:
        screen.blit(font.render(
            "All minerals collected! Press B to exit.",
            True,(200,200,200)), (10,40))

def draw_inventory():
    screen.fill((20,20,20))
    screen.blit(font.render("Inventory (B=back)", True,(255,255,255)),
                (10,10))
    y = 50
    for res in RESOURCE_TYPES:
        line = f"{res}: {inventory[res]}"
        screen.blit(font.render(line, True,(200,200,200)), (10,y))
        y += FONT_SIZE + 5

# ---------- MAIN LOOP --------------------------------------------------------
while True:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:
            # global quit
            if ev.key == pygame.K_x:
                pygame.quit(); sys.exit()

            # inventory toggle
            if ev.key == pygame.K_i and mode != "INVENTORY":
                prev_mode = mode
                mode = "INVENTORY"
                continue

            # back from inventory
            if mode == "INVENTORY" and ev.key == pygame.K_b:
                mode = prev_mode
                continue

            # MAP mode
            if mode == "MAP":
                if ev.key in NUMPAD_DIRS:
                    dx, dy = NUMPAD_DIRS[ev.key]
                    px += dx; py += dy
                elif ev.key == pygame.K_e and has_star(px,py):
                    # enter system
                    current_sys = generate_system(px,py)
                    ship_pos    = (SCREEN_W/2, SCREEN_H - 60)
                    ship_vel    = [0.0, 0.0]
                    ship_ang    = -math.pi/2
                    mode = "SYS"

            # SYS mode
            elif mode == "SYS":
                if ev.key == pygame.K_b:
                    mode = "MAP"

            # PLANET_INFO mode
            elif mode == "PLANET_INFO":
                if ev.key == pygame.K_b:
                    # move ship safe, then back to space
                    ship_pos    = (SCREEN_W/2, SCREEN_H - 60)
                    ship_vel    = [0.0, 0.0]
                    sel_planet_idx = None
                    mode = "SYS"
                elif ev.key == pygame.K_l:
                    # land on planet
                    p = current_sys[1][sel_planet_idx]
                    rng = random.Random(system_seed(px,py) ^ sel_planet_idx)
                    total_orbs = 8
                    surface_orbs = []
                    for _ in range(total_orbs):
                        ox = rng.randint(50, SCREEN_W-50)
                        oy = rng.randint(80, SCREEN_H-50)
                        res = pick_resource(p["type"], rng)
                        surface_orbs.append((ox, oy, res))
                    orb_count    = 0
                    surface_pos  = [SCREEN_W/2, SCREEN_H/2]
                    mode = "SURFACE"

            # SURFACE mode
            elif mode == "SURFACE":
                if ev.key == pygame.K_b:
                    mode = "SYS"

    # continuous input & updates
    keys = pygame.key.get_pressed()

    if mode == "SYS":
        # rotation & thrust
        rot = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            rot = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            rot = 1
        ship_ang += rot * ROT_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            ship_vel[0] += math.cos(ship_ang) * THRUST
            ship_vel[1] += math.sin(ship_ang) * THRUST
        ship_vel[0] *= DRAG; ship_vel[1] *= DRAG
        x = (ship_pos[0] + ship_vel[0]) % SCREEN_W
        y = (ship_pos[1] + ship_vel[1]) % SCREEN_H
        ship_pos = (x, y)

        # collision with star
        star, planets = current_sys
        cx, cy = SCREEN_W/2, SCREEN_H/2
        if collide(ship_pos, (cx,cy), 30 + SHIP_RAD):
            pygame.draw.circle(screen, (255,80,80),
                               (int(x),int(y)), 25)
            pygame.display.flip(); pygame.time.wait(400)
            mode = "MAP"
        else:
            # collision with planet → info
            for idx, p in enumerate(planets):
                pxp = cx + math.cos(p["angle"])*p["orbit"]
                pyp = cy + math.sin(p["angle"])*p["orbit"]
                if collide(ship_pos, (pxp,pyp), p["radius"] + SHIP_RAD):
                    sel_planet_idx = idx
                    mode = "PLANET_INFO"
                    break

    elif mode == "SURFACE":
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -SURF_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = SURF_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -SURF_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = SURF_SPEED
        surface_pos[0] = max(0, min(SCREEN_W, surface_pos[0] + dx))
        surface_pos[1] = max(0, min(SCREEN_H, surface_pos[1] + dy))

        # collect orbs
        new_orbs = []
        for ox, oy, res in surface_orbs:
            if collide(surface_pos, (ox,oy), 10 + 8):
                inventory[res] += 1
                orb_count += 1
            else:
                new_orbs.append((ox, oy, res))
        surface_orbs = new_orbs

    # draw current mode
    if   mode == "MAP":          draw_map()
    elif mode == "SYS":          draw_system()
    elif mode == "PLANET_INFO":  draw_planet_info()
    elif mode == "SURFACE":      draw_surface()
    elif mode == "INVENTORY":    draw_inventory()

    pygame.display.flip()
    clock.tick(60)
