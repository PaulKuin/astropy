# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Classes that deal with computing intervals from arrays of values based on
various criteria.
"""

from __future__ import division, print_function

import abc
import numpy as np

from ..extern import six
from ..utils.misc import InheritDocstrings
from .transform import BaseTransform
from .zscale import zscale


__all__ = ['BaseInterval', 'ManualInterval', 'MinMaxInterval',
           'AsymmetricPercentileInterval', 'PercentileInterval',
           'ZScaleInterval']


@six.add_metaclass(InheritDocstrings)
class BaseInterval(BaseTransform):
    """
    Base class for the interval classes, which, when called with an
    array of values, return an interval computed following different
    algorithms.
    """

    @abc.abstractmethod
    def get_limits(self, values):
        """
        Return the minimum and maximum value in the interval based on
        the values provided.

        Parameters
        ----------
        values : `~numpy.ndarray`
            The image values.

        Returns
        -------
        vmin, vmax : float
            The mininium and maximum image value in the interval.
        """

    def __call__(self, values, clip=True, out=None):
        """
        Transform values using this interval.

        Parameters
        ----------
        values : array-like
            The input values.
        clip : bool, optional
            If `True` (default), values outside the [0:1] range are
            clipped to the [0:1] range.
        out : `~numpy.ndarray`, optional
            If specified, the output values will be placed in this array
            (typically used for in-place calculations).

        Returns
        -------
        result : `~numpy.ndarray`
            The transformed values.
        """

        vmin, vmax = self.get_limits(values)

        if out is None:
            values = np.subtract(values, float(vmin))
        else:
            if out.dtype.kind != 'f':
                raise TypeError('Can only do in-place scaling for '
                                'floating-point arrays')
            values = np.subtract(values, float(vmin), out=out)

        if (vmax - vmin) != 0:
            np.true_divide(values, vmax - vmin, out=values)

        if clip:
            np.clip(values, 0., 1., out=values)

        return values


class ManualInterval(BaseInterval):
    """
    Interval based on user-specified values.

    Parameters
    ----------
    vmin : float, optional
        The minimum value in the scaling.  Defaults to the image
        minimum.
    vmax : float, optional
        The maximum value in the scaling.  Defaults to the image
        maximum.
    """

    def __init__(self, vmin=None, vmax=None):
        self.vmin = vmin
        self.vmax = vmax

    def get_limits(self, values):
        vmin = self.vmin or np.min(values)
        vmax = self.vmax or np.max(values)
        return vmin, vmax


class MinMaxInterval(BaseInterval):
    """
    Interval based on the minimum and maximum values in the data.
    """

    def get_limits(self, values):
        return np.min(values), np.max(values)


class AsymmetricPercentileInterval(BaseInterval):
    """
    Interval based on a keeping a specified fraction of pixels (can be
    asymmetric).

    Parameters
    ----------
    lower_percentile : float
        The lower percentile below which to ignore pixels.
    upper_percentile : float
        The upper percentile above which to ignore pixels.
    n_samples : int, optional
        Maximum number of values to use. If this is specified, and there
        are more values in the dataset as this, then values are randomly
        sampled from the array (with replacement).
    """

    def __init__(self, lower_percentile, upper_percentile, n_samples=None):
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
        self.n_samples = n_samples

    def get_limits(self, values):
        # Make sure values is a Numpy array
        values = np.asarray(values).ravel()

        # If needed, limit the number of samples. We sample with replacement
        # since this is much faster.
        if self.n_samples is not None and values.size > self.n_samples:
            values = np.random.choice(values, self.n_samples)

        # Filter out invalid values (inf, nan)
        values = values[np.isfinite(values)]

        # Determine values at percentiles
        vmin, vmax = np.percentile(values, (self.lower_percentile,
                                            self.upper_percentile))

        return vmin, vmax


class PercentileInterval(AsymmetricPercentileInterval):
    """
    Interval based on a keeping a specified fraction of pixels.

    Parameters
    ----------
    percentile : float
        The fraction of pixels to keep. The same fraction of pixels is
        eliminated from both ends.
    n_samples : int, optional
        Maximum number of values to use. If this is specified, and there
        are more values in the dataset as this, then values are randomly
        sampled from the array (with replacement).
    """

    def __init__(self, percentile, n_samples=None):
        lower_percentile = (100 - percentile) * 0.5
        upper_percentile = 100 - lower_percentile
        super(PercentileInterval, self).__init__(lower_percentile,
                                                 upper_percentile,
                                                 n_samples=n_samples)


class ZScaleInterval(BaseInterval):
    """
    Interval based on IRAF's zscale.

    http://iraf.net/forum/viewtopic.php?showtopic=134139

    Parameters
    ----------
    image : array_like
        Input array.
    nsamples : int, optional
        Number of points in array to sample for determining scaling
        factors.  Defaults to 1000.
    contrast : float, optional
        Scaling factor (between 0 and 1) for determining min and max.
        Larger values increase the difference between min and max values
        used for display. Defaults to 0.25.
    max_reject : float, optional
        If more than ``max_reject * npixels`` pixels are rejected, then
        the returned values are the min and max of the data. Defaults to
        0.5.
    min_npixels : int, optional
        If less than ``min_npixels`` pixels are rejected, then the
        returned values are the min and max of the data. Defaults to 5.
    krej : float, optional
        Number of sigma used for the rejection. Defaults to 2.5.
    max_iterations : int, optional
        Maximum number of iterations for the rejection. Defaults to 5.
    """

    def __init__(self, nsamples=1000, contrast=0.25, max_reject=0.5,
                 min_npixels=5, krej=2.5, max_iterations=5):
        self.nsamples = nsamples
        self.contrast = contrast
        self.max_reject = max_reject
        self.min_npixels = min_npixels
        self.krej = krej
        self.max_iterations = max_iterations

    def get_limits(self, values):
        return zscale(values, nsamples=self.nsamples, contrast=self.contrast,
                      max_reject=self.max_reject,
                      min_npixels=self.min_npixels, krej=self.krej,
                      max_iterations=self.max_iterations)
