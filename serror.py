class SkimpyError(Exception):
    def __init__(self,context,reason,env = None):
        if isinstance(context,tuple) or isinstance(context,list):
            self.line = context[0]
            self.col = context[1]
        else: #object
            if context is None:
                self.line = 0
                self.col = 0
            else:
                self.line = context.line
                self.col = context.col
        self.env = env
        self.reason = reason

    def __str__(self):
        return "SkimpyError: line " + str(self.line) + " col " + str(self.col) + ": " + self.reason

class StackFrame(object):
    def __init__(self,procedure,token,env):
        self.procedure = procedure
        self.token = token
        self.env = env

    def __str__(self):
        return '"' + self.procedure.name + '", called from line ' + str(self.token.line) + ' col ' + str(self.token.col)


def generate_frames(env):
    cur_frame = env.find_private("_cp")

    while cur_frame is not None:
        yield cur_frame
        cur_frame = cur_frame.env.find_private("_cp")
        
               
    
