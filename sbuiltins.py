import sdata
import senv
import operator
import sloop
import itertools
import os
import fileinput
import sys

def load_file(env,token,filename):
    # Execute a file in its entirety
    if not os.path.isfile(filename):
        raise SkimpyError(token,'load: could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
        ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    sloop.execute_code(ptext,env)
    return sdata.SkimpyNonReturn('<unspecified>')

def bind_builtin(env,name,pyf,check_arg_count=None, check_arg_types=None, is_raw=False):
    proc = sdata.PythonProc(env,name,pyf,check_arg_count, check_arg_types, is_raw)
    env.bind(name,proc)

def make_checker(test):
    def _check(value,index):
        return test(value)
    return _check

def make_predicate(test):
    def _predicate(env,tokens,arg):
        return test(arg)
    return _predicate

def py_accumulate(op,inputs):
    if not inputs:
        return None
    _v = inputs[0]
    # Left-associative combination
    for x in itertools.islice(inputs,1,None):
        _v = op(_v,x)
    return _v

def make_accumulator(op):
    def _proc(env,token,*inputs):
        return py_accumulate(op,inputs)
    return _proc


def negator(env,token,*inputs):
    if len(inputs) == 1:
        return -inputs[0]
    else:
        return accumulate(operator.sub,inputs)

def is_equal(env,token,v1,v2):
    # simple, bootstrapped initial version
#    print ('is equal ' + str(v1) + ' ' + str(v2))    
    return v1 == v2

def is_less(env,token,v1,v2):
    # simple, bootstrapped initial version
#    print ('is less ' + str(v1) + ' ' + str(v2))
    return v1 < v2

def is_greater(env,token,v1,v2):  
    return v1 > v2

def display_text(env,token,arglist):
    # Accept SkimpyValues directly here
    for arg in arglist:
        sys.stdout.write(arg.str_for_display(token))
    return sdata.SkimpyNonReturn('<unspecified>')

def remainder(env,token,divisor,dividend):
    return divisor % dividend

def make_pair(env,token,args):
    return sdata.SkimpyPair(args[0],args[1])

def pair_left(env,token,arg):
    return arg[0].car

def pair_right(env,token,arg):
    return arg[0].cdr

def is_eq(left,right):
    return left == right   # The most straightorward way is to compare Python references

def make_list(env,token,args):
    lb = sdata.list_builder()
    lb.send(None)  # Initialize generator

    for arg in args:
        lb.send(arg)
    try:
        lb.send(None)
    except StopIteration as result:
        return result.value

def map_list(env,tok,args):
    proc = args[0]
    lst = args[1]
    
    result_lst = sdata.list_builder()
    result_lst.send(None)

    for element in sdata.lister(lst):
        val = proc.apply(tok,env,None,[element])
        result_lst.send(val)

    try:
        result_lst.send(None)
    except StopIteration as result:
        return result.value

def is_pair(value):
    return isinstance(value,sdata.SkimpyPair)

def is_list(value):
    return value == sdata.the_empty_list or is_pair(value)

def is_empty_list(value):
    return value == sdata.the_empty_list

def register_builtins(env):
    bind_builtin(env,'+',make_accumulator(operator.add),\
                  check_arg_count=(1,None))

    bind_builtin(env,'*',make_accumulator(operator.mul),\
                  check_arg_count=(1,None))

    bind_builtin(env,'-',negator,\
                  check_arg_count=(1,None))

    bind_builtin(env,'/',make_accumulator(operator.truediv),\
                  check_arg_count=(1,None))

    check_pair = make_checker(is_pair)
    check_list = make_checker(is_list)
    
    check_int = (lambda arg,idx: isinstance(arg,sdata.SkimpyNumber) and type(arg.value) == int)
    check_procedure = (lambda arg,idx: isinstance(arg,sdata.SkimpyProc))

    bind_builtin(env,'=',is_equal,check_arg_count=2)
    bind_builtin(env,'<',is_less,check_arg_count=2)
    bind_builtin(env,'>',is_greater,check_arg_count=2)
    bind_builtin(env,'remainder',remainder,check_arg_count=2)
    bind_builtin(env,'load',load_file,check_arg_count=1)
    bind_builtin(env,'display',display_text,check_arg_count=(1,None),is_raw=True)
    bind_builtin(env,'cons',make_pair,check_arg_count=2,is_raw=True)
    bind_builtin(env,'car',pair_left,check_arg_count=1,
                 check_arg_types=[('pair',check_pair)], is_raw=True)
    bind_builtin(env,'cdr',pair_right,check_arg_count=1,
                 check_arg_types=[('pair',check_pair)], is_raw=True)

    bind_builtin(env,'null?',make_predicate(is_empty_list),check_arg_count=1)
    bind_builtin(env,'eq?',is_eq,check_arg_count=2)
    # The list operations
    bind_builtin(env,'map',map_list,check_arg_count=2,
                 check_arg_types=[('procedure',check_procedure),('list',check_list)], is_raw=True)

    bind_builtin(env,'list',make_list,is_raw=True)


