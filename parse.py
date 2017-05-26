from serror import SkimpyError

# Save the line and column of this token for error messages
class SkimpyToken(object):
    def __init__(self,text,line,col):
        if not text:
            raise ValueError('initializing token with empty string')
        
        self.text = text
        self.line = line
        self.col = col
 #       print ('building ' + str(self))

    def __str__(self): # Printable representation
        return self.text + " @ {" + str(self.line) + ":" + str(self.col) + "}"

    def str_pretty(self):
        if self.text and self.text[0] == '"':
            return self.text + '"'
        else:
            return self.text
     
class SkimpyConcrNonleafNode(object):
    def __init__(self,line,col,parent=None):
        self.parent = parent
        self.text = [] # list representing my substructure
        self.line = line
        self.col = col

    def append(self,v):
        self.text.append(v)
    
    def str_pretty(self):
        retv = ""

        if not self.text:
            retv += "#f"  # empty node
        else:
            retv += "("
            retv += self.text[0].str_pretty()
            for i in range(1,len(self.text)):
                retv += " "
                retv += self.text[i].str_pretty()
            retv += ")"

        return retv


# This logic is shared between all states
class SkimpyPrescanContext(object):
    def __init__(self,t_str):
        self.t_str = t_str # Store a ref to the text we're parsing for efficient slicing
        self.lc = [1,1]
        self.token_lc = [0,0]
        self.idx = 0
        self.mark = 0 # Beginning of last token

    def get_error(self,reason):
        return SkimpyError(self.lc,reason)
        
    def on_token_end(self):
        # Slice the token and add it
        new_token = self.t_str[self.mark:self.idx]
        return SkimpyToken(new_token,self.token_lc[0],self.token_lc[1])

    def single_token(self,text):
        return SkimpyToken(text,self.lc[0],self.lc[1])        

    def on_token_start(self):
        self.mark = self.idx
        self.token_lc = self.lc[:]

    def on_character(self,ch):
        self.idx += 1
        if (ch == '\n'):
            self.lc[0] += 1
            self.lc[1] = 1
        else:
            self.lc[1] += 1

    def distance(self):
        return self.idx - self.mark

def is_extended(ch):
    return ch == "+" or ch == "*" or ch == "/" or ch == "-" or ch == "_" or ch == "<" or ch == ">" or ch == "?" or ch == "!" or ch == "'"\
           or ch == "=" or ch == "<" or ch == ">" or ch == "."

# not applicable for text between quotes
def classify_char(ch):
    if ch == "(":
        return 1
    elif ch == ")":
        return 2
    elif ch == "'":
        return 4
    elif ch.isspace():
        return 0
    elif ch.isalnum() or is_extended(ch):
        return 3
    elif ch == '"':
        return 5 # quotation
    else:
        return None
    
def get_text(token):
    return token.text

def slice_token(token,b,e):
    new_text = token.text[b:e]
    return SkimpyToken(new_text,token.line,token.col)
    
def skimpy_prescan(t_str):
    # Prescan generator
    fsm_state = 0 # Four states: whitespace(0), left-parenthesis(1), right-parenthesis(2), (for one character only) and value(3)
    context = SkimpyPrescanContext(t_str)
    token_len = 0

    for ch in t_str:
        # Category of next character as whitespace, identifier, or parenthesis
        char_cat = classify_char(ch)

        if char_cat is None:
            # Invalid character
            raise context.get_error("Invalid character: " + ch)

        # If we are not inside quotes
        changed_category = fsm_state != char_cat  # Note: if fsm_category == -1, this will be true

        if fsm_state == 1 or fsm_state == 2 or fsm_state == 4 or fsm_state == 6:  # End the token in any case
            yield context.on_token_end()
        elif fsm_state == 3:  # identifier -- token if the next state is not the same
            if changed_category:
                yield context.on_token_end()
        elif fsm_state == 5:
            if fsm_state == char_cat:  # i.e. if char_cat says quote, i.e. the closing quote
                # Set state to '6' (one-past-quote) and grab the next character
                fsm_state = 6
                context.on_character(ch)
                continue
            else:
                # Still inside quotes.  Don't assign a new category
                changed_category = False
                
        # No token if we end whitespace
        if changed_category:
            token_len = 0
            fsm_state = char_cat
        else:
            token_len += 1

        # Post.  Everything but whitespace starts a token.  Quotes start a token after at least one accumulated character.
        if fsm_state == 1 or fsm_state == 2 or fsm_state == 4:
            context.on_token_start()
        elif fsm_state == 5:
            if token_len == 0:
                context.on_token_start()
        elif fsm_state == 3:
            if token_len == 0:
                context.on_token_start()
        context.on_character(ch)

    # Seal off the last token at one-past-the-end
    if fsm_state != 0 and fsm_state != -1:
        yield context.on_token_end()

def is_atom(concrete_node):
    # In the parsed tree, a node is an atom iff it's a token
    return isinstance(concrete_node,SkimpyToken)

def get_text(token):
    if not is_atom(token):
        raise TypeError('get_text called with a nontoken node')

    return token.text

def is_number(token):
    # Note: we do not create empty tokens as they cannot mean anything
    # Note 2: For now, boot-strap the number representation to Python's
    return is_atom(token) and get_text(token)[0].isnumeric()

def to_number(token):
    # This wrapper around Python's str->num converter is to declare the policy
    return float(get_text(token))

def is_string(token):
    return is_atom(token) and get_text(token)[0] == '"'

def to_python_string(token):
    return get_text(token)[1:]  # skip the tagging quotation mark

def is_varname(token):
    # This is an oversimplification
    return is_atom(token) and not is_number(token) and not is_string(token)

def generate_subnodes(concrete_node,start = 0):
    if not is_atom(concrete_node):
        for idx in range(start,len(concrete_node.text)):
            yield concrete_node.text[idx]

def generate_subnodes_reversed(concrete_node,start = None, end = 0):
    if start is None:
        start = len(concrete_node.text) - 1
    elif start < 0:  # python style
        start = len(concrete_node.text) + start
        
    if not is_atom(concrete_node):
        for idx in range(start,end - 1,-1):
            yield concrete_node.text[idx]

def get_subnode(concrete_node,index):
    if not is_atom(concrete_node):
        if index < len(concrete_node.text) and index >= -len(concrete_node.text):
            return concrete_node.text[index]
        else:
            raise ValueError('concrete node index out of bounds')
    else:
        raise ValueError('calling getsubnode on an atom')

class SkimpyTreeBuilder(object):
    def __init__(self):
        self.root = SkimpyConcrNonleafNode(None,None)
        self.node = self.root

    def push(self,token):
        self.node = SkimpyConcrNonleafNode(token.line,token.col,self.node)

    def pop(self):
        cur_node = self.node
        self.node = cur_node.parent
        self.node.append(cur_node)

    def append(self,text):
        self.node.append(text)

# Binds all function arguments (returns a 0-argument function) but delays evaluation
def python_bind(f,*args,**kwargs):
    def _proc():
        f(*args,**kwargs)
    return _proc

def skimpy_scan(t_str):
    # We prescan cleverly, by building up a sequence of operations to perform
    sbuilder = SkimpyTreeBuilder()
    lp_stack = []  # stack of left parentheses
    operations = []
    for token in skimpy_prescan(t_str):
       
        if token.text == "(":
            lp_stack.append(token)
            operations.append(python_bind(sbuilder.push, token))
        elif token.text == ")":
            if not lp_stack:
                raise SkimpyError(token,'unmatched right parenthesis')
            lp_stack.pop()
            operations.append(sbuilder.pop)  # Nothing to bind, pop takes no arguments
        else:
            if token.text and token.text[0] == '"':
                # Quoted text
                if token.text[-1] != '"':
                    raise SkimpyError(token,'unmatched quotation')
                # We need to save the quotation as a prefix, because strings make up a special type
                operations.append(python_bind(sbuilder.append,slice_token(token,0,-1)))
            else:
                operations.append(python_bind(sbuilder.append,token))

    if lp_stack:
        # Pop the token and report an error
        inparen = lp_stack.pop()
        raise SkimpyError(inparen.l,inparen.c,'unmatched left parenthesis')

    # Now let's run the functions
    for op in operations:
        op()

    # The result is the root node in the tree.  We know it's the root because the parentheses matched
    return sbuilder.node
