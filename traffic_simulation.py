import pygame
import random
import math

# Configuration
WIDTH, HEIGHT = 600, 800
FPS = 60
WHITE = (255, 255, 255)
BLACK = (20, 20, 20) # Darker asphalt
GRAY = (100, 100, 100)
YELLOW = (255, 200, 0)
RED = (255, 50, 50)
BLUE = (50, 100, 255)
CAR_GRAY = (150, 150, 150)

# Simulation Constants
SCENARIO_CURRENT = 0
SCENARIO_ENFORCED_NO_KR = 1 
SCENARIO_ENFORCED_WITH_KR = 2 

CURRENT_SCENARIO = SCENARIO_ENFORCED_NO_KR 

# Layout
# Main Road: 2 Lanes. 
# Lane 1 (Right, x=320): Slow lane / Parking entry
# Lane 2 (Left, x=280): Passing lane
LANE_WIDTH = 40
ROAD_X = 250
ROAD_WIDTH = LANE_WIDTH * 2

# Road Layout (Vertical: Bottom -> Top)
# Main road in center: x=250 to x=350
# Pocket Road (Bottom Right): y=500 to 800 (Encountered First)
# Overpass (Top Right): y=50 to 250 (Encountered Second)

# Pocket Road is SINGLE LANE width (e.g., 40px)
POCKET_ROAD_RECT = pygame.Rect(ROAD_X + ROAD_WIDTH + 10, 500, 50, 300) # Narrower
OVERPASS_RECT = pygame.Rect(ROAD_X + ROAD_WIDTH + 10, 50, 120, 200)    # Top Right

class Car:
    def __init__(self, id, car_type):
        self.id = id
        self.type = car_type # 'THROUGH', 'PARKING_POCKET', 'PARKING_OVERPASS'
        
        # Lane assignment
        if self.type == 'THROUGH':
            self.lane = 0 if random.random() < 0.5 else 1 # 0=Left, 1=Right
            self.color = CAR_GRAY
            self.target_speed = 5 + random.random() * 2
        else:
            self.lane = 1 # Right lane for parking
            self.color = BLUE if 'POCKET' in self.type else RED
            self.target_speed = 4
            
        self.x = ROAD_X + (self.lane * LANE_WIDTH) + (LANE_WIDTH/2)
        self.y = HEIGHT + 50 + random.randint(0, 100) # Start below screen
        self.speed = self.target_speed
        
        self.state = "DRIVING" 
        self.park_timer = 0
        self.wait_time = 0
        
        # Dwell time
        if CURRENT_SCENARIO == SCENARIO_ENFORCED_NO_KR:
            self.dwell_time = random.randint(180, 600)
        elif CURRENT_SCENARIO == SCENARIO_ENFORCED_WITH_KR:
            self.dwell_time = random.randint(30, 60)
        else:
            self.dwell_time = random.randint(60, 300)

        # Visual properties
        self.width = 24
        self.length = 40

    def update(self, all_cars, parked_cars):
        # 1. Car Following Logic
        car_ahead = None
        min_dist = 9999
        
        # Check cars in same lane
        for other in all_cars:
            if other.id == self.id: continue
            
            # Collision Avoidance (Separation) - INCREASED DISTANCE
            if abs(self.x - other.x) < 26 and abs(self.y - other.y) < 50:
                shift = 3 # Stronger push
                if self.y > other.y: self.y += shift
                else: self.y -= shift
                
                # Zone Constraints
                if self.state in ["PARKED", "PARKING_MOVE"]:
                    target_rect = POCKET_ROAD_RECT if 'POCKET' in self.type else OVERPASS_RECT
                    if self.y < target_rect.top + 15: self.y = target_rect.top + 15
                    if self.y > target_rect.bottom - 15: self.y = target_rect.bottom - 15
                    if self.x < target_rect.left + 10: self.x = target_rect.left + 10
                    if self.x > target_rect.right - 10: self.x = target_rect.right - 10

            # Following Logic
            same_path = False
            if self.state in ["DRIVING", "BLOCKED", "WAITING"] and other.state in ["DRIVING", "BLOCKED", "WAITING"]:
                if self.lane == other.lane: same_path = True
            elif self.state in ["PARKED", "PARKING_MOVE"] and other.state in ["PARKED", "PARKING_MOVE"]:
                if ('POCKET' in self.type and 'POCKET' in other.type) or ('OVERPASS' in self.type and 'OVERPASS' in other.type):
                    same_path = True
            
            if same_path:
                dist = self.y - other.y
                if 0 < dist < min_dist:
                    min_dist = dist
                    car_ahead = other
        
        # Lane Changing Logic (Smart Traffic)
        if self.state == "DRIVING" and self.type == "THROUGH" and self.lane == 1:
            # If blocked by a stopped car or slow traffic
            if car_ahead and car_ahead.speed < 2 and min_dist < 100:
                # Try to switch to Left Lane (Lane 0)
                can_switch = True
                for other in all_cars:
                    if other.lane == 0 and abs(other.y - self.y) < 80:
                        can_switch = False
                
                if can_switch:
                    self.lane = 0
                    self.x -= 2 # Start moving left visually
        
        # Smooth Lane Transition
        target_x_lane = ROAD_X + (self.lane * LANE_WIDTH) + (LANE_WIDTH/2)
        if self.state == "DRIVING":
            if abs(self.x - target_x_lane) > 2:
                self.x += (target_x_lane - self.x) * 0.1

        # Target Speed Logic
        desired_speed = self.target_speed
        if self.state == "BLOCKED": desired_speed = 0
        
        if car_ahead:
            if min_dist < 70: # Increased safety distance
                desired_speed = min(desired_speed, car_ahead.speed)
                if min_dist < 55: desired_speed = 0
            
        # Inertia
        if self.speed < desired_speed: self.speed += 0.1
        elif self.speed > desired_speed: self.speed -= 0.2
        if self.speed < 0: self.speed = 0
        
        # Move
        if self.state in ["DRIVING", "BLOCKED", "WAITING"]:
            self.y -= self.speed

        # 2. State Machine
        if self.state == "DRIVING":
            # Check for destination
            target_rect = None
            if self.type == 'PARKING_POCKET': target_rect = POCKET_ROAD_RECT
            elif self.type == 'PARKING_OVERPASS': target_rect = OVERPASS_RECT
            
            if target_rect:
                # Entry Point
                if target_rect.bottom - 20 < self.y < target_rect.bottom + 80:
                    cars_in_zone = [c for c in parked_cars if target_rect.collidepoint(c.x, c.y)]
                    capacity = 6 if 'POCKET' in self.type else 5
                    
                    if len(cars_in_zone) < capacity:
                        self.state = "PARKING_MOVE"
                        self.lane = -1
                        
                        # Sequential Slot Finding
                        slot_height = target_rect.height / capacity
                        taken_slots = []
                        for c in cars_in_zone:
                            rel_y = c.y - target_rect.top
                            idx = int(rel_y / slot_height)
                            taken_slots.append(idx)
                        
                        target_slot = -1
                        for i in range(capacity):
                            if i not in taken_slots:
                                target_slot = i
                                break
                        
                        if target_slot != -1:
                            self.target_x = target_rect.centerx
                            self.target_y = target_rect.top + (target_slot * slot_height) + (slot_height/2)
                        else:
                             self.state = "BLOCKED"
                    else:
                        self.state = "BLOCKED"
                        self.wait_time = 0

        elif self.state == "PARKING_MOVE":
            # Drive into spot (Curve)
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            
            if dist < 5:
                self.state = "PARKED"
            else:
                # Move faster into spot
                speed = 4
                self.x += (dx/dist) * speed
                self.y += (dy/dist) * speed
                
        elif self.state == "PARKED":
            self.park_timer += 1
            if self.park_timer > self.dwell_time:
                self.state = "LEAVING"
                
        elif self.state == "LEAVING":
            # Merge back
            target_x = ROAD_X + (1 * LANE_WIDTH) + (LANE_WIDTH/2)
            dx = target_x - self.x
            dy = -2 
            
            # Check if road is clear
            road_clear = True
            for other in all_cars:
                if other.lane == 1 and abs(other.y - self.y) < 60: # Increased merge safety check
                    road_clear = False
            
            if road_clear:
                self.x += dx * 0.05
                self.y += dy
                if abs(self.x - target_x) < 5:
                    self.state = "DRIVING"
                    self.lane = 1
                    self.type = "THROUGH"

        elif self.state == "BLOCKED":
            self.wait_time += 1
            # Retry
            target_rect = POCKET_ROAD_RECT if 'POCKET' in self.type else OVERPASS_RECT
            cars_in_zone = [c for c in parked_cars if target_rect.collidepoint(c.x, c.y)]
            capacity = 6 if 'POCKET' in self.type else 5
            
            if len(cars_in_zone) < capacity:
                self.state = "DRIVING"
            
        # Cleanup
        if self.y < -100: return "REMOVE"
        return "KEEP"

    def draw(self, surface):
        # Draw Car Body
        rect = (self.x - self.width/2, self.y - self.length/2, self.width, self.length)
        pygame.draw.rect(surface, self.color, rect, border_radius=5)
        
        # Windows
        pygame.draw.rect(surface, (50, 50, 50), (self.x - self.width/2 + 2, self.y - self.length/4, self.width-4, self.length/2 - 5))
        
        # Brake lights if stopped
        if self.speed < 0.5 and self.state in ["DRIVING", "BLOCKED"]:
            pygame.draw.circle(surface, (255, 0, 0), (self.x - 6, self.y + self.length/2), 3)
            pygame.draw.circle(surface, (255, 0, 0), (self.x + 6, self.y + self.length/2), 3)

        if self.state == "BLOCKED":
             font = pygame.font.SysFont('arial', 20, bold=True)
             text = font.render("!", True, YELLOW)
             surface.blit(text, (self.x + 10, self.y - 20))

def run_simulation():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("교통 시뮬레이션 V2: 실제 도로 흐름 반영")
    clock = pygame.time.Clock()
    
    cars = []
    spawn_timer = 0
    
    # Road markings
    dash_lines = []
    for i in range(-50, HEIGHT + 50, 60):
        dash_lines.append(i)
        
    running = True
    while running:
        screen.fill((50, 150, 50)) # Grass background
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                global CURRENT_SCENARIO
                if event.key == pygame.K_1:
                    CURRENT_SCENARIO = SCENARIO_CURRENT
                    cars = []
                elif event.key == pygame.K_2:
                    CURRENT_SCENARIO = SCENARIO_ENFORCED_NO_KR
                    cars = []
                elif event.key == pygame.K_3:
                    CURRENT_SCENARIO = SCENARIO_ENFORCED_WITH_KR
                    cars = []
                elif event.key == pygame.K_s:
                    # Save screenshot
                    filename = f"simulation_capture_{CURRENT_SCENARIO}_{pygame.time.get_ticks()}.png"
                    pygame.image.save(screen, filename)
                    print(f"Screenshot saved: {filename}")

        # Draw Road
        pygame.draw.rect(screen, BLACK, (ROAD_X, 0, ROAD_WIDTH, HEIGHT))
        
        # Draw Lanes
        # Center line (Yellow double)
        # pygame.draw.line(screen, YELLOW, (ROAD_X, 0), (ROAD_X, HEIGHT), 2) # Left edge
        # pygame.draw.line(screen, YELLOW, (ROAD_X + ROAD_WIDTH, 0), (ROAD_X + ROAD_WIDTH, HEIGHT), 2) # Right edge
        
        # Lane divider (White dashed)
        for y in dash_lines:
            pygame.draw.line(screen, WHITE, (ROAD_X + LANE_WIDTH, y), (ROAD_X + LANE_WIDTH, y + 30), 2)
        
        # Animate road (illusion of camera moving? No, fixed camera)
        
        # Draw Zones
        # Overpass
        color_overpass = (200, 150, 150) if CURRENT_SCENARIO == SCENARIO_CURRENT else (80, 80, 80)
        pygame.draw.rect(screen, (100, 100, 100), (OVERPASS_RECT.x - 10, OVERPASS_RECT.y, 10, OVERPASS_RECT.height)) # Curb
        pygame.draw.rect(screen, color_overpass, OVERPASS_RECT)
        draw_text(screen, "육교 밑 (상류)", OVERPASS_RECT.right + 10, OVERPASS_RECT.top)
        if CURRENT_SCENARIO != SCENARIO_CURRENT:
             draw_text(screen, "단속 중 (진입금지)", OVERPASS_RECT.right + 10, OVERPASS_RECT.top + 30)

        # Pocket Road
        pygame.draw.rect(screen, (100, 100, 100), (POCKET_ROAD_RECT.x - 10, POCKET_ROAD_RECT.y, 10, POCKET_ROAD_RECT.height)) # Curb
        pygame.draw.rect(screen, (220, 220, 255), POCKET_ROAD_RECT)
        draw_text(screen, "포켓도로 (하류)", POCKET_ROAD_RECT.right + 10, POCKET_ROAD_RECT.top)

        # Spawn Cars (Adjusted Volume)
        spawn_timer += 1
        spawn_rate = 15 # Faster spawn (more traffic)
        if spawn_timer > spawn_rate: 
            spawn_timer = 0
            
            rand = random.random()
            # More through traffic generally
            through_prob = 0.7 
            
            # In Scenario 3, reduce pocket road entry slightly to prevent chaos
            if CURRENT_SCENARIO == SCENARIO_ENFORCED_WITH_KR:
                through_prob = 0.8
            
            if rand < through_prob:
                cars.append(Car(len(cars), 'THROUGH'))
            else:
                # Parking car
                dest = 'PARKING_POCKET'
                if CURRENT_SCENARIO == SCENARIO_CURRENT:
                    if random.random() < 0.5: dest = 'PARKING_OVERPASS'
                cars.append(Car(len(cars), dest))
                
        # Sort cars by Y so they draw correctly (overlap)
        cars.sort(key=lambda c: c.y, reverse=False)

        # Update Cars
        parked_cars = [c for c in cars if c.state in ["PARKED", "PARKING_MOVE"]]
        
        # Count conflicts
        conflicts = len([c for c in cars if c.state == "BLOCKED"])
        
        for car in cars[:]:
            res = car.update(cars, parked_cars)
            if res == "REMOVE":
                cars.remove(car)
            car.draw(screen)

        # UI
        scenario_text = ""
        if CURRENT_SCENARIO == SCENARIO_CURRENT: scenario_text = "시나리오 1: 현황 (교통량 분산)"
        elif CURRENT_SCENARIO == SCENARIO_ENFORCED_NO_KR: scenario_text = "시나리오 2: 단속+장기주차 (본선 마비!)"
        elif CURRENT_SCENARIO == SCENARIO_ENFORCED_WITH_KR: scenario_text = "시나리오 3: 단속+K&R (원활)"
        
        # Top bar
        pygame.draw.rect(screen, WHITE, (0, 0, WIDTH, 80))
        draw_text(screen, scenario_text, 20, 20, size=25)
        draw_text(screen, f"도로 정체 차량: {conflicts}대", 20, 50, color=RED if conflicts > 3 else BLACK)
        draw_text(screen, "시뮬레이션 속도: 약 30배속", WIDTH - 250, 50, size=15, color=GRAY)
        draw_text(screen, "1:현황 2:마비 3:해결", WIDTH - 200, 20)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

def draw_text(surface, text, x, y, size=20, color=BLACK):
    try:
        font = pygame.font.SysFont('malgungothic', size)
        img = font.render(text, True, color)
        surface.blit(img, (x, y))
    except:
        pass

if __name__ == "__main__":
    run_simulation()