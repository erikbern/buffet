import heapq
import numpy
import os
import random
import PIL.Image, PIL.ImageDraw, PIL.ImageFont


def listdir(d):
    return [os.path.join(d, p) for p in os.listdir(d)]


FOODS = listdir('pics/food')
PEOPLE = listdir('pics/people')

ACTOR_BLOCKAGE_FACTOR = 1e3
PREFERENCE_FACTOR = 1e-6


class Actor:
    def __init__(self, created_at, x, y, r, goals, emoji):
        self.created_at = created_at
        self.finished_at = None
        self.x = x
        self.y = y
        self.r = r
        self.goals = goals
        self.emoji = emoji
        self.loading_left = None
        self.path = []
        self.path_color = tuple(0xe0 + int(0x20*random.random()) for z in range(3))
        self.reached = []


class RogueActor(Actor):
    def dirs(self):
        return [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, -1), (-1, 1)]

    def cost_factor(self, x, y, g, di, dj):
        return 1.0


class ClassicActor(Actor):
    def dirs(self):
        return [(0, 0), (0, -1), (1, -1), (1, 0)]

    def cost_factor(self, x, y, g, di, dj):
        if abs(y - g.y) <= self.r and di == 0 and dj == -1:
            return PREFERENCE_FACTOR  # prioritize getting the horizontal alignment with the goal
        elif di == 1 and dj == 0:
            return PREFERENCE_FACTOR  # go up if possible
        else:
            return 1.0


class SkippableActor(Actor):
    def dirs(self):
        return [(0, 0), (0, -1), (1, -1), (1, 0), (-1, -1), (-1, 0)]

    def cost_factor(self, x, y, g, di, dj):
        return 1.0


class VLineActor(Actor):
    def dirs(self):
        return [(0, 0), (1, 0), (0, -1), (-1, 0), (1, -1), (-1, -1)]

    def cost_factor(self, x, y, g, di, dj):
        if abs(x - g.x) <= self.r and di == 1 and dj == 0:
            return PREFERENCE_FACTOR  # prioritize getting the vertical alignment with the goal
        else:
            return 1.0


class Goal:
    def __init__(self, x, y, r, emoji):
        self.x = x
        self.y = y
        self.r = r
        self.emoji = emoji


class Buffet:
    def __init__(self, n=10, p=0.4, g=10, r=0.18, gr=0.24, h=6, wf=2, nw=4.5, rate=1.0, method='anarchy'):
        self.n = n   # Number of items on buffet
        self.p = p   # Probability of wanting each item
        self.g = g   # Granularity of grid
        self.r = r   # Radius of each actor
        self.h = h   # Height of grid
        self.wf = wf  # How long it takes to get food relative to moving 1 step
        self.w = nw + n + 1  # Width of grid
        self.rate = rate  # Rate of spawning new actors
        self.method = method
        emojis = random.sample(FOODS, n)
        self.goals = [Goal(x=nw+i, y=gr, r=gr, emoji=e) for i, e in enumerate(emojis)]
        self.goals.append(Goal(x=self.w+10, y=0, r=10+1, emoji=None))

        self.active_actors = []
        self.all_actors = []
        self.color_index = 0

        self.time = 0
        self.finished = 0

    def xy2ij(self, x, y):
        # Convert from real x, y to the grid indices
        return (int(numpy.ceil(y * self.g)),
                int(numpy.ceil(x * self.g)))

    def ij2xy(self, i, j):
        return (j / self.g, i / self.g)

    def get_mask(self, actors):
        # Build a grid of all obstacles
        grid = numpy.zeros((int(self.h*self.g), int(self.w*self.g)))
        border = int(numpy.ceil(self.r*self.g))
        for (i, j), _ in numpy.ndenumerate(grid):
            x, y = self.ij2xy(i, j)
            if i < border or j < border or i + border >= self.h*self.g or j + border >= self.w*self.g:
                grid[i][j] = float('inf')
        for a in actors:
            for (i, j), _ in numpy.ndenumerate(grid):
                x, y = self.ij2xy(i, j)
                # distance = ((a.x - x)**2 + (a.y - y)**2)**0.5  # circular actors
                distance = max(abs(a.x - x), abs(a.y - y))  # square actors
                if distance < 2*self.r:
                    grid[i][j] += ACTOR_BLOCKAGE_FACTOR*(1 + (self.h - y)/self.h)  # TODO: explain

        return grid

    def move_actor(self, a):
        # Generate a mask of pixels 
        grid = self.get_mask([actor for actor in self.active_actors if actor != a])

        # What's the next goal for this actor?
        next_goal = min(a.goals.keys())
        g = self.goals[next_goal]

        # If we're close to the goal, just stop and load food
        a.loading_left = None
        if max(abs(a.x - g.x), abs(a.y - g.y)) <= g.r:  # square goals
        # if (a.x - g.x)**2 + (a.y - g.y)**2 <= g.r**2:
            a.goals[next_goal] -= 1
            a.loading_left = a.goals[next_goal]
            if a.goals[next_goal] <= 0:
                a.goals.pop(next_goal)
                a.reached.append(next_goal)

        dirs = a.dirs()

        # Use Dijkstra
        # Seed starting points
        q = []
        ai, aj = self.xy2ij(a.x, a.y)
        for (i, j), _ in numpy.ndenumerate(grid):
            x, y = self.ij2xy(i, j)
            if numpy.isfinite(grid[i][j]):
                # if (x - g.x)**2 + (y - g.y)**2 < g.r**2:
                if max(abs(x - g.x), abs(y - g.y)) < g.r:  # square goals
                    heapq.heappush(q, (0, i, j, -1, -1))

        visited = set()
        i_to_matrix = numpy.ones(grid.shape, dtype=int) * -1
        j_to_matrix = numpy.ones(grid.shape, dtype=int) * -1
        while q:
            distance, i, j, i_to, j_to = heapq.heappop(q)
            if (i, j) in visited:
                continue
            i_to_matrix[i][j] = i_to
            j_to_matrix[i][j] = j_to
            if i == ai and j == aj:
                break
            visited.add((i, j))
            x, y = self.ij2xy(i, j)
            for di, dj in dirs:
                i2, j2 = i+di, j+dj
                step_size = ((di**2 + dj**2)**0.5 +  # penalization of diagonal moves
                             grid[i2][j2])  # last term just penalizes going through other people
                step_size *= a.cost_factor(x, y, g, di, dj)
                if numpy.isfinite(grid[i2][j2]):
                    heapq.heappush(q, (distance + step_size, i2, j2, i, j))
        else:
            i, j, i_to, j_to = -1, -1, -1, -1

        if i_to != -1 and j_to != -1 and grid[i_to][j_to] < ACTOR_BLOCKAGE_FACTOR:
            a.x, a.y = self.ij2xy(i_to, j_to)

        # Reconstruct the shortest path
        a.path = []
        while (i, j) != (-1, -1):
            a.path.append(self.ij2xy(i, j))
            i, j = i_to_matrix[i][j], j_to_matrix[i][j]

    def step(self):
        # Spawn new actor randomly
        if random.random() < self.rate / self.g:
            mask = self.get_mask(self.active_actors)
            # Find the most top left position that's available
            ijs = [(i, j) for (i, j), v in numpy.ndenumerate(mask) if v < ACTOR_BLOCKAGE_FACTOR]
            if ijs:
                j, i = min((j, i) for i, j in ijs)
                goals = {}
                while len(goals) == 0:
                    goals = {g: self.g*self.wf for g in range(self.n) if random.random() < self.p}
                goals[self.n] = 1  # sentinel
                x, y = self.ij2xy(i, j)
                cls = {'classic': ClassicActor, 'skippable': SkippableActor, 'rogue': RogueActor, 'vline': VLineActor}[self.method]
                a = cls(self.time, x, y, self.r, goals, random.choice(PEOPLE))
                self.active_actors.append(a)
                self.all_actors.append(a)

        # Move each actor
        keep_actors = []
        for a in self.active_actors:
            self.move_actor(a)
            if a.goals:
                keep_actors.append(a)
            else:
                a.finished_at = self.time
                self.finished += 1
        random.shuffle(keep_actors)
        self.active_actors = keep_actors
        data = [(a.created_at, a.finished_at, self.time) for a in self.all_actors]
        self.time += 1.0/self.g
        return data


def draw_frame(buffet, fn, simple):
    # Pillow (at least whatever version I have) seems to segfault occasionally
    # That's why we run it inside a pool
    if simple:
        up_f, down_f = 128, 4
    else:
        up_f, down_f = 256, 4

    im = PIL.Image.new('RGBA', (int(buffet.w*up_f), int(buffet.h*up_f)), (255, 255, 255))
    draw = PIL.ImageDraw.Draw(im)

    if not simple:
        for a in buffet.active_actors:
            for j in range(len(a.path)-1):
                draw.line((a.path[j][0]*up_f, a.path[j][1]*up_f, a.path[j+1][0]*up_f, a.path[j+1][1]*up_f),
                          fill=a.path_color, width=2*down_f)
        font_size = 100
        font = PIL.ImageFont.truetype('pics/helvetica.ttf', font_size)
        draw.text((0, buffet.h*up_f-font_size),
                  'Time: %.1fs Finished: %.0f Rate: %.2f/s' % (buffet.time, buffet.finished, buffet.finished/buffet.time),
                  fill=(0x66, 0x66, 0x66), font=font)
    for g in buffet.goals:
        if g.emoji:
            emoji = PIL.Image.open(g.emoji)
            emoji = emoji.resize((int(2*g.r*up_f), int(2*g.r*up_f)))
            im.alpha_composite(emoji, (int((g.x-g.r)*up_f),
                                       int((g.y-g.r)*up_f)))
    for a in buffet.active_actors:
        emoji = PIL.Image.open(a.emoji)
        emoji = emoji.resize((int(2*buffet.r*up_f), int(2*buffet.r*up_f)))
        im.alpha_composite(emoji, (int((a.x-buffet.r)*up_f),
                                   int((a.y-buffet.r)*up_f)))
        plate = PIL.Image.open('pics/plate.png')
        minis = [('pics/plate.png', -buffet.r, 0)] + [(buffet.goals[r].emoji, -buffet.r, 0) for r in a.reached]
        if a.loading_left:
            #draw.arc(((a.x - buffet.r)*up_f, (a.y - buffet.r)*up_f,
            #          (a.x + buffet.r)*up_f, (a.y + buffet.r)*up_f),
            #         start=0, end=360*a.loading_left/(buffet.g*buffet.wf),
            #         fill=(0, 0, 0), width=2*down_f)
            frac = a.loading_left / (buffet.g*buffet.wf)
            path = buffet.goals[min(a.goals.keys())].emoji
            minis.append(((path, -buffet.r*(1-frac), -buffet.r*frac)))
        for path, dx, dy in minis:
            mini = PIL.Image.open(path)
            mini = mini.resize((int(buffet.r*up_f), int(buffet.r*up_f)))
            im.alpha_composite(mini, (int((a.x+dx)*up_f),
                                      int((a.y+dy)*up_f)))

    im = im.resize((int(buffet.w*up_f/down_f),
                    int(buffet.h*up_f/down_f)),
                   PIL.Image.LANCZOS)
    # Crop out the rightmost part where actors exit
    im = im.crop((0, 0, int((buffet.goals[-1].x - buffet.goals[-1].r)*up_f/down_f), int(buffet.h*up_f/down_f)))
    im.save(fn)
