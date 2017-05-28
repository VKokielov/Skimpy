# Skimpy
Skimpy (no relation whatsoever to Schemepy or any other interpreter on the net -- I did not consult any of them while writing the core) -- is another attempt to write a Scheme interpreter, yadayadayada.  It is not a project for school but a personal one, hence its design is constrained by nothing but my judgment.  I wrote it in the course of a week or so, inspired by the discussion in the fourth chapter of Structure and Interpretation but with a firm resolve to be flexible in my design.  The result is this program, still in the early stages of testing and far from implementing the entire language or even a relatively complete subset.

Skimpy is somewhat boot-strapped to Python, especially in respect to:

* Garbage.  Values are represented as Python objects, as are environments.  Environments which do not escape to the global scope or which are made irrelevant because there are no references to them should be finalized by clearing refs to all values within them, and doing so recursively for pairs among the values.  This will help the dumbest Python garbage collector succeed.

* The form of evaluation.  I considered decoupling evaluation in Scheme from Python by using generators that speak with the evaluator.  It proved too complicated.  I settled for a compromise: when an evaluator determines that the result of an expression is the result of one of its subexpressions, it throws an exception and returns control to the evaluator.  This mechanism also serves to implement tail optimization with some minor alterations.
** UPDATE:  I have added an explicit-control evaluator using generators.  Unfortunately, it is much slower -- possibly because every expression must now explicitly or implicitly construct a new Python object on evaluation.  On the other hand, there is now no limit to the recursion depth.  To try, change execute_code in sloop.py to call explicit_eval instead of skimpy_eval.

In respect of values, the interpreter is less boot-strapped.  Scheme values are always represented by special Python objects.  Conversion is implicit in rare cases.  Even procedures implemented in Python can opt out of having inputs and outputs converted, by setting a flag.  This will increase performance at the expense of clarity.

Because the functional part of Python is much akin to Scheme, the boot-strap simplifies some operations and makes other look familiar.  On the other hand, this is not a wrapper but a legitimate interpreting machine.  Had coroutines been less unwieldy to use for this purpose, I would have gladly used them to separate out evaluation and objectify it.

## TRANSLATION
The interpreter, conventionally, begins by prescanning the text of a program and breaking it into a sequence of tokens.  Following that it turns strings full of parentheses into nodes of what I call the concrete tree.  The concrete tree contains intermediate nodes and leaves, consisting of the tokens.  (Each token remembers where it was parsed so that no matter where an error happens the end-user can be referred to the file.)

What happens after processing depends on the driver of the interpreter.  The eval function accepts dual arguments for the program text: nodes from the scanned program text (concrete nodes) or Python objects representing syntax, called forms or abstract nodes.  A translate function accepts both as well and is called from eval; if the object is a form, i.e. syntax has already been analyzed, the node is returned as-is, otherwise analysis constructs a form.  Thus any part of the interpreter can refer to any part of the text in either form, and Form objects among others will always cache their subexpression forms after translation.  It goes without saying that the program text is considered forever immutable; to cache translations would otherwise be incorrect.

Normally, the caching is lazy: nodes which are not needed are never reached and never translated.  (In particular, the text of a procedure is not translated during creation but only during evaluation separately for each instance of the text; perhaps it would be expedient to cache the first translation on the original lambda as well.   It is also possible to make the caching eager by running a full search / visitation on the subnode graph -- translate/enumerate subnodes in a loop until the entire tree is abstract.

Note also that I have chosen for the internals of the interpreter to begin with as few node types as possible, and to allow analysis to construct combinations of the same for syntactic sugar.  This avoids code duplication at the expense of a potential Scheme performance hit, but the loss is small and the technique makes the interpreter more modular and easier to understand.

After translation finishes, evaluation proceeds on the forms in the given environment.  Evaluation is straightforward except for tail-optimizations.  When an expression finds that its result would be identical to that of a subexpression -- e.g. in conditionals or in tail recursive calls -- it does not call the evaluator recursively, but raises an exception to return control to the evaluator from which it was called.  The same evaluator then takes the new expression and evaluates it, in a loop until no expression raises a continuation.  When this happens for a tail call, the environment is rebound with the next state of the iteration before the exception is raised (see apply in CompoundProcedure in sdata.py)

## LESSONS LEARNED
The structure of the interpreter highlights how true is the assertion that in Scheme and generally LISP data is code and code is data.  The evaluation rules are all in seval.py, the object types are in sdata.py, and the underlying API will go to builtins.py.  Rarely does modern software get to be mathematically neat, clear, and modular.
