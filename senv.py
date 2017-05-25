from serror import SkimpyError

class SkimpyEnvironment(object):
    # Initialize by extending an environment
    def __init__(self,enclosing=None):
        self.enclosing = enclosing
        self.mapping = {}
        # Private mappings for interpreter and python functions, inaccessible to the interpreted language
        # Initially, for stack traces (stores a ref to the caller's environment)
        self.pmapping = {}  

    def bind(self,key,value):
        self.mapping[key] = value

    def bind_private(self,key,value):
        self.pmapping[key] = value
        
    def find(self,key):
        if key in self.mapping:
            return self.mapping[key]
        elif self.enclosing is not None:
            return self.enclosing.find(key)
        else:
            return None

    def find_private(self,key):
        return self.pmapping[key]        
        

# A list representing ordered arguments
# To call a function, we use the bind function.  'Bind' takes a list
# of ordered arguments (as an iterable) and extends a given environment
# with the arguments according to the list

# For other kinds of arglists, such as the vararg, reimplement this function

def bind_arglist(self,call_token,env,arglist,values):
 
    if len(values) < len(self.arglist):
        raise SkimpyError(call_token, 'too few arguments for procedure')

    if len(values) > len(self.arglist):
        raise SkimpyError(call_token, 'too many arguments for procedure')
    
    new_env = SkimpyEnv(env)
    for key,arg in zip(self.arg_names,values):
        new_env.bind(key,arg)

    return new_env
            


