import numpy as np


def logtransf_data(x, offset=None):
    """
    Log transformation with a small value added

    To deal with 0's, either add a small offset manually
    or add the minimal non zero value.

    :param x: values
    :param offset: An offset, set to 0 for no offset.
    :return: Transformed values
    """
    if offset is None:
        offset = min(x[x > 0])
    return (np.log10(x + offset))


def asinhtransf_data(x, cof=5):
    """
    Asinh transformation accoring to
    asinh(x/cof)

    :param x: values
    :param cof: cofactor
    :return: transformed values
    """
    return np.arcsinh(x / cof)
