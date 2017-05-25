import parse
import sdata
from serror import SkimpyError

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
        eval_result,self.subnode_values[idx] = skimpy_eval(self.subnode_values[idx],env)
        return eval_result
    
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
        
    def seval(self,env):
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

    def seval(self,env):
        # Evaluate the operator, then evaluate the operands, then proceed to call the operator
        # Use the helper function in the base class
        op_to_call = self.evaluate_subnode(env,0)

        if not isinstance(op_to_call,sdata.SkimpyProc):
            raise SkimpyError(self.original_form, 'application: ' + str(op_to_call) + ' is not callable')
        
        op_arguments = self.evaluate_subnodes(env,1,None)
        return op_to_call.apply(self.original_form,env,op_arguments)

class SkimpyDefine(SkimpyForm):
    def __init__(self,form,key,expression):
        super(SkimpyDefine,self).__init__(form,1)
        self.key = parse.get_text(key)
        self.set_subnode(expression,0)

    def seval(self,env):
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

    def seval(self,env):
        # Return the last value evaluated
        return self.evaluate_subnodes(env)[-1]        

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

    def seval(self,env):
        cond_result = self.evaluate_subnode(env,0)

        if cond_result.pythonify():
            return self.evaluate_subnode(env,1)
        else:
            # Evaluating alternative
            alternative = self.get_subnode(2)
            if alternative is not None:
                return self.evaluate_subnode(env,2)
            else:
                return sdata.false_value

# A form-wrapper around a literal value.
# It must be converted to a python value before it is bound.
class SkimpyLiteral(SkimpyForm):
    def __init__(self,form,factory,python_value):
        super(SkimpyLiteral,self).__init__(form)
        # form must be an atom/token representing a value that can be wrapped in factory
        # note: converter is handed in
        
        self._v = factory(python_value)

    def seval(self,env):
        return self._v

# A form-wrapper around a Scheme symbol or variable
class SkimpyVariable(SkimpyForm):
    def __init__(self,form):
        super(SkimpyVariable,self).__init__(form)       
        self.varname = parse.get_text(form)

    def seval(self,env):
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
            argnames.append(argname)

        return SkimpyLambda(form,argnames,\
                            analyze_proc_body(form,parse.generate_subnodes(form,2)) )

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
            argnames = [parse.get_text(name_token) for name_token in obj_nodes]
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

def analyze_literal(form):
    if parse.is_number(form):
        return SkimpyLiteral(form,sdata.SkimpyNumber,parse.to_number(form))
    elif parse.is_string(form):
        return SkimpyLiteral(form,sdata.SkimpyString,parse.to_string(form))

def analyze_sequence(form):
    # A sequence of expressions
    return SkimpySequence(form, parse.generate_subnodes(form,1))



# Initialize a module-level dictionary mapping token values to factories (classes)
special_map = {"lambda" : analyze_lambda,
               "define" : analyze_define,
                "begin" : analyze_sequence,
               "if" : analyze_if}

def get_form_factory(form):
    # Check the map, then check the conditionss
    if not parse.is_atom(form):
        # All special forms begin with a first element
        first_element = parse.get_subnode(form,0)
        if first_element is None:
            raise SkimpyError(form, 'unexpected empty form ()')
        element_text = parse.get_text(first_element)
        if element_text in special_map:
            return special_map[element_text]
        else:
            # Treat it as an application
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

def skimpy_eval(skimpy_form,env):

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
    
    translated_form = translate(skimpy_form)
    to_return = translated_form.seval(env)

    return (to_return, translated_form)
