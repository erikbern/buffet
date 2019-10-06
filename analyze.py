import convoys.plotting, convoys.utils
import json
from matplotlib import pyplot
import pandas
import sys


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    df = pandas.DataFrame(data, columns=['created', 'converted', 'now'])
    df['group'] = 'Everyone'
    print(df)
    unit, groups, (G, B, T) = convoys.utils.get_arrays(df)
    convoys.plotting.plot_cohorts(G, B, T)
    convoys.plotting.plot_cohorts(G, B, T, model='gamma', plot_kwargs={'ls': ':'})
    pyplot.show()
