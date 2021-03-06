# -*- coding: utf-8 -*-

import brainpy as bp

__all__ = [
    'AMPA1',
    'AMPA2',
]


class AMPA1(bp.TwoEndConn):
    """AMPA conductance-based synapse (type 1).

    .. math::

        I(t)&=\\bar{g} s(t) (V-E_{syn})

        \\frac{d s}{d t}&=-\\frac{s}{\\tau_{decay}}+\\sum_{k} \\delta(t-t_{j}^{k})


    **Synapse Parameters**

    ============= ============== ======== ===================================================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- -----------------------------------------------------------------------------------
    tau_decay     2.             ms       The time constant of decay.

    g_max         .1             µmho(µS) Maximum conductance.

    E             0.             mV       The reversal potential for the synaptic current. (only for conductance-based model)

    mode          'scalar'       \        Data structure of ST members.
    ============= ============== ======== ===================================================================================


    **Synapse Variables**

    An object of synapse class record those variables for each synapse:

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    s                   0.                Gating variable.

    g                   0.                Synapse conductance on post-synaptic neuron.

    ================== ================= =========================================================


    References:
        .. [1] Brunel N, Wang X J. Effects of neuromodulation in a cortical network
                model of object working memory dominated by recurrent inhibition[J].
                Journal of computational neuroscience, 2001, 11(1): 63-85.
    """

    target_backend = 'general'

    @staticmethod
    def derivative(s, t, tau):
        ds = - s / tau
        return ds

    def __init__(self, pre, post, conn, delay=0., g_max=0.10, E=0., tau=2.0, **kwargs):
        # parameters
        self.g_max = g_max
        self.E = E
        self.tau = tau
        self.delay = delay

        # connections
        self.conn = conn(pre.size, post.size)
        self.conn_mat = conn.requires('conn_mat')
        self.size = bp.ops.shape(self.conn_mat)

        # data
        self.s = bp.ops.zeros(self.size)
        self.g = self.register_constant_delay('g', size=self.size, delay_time=delay)

        self.int_s = bp.odeint(f=self.derivative, method='exponential_euler')
        super(AMPA1, self).__init__(pre=pre, post=post, **kwargs)

    def update(self, _t):
        self.s = self.int_s(self.s, _t, self.tau)
        self.s += bp.ops.unsqueeze(self.pre.spike, 1) * self.conn_mat
        self.g.push(self.g_max * self.s)
        self.post.input -= bp.ops.sum(self.g.pull(), 0) * (self.post.V - self.E)


class AMPA2(bp.TwoEndConn):
    """AMPA conductance-based synapse (type 2).
    
    .. math::

        I_{syn}&=\\bar{g}_{syn} s (V-E_{syn})

        \\frac{ds}{dt} &=\\alpha[T](1-s)-\\beta s

    **Synapse Parameters**
    
    ============= ============== ======== ================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- ------------------------------------------------
    g_max         .42            µmho(µS) Maximum conductance.

    E             0.             mV       The reversal potential for the synaptic current.

    alpha         .98            \        Binding constant.

    beta          .18            \        Unbinding constant.

    T             .5             mM       Neurotransmitter concentration.

    T_duration    .5             ms       Duration of the neurotransmitter concentration.

    mode          'scalar'       \        Data structure of ST members.
    ============= ============== ======== ================================================    
    

    **Synapse Variables**

    An object of synapse class record those variables for each synapse:
    
    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    s                  0                 Gating variable.
    
    g                  0                 Synapse conductance.

    t_last_pre_spike   -1e7              Last spike time stamp of the pre-synaptic neuron.

    ================== ================= =========================================================


    References:
        .. [1] Vijayan S, Kopell N J. Thalamic model of awake alpha oscillations 
                and implications for stimulus processing[J]. Proceedings of the 
                National Academy of Sciences, 2012, 109(45): 18553-18558.
    """

    target_backend = 'general'

    @staticmethod
    def derivative(s, t, TT, alpha, beta):
        ds = alpha * TT * (1 - s) - beta * s
        return ds

    def __init__(self, pre, post, conn, delay=0., g_max=0.42, E=0.,
                 alpha=0.98, beta=0.18, T=0.5, T_duration=0.5, **kwargs):
        # parameters
        self.delay = delay
        self.g_max = g_max
        self.E = E
        self.alpha = alpha
        self.beta = beta
        self.T = T
        self.T_duration = T_duration

        # connections
        self.conn = conn(pre.size, post.size)
        self.conn_mat = conn.requires('conn_mat')
        self.size = bp.ops.shape(self.conn_mat)

        # variables
        self.s = bp.ops.zeros(self.size)
        self.g = self.register_constant_delay('g', size=self.size, delay_time=delay)
        self.t_last_pre_spike = -1e7 * bp.ops.ones(self.size)

        self.int_s = bp.odeint(f=self.derivative, method='exponential_euler')
        super(AMPA2, self).__init__(pre=pre, post=post, **kwargs)

    def update(self, _t):
        spike = bp.ops.unsqueeze(self.pre.spike, 1) * self.conn_mat
        self.t_last_pre_spike = bp.ops.where(spike, _t, self.t_last_pre_spike)
        TT = ((_t - self.t_last_pre_spike) < self.T_duration) * self.T
        self.s = self.int_s(self.s, _t, TT, self.alpha, self.beta)
        self.g.push(self.g_max * self.s)
        self.post.input -= bp.ops.sum(self.g.pull(), 0) * (self.post.V - self.E)

