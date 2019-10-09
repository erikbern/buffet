import argparse
import json
import multiprocessing
from buffet import Buffet, draw_frame


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rate', type=float, default=1.0)
    parser.add_argument('--draw', action='store_true')
    parser.add_argument('--simple', action='store_true')  # draw less, for gif
    parser.add_argument('--method', choices=['classic', 'vline', 'rogue', 'skippable'], required=True)
    parser.add_argument('--output', default='buffet.json')
    parser.add_argument('--draw-dir', default='frames')
    parser.add_argument('--steps', default=1500, type=int)
    # todo: add more arguments
    args = parser.parse_args()

    b = Buffet(rate=args.rate, method=args.method)
    pool = multiprocessing.Pool(10)  # only used for drawing, see comment in draw_frame
    for step in range(args.steps):
        print('###### step', step)
        data = b.step()
        with open(args.output, 'w') as f:
            json.dump(data, f)
        if args.draw:
            pool.apply(draw_frame, (b, '%s/%06d.png' % (args.draw_dir, step), args.simple))
