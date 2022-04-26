# describes tiling of multiple loops.
# FIXME update serialization
# TODO rewrite this so that it doesn't 

from __future__ import annotations
import sys
from exo import proc, Procedure, DRAM, config, instr, QAST
from MoST.MoST_base import *
from MoST.qast_utils.loopReader import *
from itertools import dropwhile

class TilingSchedule(MoSTSchedule):
    #tile_dict is a dict from strings (var names) to numbers.
    def __init__(self, tile_dict=dict(), simplify=True):
        self.tile_dict = tile_dict
        #self.loop_bounds = loop_bounds
        #self.tile_bounds = tile_bounds
        self.simplify = simplify

    def apply(self, fn, backend="exo"):
        loop_vars = getNestVars(fn)
        assert set(self.tile_dict.keys()).intersection(set(loop_vars)) == set(self.tile_dict.keys()), "tile vars don't match loop vars of function you're applying to!"
        for loop_idx in loop_vars:
            if loop_idx not in self.tile_dict:
                continue
            block_size = self.tile_dict[loop_idx]
            new_names = (loop_idx + "_out", loop_idx + "_in")
            perfect = False #FIXME detect if lo, hi are constant; can infer
            fn = fn.split(
                loop_idx + " #0",
                block_size,
                new_names,
                tail='cut',
                perfect=perfect)
            loop_indices = getNestVars(fn)
            _, *indices_after = dropwhile(lambda idx: idx != loop_idx + '_in', loop_indices)
            for idxafter in indices_after:
                fn = fn.reorder(loop_idx + "_in #0", idxafter)
        if self.simplify:
            fn = fn.simplify()
        return fn

    #a 2d list containing the mappings
    #order of self.tile_dict has to follow right order of loops -- can change if needed to output dictionary
    # [] throws error if it is a tile but can be modified to accomodate that. 
    #TODO: Error checks
    def CoSA_apply(self, fn):
        loop_vars = getNestVars(fn)
        full_tile_dict = {}
        tiles = dict()
        for i in range(len(loop_vars)):
            full_tile_dict[loop_vars[i]] = self.tile_dict[i]
        i = 0
        while full_tile_dict:
            tiles = {}
            for x in full_tile_dict.keys():
                temp = full_tile_dict[x]
                #for case when split is 1 or there is just one number to split loop on
                if(temp[0] == 1 or len(temp) == 1):
                    full_tile_dict[x].pop(0)
                    continue
                tiles[x + "_out" * i] = temp[0]
                full_tile_dict[x].pop(0)
            self.tile_dict = tiles
            fn = self.apply(fn)
            delete = [key for key in full_tile_dict if full_tile_dict[key] == []]
            for key in delete: del full_tile_dict[key]
            i += 1
        return fn

    # generates tiles for projective nested loops
    # see https://arxiv.org/abs/2003.00119
    # but this also includes ability to determine optimal alloc
    # thanks to Riley Murray for the code to do this
    @classmethod
    def generateHBLProjectiveTile(cls, bounds, accesses, memsize, verbose=False):
        import numpy as np
        import cvxpy as cp

        def make_model(ell, phis, M):
            """
            ell : a numpy ndarray.
            phis : list. phi[j] is a list (or numpy ndarray) containing some integers from range(n)
            M : real numeric type
            """
            n = ell.size
            m = len(phis)
            ell[ell == np.inf] = M
            # optimization variable
            b = cp.Variable(shape=(n,), name='b', pos=True)
            # constraints
            summands = [cp.prod(b[phis[j]]) for j in range(m)]
            constraints = [cp.sum(summands) <= M, b <= ell]
            # objective function
            objective = cp.Maximize(cp.prod(b))
            # Problem object
            prob = cp.Problem(objective, constraints)
            return prob

        varidx = dict([(bounds[i].name, i) for i in range(len(bounds))])
        idxvar = dict([(i, bounds[i].name) for i in range(len(bounds))])
        loophi = [loop.hi for loop in bounds]
        looplo = [loop.lo for loop in bounds]
        ell = np.array([loop.hi - loop.lo for loop in bounds])
        phis = [[varidx[var] for var in access.support] for access in accesses]

        if(verbose):
            print("ell is: ", ell, " and phis are: ", phis)

        #FIXME deal with cases where you have scalar reads, or slice reads
        # e.g. A[0,i] later. right now it'll crash this.

        #demo_ell = np.array([500, 1500, 10])
        #demo_phis = [[0, 1],  # indexing into C[i,j]
        #            [0, 2],  # indexing into A[i,k]
        #            [2, 1]]  # indexing into B[k,j]
        #demo_M = 1024

        # construct and solve the model
        demo_prob = make_model(ell, phis, memsize)
        demo_prob.solve(verbose=verbose, gp=True)

        # recover the optimal solution
        opt_b = demo_prob.var_dict['b'].value.tolist()
        def round_approx(var, thresh=0.98):
            if var % 1 >= thresh:
                return round(var)
            else:
                return int(var)
        round_b = [round_approx(i) for i in opt_b]
        output_tile = dict([(idxvar[i], round_b[i]) for i in range(len(round_b))])
        print(output_tile)
        return cls(output_tile)