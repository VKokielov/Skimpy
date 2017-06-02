import senv
import parse
import sdata
import seval
import sbuiltins
import os
import fileinput
import sys
import time
import serror
from serror import SkimpyError

def execute_code(text,env,recipient):
    tree = parse.skimpy_scan(text)

    for subnode in parse.generate_subnodes(tree):
        try:
            result = seval.skimpy_eval(subnode,env)[0]
            recipient(result)
        except Exception as e:
            recipient(e)

def receive_to_print(eval_result):
    print ('>> ' + str(eval_result) + '\n')

def run_file(env,filename):
    # As above but interactive from the interpreter
    if not os.path.isfile(filename):
        raise ValueError('could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
            ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    execute_code(ptext,env,receive_to_print)

def prepare():
    # Creates a new global environment and adds bindings for
    # all builtins
    global_env = senv.SkimpyEnvironment()
    sbuiltins.register_builtins(global_env)
    
    global_env.bind('#\\newline',sdata.SkimpyChar('\n'))

    return global_env

if __name__ == "__main__":
    global_env = prepare()

    # Sit in a loop and read stdin until eof
    file_name = "C:\\Users\\vkramer\\Documents\\skimpy_test.scm"
    if len(sys.argv) >= 2:
        file_name = sys.argv[1]
    try:
        time1 = time.time()
        run_file(global_env,file_name)
        print ('total time to run: ' + str(time.time() - time1))
    except SkimpyError as skimpy_err:
        if skimpy_err.env is not None:
            # TODO:  Make stack frames objects for readability (no other good reason)
            # Trace through the procedures
            print(str(skimpy_err))
            print('Stack trace:')
            for stack_frame in serror.generate_frames(skimpy_err.env):
                print (str(stack_frame))
        else:
            print (str(skimpy_err))
            
            

