import convoys.plotting, convoys.utils
import json
from matplotlib import pyplot
import numpy
import pandas
import sys


def get_data(fns):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)
        for created, converted, now in data['data']:
            yield fn, data['rate'], data['method'], created, converted, now


if __name__ == '__main__':
    pyplot.style.use('seaborn-whitegrid')
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['filename', 'rate', 'method', 'created', 'converted', 'now'])
    max_T = max(df['now'])
    df = df[df['created'] >= max_T/3]  # Remove the "burn-in period"
    unit, groups, (G, B, T) = convoys.utils.get_arrays(df, groups='method')
    m = convoys.plotting.plot_cohorts(G, B, T, groups=groups)  #, ci=0.8)
    ts = numpy.linspace(0, max_T, 1000)
    colors = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
    for j, (group, color) in enumerate(zip(groups, colors)):
        ys = m.cdf(j, ts)
        t_end, y_end = max((t, y) for t, y in zip(ts, ys) if not numpy.isnan(y))
        pyplot.text(t_end, 100.*y_end, group, ha='left', va='center', color=color)

    pyplot.xlabel('Time elapsed after person entering system (s)')
    pyplot.ylabel('Completion rate (%)')
    pyplot.show()
