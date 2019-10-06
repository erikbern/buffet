import itertools
import json
import multiprocessing
import os
import random
from buffet import Buffet, draw_frame


def run_one(args):
    method, rate = args
    fn = 'simulations/%s_%f.json' % (method, rate)
    if os.path.exists(fn):
        return

    b = Buffet(rate=rate, method=method)
    for step in range(3000):  # burn in + samples
        print('###### step', step)
        data = b.step()

    with open(fn, 'w') as f:
        json.dump({'method': method, 'rate': rate, 'data': data}, f)


if __name__ == '__main__':
    methods = ['classic', 'vline', 'rogue', 'skippable']
    rates = [(z+1)/10 for z in range(15)]
    pool = multiprocessing.Pool()
    combinations = list(itertools.product(methods, rates))
    random.shuffle(combinations)

    for _ in pool.imap_unordered(run_one, combinations):
        pass

    pool.close()
    pool.join()
