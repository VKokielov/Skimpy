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
        if key in self.pmapping:
            return self.pmapping[key]
        else:
            return None

    def __str__(self):
        return str_dict(self.mapping) + "|" + str_dict(self.pmapping) + ":" + str(self.enclosing)

def str_dict(dictionary):
    if dictionary is None:
        return "None"
    
    rv = "["
    for k,v, in dictionary.items():
        rv += str(k) + ":" + str(v) + ", "
        
    return rv

# A list representing ordered arguments
# To call a function, we use the bind function.  'Bind' takes a list
# of ordered arguments (as an iterable) and extends a given environment
# with the arguments according to the list

# For other kinds of arglists, such as the vararg, reimplement this function

def bind_arglist(call_token,env,arglist,values,rebind=False):

    # Note: when rebinding for a tail recursion, this check ensures that we don't leave any 'stale' arguments from the previous call
    if len(values) < len(arglist):
        raise SkimpyError(call_token, 'too few arguments for procedure')

    if len(values) > len(arglist):
        raise SkimpyError(call_token, 'too many arguments for procedure')

    if not rebind:
        bind_env = SkimpyEnvironment(env)
    else:
        bind_env = env
        
    for key,arg in zip(arglist,values):
        bind_env.bind(key,arg)
    
    return bind_env # note: if rebind=True, this returns env again!
            


