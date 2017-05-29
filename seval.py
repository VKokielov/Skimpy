import parse
import sdata
from serror import SkimpyError
from enum import Enum

class EvalMessage(Enum):
    CONTINUATION = 0
    RESULT = 1
    
# Allow for tail-optimization by passing upstream an expression to be evaluated instead of a given one
class ContinuationException(Exception):
    def __init__(self,form):
        self.form = form

# This module contains all the evaluation rules for Scheme, including the two most important ones, lambda and apply
class SkimpyForm(object):
    def __init__(self,form,n_subnodes=None):
        if n_subnodes is not None:
            self.subnode_values = [None] * n_subnodes
        else:
            self.subnode_values = None
        self.original_form = form

    def set_subnode(self,form,index):
        if self.subnode_values is None:
            raise ValueError('subnode list is not initialized; did you forget to pass in the node count to the constructor?')

        self.subnode_values[index] = form

    def get_subnode(self,index):
        return self.subnode_values[index]

    def subnodes(self,iterable):
        self.subnode_values = list(iterable)

    def evaluate_subnode(self,env,idx):
        eval_result,self.subnode_values[idx] = skimpy_eval(self.subnode_values[idx],env,None)
        return eval_result

    def make_subnode_evaluator(self,env,idx):
        if idx < 0:
            idx = len(self.subnode_values) + idx

#        if not isinstance(self.subnode_values[idx],SkimpyForm):
#            print ('translating ' + self.subnode_values[idx].str_pretty())
            
        self.subnode_values[idx] = translate(self.subnode_values[idx])
        return self.subnode_values[idx].make_eval(env)

    def make_subnode_evaluators(self,env,range_l=0,range_u=None):
        if range_u is None:
            range_u = len(self.subnode_values)

        if range_u < 0:
            range_u = len(self.subnode_values) + range_u

 #       print (str(self) + ': tr from ' + str(range_l) + ' to ' + str(range_u) + ' len ' + str(len(self.subnode_values)))
        
        for idx in range(range_l,range_u):
            yield self.make_subnode_evaluator(env,idx)  

    def evaluate_subnode_as_continuation(self,env,idx):
        # Force an explicit translation of the subnode so we can cache the reference
        self.subnode_values[idx] = translate(self.subnode_values[idx])
        # Raise a ContinuationException
        raise ContinuationException(self.subnode_values[idx])

    def translate_subnodes(self):
        for idx in range(0,len(self.subnode_values)):
            self.subnode_values[idx] = translate(self.subnode_values)
            
    def evaluate_subnodes(self,env,range_l=0,range_u=None):
        if range_u is None:
            range_u = len(self.subnode_values)

        result_list = []
        for idx in range(range_l,range_u):
            result_list.append(self.evaluate_subnode(env,idx))

        return result_list

class SkimpyLambda(SkimpyForm):
    def __init__(self,form,argnames,text):
        super(SkimpyLambda,self).__init__(form,1)

        self.argnames = argnames

        # Save the text as a (currently unevaluated) subnode
        self.set_subnode(text,0)
        self.proc_id = 1

    def make_eval(self,env):
        to_ret = sdata.CompoundProc(env,'#compound-procedure-' + str(self.proc_id), self.argnames, self.get_subnode(0))
        self.proc_id += 1
        return (to_ret, EvalMessage.RESULT)
    
        yield None  # Force this to be a generator
        
    def seval(self,env,caller_id):
        # The text node is not automatically translated here.  What this means is that, unless you pretranslate the form,
        # the text will be retranslated each time a different actual procedure with a separate environment is applied.

        # On the other hand, the CompoundProc object below evaluates the text and therefore caches the translation after
        # the first evaluation.
        to_ret = sdata.CompoundProc(env,'#compound-procedure-' + str(self.proc_id), self.argnames, self.get_subnode(0))
        self.proc_id += 1
        return to_ret

class SkimpyApply(SkimpyForm):
    def __init__(self,form,subexprs):
        # We already know form is not an atom and there are no other syntactic restrictions        
        super(SkimpyApply,self).__init__(form)

        # note to self: the parsed program text should be immutable
        self.subnodes(subexprs)

    def make_eval(self,env):
        op_eval = self.make_subnode_evaluator(env,0)        
        op = (yield op_eval)

        if not isinstance(op,sdata.SkimpyProc):
            raise SkimpyError(self.original_form, 'application: ' + str(op_to_call) + ' is not callable')
        
        op_arguments = []
        for arg_eval in self.make_subnode_evaluators(env,1,None):
            result = (yield arg_eval)
            op_arguments.append(result)

        applier = op.make_applier(self.original_form,env,op_arguments)
        return (applier,EvalMessage.CONTINUATION)

    def seval(self,env,caller_id):
        # Evaluate the operator, then evaluate the operands, then proceed to call the operator
        # Use the helper function in the base class
        op_to_call = self.evaluate_subnode(env,0)

        if not isinstance(op_to_call,sdata.SkimpyProc):
            raise SkimpyError(self.original_form, 'application: ' + str(op_to_call) + ' is not callable')
        
        op_arguments = self.evaluate_subnodes(env,1,None)
        return op_to_call.apply(self.original_form,env,caller_id,op_arguments)

class SkimpyDefine(SkimpyForm):
    def __init__(self,form,key,expression):
        super(SkimpyDefine,self).__init__(form,1)
        self.key = parse.get_text(key)
        self.set_subnode(expression,0)

    def make_eval(self,env):
        bv_eval = self.make_subnode_evaluator(env,0)
        # Evaluate, then return nothing.
        bound_value = (yield bv_eval)
#        print ('binding ' + str(bound_value) + ' to ' + self.key)
        env.bind (self.key, bound_value)
        return (sdata.SkimpyNonReturn(self.key),EvalMessage.RESULT)
        
    def seval(self,env,caller_id):
        bound_value = self.evaluate_subnode(env,0)
        # Add a binding to the environment
        env.bind(self.key,bound_value)
        return sdata.SkimpyNonReturn(self.key)

class SkimpySequence(SkimpyForm):
    def __init__(self,form,subexprs):
        # NOTE:  since we use sequences for syntactic neologisms which are not explicitly a 'begin' form and have no counterpart in the tree,
        # -- e.g. procedure bodies -- form might refer to an outer context
        # See analyze_lambda and analyze_define for details.
        
        super(SkimpySequence,self).__init__(form)
        # Store the expressions just as in 'apply'.  Later evaluate them in order
        self.subnodes(subexprs)

    def make_eval(self,env):
        statement_nodes = self.make_subnode_evaluators(env,0,-1)

        for node in statement_nodes:
            yield node

        return (self.make_subnode_evaluator(env,-1),EvalMessage.CONTINUATION)
        
    def seval(self,env,caller_id):
        # Evaluate everything but the last node, then make the last node a continuation
        last_node = len(self.subnode_values)-1
        self.evaluate_subnodes(env,0,last_node)
        self.evaluate_subnode_as_continuation(env,last_node)

class SkimpyIf(SkimpyForm):
    def __init__(self,form,cond,consequence,alternative):
        if alternative is not None:
            n_subnodes = 3
        else:
            n_subnodes = 2

        super(SkimpyIf,self).__init__(form,n_subnodes)
        self.set_subnode(cond,0)
        self.set_subnode(consequence,1)
        if alternative is not None:
            self.set_subnode(alternative,2)

#        print ('processing if: ' + form.str_pretty() + ', count ' + str(n_subnodes))

    def make_eval(self,env):
        cond_evaluator = self.make_subnode_evaluator(env,0)
        cond_result = (yield cond_evaluator)

        if not sdata.is_false(cond_result):
            return (self.make_subnode_evaluator(env,1), EvalMessage.CONTINUATION)
        else:
            if len(self.subnode_values) > 2:
                return (self.make_subnode_evaluator(env,2), EvalMessage.CONTINUATION) 
            else:
                return sdata.false_value
    
    def seval(self,env,caller_id):
        cond_result = self.evaluate_subnode(env,0)

        if not sdata.is_false(cond_result):
            self.evaluate_subnode_as_continuation(env,1)
        else:
            # Evaluating alternative
            if len(self.subnode_values) > 2:
                self.evaluate_subnode_as_continuation(env,2)
            else:
                return sdata.false_v

class QualifierType(Enum):
    Q_OR = 0
    Q_AND = 1

class SkimpyQualifier(SkimpyForm):
    def __init__(self,form,subexpressions,qualifier_type):
        self.subnodes(subexpressions)
        self.qualifier_type = qualifier_type

    def make_eval(self,env):
        
        for subnode_eval in self.make_subnode_evaluators(env,0,-1):
            result = (yield subnode_eval)
            # Short circuit
            
            if self.qualifier_type == QualifierType.Q_OR:
                if not sdata.is_false(result):
                    return (result,EvalMessage.RESULT)
            else:  # AND
                if sdata.is_false(result):
                    return sdata.false_val            

        return (self.make_subnode_evaluator(env,-1),EvalMessage.CONTINUATION)
    
    def seval(self,env,caller_id):
        # Short-circuit evaluation
        last_node_idx = len(self.subnode_values)-1
        for idx in range(0,last_node_idx):
            node = self.get_subnode(idx)
            result = self.evaluate_subnode(env,idx)
            if self.qualifier_type == QualifierType.Q_OR:
                if not sdata.is_false(result):
                    return result
            else:  # AND
                if sdata.is_false(result):
                    return sdata.false_val

        # Last node should be tossed up as a continuation in both cases
        self.evaluate_subnode_as_continuation(env,last_node_idx)
        
# A form-wrapper around a literal value.
# It must be converted to a python value before it is bound.
class SkimpyLiteral(SkimpyForm):
    def __init__(self,form,factory,python_value):
        super(SkimpyLiteral,self).__init__(form)
        # form must be an atom/token representing a value that can be wrapped in factory
        # note: converter is handed in
        
        self._v = factory(python_value)

    def make_eval(self,env):
        return (self._v,EvalMessage.RESULT)
        yield None
    
    def seval(self,env,caller_id):
        return self._v

# A form-wrapper around a Scheme symbol or variable
class SkimpyVariable(SkimpyForm):
    def __init__(self,form):
        super(SkimpyVariable,self).__init__(form)       
        self.varname = parse.get_text(form)

    def make_eval(self,env):
        binding = env.find(self.varname)
        if binding is None:
            raise SkimpyError(self.original_form, 'unbound variable in this context: ' + self.varname)

        return (binding,EvalMessage.RESULT)
        yield None
        
    def seval(self,env,caller_id):
        binding = env.find(self.varname)
        if binding is None:
            raise SkimpyError(self.original_form, 'unbound variable in this context: ' + self.varname)

        return binding
    

def analyze_proc_body(ref_form,form_iterator):
    proc_body_list = list(form_iterator)  # this makes sense because we will use these one way or another

    if not proc_body_list:
        raise SkimpyException(ref_form, 'empty procedure body')
    elif len(proc_body_list) == 1:
        return proc_body_list[0]
    else:
        # note that ref_form is from an outer context!
        return SkimpySequence(ref_form, proc_body_list)

def analyze_lambda(form):
        # Build up the AST entry for the procedure
        arglist_node = parse.get_subnode(form,1)

        if arglist_node is None or parse.is_atom(arglist_node):
            err_node = arglist_node if arglist_node is not None else form
            raise SkimpyError(err_node, 'lambda: invalid syntax')

        argnames = []
        for argname in parse.generate_subnodes(arglist_node):
            if not parse.is_varname(argname):
                raise SkimpyError(form, 'lambda: invalid syntax in argument list')
            argnames.append(parse.get_text(argname))

        return SkimpyLambda(form,argnames,\
                            analyze_proc_body(form,parse.generate_subnodes(form,2)) )

def analyze_let(form):
    # A let is a lambda which is immediately applied
    # Let's extract the parts
    # NOTE:  There are more efficient as-if ways to do this.  I will consider a special SkimpyLet.
    
    # TODO: Syntax checks
    
    binding_list = parse.get_subnode(form,1)
    text = parse.generate_subnodes(form,2)
    
    argnames = []
    apply_list = [None]  # Reserve space for the procedure represented by the lambda
    # Go through the bindings, adding variable names to the argument list (see analyze_define) and
    # expressions to the application list
    for node in parse.generate_subnodes(binding_list):
        argnames.append (parse.get_text(parse.get_subnode(node,0)))
        apply_list.append (parse.get_subnode(node,1))

    apply_list[0] = SkimpyLambda(form,argnames,analyze_proc_body(form,text))
    return SkimpyApply(form,apply_list)
    
def analyze_define(form):
    # Two possibilities.  Regular define or regular define with lambda
    # Example:  (1) (define x 5)
    # (2) (define (add x y) (print 'adding') (+ x y))
    
    form_subnodes = parse.generate_subnodes(form,1)
    try:    
        defined_obj = next(form_subnodes)

        if not parse.is_atom(defined_obj):
            obj_nodes = parse.generate_subnodes(defined_obj)
            try:
                var_token = next(obj_nodes)
            except StopIteration:
                raise SkimpyError(defined_obj, 'define: invalid syntax')
            
            # Construct the lambda from the remainder
            argnames = []
            for argname in obj_nodes:
                if not parse.is_varname(argname):
                    raise SkimpyError(form, 'define: invalid syntax in argument list')
                argnames.append(parse.get_text(argname))
            
            proc_text = analyze_proc_body(form,form_subnodes)
            def_expr = SkimpyLambda(form,argnames,proc_text)
        else:
            var_token = defined_obj
            def_expr = next(form_subnodes)
    except StopIteration:
        raise SkimpyError(form, 'invalid syntax')
        
    return SkimpyDefine(form,var_token,def_expr)

def analyze_apply(form):
    return SkimpyApply(form, parse.generate_subnodes(form))

def analyze_if(form):
    cond = parse.get_subnode(form,1)
    consequent = parse.get_subnode(form,2)
    alternative = parse.get_subnode(form,3)

    if cond is None or consequent is None:
        raise SkimpyError(form, 'ill-formed if')

    return SkimpyIf(form,cond,consequent,alternative)

def analyze_cond(form):
    # Build up a list of conditions and consequents
    # We can simplify everything by building up a chain of ifs-elses from the last alternative
    # This is not bad in computation either because ifs raise ContinuationExceptions.

    # TODO:  Syntax checks!!!!

    last_cond = parse.get_subnode(form,-1)

    alternative = None
    start_idx = -1
    final_test = parse.get_subnode(last_cond,0)
#    print ('ftext ' + final_test.str_pretty())
    if parse.is_atom(final_test) and parse.get_text(final_test) == "else":
        alternative = parse.get_subnode(last_cond,1)
        start_idx = -2

    # Ifs with consequents
    for node in parse.generate_subnodes_reversed(form,start_idx,1):
        alternative = SkimpyIf(form,parse.get_subnode(node,0), parse.get_subnode(node,1),alternative)

    return alternative

def analyze_or(form):
    return SkimpyQualifier(form, parse.generate_subnodes(form,1), QualifierType.Q_OR)

def analyze_and(form):
    return SkimpyQualifier(form, parse.generate_subnodes(form,1), QualifierType.Q_AND)
        
def analyze_literal(form):
    if parse.is_number(form):
        return SkimpyLiteral(form,sdata.SkimpyNumber,parse.to_number(form))
    elif parse.is_string(form):
        return SkimpyLiteral(form,sdata.SkimpyString,parse.to_python_string(form))

def analyze_sequence(form,implicit=False):
    # A sequence of expressions
    return SkimpySequence(form, parse.generate_subnodes(form,0 if implicit else 1))

def analyze_implicit_sequence(form):
    # NOTE:  This is like analyze_proc_body above, except it preserves the tree.
    return analyze_sequence(form,implicit=True)

# Initialize a module-level dictionary mapping token values to factories (classes)
special_map = {"lambda" : analyze_lambda,
               "define" : analyze_define,
                "begin" : analyze_sequence,
               "if" : analyze_if,
               "cond" : analyze_cond,
               "let" : analyze_let,
               "or" : analyze_or,
               "and" : analyze_and}

def get_form_factory(form):
    # Check the map, then check the conditionss
    if not parse.is_atom(form):
        if form.parent is None:
            # Analyze the root by building a sequence
            return analyze_implicit_sequence
        
        # All special forms begin with a first element
        first_element = parse.get_subnode(form,0)
        if first_element is None:
            raise SkimpyError(form, 'unexpected empty form ()')

        if parse.is_atom(first_element):
            element_text = parse.get_text(first_element)
            if element_text in special_map:
                return special_map[element_text]
        
        # If nothing else works, treat this as an application
        return analyze_apply
    else:
        if parse.is_varname(form):
            return SkimpyVariable # In this case we can return the class name because the constructor just takes form
        else:
            return analyze_literal

def translate(form):
    # translate() will return the object it gets if it's already a SkimpyForm
    # Otherwise translate uses get_form_factory to get a factory for the right kind of SkimpyForm object.
    # get_form_factory performs a superficial analysis and returns, except in one case, an analyze_... function as the factory.
    # translate() proceeds to call the factory, which analyzes the form more deeply and produces the right object
    if not isinstance(form,SkimpyForm):
        cl = get_form_factory(form)  # Analyze the syntax of the node to find the right factory

        # Construct the form and translate it superficially
        return cl(form)
    else:
        return form

def preprocess(form):
    # Preprocess a concrete tree into an abstract one
    # This is called on the root of a program, so let's handle it specially
    tree_stack = []

    for node in parse.generate_subnodes(form):
        tree_stack.append(translate(node))

    while tree_stack:
        current = tree_stack.pop()
        # Translate and push
        if current.subnode_values:
            current.translate_subnodes()
            tree_stack.extend(current.subnode_values)

def explicit_eval(skimpy_form,env):
    # The explicit evaluator does not use the Python stack for evaluation
    # Instead it uses its own stack and signals.  It treats each form as a factory for evaluators.  It communicates
    # with evaluators using send(), i.e. make_eval can be a generator

    trans_form = translate(skimpy_form)
    eval_list = [trans_form.make_eval(env)]
    returned_result = None # The result of the previous evaluation

    while eval_list:
        to_eval = eval_list[-1]
 #       print ('loop v ' + str(to_eval) + ':' + str(len(eval_list)))

        # Make it generator-style natural
        try:
            next_request = to_eval.send(returned_result)

            # Hack to enable iterative recursion (tail-optimization)
            appl_class = sdata.CompoundProc.Applier
            if isinstance(next_request, appl_class):
                next_request._user = to_eval
                
            eval_list.append(next_request)
            returned_result = None # So the new request won't be fed a leftover (illegal per Python)
        except StopIteration as iter_exc:
            eval_result = iter_exc.value
            eval_list.pop()
            
            if eval_result[1] == EvalMessage.CONTINUATION:
                eval_list.append(eval_result[0])
                returned_result = None
            else:
                returned_result = eval_result[0]
                
    return returned_result

def skimpy_eval(skimpy_form,env,caller_id = None):

    # In this interpreter, the form classes above delimit evaluation rules for various parts.
    # Form objects are nodes -- either in the concrete tree of tokens built by parse.skimpy_scan, or the AST nodes that derive from
    # SkimpyForm above.

    # Only SkimpyForms can be evaluated, so if the node in question is a subnode of the immutable concrete tree representing the program,
    # we must first translate it with the translate() function above.

    # The translated node is evaluated by dispatching to seval() on the SkimpyForm object (or rather an object of one of the subtypes.)
    # The function returns a pair with the result of the evaluation but also the translated node, so that callers can, if they wish,
    # cache the translated object in place of the original node.  
    
    # Note that translation of compound forms is 'shallow' or 'lazy' -- in the sense that, once a node is analyzed, its subnodes are not
    # automatically translated.  Subnodes are translated whenever we want or need to translate them

    # It is possible by using recursion to translate the entire CST into an AST right after parsing,
    # i.e. to translate eagerly (and greedily).  In this case form will always be an AST node.  See recursive_translate() below.

    # NOTE regarding continuations:
    # To facilitate tail recursion, we can return control here with an exception instead of calling this function recursively
    # The caller_id value passed in during procedure application will be equal to the procedure object.  Thus if some
    # subexpression simplifies to a recursive call to the same function, we will rebind the arguments in the environment
    # and return here, instead of getting deeper into the recursion.

    # (Exceptions in Python must be fairly performant; StopIteration is still used to signal the end of any iteration.)

    final_eval = False
    original_translated_form = translate(skimpy_form)

    translated_form = original_translated_form
    while not final_eval:
        try:
            to_return = translated_form.seval(env,caller_id)
            final_eval = True
        except ContinuationException as ce:
            # replace the form
            skimpy_form = ce.form
            translated_form = translate(skimpy_form)

    return (to_return, original_translated_form)
