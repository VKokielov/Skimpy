class SkimpyError(Exception):
    def __init__(self,context,reason):
        if isinstance(context,tuple) or isinstance(context,list):
            self.line = context[0]
            self.col = context[1]
        else: #object
            if context is None:
                self.line = 0
                self.col = 0
            else:
                self.line = context.line
                self.col = context.col
            
        self.reason = reason

    def __str__(self):
        return "SkimpyError: line " + str(self.line) + " col " + str(self.col) + ": " + self.reason
    
