# rules.py
# Contains the transformation rules for Terminator.
# Each rule is a class that knows how to transform a specific
# piece of the C++ AST into a Python equivalent.

# Import the AST node definitions from the main module.
# This creates a circular dependency, which is generally not ideal,
# but is acceptable for this two-file structure to keep things simple.
import terminator as ast

class Rule:
    """Base class for all transformation rules."""
    def visit(self, node):
        """
        Process a node. If the node is of a type this rule can
        transform, it should return a new, transformed node.
        Otherwise, it should return the original node.
        """
        return node

class ForLoopToRangeRule(Rule):
    """Converts simple C-style for loops to Python's `for i in range(...)`."""
    def visit(self, node):
        if not isinstance(node, ast.ForLoop):
            return node

        # This rule is very specific for demonstration. A real-world
        # version would be more flexible.
        # It looks for: for(int i = 0; i < N; i++)

        # 1. Check init: `int i = 0`
        init = node.init
        if not (isinstance(init, ast.VarDecl) and isinstance(init.init, ast.Literal) and init.init.value == 0):
            return node
        
        loop_var = init.name

        # 2. Check condition: `i < N`
        cond = node.cond
        if not (isinstance(cond, ast.BinaryOp) and cond.op == '<' and 
                isinstance(cond.left, ast.Identifier) and cond.left.name == loop_var):
            return node
        
        upper_bound = cond.right

        # 3. Check increment: `i++` or `++i`
        inc = node.inc
        if not (isinstance(inc, ast.UnaryOp) and inc.op == '++' and
                isinstance(inc.operand, ast.Identifier) and inc.operand.name == loop_var):
            return node
        
        # If all conditions match, create a new Pythonic for loop node
        # We need a new node type for this, let's call it `PythonForLoop`
        # and add it to `terminator.py`'s generator.
        
        # For simplicity in this example, we will re-purpose the ForLoop node and
        # let the code generator handle it. Let's create a *new* node type in memory
        # to represent the pythonic loop.
        class PythonForLoop(ast.Node):
            def __init__(self, target, iter, body):
                self.target = target
                self.iter = iter
                self.body = body

        # Add a visitor for this new node type to the code generator dynamically.
        # This is a bit of a hack, but keeps the files separate.
        def visit_PythonForLoop(self, node):
            target = self.visit(node.target)
            iterable = self.visit(node.iter)
            code = f"for {target} in range({iterable}):\n"
            self._indent_level += 1
            if not node.body:
                code += f"{self._indent()}pass\n"
            else:
                for stmt in node.body:
                    # The body is nested inside another node in our parsing
                    if isinstance(stmt, ast.Node) and hasattr(stmt, 'body'):
                        for sub_stmt in stmt.body:
                            code += f"{self._indent()}{self.visit(sub_stmt)}\n"
                    else:
                        code += f"{self._indent()}{self.visit(stmt)}\n"

            self._indent_level -= 1
            return code
        
        # Monkey-patch the code generator
        if not hasattr(ast.PythonCodeGenerator, 'visit_PythonForLoop'):
            ast.PythonCodeGenerator.visit_PythonForLoop = visit_PythonForLoop

        return PythonForLoop(
            target=ast.Identifier(loop_var),
            iter=upper_bound,
            body=node.body
        )

class StdCoutToPrintRule(Rule):
    """Converts `std::cout << ...` chains to Python's `print()` function."""
    def visit(self, node):
        if not isinstance(node, ast.BinaryOp) or node.op != '<<':
            return node

        # Check if it's a `std::cout` chain
        if not (isinstance(node.left, ast.Identifier) and node.left.name == 'std::cout'):
            # It could be a nested chain, e.g., (std::cout << "a") << "b"
            if not (isinstance(node.left, ast.BinaryOp) and node.left.op == '<<'):
                return node
        
        # It's a `cout` call. Let's flatten the chain and collect arguments.
        args = self._flatten_cout_chain(node)
        
        # Create a new CallExpr node representing print()
        return ast.CallExpr(
            callee=ast.Identifier('print'),
            args=args
        )

    def _flatten_cout_chain(self, node):
        """Recursively collects all parts of a `<<` chain."""
        args = []
        # The right side is always an argument
        
        # Special case: std::endl should become a keyword arg flush=True
        # For simplicity, we'll just ignore it here, but a real implementation would handle it.
        if isinstance(node.right, ast.Identifier) and node.right.name == 'std::endl':
             pass # Drop std::endl
        else:
            args.append(node.right)

        # Traverse left to find the rest of the chain
        if isinstance(node.left, ast.BinaryOp) and node.left.op == '<<':
            args = self._flatten_cout_chain(node.left) + args
        
        return args