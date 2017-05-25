class SkimpyError(BaseException):
    def __init__(self,l,c,reason):
        self.line = l
        self.col = c
        self.reason = reason

    def __init__(self,form,reason):
        self.line = form.line
        self.col = form.col
        self.reason = reason

    def __str__(self):
        return "SkimpyError: line " + str(self.line) + " col " + str(self.col) + ": " + self.reason
    
