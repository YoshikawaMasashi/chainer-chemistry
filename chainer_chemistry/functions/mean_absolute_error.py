import numpy

import chainer
from chainer.backends import cuda
from chainer import function_node
from chainer.utils import type_check


class MeanAbsoluteError(function_node.FunctionNode):

    """Mean absolute error function."""

    def __init__(self, ignore_nan=False):
        # TODO(mottodora): implement task weight calculation
        self.ignore_nan = ignore_nan

    def check_type_forward(self, in_types):
        type_check.expect(in_types.size() == 2)
        type_check.expect(
            in_types[0].dtype == numpy.float32,
            in_types[1].dtype == numpy.float32,
            in_types[0].shape == in_types[1].shape
        )

    def forward_cpu(self, inputs):
        self.retain_inputs((0, 1))
        x0, x1 = inputs
        diff = (inputs[0] - inputs[1]).ravel()
        # TODO(mottodora): add reduce option
        if self.ignore_nan:
            diff[numpy.isnan(diff)] = 0.
        return numpy.array(abs(diff).sum() / diff.size, dtype=diff.dtype),

    def forward_gpu(self, inputs):
        self.retain_inputs((0, 1))
        cupy = cuda.cupy
        diff = (inputs[0] - inputs[1]).ravel()
        if self.ignore_nan:
            diff[cupy.isnan(diff)] = 0.
        return abs(diff).sum() / diff.dtype.type(diff.size),

    def backward(self, indexes, gy):
        x0, x1 = self.get_retained_inputs()
        xp = cuda.get_array_module(x0)
        diff = x0 - x1
        if self.ignore_nan:
            diff = chainer.functions.where(xp.isnan(diff.array),
                                           xp.zeros_like(diff.array), diff)
        coeff = gy[0] * gy[0].data.dtype.type(1. / diff.size)
        coeff = chainer.functions.broadcast_to(coeff, diff.shape)
        gx0 = coeff * chainer.functions.sign(diff)
        return gx0, -gx0


def mean_absolute_error(x0, x1, ignore_nan=False):
    """Mean absolute error function.

    This function computes mean absolute error between two variables. The mean
    is taken over the minibatch.

    """
    return MeanAbsoluteError(ignore_nan).apply((x0, x1))[0]
