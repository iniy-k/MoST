# describes tiling of multiple loops.
# FIXME figure out what the best way of calling SysTL functions here is.

class TilingSchedule(MoSTSchedule):

    # takes as input a dictionary mapping tile vars to tuples
    # each tuple is of the form: (tile size,  tail strategy (optional), perfect? (optional), [additional params])
    def __init__(tile_vars, tile_size):
        self.tile = tile_vars

    # Given
    def apply(fn, backend="systl"):
        for loop_var in tile_vars:
            tile_size = tile[loop_var][1]
            out_vars = (loop_var + "_out", loop_var + "_in")
            if len(tile[loop_var] >= 2):
                tail_strat = tile[loop_var][2]
            else:
                tail_strat = "guard"
            perfect = False
            if len(tile[loop_var] >= 3):
                perfect = tile[loop_var][3]
            fn = fn.split(loop_var, split_const, out_vars,
              tail='guard', perfect=False)
            

    def serialize():
        raise notImplementedError

    def deserialize():
        raise notImplementedError

    # Spits out SysTL code that does the same thing 
    # May or may not be a good idea,
    # depending on how important you think the ability to
    # punch through the black box is.
    def generateBackendCode(fn, backend="systl"):
        raise NotImplementedError