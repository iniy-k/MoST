from __future__ import annotations
from cmath import cos
import sys
from exo import proc, Procedure, DRAM, config, instr, QAST
import matmap.base as matmap
from matmap.qast_utils.loopReader import *
import matmap.transforms.TilingTransform as ts
import matmap.transforms.ReorderingTransform as rs
from matmap.cosa.src.cosa import *
from matmap.cosa.src.cosa_constants import _A, _B
from matmap.cosa.src.cosa_input_objs import Prob, Arch, Mapspace

class CoSATransform(matmap.CompoundTransform):

    #takes in all of CoSA parameters to create this object.
    def __init__(self, cosa_parameters, obj):
        self.cosa_parameters = cosa_parameters
        self.obj = obj
        self.run_cosa()
        self.subschedules = self.helper()

    #runs cosa and assigns variable values to class object values. And also creates 
    def run_cosa(self):
        parser = construct_argparser()
        args, unknown = parser.parse_known_args()

        prob_path = pathlib.Path(args.prob_path).resolve()
        arch_path = pathlib.Path(args.arch_path).resolve()
        mapspace_path = pathlib.Path(args.mapspace_path).resolve()
        output_path = args.output_dir

        status_dict = {}
        prob = Prob(prob_path)
        arch = Arch(arch_path)

        self.tiling_config = prob.prob_factors

        # An object defines the user-defined bypass pattern. 
        mapspace = Mapspace(mapspace_path)
        mapspace.init(prob, arch)

        # even mapping
        B = _B
        Z = None

        # uneven mapping config
        # Z = _Z
        # B = None

        # partition ratios for W, IA, OA
        part_ratios = [
            [1, 0, 0],
            [0, 0, 1],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0.25, 0.75],
            [0.33, 0.33, 0.33],
        ]
        self.factor_config, self.spatial_config, outer_perm_config, self.run_time = cosa(prob, arch, _A, B, part_ratios, global_buf_idx=4,
                                                                        Z=Z)

        #parse cosa permuation output and prepare to create reorder obj
        loops = readLoopNest(self.obj)[0]
        loop_list = []
        for loop in loops:
            loop_list.append(loop.name)
        loop_order = {}
        num = 0
        for i in outer_perm_config:
            loop_order[i] = loop_list[num]
            num += 1
        self.perm_config = []
        for i in range(len(outer_perm_config)):
            self.perm_config.append(loop_order[i])
        self.perm_sched = rs.ReorderingTransform(self.perm_config)

        #parse cosa tiling_config and prepare to create tiling obj

        self.tile_dict = self.tiling_config
        


    def helper(self):


        transformations = []
        transformations.append(self.perm_sched)

        #a 2d list containing the mappings
        #order of self.tile_dict has to follow right order of loops -- can change if needed to output dictionary
        # [] throws error if it is a tile but can be modified to accomodate that. 
        #TODO: Error checks

        # Tiling Transform
        loop_vars = getNestVars(self.obj)
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
                tiles[x + "o" * i] = temp[0]
                full_tile_dict[x].pop(0)
            tile_sched = ts.TilingTransform(tiles)
            transformations.append(tile_sched)
            delete = [key for key in full_tile_dict if full_tile_dict[key] == []]
            for key in delete: del full_tile_dict[key]
            i += 1

        return transformations



    



    
    
    
    

    
        


