import convoys.plotting, convoys.utils
import json
import numpy
import pandas
from matplotlib import pyplot
import scipy.stats
import sys


METHODS = {
    'classic': 'Classic',
    'rogue': 'Rogue',
    'vline': 'Perpendicular lines',
    'skippable': 'Skips OK but never go backwards',
}


def get_queue_size(data):
    max_t = max(t for _, _, t in data['data'])
    arrived = sorted(t for t, _, _ in data['data'])
    left = sorted(t for _, t, _ in data['data'] if t is not None)
    ts = numpy.linspace(0, max_t, 1000)
    in_queue = numpy.searchsorted(arrived, ts) - \
               numpy.searchsorted(left, ts)
    return ts, in_queue


def queue_p_value(data):
    max_t = max(t for _, _, t in data['data'])
    arrived = sorted(t for t, _, _ in data['data'])
    left = sorted(t for _, t, _ in data['data'] if t is not None)
    k1 = sum(1 for t in arrived if t >= max_t/3)
    k2 = sum(1 for t in left if t >= max_t/3)
    a, scale = k1 + k2, 1./2
    rvs = scipy.stats.gamma.rvs(a, 0, scale, size=(10000, 2))
    rvs = scipy.stats.poisson.rvs(rvs, 0)
    deltas = rvs[:,1] - rvs[:,0]
    p_value = (deltas > k1 - k2).mean()
    return p_value


def plot_queues(fns):
    datas_by_method = {}
    for fn in sorted(fns):
        data = json.load(open(fn))
        datas_by_method.setdefault(data['method'], []).append(data)

    c = pyplot.cm.get_cmap('RdYlGn')
    for method, datas in datas_by_method.items():
        out_fn = 'queue_%s.png' % method
        print('Generating', out_fn)
        pyplot.clf()
        for data in datas:
            ts, in_queue = get_queue_size(data)
            p_value = queue_p_value(data)
            color = (1, .0, .0, .5) if p_value < 0.05 else (.0, 1, .0, .5)
            pyplot.plot(ts, in_queue, color=color, linewidth=2)
            pyplot.text(ts[-1], in_queue[-1], data['rate'], ha='left', va='center', color=color)

        pyplot.title('Number of people in the system for the "%s" method' % METHODS[method])
        pyplot.xlabel('Time elapsed (s)')
        pyplot.ylabel('Number of people in the system')
        pyplot.savefig(out_fn)


def get_cohort_data(fns):
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)
        for created, converted, now in data['data']:
            yield fn, data['rate'], data['method'], created, converted, now


def plot_cohorts(df, slice_by, title, out_fn, legend=False, annotate=None):
    print('Generating', out_fn)
    unit, groups, (G, B, T) = convoys.utils.get_arrays(df, groups=slice_by)
    pyplot.clf()
    m = convoys.plotting.plot_cohorts(G, B, T, groups=groups, plot_kwargs={'linewidth': 5}, label_fmt='%(group)s')
    max_t = max(df['now'])
    ts = numpy.linspace(0, max_t, 1000)
    colors = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
    for j, group in enumerate(groups):
        ys = m.cdf(j, ts)
        t_end, y_end = max((t, y) for t, y in zip(ts, ys) if not numpy.isnan(y))
        if annotate:
            pyplot.text(t_end, 100.*y_end, annotate % group, ha='left', va='center', color=colors[j%len(colors)])

    pyplot.title(title)
    pyplot.xlabel('Time elapsed after person entering system (s)')
    pyplot.ylabel('Completion rate (%)')
    if legend:
        pyplot.legend()
    pyplot.savefig(out_fn)


def plot_all_cohorts(fns):
    df = pandas.DataFrame(get_cohort_data(fns), columns=['filename', 'rate', 'method', 'created', 'converted', 'now'])
    df['rate_group'] = df['rate'].apply(lambda rate: numpy.round(rate*5)/5)
    max_t = max(df['now'])
    df = df[df['created'] >= max_t/3]  # Remove the "burn-in period"

    for method in df['method'].unique():
        df_m = df[df['method'] == method]
        plot_cohorts(df_m, 'rate_group', 'Time to get food for the "%s" method' % METHODS[method], 'cohorts_%s.png' % method, annotate='rate=%.1f/s')

    df_m = df[df['rate_group'] == 0.6]
    df_m['method_human_readable'] = df_m['method'].apply(lambda z: METHODS[z])
    plot_cohorts(df_m, 'method_human_readable', 'Time to get food per method (arrival rate 0.6/s)', 'cohorts_all.png', legend=True)


def plot_stats(fns):
    xs_by_method = {}
    ys_by_method = {}
    for fn in fns:
        with open(fn, 'r') as f:
            data = json.load(f)

        # Get queue size over time
        ts, in_queue = get_queue_size(data)
        in_queue_avg = in_queue[int(len(in_queue)/3):].mean()

        # Use Little's law to infer the cycle time
        littles_latency = in_queue_avg / data['rate']

        # See if the queue is in an equilibrium
        if queue_p_value(data) > 0.05:
            xs_by_method.setdefault(data['method'], []).append(data['rate'])
            ys_by_method.setdefault(data['method'], []).append(littles_latency)

    for method in sorted(xs_by_method.keys()):
        pyplot.scatter(xs_by_method[method], ys_by_method[method], label=method, s=150, alpha=0.7)

    pyplot.grid(True, which='both', axis='both')
    pyplot.ylabel('Average waiting time (s)')
    pyplot.xlabel('Arrival rate (1/s)')
    pyplot.legend()
    pyplot.savefig('stats.png')


if __name__ == '__main__':
    pyplot.style.use('seaborn-whitegrid')
    pyplot.rcParams.update({'font.size': 18})
    pyplot.figure(figsize=(12, 9))
    fns = sys.argv[1:]

    plot_stats(fns)
    plot_queues(fns)
    plot_all_cohorts(fns)

