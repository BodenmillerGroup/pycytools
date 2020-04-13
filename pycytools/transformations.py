import numpy as np


def logtransf_data(x):
    """

    :param x:
    :return:
    """
    xmin = min(x[x > 0])
    return (np.log10(x + xmin))


def asinhtransf_data(x, cof=5):
    """

    :param x:
    :param cof:
    :return:
    """
    return np.arcsinh(x / cof)
