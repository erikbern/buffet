import json
from matplotlib import pyplot
import numpy
import sys
from lib import get_queue_size


def plot_queues(fns):
    pyplot.style.use('seaborn-whitegrid')
    c = pyplot.cm.get_cmap('viridis')
    colors = c(numpy.linspace(0, 1, len(fns)))
    for color, fn in zip(colors, sorted(fns)):
        data = json.load(open(fn))
        ts, in_queue = get_queue_size(data)
        pyplot.plot(ts, in_queue, color=color)
        pyplot.text(ts[-1], in_queue[-1], data['rate'], ha='left', va='center', color=color)

    pyplot.xlabel('Time elapsed (s)')
    pyplot.ylabel('Number of people in the system')
    pyplot.legend()


if __name__ == '__main__':
    plot_queues(sys.argv[1:])
    pyplot.show()
    
