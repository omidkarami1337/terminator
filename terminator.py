# terminator.py
# Written by Omid Karami
# Core logic for the Terminator C++ to Python transpiler.
# This file contains the parser, internal AST nodes, node traverser,
# Python code generator, and the command-line interface.

import sys
import argparse
import difflib
from pathlib import Path

# We recommend installing clang with: pip install libclang
try:
    import clang.cindex
except ImportError:
    print("Error: libclang is not installed. Please run 'pip install libclang'", file=sys.stderr)
    sys.exit(1)

# Import rules from the rules module
import rules as rule_definitions

# --- 1. Internal AST Node Definitions -----------------------------------------
# These classes define the structure of our simplified, internal AST.

class Node:
    """Base class for all AST nodes."""
    def __repr__(self):
        # A generic representation for debugging
        fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({fields})"

class TranslationUnit(Node):
    """The root of the AST, representing a file."""
    def __init__(self, body):
        self.body = body # List of top-level nodes (functions, classes, etc.)

class FunctionDecl(Node):
    """Represents a function definition."""
    def __init__(self, name, params, body, return_type):
        self.name = name
        self.params = params
        self.body = body
        self.return_type = return_type

class VarDecl(Node):
    """Represents a variable declaration, e.g., int x = 10;"""
    def __init__(self, name, var_type, init=None):
        self.name = name
        self.var_type = var_type
        self.init = init

class CallExpr(Node):
    """Represents a function call."""
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

class BinaryOp(Node):
    """Represents a binary operation, e.g., a + b."""
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right
        
class UnaryOp(Node):
    """Represents a unary operation, e.g., ++i."""
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class ForLoop(Node):
    """Represents a C-style for loop."""
    def __init__(self, init, cond, inc, body):
        self.init = init
        self.cond = cond
        self.inc = inc
        self.body = body

class Identifier(Node):
    """Represents a variable or function name."""
    def __init__(self, name):
        self.name = name

class Literal(Node):
    """Represents a literal value like a number or string."""
    def __init__(self, value):
        self.value = value

# --- 2. C++ Parser and AST Converter ----------------------------------------
# This class uses libclang to parse C++ and convert the Clang AST
# to our internal, simpler AST.

class CppParser:
    """Parses C++ code into our internal AST using libclang."""
    def __init__(self):
        self.index = clang.cindex.Index.create()

    def parse(self, content, filename='temp.cpp'):
        tu = self.index.parse(filename, args=['-std=c++11'], unsaved_files=[(filename, content)])
        if not tu:
            raise RuntimeError("Failed to parse C++ code.")
        
        # Check for parsing errors
        errors = [d for d in tu.diagnostics if d.severity >= clang.cindex.Diagnostic.Error]
        if errors:
            error_messages = "\n".join([f"- {e.spelling} at {e.location}" for e in errors])
            print(f"Warning: Clang reported errors during parsing:\n{error_messages}\n", file=sys.stderr)

        return self._convert_ast(tu.cursor)

    def _convert_ast(self, cursor):
        """Recursively converts a Clang cursor to an internal Node."""
        kind = cursor.kind
        
        if kind == clang.cindex.CursorKind.TRANSLATION_UNIT:
            return TranslationUnit([self._convert_ast(c) for c in cursor.get_children()])

        if kind == clang.cindex.CursorKind.FUNCTION_DECL:
            params = [self._convert_ast(c) for c in cursor.get_arguments()]
            # Find the body of the function
            body_stmts = []
            for c in cursor.get_children():
                if c.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                    body_stmts = [self._convert_ast(s) for s in c.get_children()]
                    break
            return FunctionDecl(cursor.spelling, params, body_stmts, cursor.result_type.spelling)
        
        if kind == clang.cindex.CursorKind.PARM_DECL:
            return VarDecl(cursor.spelling, cursor.type.spelling)

        if kind == clang.cindex.CursorKind.VAR_DECL:
            init_val = None
            # A VAR_DECL might have an initializer as a child
            children = list(cursor.get_children())
            if children:
                init_val = self._convert_ast(children[0])
            return VarDecl(cursor.spelling, cursor.type.spelling, init_val)

        if kind == clang.cindex.CursorKind.CALL_EXPR:
            callee = Identifier(cursor.spelling)
            args = [self._convert_ast(c) for c in cursor.get_arguments()]
            return CallExpr(callee, args)

        if kind == clang.cindex.CursorKind.BINARY_OPERATOR:
            children = list(cursor.get_children())
            if len(children) == 2:
                left = self._convert_ast(children[0])
                right = self._convert_ast(children[1])
                return BinaryOp(cursor.spelling, left, right)

        if kind == clang.cindex.CursorKind.UNARY_OPERATOR:
            op_map = {
                clang.cindex.UO_PREINC: '++',
                clang.cindex.UO_POSTINC: '++',
                clang.cindex.UO_PREDEC: '--',
                clang.cindex.UO_POSTDEC: '--',
            }
            # Clang's API for unary operator spelling is tricky, so we map it.
            op_string = op_map.get(cursor.opcode, "op?")
            return UnaryOp(op_string, self._convert_ast(list(cursor.get_children())[0]))

        if kind == clang.cindex.CursorKind.DECL_REF_EXPR:
            return Identifier(cursor.spelling)

        if kind == clang.cindex.CursorKind.INTEGER_LITERAL:
            return Literal(int(list(cursor.get_tokens())[0].spelling))

        if kind == clang.cindex.CursorKind.STRING_LITERAL:
            # Clang includes quotes, so we strip them.
            return Literal(list(cursor.get_tokens())[0].spelling.strip('"'))
            
        if kind == clang.cindex.CursorKind.FOR_STMT:
            children = list(cursor.get_children())
            # C-style for loop has 3 or 4 children: init, cond, inc, body
            if len(children) >= 3:
                init = self._convert_ast(children[0])
                cond = self._convert_ast(children[1])
                inc = self._convert_ast(children[2])
                body = [self._convert_ast(children[3])] if len(children) > 3 else []
                return ForLoop(init, cond, inc, body)

        # Fallback for unhandled nodes: return a generic representation
        # In a real tool, you would expand this mapping significantly.
        return Identifier(f"UNHANDLED<{kind.name}>")


# --- 3. Node Traverser and Rule Engine --------------------------------------

class NodeVisitor:
    """Base class for visitors that walk the AST."""
    def visit(self, node):
        if not isinstance(node, Node):
            return node
        
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field, value in node.__dict__.items():
            if isinstance(value, list):
                for i, item in enumerate(value):
                    value[i] = self.visit(item)
            elif isinstance(value, Node):
                setattr(node, field, self.visit(value))
        return node

class RuleApplier(NodeVisitor):
    """A traverser that applies a list of rules to each node."""
    def __init__(self, rules):
        self.rules = rules

    def visit(self, node):
        # First, let the rules try to transform the current node
        for rule in self.rules:
            # A rule might transform the node, so we update it
            node = rule.visit(node)
        
        # Then, continue traversing into the (potentially new) node's children
        return super().generic_visit(node)


# --- 4. Python Pretty Printer ------------------------------------------------

class PythonCodeGenerator(NodeVisitor):
    """Walks the final AST and generates formatted Python code."""
    def __init__(self):
        self._indent_level = 0

    def _indent(self):
        return "    " * self._indent_level

    def generate(self, node):
        return self.visit(node)

    def visit_TranslationUnit(self, node):
        return "\n\n".join(self.visit(child) for child in node.body if not isinstance(child, Identifier))

    def visit_FunctionDecl(self, node):
        params = ", ".join(self.visit(p) for p in node.params)
        
        # Attempt to add type hints
        return_hint = ""
        py_type = self._map_type(node.return_type)
        if py_type and py_type != "None":
            return_hint = f" -> {py_type}"

        code = f"def {node.name}({params}){return_hint}:\n"
        self._indent_level += 1
        
        if not node.body:
             code += f"{self._indent()}pass\n"
        else:
            for stmt in node.body:
                code += f"{self._indent()}{self.visit(stmt)}\n"
        self._indent_level -= 1
        
        # Add a common Python pattern to run main
        if node.name == "main":
            code += f'\n\nif __name__ == "__main__":\n'
            code += f'    main()'
            
        return code

    def visit_VarDecl(self, node):
        # In Python, declaration is implicit with assignment.
        # We handle type hints here.
        py_type = self._map_type(node.var_type)
        type_hint = f": {py_type}" if py_type else ""

        if node.init:
            return f"{node.name}{type_hint} = {self.visit(node.init)}"
        return f"{node.name}{type_hint} = None" # Initialize if no value is given
    
    def visit_CallExpr(self, node):
        callee = self.visit(node.callee)
        args = ", ".join(self.visit(arg) for arg in node.args)
        return f"{callee}({args})"

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return f"({left} {node.op} {right})"

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        if node.op == '++' or node.op == '--': # Convert to += 1 or -= 1
            op_map = {'++': '+=', '--': '-='}
            return f"{operand} {op_map[node.op]} 1"
        return f"{node.op}{operand}"

    def visit_ForLoop(self, node):
        # This assumes the loop has been transformed by a rule.
        # If a ForLoop node reaches here, it means no rule could simplify it.
        init_str = self.visit(node.init) if node.init else "# init"
        cond_str = self.visit(node.cond) if node.cond else "# cond"
        inc_str = self.visit(node.inc) if node.inc else "# inc"
        
        code = f"# Original C++ for loop was not transformed\n"
        code += f"{init_str}\n"
        code += f"while {cond_str}:\n"
        self._indent_level += 1
        
        for stmt in node.body:
            code += f"{self._indent()}{self.visit(stmt)}\n"
        code += f"{self._indent()}{inc_str}\n"
        
        self._indent_level -= 1
        return code
        
    def visit_Identifier(self, node):
        return node.name

    def visit_Literal(self, node):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)

    def _map_type(self, cpp_type):
        """Maps C++ types to Python type hints."""
        type_map = {
            "int": "int",
            "float": "float",
            "double": "float",
            "bool": "bool",
            "std::string": "str",
            "string": "str",
            "void": "None"
        }
        return type_map.get(cpp_type.replace("const ", ""), None)


# --- 5. Main Orchestrator and CLI ------------------------------------------

class Terminator:
    """Orchestrates the entire C++ to Python conversion process."""
    def __init__(self, active_rules):
        self.parser = CppParser()
        self.rule_applier = RuleApplier(active_rules)
        self.code_generator = PythonCodeGenerator()

    def convert(self, cpp_code):
        # 1. Parse C++ to Clang AST, then convert to Internal AST
        internal_ast = self.parser.parse(cpp_code)
        
        # 2. Apply all active transformation rules
        modified_ast = self.rule_applier.visit(internal_ast)
        
        # 3. Generate Python code from the modified AST
        python_code = self.code_generator.generate(modified_ast)
        
        return python_code

def main():
    """Defines and handles command-line arguments."""
    
    # Dynamically find all available rule classes from the rules module
    available_rules = {name: cls for name, cls in rule_definitions.__dict__.items() if isinstance(cls, type) and issubclass(cls, rule_definitions.Rule) and cls is not rule_definitions.Rule}
    
    parser = argparse.ArgumentParser(
        description="Terminator: A C++ to Python transpiler.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input", help="Input C++ file or directory.")
    parser.add_argument("-o", "--output", help="Output Python file or directory. If not provided, prints to console.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing to files.")
    parser.add_argument("--show-diff", action="store_true", help="Show a diff of the changes. Implies --dry-run.")
    parser.add_argument(
        "--rules", 
        nargs='*',
        choices=list(available_rules.keys()),
        default=list(available_rules.keys()),
        help=f"Specify which rules to apply. By default, all are active.\nAvailable: {', '.join(available_rules.keys())}"
    )

    args = parser.parse_args()
    
    # Instantiate the selected rules
    active_rule_instances = [available_rules[name]() for name in args.rules]
    
    terminator = Terminator(active_rule_instances)
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    if input_path.is_file():
        process_file(input_path, args, terminator)
    else:
        # Process all .cpp and .h files in the directory
        for file in list(input_path.glob("**/*.cpp")) + list(input_path.glob("**/*.h")):
            process_file(file, args, terminator, base_dir=input_path)

def process_file(file_path, args, terminator, base_dir=None):
    """Handles the conversion logic for a single file."""
    print(f"Processing: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()

        python_code = terminator.convert(original_code)

        if args.show_diff:
            diff = difflib.unified_diff(
                original_code.splitlines(keepends=True),
                python_code.splitlines(keepends=True),
                fromfile=f'a/{file_path.name}',
                tofile=f'b/{file_path.with_suffix(".py").name}'
            )
            print("--- DIFF ---")
            sys.stdout.writelines(diff)
            print("------------")
            return

        if args.dry_run:
            print("--- DRY RUN (Output) ---")
            print(python_code)
            print("------------------------")
            return
        
        if args.output:
            output_path = Path(args.output)
            if base_dir: # Preserve directory structure
                relative_path = file_path.relative_to(base_dir)
                final_output_path = (output_path / relative_path).with_suffix('.py')
                final_output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                final_output_path = output_path
            
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"Successfully converted to: {final_output_path}")

        else: # Print to stdout
            print(python_code)
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()