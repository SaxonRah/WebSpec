# WebSpec DSL for Visual Studio Code

Syntax highlighting, code snippets, and language support for the
[WebSpec](https://github.com/SaxonRah/WebSpec) browser testing DSL.

## Features

- Full syntax highlighting for `.ws` files
- 30+ code snippets for common patterns
- Auto-indent for block constructs (if/repeat/for/try/define/using)
- Bracket matching and auto-closing for quotes and parentheses
- Code folding for all block constructs
- Comment toggling with `Ctrl+/`

## Installation

### From VSIX (local installation)

    cd webspec-vscode
    npx vsce package
    code --install-extension webspec-dsl-1.0.0.vsix

### Development mode

    # Symlink into VS Code extensions
    # Windows:
    mklink /D "%USERPROFILE%\.vscode\extensions\webspec-dsl" "E:\WebSpec\webspec-vscode"

    # macOS/Linux:
    ln -s /path/to/webspec-vscode ~/.vscode/extensions/webspec-dsl

    # Then reload VS Code (Ctrl+Shift+P → "Reload Window")

## Snippet Prefixes

| Prefix    | Snippet                        |
|-----------|--------------------------------|
| `nav`     | Navigate to URL                |
| `click`   | Click element                  |
| `type`    | Type into input near label     |
| `typepl`  | Type into input by placeholder |
| `sel`     | Select dropdown option         |
| `check`   | Check checkbox                 |
| `vvis`    | Verify visible                 |
| `vtext`   | Verify text content            |
| `vcon`    | Verify contains                |
| `vurl`    | Verify URL                     |
| `vtitle`  | Verify title                   |
| `vcnt`    | Verify count                   |
| `setvar`  | Set variable                   |
| `settext` | Set variable from text         |
| `setcnt`  | Set variable from count        |
| `log`     | Log message                    |
| `logv`    | Log variable                   |
| `wait`    | Wait seconds                   |
| `waitfor` | Wait for element               |
| `waiturl` | Wait until URL                 |
| `if`      | If-then block                  |
| `ifelse`  | If-then-else block             |
| `repeat`  | Repeat N times                 |
| `while`   | Repeat while                   |
| `foreach` | For-each loop                  |
| `try`     | Try-catch block                |
| `define`  | Define subroutine              |
| `call`    | Call subroutine                |
| `using`   | Data-driven block              |
| `import`  | Import script                  |
| `ss`      | Take screenshot                |
| `exec`    | Execute JavaScript             |
| `frame`   | Switch to/from iframe          |
| `key`     | Press keyboard key             |
| `login`   | Full login flow template       |
| `wstest`  | Complete test template         |

## Color Scopes

The grammar assigns semantic scopes for theme customization:

| Scope                          | What it highlights                 |
|--------------------------------|------------------------------------|
| `keyword.control.navigation`   | navigate, go back, refresh         |
| `keyword.action.*`             | click, type, select, check, scroll |
| `keyword.assertion`            | verify                             |
| `keyword.control.wait`         | wait, seconds                      |
| `keyword.control.flow`         | if, then, else, end                |
| `keyword.control.loop`         | repeat, for, each, while, times    |
| `keyword.control.trycatch`     | try, on error                      |
| `keyword.definition`           | define                             |
| `keyword.call`                 | call                               |
| `keyword.control.data`         | using                              |
| `keyword.control.import`       | import                             |
| `keyword.selector.*`           | with, near, inside, above, below   |
| `entity.name.type.element`     | button, link, input, heading, etc. |
| `constant.language.visibility` | visible, hidden, enabled, etc.     |
| `variable.other`               | $varname, ${varname}               |
| `constant.numeric`             | 42, 3.14                           |
| `constant.numeric.ordinal`     | 1st, 2nd, 3rd                      |
| `string.quoted`                | "strings", 'strings'               |
| `comment.line`                 | # comments                         |

---

# Install & Test
## Option 1: Symlink for development
    ### Windows (run as admin):
    `mklink /D "%USERPROFILE%\.vscode\extensions\webspec-dsl" "E:\WebSpec\webspec-vscode"`

## Option 2: Copy the folder
    `xcopy /E /I webspec-vscode "%USERPROFILE%\.vscode\extensions\webspec-dsl"`

### Then reload VS Code: Ctrl+Shift+P → "Developer: Reload Window"
### Open any .ws file - syntax highlighting and snippets are active