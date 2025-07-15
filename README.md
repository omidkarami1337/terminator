# Terminator: A C++ to Python Modernizer

**Terminator** is an experimental, rule-based transpiler designed to convert C++ source code into modern, idiomatic Python. It is heavily inspired by tools like [Rector](https://getrector.com/) for PHP, focusing on a robust, AST-based approach to code transformation rather than simple text replacement.

The primary goal of Terminator is to provide an extensible framework where developers can easily add new conversion rules to handle more C++ patterns and idioms over time.

---

## 🏛️ Architecture & Core Concept

Terminator avoids fragile regular expressions and operates on a structured representation of the code. The conversion process is a multi-stage pipeline, ensuring accuracy and extensibility.

**Workflow:**

C++ Source -> [Clang Parser] -> C++ AST -> [AST Converter] -> Internal AST -> [Rule Engine] -> Modified AST -> [Code Generator] -> Python Source


1.  **Parse:** The C++ code is first parsed into a detailed Abstract Syntax Tree (AST) using `libclang`, the library behind the Clang compiler. This gives us a deep, semantic understanding of the code.
2.  **Convert:** The complex `libclang` AST is converted into a simpler, custom *Internal AST*. The nodes of this tree are designed to be language-agnostic or closer to Python's concepts, making them easier to work with.
3.  **Apply Rules:** A **Traverser** walks the Internal AST. At each node, it applies a set of active **Rules**. Each rule is a small, independent unit of logic that knows how to transform a specific pattern (e.g., a C-style `for` loop). If a rule finds a match, it transforms the AST node into its Python equivalent.
4.  **Generate Code:** After all rules have been applied, a **Pretty Printer** walks the final, modified AST and generates clean, formatted Python code.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.8+
-   The `libclang` library. You can install it via pip:
    ```bash
    pip install libclang
    ```

### Usage

The tool is run from the command line.

```bash
# Convert a single file and print to the console
python terminator.py path/to/your/file.cpp

# Convert a single file and save the output
python terminator.py file.cpp -o new_file.py

# Convert an entire directory, preserving the structure
python terminator.py ./src/ -o ./output/

# Perform a dry run without writing any files
python terminator.py file.cpp --dry-run

# Show a diff of the changes (implies --dry-run)
python terminator.py file.cpp --show-diff

# Run with only specific rules active
python terminator.py file.cpp --rules ForLoopToRangeRule
📝 Example Conversion
Here is a simple example of what Terminator can do.

Sample C++ Input (sample.cpp)
C++

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
Generated Python Output
Python

def greet() -> None:
    for i in range(5):
        print("Hello, Terminator! Iteration: ", i)


def main() -> int:
    greet()
    return 0


if __name__ == "__main__":
    main()
🔧 How to Add a New Rule
Terminator is designed for easy extension. To add a new transformation rule:

Open rules.py: This file contains all rule definitions.

Create a New Rule Class: Define a new class that inherits from the base Rule class.

Python

from terminator import ast, Rule

class MyNewGuidelineRule(Rule):
    # ...
Implement the visit Method: This is the core of your rule. The method receives an AST node. Your job is to check if this node matches the pattern you want to transform.

If it does not match, return the node unchanged.

If it does match, create and return a new, transformed node.

Python

class CStyleCastToPythonCast(Rule):
    def visit(self, node):
        # We are looking for C-style casts, which clang often parses as
        # a CallExpr to a type. This is a simplified example.
        if not isinstance(node, ast.CallExpr):
            return node # Not a call, so we don't care.

        # Check if the "function" being called is a type name
        if isinstance(node.callee, ast.Identifier) and node.callee.name == "int":
            # It's a cast like `(int)some_var`. Transform it to `int(some_var)`
            # which is conveniently also a CallExpr.
            # Here, we just ensure the callee is `int` and not `(int)`.

            # Create a new node representing `int(arg)`
            return ast.CallExpr(
                callee=ast.Identifier("int"),
                args=node.args
            )

        return node # Return original node if no transformation was made
The Rule is Automatically Registered: Terminator automatically discovers all Rule subclasses in rules.py. You can now activate it via the CLI with --rules CStyleCastToPythonCast or it will run by default if you don't specify any rules.

**WrittenbyOmidKarami**