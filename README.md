# Terminator: A C++ to Python Modernizer

**Terminator** is an experimental, rule-based transpiler that converts C++ source code into modern, idiomatic Python. Inspired by tools like [Rector](https://getrector.com/) for PHP, Terminator uses a robust Abstract Syntax Tree (AST)-based approach to ensure accurate and extensible code transformations, avoiding fragile regex-based methods.

The primary goal of Terminator is to provide a flexible and developer-friendly framework for converting C++ code to Python, with an extensible rule system that allows users to add new transformation rules for various C++ patterns and idioms.

---

## 🏛️ Architecture & Core Concept

Terminator operates on a structured, multi-stage pipeline to transform C++ code into Python. By leveraging the power of `libclang` and a custom AST, it ensures semantic accuracy and maintainability.

**Workflow:**

```
C++ Source → [Clang Parser] → C++ AST → [AST Converter] → Internal AST → [Rule Engine] → Modified AST → [Code Generator] → Python Source
```

1. **Parse**: The C++ source code is parsed into a detailed Abstract Syntax Tree (AST) using `libclang`, the library behind the Clang compiler. This provides a deep, semantic understanding of the code structure.
2. **Convert**: The complex `libclang` AST is transformed into a simplified, custom **Internal AST**. This intermediate representation is language-agnostic or closer to Python concepts, making it easier to process.
3. **Apply Rules**: A **Traverser** walks the Internal AST and applies a set of active **Rules**. Each rule is an independent unit of logic designed to transform specific C++ patterns (e.g., a C-style `for` loop) into their Python equivalents.
4. **Generate Code**: A **Pretty Printer** traverses the modified AST and generates clean, idiomatic, and properly formatted Python code.

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.8 or higher.
- **libclang**: The Clang library for parsing C++ code. Install it via pip:
  ```bash
  pip install libclang
  ```

### Installation

1. Clone the Terminator repository:
   ```bash
   git clone https://github.com/omidkarami1337/terminator.git
   cd terminator
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

Terminator is a command-line tool with flexible options for converting C++ code to Python.

```bash
# Convert a single file and print the output to the console
python terminator.py path/to/file.cpp

# Convert a single file and save the output to a specified file
python terminator.py path/to/file.cpp -o output.py

# Convert an entire directory, preserving the directory structure
python terminator.py ./src/ -o ./output/

# Perform a dry run (preview changes without writing files)
python terminator.py path/to/file.cpp --dry-run

# Show a diff of the changes (implies --dry-run)
python terminator.py path/to/file.cpp --show-diff

# Run with specific rules only (e.g., convert for loops to Python range)
python terminator.py path/to/file.cpp --rules ForLoopToRangeRule
```

### Example Conversion

Below is an example of how Terminator transforms C++ code into Python.

**Sample C++ Input (`sample.cpp`)**:
```cpp
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
```

**Generated Python Output**:
```python
def greet() -> None:
    for i in range(5):
        print(f"Hello, Terminator! Iteration: {i}")

def main() -> int:
    greet()
    return 0

if __name__ == "__main__":
    main()
```

---

## 🔧 Extending Terminator: Adding New Rules

Terminator is designed to be easily extensible. Developers can add new transformation rules to handle additional C++ patterns.

### Steps to Add a New Rule

1. **Open `rules.py`**: This file contains all rule definitions.

2. **Create a New Rule Class**: Define a class that inherits from the base `Rule` class.

   ```python
   from terminator import ast, Rule

   class MyNewGuidelineRule(Rule):
       # Your rule logic goes here
       pass
   ```

3. **Implement the `visit` Method**: This method processes an AST node. Check if the node matches the pattern you want to transform. If it matches, return a new, transformed node; otherwise, return the original node unchanged.

   **Example Rule: Converting C-Style Casts to Python**
   ```python
   class CStyleCastToPythonCast(Rule):
       def visit(self, node):
           # Check for C-style casts, e.g., `(int)some_var`
           if not isinstance(node, ast.CallExpr):
               return node  # Not a call expression, so no transformation

           # Check if the "function" being called is a type name (e.g., `int`)
           if isinstance(node.callee, ast.Identifier) and node.callee.name == "int":
               # Transform `(int)some_var` to `int(some_var)`
               return ast.CallExpr(
                   callee=ast.Identifier("int"),
                   args=node.args
               )

           return node  # Return unchanged node if no transformation applies
   ```

4. **Automatic Rule Registration**: Terminator automatically discovers all `Rule` subclasses in `rules.py`. Your new rule can be activated via the CLI using `--rules MyNewGuidelineRule` or will run by default if no specific rules are specified.

---

## 🛠️ Supported Transformations

Terminator currently supports the following transformations (more can be added via custom rules):

- Converting C++ `for` loops to Python `range`-based loops.
- Transforming C-style casts (e.g., `(int)x`) to Python casts (e.g., `int(x)`).
- Converting `std::cout` output statements to Python `print` calls.
- Adding Python-style `if __name__ == "__main__":` guards for `main` functions.
- Mapping C++ function signatures to Python with type hints (where applicable).

See `rules.py` for the full list of available rules.

---

## 📚 Limitations

- **Incomplete C++ Support**: Terminator is experimental and does not yet support the full C++ language (e.g., templates, pointers, or complex class hierarchies).
- **Idiomatic Python**: While Terminator aims for idiomatic Python, some transformations may require manual adjustment for optimal readability or performance.
- **Error Handling**: Invalid C++ code may cause parsing errors. Ensure your input code is syntactically correct.

---

## 🤝 Contributing

We welcome contributions to make Terminator more robust and feature-complete! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/my-new-feature`).
3. Add your changes, such as new rules or improvements to the core pipeline.
4. Write tests to validate your changes (see `tests/` directory).
5. Submit a pull request with a clear description of your changes.

Please follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).

---

## 📜 License

Terminator is licensed under the [MIT License](LICENSE). See the `LICENSE` file for details.

---

## 📬 Contact

For questions, suggestions, or bug reports, please open an issue on the [GitHub repository](https://github.com/omidkarami1337/terminator) or contact the maintainer at [omidkaramibio@gmail.com](mailto:omidkaramibio@gmail.com).

---

**Written by Omid Karami**  
Happy transpiling! 🚀
