import json
from matplotlib import pyplot
import numpy
import scipy.optimize
import sys


def plot_queues(fns):
    pyplot.style.use('seaborn-whitegrid')
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

    pyplot.xlabel('Time elapsed (s)')
    pyplot.ylabel('Number of people in the system')
    pyplot.legend()


if __name__ == '__main__':
    plot_queues(sys.argv[1:])
    pyplot.show()
    
