import convoys.single, convoys.utils
import json
import numpy
from matplotlib import pyplot
import pandas
import sys


def get_data(fns, p=90):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)
        df = pandas.DataFrame(data['data'], columns=['created', 'converted', 'now'])
        max_T = max(df['now'])
        throughput_1 = (df['created'] >= max_T/3).sum() / (max_T * 2/3)
        throughput_2 = (df['converted'] >= max_T/3).sum() / (max_T * 2/3)
        throughput = (throughput_1 * throughput_2)**0.5
        df = df[df['created'] >= max_T/3]  # Remove the "burn-in period"
        df['group'] = None
        unit, groups, (G, B, T) = convoys.utils.get_arrays(df)
        km = convoys.single.KaplanMeier()
        km.fit(B, T)
        t = numpy.linspace(0, max(T), 1000, endpoint=False)
        y = km.cdf(t)
        average_t = numpy.trapz(t, y)
        percentile_t = numpy.interp(p/100, y, t)
        # throughput = df['created'].count() / (max_T * 2/3)
        yield (data['method'], data['rate'], throughput, percentile_t)


if __name__ == '__main__':
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['method', 'rate', 'throughput', 'latency'])
    for method in df['method'].unique():
        df_m = df[df['method'] == method]
        pyplot.scatter(df_m['throughput'].values, df_m['latency'].values, label=method)

    pyplot.yscale('log')
    pyplot.legend()
    pyplot.show()
