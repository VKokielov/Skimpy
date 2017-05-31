import senv
import parse
import sdata
import seval
import sbuiltins
import os
import fileinput
import sys
import time
from serror import SkimpyError

def execute_code(text,env,interactive=False):
    tree = parse.skimpy_scan(text)

    for subnode in parse.generate_subnodes(tree):
        result = seval.skimpy_eval(subnode,env)[0]
        if interactive:
            print ('>> ' + str(result) + '\n')

def run_file(env,filename):
    # As above but interactive from the interpreter
    if not os.path.isfile(filename):
        raise ValueError('could not find file ' + filename)

    ptext = None
    with open(filename,'r') as prog_file:
        ptext = prog_file.read()

    # NOTE:  We execute file inside the current environment, not the top-level
    execute_code(ptext,env,interactive=True)

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
    except SkimpyError as serr:
        print (str(serr))

