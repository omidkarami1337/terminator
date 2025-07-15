Terminator: A C++ to Python Modernizer
Terminator is an experimental, rule-based transpiler designed to convert C++ source code into modern, idiomatic Python.
Inspired by tools like Rector for PHP, Terminator relies on an AST-based semantic transformation approach instead of simple text replacement.

The primary goal of Terminator is to provide an extensible framework that allows developers to easily add new conversion rules to handle more C++ patterns and idioms over time.

🏛️ Architecture & Core Concepts
Terminator avoids fragile regular expressions and works on a structured representation of the code.
The conversion process is a multi-stage pipeline ensuring accuracy and extensibility.

🔷 Workflow:
C++ Source
→ [Clang Parser]
→ C++ AST
→ [AST Converter]
→ Internal AST
→ [Rule Engine]
→ Modified AST
→ [Code Generator]
→ Python Source

Stages:
Parse:
The C++ code is parsed into a detailed Abstract Syntax Tree (AST) using libclang.

Convert:
The complex libclang AST is converted into a simpler, custom Internal AST designed to be closer to Python concepts.

Apply Rules:
A traverser walks the Internal AST and applies active Rules at each node. Each Rule is a small, independent logic unit that transforms matched patterns into their Python equivalents.

Generate Code:
After all rules are applied, a Pretty Printer generates clean, formatted Python code from the modified AST.

🚀 Getting Started
Prerequisites:
Python 3.8 or higher

libclang library

Install libclang via pip:

pip install libclang

📋 Usage
Run from the command line:

# Convert a single file and print to console
python terminator.py path/to/your/file.cpp

# Convert a single file and save output
python terminator.py file.cpp -o new_file.py

# Convert an entire directory, preserving structure
python terminator.py ./src/ -o ./output/

# Perform a dry run without writing files
python terminator.py file.cpp --dry-run

# Show a diff of changes (implies --dry-run)
python terminator.py file.cpp --show-diff

# Run with only specific rules active
python terminator.py file.cpp --rules ForLoopToRangeRule

📝 Example Conversion
🎯 Sample C++ Input (sample.cpp):

#include <iostream>
#include <string>

void greet() {
    for (int i = 0; i < 5; ++i) {
        std::cout << "Hello, Terminator! Iteration: " << i << std::endl;
    }
}

int main() {
    greet();
    return 0;
}

🔷 Generated Python Output:

def greet() -> None:
    for i in range(5):
        print("Hello, Terminator! Iteration: ", i)


def main() -> int:
    greet()
    return 0


if __name__ == "__main__":
    main()

🔧 How to Add a New Rule
Terminator is designed for easy extensibility.

Steps:

Open rules.py which contains all rule definitions.

Create a new class inheriting from the base Rule class.

Example:

from terminator import ast, Rule

class CStyleCastToPythonCast(Rule):
    def visit(self, node):
        if not isinstance(node, ast.CallExpr):
            return node  # Not matched

        if isinstance(node.callee, ast.Identifier) and node.callee.name == "int":
            # Transform (int)some_var to int(some_var)
            return ast.CallExpr(
                callee=ast.Identifier("int"),
                args=node.args
            )

        return node

Notes:

The visit method is the core of the rule.

Return the original node if it does not match.

Return a new transformed node if it matches.

All Rule subclasses are automatically registered.

Activate your new rule with --rules YourRuleName or let it run by default.

Written by Omid Karami
