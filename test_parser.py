import unittest
import parse
from parse import *

class TestSkimpyParser(unittest.TestCase):

    def assertNodeWithXChildren(self,text,lbound,ubound=None):
        if ubound is None:
            ubound = lbound+1

        self.assertIsInstance(text,SkimpyConcrNonleafNode,'should be a nonleaf node')
        #print('text ' + str(len(text.text)))
        self.assertTrue(len(text.text) >= lbound)
        self.assertTrue(len(text.text) < ubound)

    def assertTokenWithText(self,text,contents):
        self.assertIsInstance(text,SkimpyToken)
        self.assertEqual(text.text,contents)

    def test_empty(self):
        # Test for the existence of the root node here.  In all following tests, just fetch it
        text_root = skimpy_scan("()")

        self.assertNodeWithXChildren(text_root,1)
        text = text_root.text[0]

        self.assertNodeWithXChildren(text,0)
        self.assertEqual(text.str_pretty(), "#f")

    def test_token(self):
        input_id = "a-long-scheme-id"
        text = skimpy_scan(input_id).text[0]
        self.assertTokenWithText(text,input_id)
        self.assertEqual(text.str_pretty(), input_id)

    def test_nested(self):
        text = skimpy_scan("(+ 1 (* 2 3))").text[0]
        
        self.assertNodeWithXChildren(text,3)
        
        plus = text.text[0]
        self.assertTokenWithText(plus,"+")
        ladd = text.text[1]
        self.assertTokenWithText(ladd,"1")
        radd = text.text[2]
        self.assertNodeWithXChildren(radd,3)

        self.assertTokenWithText(radd.text[0],"*")
        self.assertTokenWithText(radd.text[1],"2")
        self.assertTokenWithText(radd.text[2],"3")
        
        self.assertEqual(text.str_pretty(), "(+ 1 (* 2 3))")
          
if __name__ == '__main__':
    unittest.main()
