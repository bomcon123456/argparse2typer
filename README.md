# argparse2typer
## Use case
- Do you ever need to work on an open source project and find that they use argparse? Nothing's wrong with argparse but you have already been falling in love with `typer` CLI (you all will someday)?
- Fear no more, just use `argparse2typer` and all the argparse code would be parsed into `typer` CLI with as little changes as possible.

## Installation
- With pip:
```
pip install argparse2typer
```

## Usage
1. Locate the line `args = parser.parse_args()` in the original script
2. Import the function `from argparse2typer import argparse2typer`
3. Run the function before `parse_args`:
```
argparse2typer(parser) # <- new line
args = parser.parse_args()
```
4. New file will be created with the typer CLI format!
