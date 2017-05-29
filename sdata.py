import senv
import seval
import parse
import numbers
from serror import SkimpyError

class SkimpyValue(object):
    def pythonify(self):
        # print ('pythonifying self')
        return self # default -- identity
    
    def __str__(self):
        # When pythonify returns self, we are in catch-22
        python_val = self.pythonify()
        if python_val == self:
            return super(SkimpyValue,self).__str__()
        else:
            return str(python_val)

    def str_for_display(self,token):
        return str(self)

class SkimpyProc(SkimpyValue):
    def __init__(self,enc_env,name,arglist,text):
        self.enc_env = enc_env
        self.name = name
        self.arglist = arglist
        self.text = text

class CompoundProc(SkimpyProc):
    def __init__(self,*args):
        super(CompoundProc,self).__init__(*args)

    def __str__(self):
        return self.name

    class Applier(object):
        def __init__(self,token,exec_env,values,host):
            self.token = token
            self.exec_env = exec_env
            self.values = values
            self.host = host
            self._user = None

        def send(self,result):
            # result should be None here
            # NOTE:  _user was set by the explicit_eval function!
            requester = self._user
            my_host = self.host
            my_host.text = seval.translate(my_host.text)
            
            if isinstance(requester,CompoundProc.Applier) and requester.host == my_host:
                senv.bind_arglist(self.token,self.exec_env,my_host.arglist,self.values,rebind=True)
                raise StopIteration ((my_host.text.make_eval(exec_env),seval.EvalMessage.CONTINUATION))
            else:
                new_env = senv.bind_arglist(self.token,my_host.enc_env,my_host.arglist,self.values)
                new_env.bind_private("_cp",self)         
                raise StopIteration ((my_host.text.make_eval(new_env),seval.EvalMessage.CONTINUATION))            

    def make_applier(self,token,exec_env,values):
        return CompoundProc.Applier(token,exec_env,values,self)
        
    def apply(self,token,exec_env,caller_id,values):
        # NOTE:  exec_env is passed through from eval in case we ever need it, but we extend the environment in which we evaluated the lambda!!
        
        # Extend the environment and call the procedure with the variables bound
        # The 'call' function is all that's different between procedure types
        # The returned value is passed back to eval.
        # We are bootstrapping the return to Python.
        
        if caller_id == self:
            # This is the same procedure.  Do a continuation
            # That is, rebind the arguments into the calling environment and raise a ContinuationException
            senv.bind_arglist(token,exec_env,self.arglist,values,rebind=True)
            new_text = seval.translate(self.text)  # As in seval, explicit translation to cache the analyzed text if it was not cached on the form
            self.text = new_text
            raise seval.ContinuationException(self.text)
        else:
            new_env = senv.bind_arglist(token,self.enc_env,self.arglist,values)
            
            to_return,new_text = seval.skimpy_eval(self.text,new_env,self)
            self.text = new_text
            
        return to_return    


# To users these are indistinguishable if 'apply' is used to call a procedure
class PythonProc(SkimpyProc):
    def __init__(self,enc_env,name,pyf,check_arg_count=None,check_arg_types=None,is_raw = False):
        
        super(PythonProc,self).__init__(enc_env,name,arglist=None,text=None)
        self.check_arg_count = check_arg_count
        self.check_arg_types = check_arg_types
        
        self.pyf = pyf
        self.is_raw = is_raw  # Do not pythonify values -- pass the list of objects

    def __str__(self):
        return 'primitive-procedure ' + self.name

    def make_applier(self,token,exec_env,values):
        # This just calls apply.  A primitive applier is always a leaf in the computation
        if False:
            yield None

        return [self.apply(token,exec_env,None,values), seval.EvalMessage.RESULT]
    
    def apply(self,token,exec_env,caller_id,values):
        if self.check_arg_count is not None:
            if isinstance(self.check_arg_count,tuple):
                min_args = self.check_arg_count[0]
                max_args = self.check_arg_count[1]
            else:
                min_args = self.check_arg_count
                max_args = self.check_arg_count
                
            if min_args is not None and len(values) < min_args:
                raise SkimpyError(token, 'too few arguments for builtin procedure ' + str(self.name))
            if max_args is not None and len(values) > max_args:
                raise SkimpyError(token, 'too many arguments for builtin procedure ' + str(self.name))

        if self.check_arg_types is not None:
            # Zip helps here.  It stops checking only when either values or check_arg_types is exhausted
            # To check varargs, make check_arg_types an infinite generator
            idx = 0
            for check_pair,value in zip(self.check_arg_types,values):
                if not check_pair[1](value,idx):
                    raise SkimpyError(token,'argument ' + str(idx) + ': wrong argument type for builtin procedure ' + str(self.name)\
                                      + '; expected ' + check_pair[0])
                idx += 1
            
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

class SkimpyChar(SkimpyValue):
    def __init__(self,value):
        if len(value) != 1:
            raise ValueError('A character must be of length 1')
        self.value = value

    def pythonify(self):
        return self.value

class _SkimpyBool(SkimpyValue):
    def __init__(self,value):
        self.value = value

    def pythonify(self):
        return self.value

    def __bool__(self):
        return self.value

true_val = _SkimpyBool(True)
false_val = _SkimpyBool(False)

def is_false(val):
    # As a matter of policy there should only be one #f.
    # But let's not depend on it
    return isinstance(val,_SkimpyBool) and val.value == False

class SkimpyEmptyList(SkimpyValue):
    def __init__(self):
        pass

    def __str__(self):
        return ""  # this is quite deliberate

the_empty_list = SkimpyEmptyList()

class SkimpySymbol(SkimpyValue):
    pass

class SkimpyPair(SkimpyValue):
    # NOTE:  We don't Pythonify pairs.  x.car and x.cdr is not harder to type or read than x[0]/x[1].  It is arguably clearer here.
    def __init__(self,car,cdr):
        self.car = car
        self.cdr = cdr

    def __str__(self):
        return self.str_for_display(None)

    def str_for_display(self,token):
        return prettify_pair(token,self,detect_cycles=True)        

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
    if isinstance(python_value,bool):
        if python_value:
            return true_val
        else:
            return false_val
    elif isinstance(python_value,numbers.Number):
        return SkimpyNumber(python_value)
    else:
        return python_value  # By default, return what I get (as with pythonify)

def skimpy_lister(first_pair):
    if not is_list(first_pair):
        raise ValueError('skimpy_lister must be used with a list as the first argument')

    pair = first_pair
    while not isinstance(pair,SkimpyNil):
        yield pair.car
        pair = pair.cdr

def prettify_pair(command_token,pair,detect_cycles=False):
    # An extremely dumb pretty-printer for pairs.  Recursive, so
    #   1) limited by the Python stack
    #   2) strings will be allocated and discarded left and right
    if not isinstance(pair,SkimpyPair):
        raise ValueError('prettify_pair called with non-pair')
    
    def pair_prettifier(obj,cycle_detector):
        if not isinstance(obj,SkimpyPair):
            # Just get the string rep
            return str(obj)

        # Now deal with the pair
        if cycle_detector is not None:
            if obj in cycle_detector:
                raise SkimpyError(command_token, "list structure contains cycles.")
            cycle_detector.add(obj)

        left = obj.car
        right = obj.cdr
        
        # We don't care about form_left because form_left is not specially printed (i.e. has no dot dilemma)
        form_left = pair_prettifier(left,cycle_detector)
        if right == the_empty_list:
            form_right = None
        else:
            form_right = pair_prettifier(right,cycle_detector)            

        # 2(3) = 6 possibilities for car and cdr as pairs and nonpairs
        result_str = ""
        if isinstance(left,SkimpyPair):
            if form_right is None:
                result_str = "({left_v})".format(left_v = form_left, right_v = form_right)
            elif isinstance(right,SkimpyPair):
                result_str = "({left_v}) {right_v}".format(left_v = form_left, right_v = form_right)
            else:
                result_str = "({left_v}) . {right_v}".format(left_v = form_left, right_v = form_right)
        else:
            if form_right is None:
                result_str = "{left_v}".format(left_v = form_left, right_v = form_right)               
            elif isinstance(right,SkimpyPair):
                result_str = "{left_v} {right_v}".format(left_v = form_left, right_v = form_right)
            else:
                result_str = "{left_v} . {right_v}".format(left_v = form_left, right_v = form_right)
        return result_str

    if detect_cycles:
       return "(" + pair_prettifier(pair,set()) + ")"
    else:
        return "(" + pair_prettifier(pair,None) + ")"
    
        
# quote and unquote
# quote is used to turn a subtree of Skimpy tokens into a Scheme data structure
# unquote does the opposite, in preparation for evaluating the text of a Skimpy program

def nodes_to_list(quotable):
    pass
