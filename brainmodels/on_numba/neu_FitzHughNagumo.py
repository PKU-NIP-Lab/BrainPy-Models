# -*- coding: utf-8 -*-

import brainpy as bp

__all__ = [
    'FitzHughNagumo'
]


class FitzHughNagumo(bp.NeuGroup):
    """FitzHugh-Nagumo neuron model [1]_.

    The FHN Model is an example of a relaxation oscillator
    because, if the external stimulus :math:`I_{\\text{ext}}`
    exceeds a certain threshold value, the system will exhibit
    a characteristic excursion in phase space, before the
    variables :math:`v` and :math:`w` relax back to their rest values.

    This behaviour is typical for spike generations (a short,
    nonlinear elevation of membrane voltage :math:`v`,
    diminished over time by a slower, linear recovery variable
    :math:`w`) in a neuron after stimulation by an external
    input current.

    .. math::

        {\\dot {v}}=v-{\\frac {v^{3}}{3}}-w+RI_{\\rm {ext}}

        \\tau {\\dot  {w}}=v+a-bw


    **Neuron Parameters**

    ============= ============== ======== ========================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- ------------------------
    a             1              \        positive constant

    b             1              \         positive constant

    tau           10             ms       Membrane time constant.

    V_th          1.           mV       Threshold potential of spike.
    ============= ============== ======== ========================


    **Neuron Variables**

    An object of neuron class record those variables for each synapse:

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    V                   0.                Membrane potential.

    w                   0.                A recovery variable which represents
                                          the combined effects of sodium channel
                                          de-inactivation and potassium channel
                                          deactivation.

    input               0.                External and synaptic input current.

    spike               0.                Flag to mark whether the neuron is spiking.

    t_last_spike       -1e7               Last spike time stamp.
    ================== ================= =========================================================

    References
    ----------

    .. [1] FitzHugh, Richard. "Impulses and physiological states in theoretical models of nerve membrane." Biophysical journal 1.6 (1961): 445-466.


    """

    target_backend = ['numpy', 'numba']

    @staticmethod
    def derivative(V, w, t, Iext, a, b, tau):
        dw = (V + a - b * w) / tau
        dV = V - V * V * V / 3 - w + Iext
        return dV, dw

    def __init__(self, size, a=0.7, b=0.8, tau=12.5, Vth=1.8, **kwargs):
        super(FitzHughNagumo, self).__init__(size=size, **kwargs)

        # parameters
        self.a = a
        self.b = b
        self.tau = tau
        self.Vth = Vth

        # variables
        self.V = bp.ops.zeros(self.num)
        self.w = bp.ops.zeros(self.num)
        self.input = bp.ops.zeros(self.num)
        self.spike = bp.ops.zeros(self.num, dtype=bool)
        self.t_last_spike = bp.ops.ones(self.num) * -1e7

        self.integral = bp.odeint(self.derivative)

    def update(self, _t, _i, _dt):
        for i in range(self.num):
            V, w = self.integral(self.V[i], self.w[i], _t, self.input[i], self.a, self.b, self.tau)
            spike = (V >= self.Vth) and (self.V[i] < self.Vth)
            self.spike[i] = spike
            if spike:
                self.t_last_spike[i] = _t
            self.V[i] = V
            self.w[i] = w
            self.input[i] = 0.