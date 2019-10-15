import json
import numpy
from matplotlib import pyplot
import pandas
import scipy.stats
import sys


def get_data(fns, p=80):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)

        max_t = max(t for _, _, t in data['data'])
        arrived = sorted(t for t, _, _ in data['data'])
        left = sorted(t for _, t, _ in data['data'] if t is not None)
        ts = numpy.linspace(0, max_t, 1000)
        in_queue = numpy.searchsorted(arrived, ts) - \
                   numpy.searchsorted(left, ts)
        in_queue_avg = in_queue[:int(len(in_queue)*2/3)].mean()

        # Use Little's law to infer the cycle time
        littles_latency = in_queue_avg / data['rate']

        # See if the queue is in an equilibrium
        k1 = sum(1 for t in arrived if t >= max_t/3)
        k2 = sum(1 for t in left if t >= max_t/3)
        a, scale = k1 + k2, 1./2
        rvs = scipy.stats.gamma.rvs(a, 0, scale, size=(10000, 2))
        probs = numpy.prod(scipy.stats.gamma.pdf(rvs, a, 0, scale), axis=1)
        prob = numpy.prod(scipy.stats.gamma.pdf([k1, k2], a, 0, scale))
        p_value = (probs < prob).mean()  # at least as extreme

        if p_value >= 0:
            yield (data['method'], data['rate'], littles_latency)


if __name__ == '__main__':
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['method', 'rate', 'latency'])

    colors = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
    for color, method in zip(colors, df['method'].unique()):
        df_m = df[df['method'] == method]  #  & df['latency'].apply(numpy.isfinite)]
        pyplot.scatter(df_m['rate'].values, df_m['latency'].values, marker='o', label=method, color=color)

    pyplot.grid(True, which='both', axis='both')
    pyplot.ylabel('Average waiting time (s)')
    pyplot.xlabel('Arrival rate (1/s)')
    pyplot.legend()
    pyplot.show()
