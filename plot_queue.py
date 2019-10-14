import json
from matplotlib import pyplot
import numpy
import scipy.optimize
import sys


def plot_queues(fns):
    c = pyplot.cm.get_cmap('viridis')
    colors = c(numpy.linspace(0, 1, len(fns)))
    for color, fn in zip(colors, sorted(fns)):
        data = json.load(open(fn))
        max_t = max(t for _, _, t in data['data'])
        arrived = sorted(t for t, _, _ in data['data'])
        left = sorted(t for _, t, _ in data['data'] if t is not None)
        ts = numpy.linspace(0, max_t, 1000)
        in_queue = numpy.searchsorted(arrived, ts) - \
                   numpy.searchsorted(left, ts)
        pyplot.plot(ts, in_queue, color=color)
        pyplot.text(ts[-1], in_queue[-1], data['rate'], ha='left', va='center', color=color)


def fit(ts, in_queue):
    # try to fit a y = min(kx, m)

    def loss(params, f):
        loss = numpy.sum((f(params) - in_queue)**2)
        return loss

    def f1(params):
        k, m = params
        return numpy.minimum(k*ts, m)

    def f2(params):
        k, = params
        return k*ts

    r1 = scipy.optimize.minimize(loss, (1, 1), args=(f1,))
    pyplot.plot(ts, f1(r1.x))

    r2 = scipy.optimize.minimize(loss, (1,), args=(f2,))
    pyplot.plot(ts, f2(r2.x))

    print('ratio:', r1.fun - r2.fun)


if __name__ == '__main__':
    plot_queues(sys.argv[1:])
    pyplot.legend()
    pyplot.show()
    
