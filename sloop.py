import senv
import parse
import sdata
import seval
import operator
#import sbuiltins
import itertools
import os
import fileinput
import sys
from serror import SkimpyError

def execute_code(text,env,interactive=False):
    tree = parse.skimpy_scan(text)

    for expr in parse.generate_subnodes(tree):
        result = seval.skimpy_eval(expr,env)
        if interactive:
            print ('>> ' + str(result[0]) + '\n')

def load_file(env,token,filename):
    # Execute a file in its entirety
    if not os.path.isfile(filename):
        raise SkimpyError(token,'load: could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
        ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    execute_code(ptext,env)
    return sdata.SkimpyNonReturn('<unspecified>')

def run_file(env,filename):
    # As above but interactive from the interpreter
    if not os.path.isfile(filename):
        raise ValueError('could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
        ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    execute_code(ptext,env,interactive=True)

def bind_builtin(env,name,pyf,check_arg_count=None, is_raw=False):
    proc = sdata.PythonProc(env,name,pyf,check_arg_count, is_raw)
    env.bind(name,proc)

def accumulate(op,inputs):
    if not inputs:
        return None
    _v = inputs[0]
    # Left-associative combination
    for x in itertools.islice(inputs,1,None):
        _v = op(_v,x)
    return _v

def make_accumulator(op):
    def _proc(env,token,*inputs):
        return accumulate(op,inputs)
    return _proc


def negator(env,token,*inputs):
    if len(inputs) == 1:
        return -inputs[0]
    else:
        return accumulate(operator.sub,inputs)

def is_equal(env,token,v1,v2):
    # simple, bootstrapped initial version
    return v1 == v2

def is_less(env,token,v1,v2):
    # simple, bootstrapped initial version
#    print ('<:' + str(v1) + ' vs ' + str(v2))
    return v1 < v2

def is_greater(env,token,v1,v2):
    # simple, bootstrapped initial version
#    print ('>:' + str(v1) + ' vs ' + str(v2))    
    return v1 > v2

def display_text(env,token,*args):
    for arg in args:
        sys.stdout.write(str(arg) + ' ')
    sys.stdout.write('\n')
    return sdata.SkimpyNonReturn('<unspecified>')

def prepare():
    # Creates a new global environment and adds bindings for
    # all builtins
    global_env = senv.SkimpyEnvironment()
    
    bind_builtin(global_env,'+',make_accumulator(operator.add),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'*',make_accumulator(operator.mul),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'-',negator,\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'/',make_accumulator(operator.truediv),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'=',is_equal,check_arg_count=2)
    bind_builtin(global_env,'<',is_less,check_arg_count=2)
    bind_builtin(global_env,'>',is_greater,check_arg_count=2)
    bind_builtin(global_env,'load',load_file,check_arg_count=1)
    bind_builtin(global_env,'print',display_text,check_arg_count=(1,None))

    global_env.bind('#t',sdata.true_val)
    global_env.bind('#f',sdata.false_val)

    return global_env

if __name__ == "__main__":
    global_env = prepare()

    # Sit in a loop and read stdin until eof
    run_file(global_env,"C:\\Users\\vkramer\\Documents\\skimpy_test.scm")

