# -*- coding: utf-8 -*-
import brainpy as bp
from numba import prange

__all__ = [
    'NMDA'
]


class NMDA(bp.TwoEndConn):
    """NMDA conductance-based synapse.

    .. math::

        & I_{syn} = \\bar{g} s (V-E_{syn}) \\cdot g_{\\infty}

        & g_{\\infty}(V,[{Mg}^{2+}]_{o}) = (1+{e}^{-\\alpha V}
        \\frac{[{Mg}^{2+}]_{o}} {\\beta})^{-1} 

        & \\frac{d s_{j}(t)}{dt} = -\\frac{s_{j}(t)}
        {\\tau_{decay}}+a x_{j}(t)(1-s_{j}(t)) 

        & \\frac{d x_{j}(t)}{dt} = -\\frac{x_{j}(t)}{\\tau_{rise}}+
        \\sum_{k} \\delta(t-t_{j}^{k})


    where the decay time of NMDA currents is taken to be :math:`\\tau_{decay}` =100 ms,
    :math:`a= 0.5 ms^{-1}`, and :math:`\\tau_{rise}` =2 ms


    **Synapse Parameters**

    ============= ============== =============== ================================================
    **Parameter** **Init Value** **Unit**        **Explanation**
    ------------- -------------- --------------- ------------------------------------------------
    g_max         .15            µmho(µS)        Maximum conductance.

    E             0.             mV              The reversal potential for the synaptic current.

    alpha         .062           \               Binding constant.

    beta          3.57           \               Unbinding constant.

    cc_Mg         1.2            mM              Concentration of Magnesium ion.

    tau_decay     100.           ms              The time constant of decay.

    tau_rise      2.             ms              The time constant of rise.

    a             .5             1/ms 

    mode          'scalar'       \               Data structure of ST members.
    ============= ============== =============== ================================================    
    
    
    Returns:
        bp.Syntype: return description of the NMDA synapse model.

    **Synapse State**

    ST refers to the synapse state, items in ST are listed below:
    
    =============== ================== =========================================================
    **Member name** **Initial values** **Explanation**
    --------------- ------------------ --------------------------------------------------------- 
    s               0                     Gating variable.
    
    g               0                     Synapse conductance.

    x               0                     Gating variable.
    =============== ================== =========================================================
    
    Note that all ST members are saved as floating point type in BrainPy, 
    though some of them represent other data types (such as boolean).
        
    References:
        .. [1] Brunel N, Wang X J. Effects of neuromodulation in a 
               cortical network model of object working memory dominated 
               by recurrent inhibition[J]. 
               Journal of computational neuroscience, 2001, 11(1): 63-85.
    
    """

    target_backend = ['numpy', 'numba', 'numba-parallel', 'numba-cuda']

    @staticmethod
    def derivative(s, x, t, tau_rise, tau_decay, a):
        dxdt = -x / tau_rise
        dsdt = -s / tau_decay + a * x * (1 - s)
        return dsdt, dxdt

    def __init__(self, pre, post, conn, delay=0., g_max=0.15, E=0., cc_Mg=1.2,
                 alpha=0.062, beta=3.57, tau=100, a=0.5, tau_rise=2., **kwargs):
        # parameters
        self.g_max = g_max
        self.E = E
        self.alpha = alpha
        self.beta = beta
        self.cc_Mg = cc_Mg
        self.tau = tau
        self.tau_rise = tau_rise
        self.a = a
        self.delay = delay

        # connections
        self.conn = conn(pre.size, post.size)
        self.pre_ids, self.post_ids = conn.requires('pre_ids', 'post_ids')
        self.size = len(self.pre_ids)

        # variables
        self.s = bp.ops.zeros(self.size)
        self.x = bp.ops.zeros(self.size)
        self.g = self.register_constant_delay('g', size=self.size, delay_time=delay)

        self.integral = bp.odeint(f=self.derivative, method='euler')

        super(NMDA, self).__init__(pre=pre, post=post, **kwargs)

    def update(self, _t):
        for i in prange(self.size):
            pre_id = self.pre_ids[i]

            self.x[i] += self.pre.spike[pre_id]
            self.s[i], self.x[i] = self.integral(self.s[i], self.x[i], _t, self.tau_rise, self.tau, self.a)

            # output
            self.g.push(i, self.g_max * self.s[i])

            post_id = self.post_ids[i]

            g_inf = 1 + self.cc_Mg / self.beta * bp.ops.exp(-self.alpha * self.post.V[post_id])

            self.post.input[post_id] -= self.g.pull(i) * (self.post.V[post_id] - self.E) / g_inf
