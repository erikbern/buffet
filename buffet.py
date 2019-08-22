import heapq
import multiprocessing
import numpy
import random
import PIL.Image, PIL.ImageDraw, PIL.ImageFont


class Actor:
    def __init__(self, x, y, goals, emoji):
        self.x = x
        self.y = y
        self.goals = goals
        self.emoji = emoji
        self.loading_left = None


class Goal:
    def __init__(self, x, y, r, emoji):
        self.x = x
        self.y = y
        self.r = r
        self.emoji = emoji


class Buffet:
    def __init__(self, n=10, p=0.3, g=10, r=0.25, h=2, wf=2, nw=4):
        self.n = n   # Number of items on buffet
        self.p = p   # Probability of wanting each item
        self.g = g   # Granularity of grid
        self.r = r   # Radius of each actor
        self.h = h   # Height of grid
        self.wf = wf  # How long it takes to get food relative to moving 1 step
        self.w = nw + n + 1  # Width of grid
        self.goals = [Goal(x=nw+i, y=r, r=r, emoji=random.randint(1, 19)) for i in range(n)]  # TODO: don't hardcode
        self.goals.append(Goal(x=self.w+10, y=h/2, r=10+2*r, emoji=None))

        self.actors = []
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
        # This works as a distance function as well
        grid = numpy.zeros((self.h*self.g, self.w*self.g))
        border = int(numpy.ceil(self.r*self.g))
        for (i, j), _ in numpy.ndenumerate(grid):
            x, y = self.ij2xy(i, j)
            for actor in actors:
                # distance = ((actor.x - x)**2 + (actor.y - y)**2)**0.5
                distance = max(abs(actor.x - x), abs(actor.y - y))
                if distance <= 2*self.r:
                    grid[i][j] += 1000
                #else:
                #    grid[i][j] += 1.0 * 2*self.r/distance
            if i < border or j < border or i + border >= self.h*self.g or j + border >= self.w*self.g:
                grid[i][j] = float('inf')
        return grid

    def move_actor(self, a):
        # Generate a mask of pixels 
        grid = self.get_mask([actor for actor in self.actors if actor != a])

        # What's the next goal for this actor?
        next_goal = min(a.goals.keys())
        g = self.goals[next_goal]

        # If we're close to the goal, just stop and load food
        a.loading_left = None
        if (a.x - g.x)**2 + (a.y - g.y)**2 <= g.r**2:
            a.goals[next_goal] -= 1
            a.loading_left = a.goals[next_goal]
            print('loading:', next_goal, ':', a.goals[next_goal])
            if a.goals[next_goal] <= 0:
                a.goals.pop(next_goal)

        # 9 directions
        dirs = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, -1), (-1, 1)]
        dirs = [(0, 0), (1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1)]

        def heuristic(i1, j1, i2, j2):
            return max(abs(i1-i2), abs(j1-j2))

        # Use A* search algorithm
        # Seed starting points
        q = []
        ai, aj = self.xy2ij(a.x, a.y)
        for (i, j), _ in numpy.ndenumerate(grid):
            x, y = self.ij2xy(i, j)
            if (x - g.x)**2 + (y - g.y)**2 < g.r**2:
                if numpy.isfinite(grid[i][j]):
                    fg, fh = 0, heuristic(i, j, ai, aj)
                    heapq.heappush(q, (fg+fh, fg, fh, i, j, None, None))

        fgs = numpy.ones(grid.shape) * float('inf')
        visited = set()
        while q:
            ff, fg, fh, i, j, i_to, j_to = heapq.heappop(q)
            if (i, j) in visited:
                continue
            if i == ai and j == aj:
                print(ff, fg, fh, i, j, i_to, j_to)
                break
            visited.add((i, j))
            fgs[i][j] = fg
            for di, dj in dirs:
                i2, j2 = i+di, j+dj
                fg2 = fg + (di**2 + dj**2)**0.1 + grid[i2][j2]  # mild penalization of diagonal moves
                if numpy.isfinite(grid[i2][j2]):
                    fh2 = heuristic(i2, j2, ai, aj)
                    heapq.heappush(q, (fg2+fh2, fg2, fh2, i2, j2, i, j))

        if i_to is not None and j_to is not None and grid[i_to][j_to] < 1000 and numpy.isfinite(fgs[i_to][j_to]):
            print('go from', i, j, 'to', i_to, j_to)
            a.x, a.y = self.ij2xy(i_to, j_to)

    def step(self):
        # Spawn new actor if the top left corner is empty
        mask = self.get_mask(self.actors)
        x = y = self.r
        i, j = self.xy2ij(x, y)
        if mask[i][j] < 1000:  # Empty so spawn new
            goals = {g: self.g*self.wf for g in range(1, self.n+1) if random.random() < self.p}
            goals[self.n] = 1  # sentinel
            print(goals)
            a = Actor(x, y, goals, random.randint(1, 55))  # todo: don't hardcode
            self.actors.append(a)

        # Move each actor
        keep_actors = []
        for a in self.actors:
            self.move_actor(a)
            if a.goals:
                keep_actors.append(a)
            else:
                self.finished += 1
        random.shuffle(keep_actors)
        self.actors = keep_actors
        self.time += 1.0/self.g


def draw_frame(buffet, fn, up_f=200, down_f=4):
    # Pillow (at least whatever version I have) seems to segfault occasionally
    # That's why we run it inside a pool
    im = PIL.Image.new('RGBA', (int(buffet.w*up_f), int(buffet.h*up_f)), (255, 255, 255))
    draw = PIL.ImageDraw.Draw(im)

    font_size = 100
    font = PIL.ImageFont.truetype('helvetica.ttf', font_size)
    draw.text((0, buffet.h*up_f-font_size),
              'Time: %.1fs Finished: %.0f Rate: %.2f/s' % (buffet.time, buffet.finished, buffet.finished/buffet.time),
              fill=(0x66, 0x66, 0x66), font=font)
    for a in buffet.actors:
        next_goal = min(a.goals.keys())
        g = buffet.goals[next_goal]
        draw.line((a.x*up_f, a.y*up_f, g.x*up_f, g.y*up_f),
                  fill=(0xf3, 0xf3, 0xf3), width=2*down_f)
    for g in buffet.goals:
        #draw.ellipse(((g.x - g.r)*up_f, (g.y - g.r)*up_f,
        #              (g.x + g.r)*up_f, (g.y + g.r)*up_f),
        #             outline=(240, 240, 240), width=2*down_f, fill=(255, 0, 0))
        if g.emoji:
            emoji = PIL.Image.open('pics/food/%d.png' % g.emoji)
            emoji = emoji.resize((int(2*g.r*up_f), int(2*g.r*up_f)))
            im.alpha_composite(emoji, (int((g.x-g.r)*up_f),
                                       int((g.y-g.r)*up_f)))
    for a in buffet.actors:
        #draw.ellipse(((a.x - buffet.r)*up_f, (a.y - buffet.r)*up_f,
        #              (a.x + buffet.r)*up_f, (a.y + buffet.r)*up_f),
        #             fill=(255, 200, 200))
        emoji = PIL.Image.open('pics/people/%d.png' % a.emoji)
        emoji = emoji.resize((int(2*buffet.r*up_f), int(2*buffet.r*up_f)))
        im.alpha_composite(emoji, (int((a.x-buffet.r)*up_f),
                                   int((a.y-buffet.r)*up_f)))
        if a.loading_left:
            print(360*a.loading_left/(buffet.g*buffet.wf), 'degrees')
            draw.arc(((a.x - buffet.r)*up_f, (a.y - buffet.r)*up_f,
                      (a.x + buffet.r)*up_f, (a.y + buffet.r)*up_f),
                     start=0, end=360*a.loading_left/(buffet.g*buffet.wf),
                     fill=(0, 0, 0), width=2*down_f)
    im.resize((int(buffet.w*up_f/down_f),
               int(buffet.h*up_f/down_f)),
              PIL.Image.LANCZOS).save(fn)


if __name__ == '__main__':
    b = Buffet()
    pool = multiprocessing.Pool(10)
    frame = 0
    while True:
        b.step()
        pool.apply(draw_frame, (b, 'frames/%06d.png' % frame))
        frame += 1
