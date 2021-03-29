# -*- coding: utf-8 -*-
import brainpy as bp

__all__ = [
    'Alpha'
]
class Alpha(bp.TwoEndConn):
    """
    Alpha synapse.

    .. math::

        \\frac {ds} {dt} &= x

        \\tau^2 \\frac {dx} {dt} = - 2 \\tau x & - s + \\sum_f \\delta(t-t^f)


    For conductance-based (co-base=True):

    .. math::

        I_{syn}(t) = g_{syn} (t) (V(t)-E_{syn})


    For current-based (co-base=False):

    .. math::

        I(t) = \\bar{g} s (t)

    **Synapse Parameters**

    ============= ============== ======== ===================================================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- -----------------------------------------------------------------------------------
    tau_decay     2.             ms       The time constant of decay.

    g_max         .2             µmho(µS) Maximum conductance.

    E             0.             mV       The reversal potential for the synaptic current. (only for conductance-based model)

    co_base       False          \        Whether to return Conductance-based model. If False: return current-based model.

    mode          'scalar'       \        Data structure of ST members.
    ============= ============== ======== ===================================================================================  

    Returns:
        bp.Syntype: return description of the alpha synapse model.

    **Synapse State**


    ST refers to the synapse state, items in ST are listed below:

    ================ ================== =========================================================
    **Member name**  **Initial values** **Explanation**
    ---------------- ------------------ ---------------------------------------------------------    
    g                  0                  Synapse conductance on the post-synaptic neuron.
    s                  0                  Gating variable.
    x                  0                  Gating variable.  
    ================ ================== =========================================================

    Note that all ST members are saved as floating point type in BrainPy, 
    though some of them represent other data types (such as boolean).

    References:
        .. [1] Sterratt, David, Bruce Graham, Andrew Gillies, and David Willshaw. 
                "The Synapse." Principles of Computational Modelling in Neuroscience. 
                Cambridge: Cambridge UP, 2011. 172-95. Print.
    """
    
    target_backend = 'general'

    @staticmethod
    def derivative(s, x, t, tau):
        dxdt = (-2 * tau * x - s) / (tau ** 2)
        dsdt = x
        return dsdt, dxdt

    def __init__(self, pre, post, conn, delay=0., tau=2.0, **kwargs):
        # parameters
        self.tau = tau
        self.delay = delay

        # connections
        self.conn = conn(pre.size, post.size)
        self.conn_mat = conn.requires('conn_mat')
        self.size = bp.backend.shape(self.conn_mat)

        # variables
        self.s = bp.backend.zeros(self.size)
        self.x = bp.backend.zeros(self.size)
        
        self.w = bp.backend.ones(self.size) * .2
        self.out = self.register_constant_delay('out', size=self.size, delay_time=delay)

        self.integral = bp.odeint(f=self.derivative, method='euler')
        super(Alpha, self).__init__(pre=pre, post=post, **kwargs)

    def update(self, _t):
        self.s, self.x = self.integral(self.s, self.x, _t, self.tau)
        self.x += bp.backend.reshape(self.pre.spike, (-1, 1)) * self.conn_mat
        self.out.push(self.w * self.s)
        self.post.input += bp.backend.sum(self.out.pull(), axis=0)