import json
import numpy
from matplotlib import pyplot
import pandas
import sys
from lib import get_queue_size, queue_p_value


def get_data(fns, p=80):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)

        # Get queue size over time
        ts, in_queue = get_queue_size(data)
        in_queue_avg = in_queue[int(len(in_queue)/3):].mean()

        # Use Little's law to infer the cycle time
        littles_latency = in_queue_avg / data['rate']

        # See if the queue is in an equilibrium
        p_value = queue_p_value(data)

        if p_value > 0.05:
            yield (data['method'], data['rate'], littles_latency)


if __name__ == '__main__':
    pyplot.style.use('seaborn-whitegrid')
    df = pandas.DataFrame(get_data(sys.argv[1:]), columns=['method', 'rate', 'latency'])

    for method in df['method'].unique():
        df_m = df[df['method'] == method]
        pyplot.scatter(df_m['rate'].values, df_m['latency'].values, marker='o', label=method)

    pyplot.grid(True, which='both', axis='both')
    pyplot.ylabel('Average waiting time (s)')
    pyplot.xlabel('Arrival rate (1/s)')
    pyplot.legend()
    pyplot.show()
