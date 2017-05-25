import senv
import parse
import sdata
import seval
import operator
#import sbuiltins
import itertools

def bind_builtin(env,name,pyf,check_arg_count=None, is_raw=False):
    proc = sdata.PythonProc(env,name,pyf,check_arg_count, is_raw)
    env.bind(name,proc)

def make_accumulator(op):
    def accumulate(env,token,*inputs):
        if not inputs:
            return None
        _v = inputs[0]
        # Left-associative combination
        for x in itertools.islice(inputs,1,None):
            _v = op(_v,x)
        return _v
    return accumulate

def is_equal(env,token,v1,v2):
    # simple, bootstrapped initial version
    return v1 == v2

def prepare():
    # Creates a new global environment and adds bindings for
    # all builtins
    global_env = senv.SkimpyEnvironment()
    bind_builtin(global_env,'+',make_accumulator(operator.add),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'*',make_accumulator(operator.mul),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'-',make_accumulator(operator.sub),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'/',make_accumulator(operator.truediv),\
                  check_arg_count=(1,None))

    bind_builtin(global_env,'=',is_equal,check_arg_count=2)

    global_env.bind('#t',sdata.true_val)
    global_env.bind('#f',sdata.false_val)

    return global_env

def execute_code(text,env):
    tree = parse.skimpy_scan(text)

    for expr in parse.generate_subnodes(tree):
        result = seval.skimpy_eval(expr,env)

    print ('eval: ' + str(result[0]) + '\n')

if __name__ == "__main__":
    global_env = prepare()

    text_square = "(define (square x) (* x x))"
    execute_code(text_square,global_env)

    text_do_square = "(square 5)"
    execute_code(text_do_square,global_env)

    text_factorial = "(define (factorial n)\
           (if (= n 1) 1 (* n (factorial (- n 1)))))"
    execute_code(text_factorial,global_env)

    text_do_factorial = "(factorial 4)"
    execute_code(text_do_factorial,global_env)
