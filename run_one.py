import argparse
import json
import multiprocessing
from buffet import Buffet, draw_frame


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rate', type=float, default=1.0)
    parser.add_argument('--draw', action='store_true')
    parser.add_argument('--simple', action='store_true')  # draw less, for gif
    parser.add_argument('--method', choices=['classic', 'skippable', 'vline', 'anarchy'], required=True)
    parser.add_argument('--output', default='buffet.json')
    # todo: add more arguments
    args = parser.parse_args()

    b = Buffet(rate=args.rate, method=args.method)
    pool = multiprocessing.Pool(10)
    step = 0
    while True:
        print('###### step', step)
        data = b.step()
        with open(args.output, 'w') as f:
            json.dump(data, f)
        if args.draw:
            pool.apply(draw_frame, (b, 'frames/%06d.png' % step, args.simple))
        step += 1
