import argparse
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
        self.path = []
        self.path_color = tuple(0xe0 + int(0x20*random.random()) for z in range(3))
        self.reached = []


class Goal:
    def __init__(self, x, y, r, emoji):
        self.x = x
        self.y = y
        self.r = r
        self.emoji = emoji


class Buffet:
    def __init__(self, n=7, p=0.4, g=10, r=0.18, gr=0.24, h=4, wf=2, nw=3.0, rate=1.0, method='anarchy'):
        self.n = n   # Number of items on buffet
        self.p = p   # Probability of wanting each item
        self.g = g   # Granularity of grid
        self.r = r   # Radius of each actor
        self.h = h   # Height of grid
        self.wf = wf  # How long it takes to get food relative to moving 1 step
        self.w = nw + n + 1  # Width of grid
        self.rate = rate  # Rate of spawning new actors
        self.method = method
        emojis = numpy.random.choice(19, size=n, replace=False)+1  # TODO: don't hardcode size
        self.goals = [Goal(x=nw+i, y=gr, r=gr, emoji=e) for i, e in enumerate(emojis)]
        self.goals.append(Goal(x=self.w+10, y=0, r=10+1, emoji=None))

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
                    grid[i][j] += 1000*(1 + (self.h - y)/self.h)  # TODO: explain

        return grid

    def move_actor(self, a):
        # Generate a mask of pixels 
        grid = self.get_mask([actor for actor in self.actors if actor != a])

        # What's the next goal for this actor?
        next_goal = min(a.goals.keys())
        g = self.goals[next_goal]

        # If we're close to the goal, just stop and load food
        a.loading_left = None
        if max(abs(a.x - g.x), abs(a.y - g.y)) <= g.r:  # square goals
        # if (a.x - g.x)**2 + (a.y - g.y)**2 <= g.r**2:
            a.goals[next_goal] -= 1
            a.loading_left = a.goals[next_goal]
            print('loading:', next_goal, ':', a.goals[next_goal])
            if a.goals[next_goal] <= 0:
                a.goals.pop(next_goal)
                a.reached.append(next_goal)

        if self.method in ['anarchy']:
            # 9 directions
            dirs = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, -1), (-1, 1)]
        elif self.method in ['classic']:
            dirs = [(0, 0), (0, -1), (1, -1), (1, 0)]
        elif self.method in ['vline', 'skippable']:
            dirs = [(0, 0), (1, 0), (0, -1), (-1, 0), (1, -1), (-1, -1)]

        def heuristic(i1, j1, i2, j2):
            return max(abs(i1-i2), abs(j1-j2))

        # Use A* search algorithm
        # Seed starting points
        q = []
        ai, aj = self.xy2ij(a.x, a.y)
        for (i, j), _ in numpy.ndenumerate(grid):
            x, y = self.ij2xy(i, j)
            if numpy.isfinite(grid[i][j]):
                # if (x - g.x)**2 + (y - g.y)**2 < g.r**2:
                if max(abs(x - g.x), abs(y - g.y)) < g.r:  # square goals
                    fg, fh = 0, heuristic(i, j, ai, aj)
                    heapq.heappush(q, (fg+fh, fg, fh, i, j, -1, -1))

        fgs = numpy.ones(grid.shape) * float('inf')
        visited = set()
        i_to_matrix = numpy.ones(grid.shape, dtype=int) * -1
        j_to_matrix = numpy.ones(grid.shape, dtype=int) * -1
        while q:
            ff, fg, fh, i, j, i_to, j_to = heapq.heappop(q)
            if (i, j) in visited:
                continue
            i_to_matrix[i][j] = i_to
            j_to_matrix[i][j] = j_to
            if i == ai and j == aj:
                print(ff, fg, fh, i, j, i_to, j_to)
                break
            visited.add((i, j))
            fgs[i][j] = fg
            x, y = self.ij2xy(i, j)
            for di, dj in dirs:
                i2, j2 = i+di, j+dj
                step_size = ((di**2 + dj**2)**0.5 +  # penalization of diagonal moves
                             + grid[i2][j2])  # last term just penalizes going through other people
                if self.method == 'vline':
                    if abs(x - g.x) < self.r and di == 1 and dj == 0:
                        # prioritize getting the vertical alignment with the goal
                        step_size *= 1e-3
                elif self.method == 'skippable':
                    if abs(y - g.y) < self.r and di == j and dj == 1:
                        # prioritize getting the horizontal alignment with the goal
                        step_size *= 1e-3
                fg2 = fg + step_size
                if numpy.isfinite(grid[i2][j2]):
                    fh2 = heuristic(i2, j2, ai, aj)
                    heapq.heappush(q, (fg2+fh2, fg2, fh2, i2, j2, i, j))
        else:
            i, j, i_to, j_to = -1, -1, -1, -1

        if i_to is -1:
            print('stuck!!! next goal is', next_goal)

        if i_to != -1 and j_to != -1 and grid[i_to][j_to] < 1000 and numpy.isfinite(fgs[i_to][j_to]):
            print('go from', i, j, 'to', i_to, j_to)
            a.x, a.y = self.ij2xy(i_to, j_to)

        # Reconstruct the shortest path
        a.path = []
        while (i, j) != (-1, -1):
            a.path.append(self.ij2xy(i, j))
            i, j = i_to_matrix[i][j], j_to_matrix[i][j]

    def step(self):
        # Spawn new actor randomly
        if random.random() < self.rate / self.g:
            mask = self.get_mask(self.actors)
            # Find the most top left position that's available
            j, i = min((j, i) for (i, j), v in numpy.ndenumerate(mask) if v < 1000)
            print('spawning at', i, j)
            #i, j = self.xy2ij(self.r, self.r)
            #if mask[i][j] < 1000:
            goals = {}
            while len(goals) == 0:
                goals = {g: self.g*self.wf for g in range(self.n) if random.random() < self.p}
            goals[self.n] = 1  # sentinel
            x, y = self.ij2xy(i, j)
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


def draw_frame(buffet, fn, simple):
    # Pillow (at least whatever version I have) seems to segfault occasionally
    # That's why we run it inside a pool
    if simple:
        up_f, down_f = 200, 4
    else:
        up_f, down_f = 200, 2

    im = PIL.Image.new('RGBA', (int(buffet.w*up_f), int(buffet.h*up_f)), (255, 255, 255))
    draw = PIL.ImageDraw.Draw(im)

    if not simple:
        for a in buffet.actors:
            for j in range(len(a.path)-1):
                draw.line((a.path[j][0]*up_f, a.path[j][1]*up_f, a.path[j+1][0]*up_f, a.path[j+1][1]*up_f),
                          fill=a.path_color, width=2*down_f)
        font_size = 100
        font = PIL.ImageFont.truetype('helvetica.ttf', font_size)
        draw.text((0, buffet.h*up_f-font_size),
                  'Time: %.1fs Finished: %.0f Rate: %.2f/s' % (buffet.time, buffet.finished, buffet.finished/buffet.time),
                  fill=(0x66, 0x66, 0x66), font=font)
    for g in buffet.goals:
        if g.emoji:
            emoji = PIL.Image.open('pics/food/%d.png' % g.emoji)
            emoji = emoji.resize((int(2*g.r*up_f), int(2*g.r*up_f)))
            im.alpha_composite(emoji, (int((g.x-g.r)*up_f),
                                       int((g.y-g.r)*up_f)))
    for a in buffet.actors:
        emoji = PIL.Image.open('pics/people/%d.png' % a.emoji)
        emoji = emoji.resize((int(2*buffet.r*up_f), int(2*buffet.r*up_f)))
        im.alpha_composite(emoji, (int((a.x-buffet.r)*up_f),
                                   int((a.y-buffet.r)*up_f)))
        plate = PIL.Image.open('pics/plate.png')
        minis = [('pics/plate.png', -buffet.r, 0)] + [('pics/food/%d.png' % buffet.goals[r].emoji, -buffet.r, 0) for r in a.reached]
        if a.loading_left:
            #draw.arc(((a.x - buffet.r)*up_f, (a.y - buffet.r)*up_f,
            #          (a.x + buffet.r)*up_f, (a.y + buffet.r)*up_f),
            #         start=0, end=360*a.loading_left/(buffet.g*buffet.wf),
            #         fill=(0, 0, 0), width=2*down_f)
            frac = a.loading_left / (buffet.g*buffet.wf)
            path = 'pics/food/%d.png' % buffet.goals[min(a.goals.keys())].emoji
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rate', type=float, default=1.0)
    parser.add_argument('--draw', action='store_true')
    parser.add_argument('--simple', action='store_true')  # draw less, for gif
    parser.add_argument('--method', choices=['classic', 'skippable', 'vline', 'anarchy'])
    # todo: add more arguments
    args = parser.parse_args()

    b = Buffet(rate=args.rate, method=args.method)
    pool = multiprocessing.Pool(10)
    frame = 0
    while True:
        b.step()
        if args.draw:
            pool.apply(draw_frame, (b, 'frames/%06d.png' % frame, args.simple))
        frame += 1
