import convoys.plotting, convoys.utils
import json
from matplotlib import pyplot
import pandas
import sys


def get_data(fns):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)
        if type(data) == dict:
            data = data['data']
        for created, converted, now in data:
            yield fn, created, converted, now


if __name__ == '__main__':
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['group', 'created', 'converted', 'now'])
    max_T = max(df['now'])
    df = df[df['created'] >= max_T/3]  # Remove the "burn-in period"
    unit, groups, (G, B, T) = convoys.utils.get_arrays(df)
    convoys.plotting.plot_cohorts(G, B, T, groups=groups, ci=0.8)
    pyplot.legend()
    pyplot.show()
