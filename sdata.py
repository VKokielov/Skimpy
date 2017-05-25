import senv
import seval
import parse
import numbers
from serror import SkimpyError

class SkimpyValue(object):
    def pythonify(self):
        return self # default -- identity
    def __str__(self):
        return str(self.pythonify())

class SkimpyProc(SkimpyValue):
    def __init__(self,enc_env,name,arglist,text):
        self.enc_env = enc_env
        self.name = name
        self.arglist = arglist
        self.text = text
    
    def apply(self,token,exec_env,values):
        # NOTE:  exec_env is passed through from eval in case we ever need it, but we extend the environment in which we evaluated the lambda!!
        
        # Extend the environment and call the procedure with the variables bound
        # The 'call' function is all that's different between procedure types
        # The returned value is passed back to eval.
        # We are bootstrapping the return to Python.
        new_env = senv.bind_arglist(token,self.enc_env,self.arglist,values)
        
        return self.call(token,new_env)

class CompoundProc(SkimpyProc):
    def __init__(self,*args):
        super(CompoundProc,self).__init__(*args)

    def call(self,token,env):
        # Evaluate the body of the text in the new environment
        # Store the new text once (and if) it's translated
        
        to_return,self.text = seval.skimpy_eval(self.text,env)
        return to_return

# To users these are indistinguishable if 'apply' is used to call a procedure
class PythonProc(SkimpyProc):
    def __init__(self,enc_env,name,pyf,check_arg_count=None,is_raw = False):
        
        super(PythonProc,self).__init__(enc_env,name,arglist=None,text=None)
        self.check_args = check_arg_count
        self.pyf = pyf
        self.is_raw = is_raw  # Do not pythonify values -- pass the list of objects

    def apply(self,token,exec_env,values):
        if self.check_args is not None:
            if isinstance(self.check_args,tuple):
                min_args = self.check_args[0]
                max_args = self.check_args[1]
            else:
                min_args = self.check_args
                max_args = self.check_args
                
            if min_args is not None and len(values) < min_args:
                raise SkimpyError(token, 'too few arguments for builtin procedure')
            if max_args is not None and len(values) > max_args:
                raise SkimpyError(token, 'too many arguments for builtin procedure')
            
        # Do not bother binding the values into the environment, it's wasted time
        # The called python function knows what it expects in values
        
        # If the python function wants to let a compound-procedure escape from it, it should use Skimpy primitives to extend enc_env
        # exactly the way it will use sdata.CompoundProc(...) to build the procedure.
        if not self.is_raw:
            # Pythonify all values first.  Obviously slower, but much more convenient
            val_list = [val.pythonify() for val in values]
            return skimpify(self.pyf(self.enc_env, token, *val_list))
        else:
            # In this case it's just a thin wrapper
            return self.pyf(self.enc_env,token,values)

class SkimpyNumber(SkimpyValue):
    def __init__(self,value):
        self.value = value

    def pythonify(self):
        return self.value

class SkimpyString(SkimpyValue):
    def __init__(self,value):
        self.value = value

    def pythonify(self):
        return self.value

class SkimpyBool(SkimpyValue):
    def __init__(self,value):
        self.value = value

    def pythonify(self):
        return self.value

    def __bool__(self):
        return self.value

true_val = SkimpyBool(True)
false_val = SkimpyBool(False)
    
class SkimpyNil(SkimpyValue):
    pass

class SkimpySymbol(SkimpyValue):
    pass

class SkimpyPair(SkimpyValue):
    def __init__(self,car,cdr):
        self.car = car
        self.cdr = cdr

# A value that doesn't count as a return, but has a string description
class SkimpyNonReturn(SkimpyValue):
    def __init__(self,tag):
        self.tag = tag

    def __str__(self):
        return self.tag
# Conversions
# NOTE:  skimpify and pythonify are shallow.  For example, lists will not turn into python lists automatically
# For deep conversions you must implement your own functions.
# But it's even better to use functional techniques.  For example, the skimpy_lister() generator will produce the full
# list of values corresponding to a sequence of pairs.  (Of course, if there is a cycle, the generator will run around in circles)

def skimpify(python_value):
    # Represent numbers as SkimpyNumbers, strings as SkimpyStrings, and pairs -- tuples of size 2 -- as SkimpyPairs
    # Lists are not represented.  Construct lists with the list builder.
    if isinstance(python_value,numbers.Number):
        return SkimpyNumber(python_value)
    elif isinstance(python_value,bool):
        if python_value:
            return true_value
        else:
            return false_value
    else:
        return python_value  # By default, return what I get (as with pythonify)

def skimpy_lister(first_pair):
    if not is_list(first_pair):
        raise ValueError('skimpy_lister must be used with a list as the first argument')

    pair = first_pair
    while not isinstance(pair,SkimpyNil):
        yield pair.car
        pair = pair.cdr

def nodes_to_list(quotable):
    pass
