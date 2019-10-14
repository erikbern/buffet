import convoys.plotting
import convoys.single, convoys.utils
import json
import numpy
from matplotlib import pyplot
import pandas
import scipy.optimize
import sys


SENTINEL = 1e18


def get_data(fns, p=80):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)
        if data['rate'] < 0.25:
            continue

        df = pandas.DataFrame(data['data'], columns=['created', 'converted', 'now'])
        max_T = max(df['now'])

        in_queue = df['created'].count() - df['converted'].count()
        # Use little's law to infer the cycle time
        littles_latency = in_queue / data['rate']

        df = df[df['created'] >= max_T/3]  # Remove the "burn-in period"
        df['group'] = None
        unit, groups, (G, B, T) = convoys.utils.get_arrays(df)
        km = convoys.single.KaplanMeier()
        km.fit(B, T)
        t = numpy.linspace(0, max(T), 1000, endpoint=False)
        y = km.cdf(t)
        t, y = numpy.append(t, [SENTINEL]), numpy.append(y, [1.0])  # Add sentinel
        # average_t = numpy.trapz(t, y)
        percentile_latency = numpy.interp(p/100, y, t)

        print(data['method'], data['rate'], littles_latency, percentile_latency)
        yield (data['method'], data['rate'], littles_latency, percentile_latency)


if __name__ == '__main__':
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['method', 'rate', 'latency', 'latency2'])
    df.plot.scatter('latency', 'latency2')
    pyplot.ylim([0, 100])
    pyplot.show()

    max_latency = max(t for t in df['latency'] if t < SENTINEL * 0.01)
    y_max = max_latency*1.25
    df['latency_capped'] = df['latency'].apply(lambda z: y_max if z >= y_max else SENTINEL)

    colors = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
    for color, method in zip(colors, df['method'].unique()):
        df_m = df[df['method'] == method]
        pyplot.scatter(df_m['rate'].values, df_m['latency'].values, marker='o', label=method, color=color)
        for x, y in zip(df_m['rate'].values, df_m['latency_capped'].values):
            delta = 3
            pyplot.annotate('', xy=(x, y-delta), xytext=(x, y+delta), annotation_clip=False,
                            arrowprops=dict(color=color, arrowstyle='<-', lw=2))

        continue

        xy = [(x, y) for x, y in zip(df_m['rate'].values, df_m['latency'].values)]  # if y < SENTINEL * 0.01]
        max_x = max(x for x, y in xy if y < SENTINEL * 0.01)

        def loss(params):
            k0, c0 = params
            k, c = numpy.exp(k0), max_x + numpy.exp(c0)
            l = sum((numpy.log(k / (c - x)) - numpy.log(y))**2 for x, y in xy)
            print(k, c, '->', l)
            return l

        res = scipy.optimize.minimize(loss, [10, 10])
        k0, c0 = res.x
        k, c = numpy.exp(k0), max_x + numpy.exp(c0)
        print('solution:', k, c)
        xs = numpy.linspace(0, 2, 1000)
        pyplot.plot(xs, k / (c - xs), linestyle=':', color=color)


    pyplot.grid(True, which='both', axis='both')
    pyplot.legend()
    pyplot.ylim([0, y_max])
    pyplot.show()
