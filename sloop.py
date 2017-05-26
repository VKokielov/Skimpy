import senv
import parse
import sdata
import seval
import operator
#import sbuiltins
import itertools
import os
import fileinput
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
        raise SkimpyError(token,'include: could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
        ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    execute_code(ptext,env)
    return sdata.SkimpyNonReturn('<unspecified>')

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
    return v1 < v2

def is_greater(env,token,v1,v2):
    # simple, bootstrapped initial version
    return v1 > v2

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

    global_env.bind('#t',sdata.true_val)
    global_env.bind('#f',sdata.false_val)

    return global_env


if __name__ == "__main__":
    global_env = prepare()

    # Sit in a loop and read stdin until eof
    #for line in fileinput.input():
    #    execute_code(line,global_env,interactive=True)
    load_file(global_env,None,"C:\\Users\\vkramer\\Documents\\skimpy_test.scm")

#    text_square = "(define (square x) (* x x))"
#    execute_code(text_square,global_env)

#    text_do_square = "(square 5)"
#    execute_code(text_do_square,global_env)

#    text_factorial = "(define (factorial n)\
#           (if (= n 1) 1 (* n (factorial (- n 1)))))"
#    execute_code(text_factorial,global_env)

#    text_iter_factorial = "(define (fac-iter c n)\
#                          (if (= n 0) c (fac-iter (* c n) (- n 1))))"
#    execute_code(text_iter_factorial,global_env)
    
    #text_do_factorial = "(factorial 10)"
    #execute_code(text_do_factorial,global_env)
    
#    text_do_iter_f = "(fac-iter 1 10)"
#    execute_code(text_do_iter_f,global_env)
