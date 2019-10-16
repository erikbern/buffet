import numpy
import scipy.stats


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
    probs = numpy.prod(scipy.stats.gamma.pdf(rvs, a, 0, scale), axis=1)
    prob = numpy.prod(scipy.stats.gamma.pdf([k1, k2], a, 0, scale))
    p_value = (probs < prob).mean()  # at least as extreme
    return p_value
