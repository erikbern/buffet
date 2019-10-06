import itertools
import json
import multiprocessing
import random
from buffet import Buffet, draw_frame


def run_one(args):
    method, rate = args
    b = Buffet(rate=rate, method=method)
    for step in range(3000):  # burn in + samples
        data = b.step()
    return (method, rate, data)


if __name__ == '__main__':
    methods = ['classic', 'vline', 'rogue']
    rates = [(z+1)/10 for z in range(15)]
    pool = multiprocessing.Pool()
    combinations = list(itertools.product(methods, rates))
    random.shuffle(combinations)
    for method, rate, data in pool.imap_unordered(run_one, combinations):
        print(method, rate, data)
        with open('simulations/%s_%f.json' % (method, rate), 'w') as f:
            json.dump({'method': method, 'rate': rate, 'data': data}, f)
    pool.close()
    pool.join()
