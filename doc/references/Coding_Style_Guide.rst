..
    _ Copyright (c) 2024 Battelle Memorial Institute
    _ file: Code_References.rst

.. _code_style_guide_label:

Coding Style Guide
==================

PEP 8
*****

TESP largely conforms to `PEP 8`_ with the big exception of line lengths:

- Code can run to 120 characters per line
- Comments must be 79 characters or less per line

The following are a few highlights to serve as a reminder:

Indentation
-----------
Four spaces per level, no tabs

You should be able to configured your editor to type four spaces for you when you hit the tab key.

Binary Operators
----------------
Generally binary operators are surrounded by spaces to clearly indicate the operands. That said, the use of spaces to help indicate order of operations can be helpful in long strings of binary operators. Use your best judgement::

    # Correct:
    i = i + 1
    submitted += 1
    x = x*2 - 1
    hypot2 = x*x + y*y
    c = (a+b) * (a-b)
    
    # Wrong:
    i=i+1
    submitted +=1
    x = x * 2 - 1
    hypot2 = x * x + y * y
    c = (a + b) * (a - b)


If you need to break a long equation across lines, add the line break before the binary operator so that the operator is the first character on each line::

    total = (first_part 
            + second_part
            - third part)



Blank Lines
-----------
- Top level functions and classes have **two** blank lines before and after
- Methods inside a class have **one** blank line before and after
- Use blank lines sparingly to separate logical blocks inside a function or method


Imports
-------
Imports should happen at the top of the file after the docstring for the file.

One imported package per line::

    # Correct:
    import os
    import sys
    

    # Wrong:
    import os, sys


Comments
--------
- Comments should be complete sentences.
- Block comments

    - Block comments before the code they describe.
    - Block comments with multiple paragraphs should have a blank line with a leading "#" between paragraphs.
    - Block comments don't have leading indents.
    
- Inline comments can should be used sparingly and should be brief.
- Space after the "#" before the comment.


Exceptions
----------
When raising exception (such as in "try...except" conditionals), use the built-in exceptions `defined by Python`_.
These exceptions can be sub-classed if needed.



TESP-Specific Style
*******************
The following may be partially borrowed from PEP 8 but are more specific to how TESP is going to do things.

Naming Convention
-----------------
 - **Classes**: CapitalizeEachWord
 - **Variable**: lower_case_using_underscores
 - **Constants**: ALL_CAPS_WITH_UNDERSCORES
 - **Type names**: CapitalizeEachWord


String Quotes
-------------
Use double quotes (" ") for the top level of string literals.


Function Length
---------------
Try to keep a single function's/method's length to something on the order of 40-60 lines. This is roughly a screen's worth of text.

Shorter functions are generally preferable as they increase comprehension of the code. Long functions present a number of challenges:

- Long functions tend to require the reader to retain more comprehension in their mind simultaneously
- Long functions tend to require more scrolling through the file
- Long functions tend to obfuscate functionality 

Generally, breaking longer functions up into smaller functional blocks tends to solve these problems: it labels the functionality with a (hopefully) descriptive name, it shortens up the length of the function and reduces the mental load required to understand the function.


Docstrings and Type-Hinting
---------------------------
Every module (file) class, and function/method needs a docstring at it's beginning. `PEP 257_` provides guidance. Additionally, we use `PEP 484_` to provide type hinting in the function signature; this allows to omit them as an explicit portion of the docstring. We use a parser that reads the function/method signature and docstring to auto-generate API documentation 

The docstring should provide users of the function/method sufficient understanding to allow them to use it effectively. They also help developers who need to maintain or trouble-shoot the code at some future time. 

Docstrings start with three double-quotes (""") with the documentation prose beginning on the same line::

    def total_weight(car_weight: float, cargo_weight: float) -> float:
        """Find the total weight by adding the weight of the car and cargo.""""
      
For multi-line comments::

    def total_weight(car_weight: float, cargo_weight: float) -> float:
        """Find the total weight by adding the weight of the car and cargo.
        This is not a complicated operation but worth calling out as an explicit
        function so that more complicated versions can be implemented in the
        future.
        """"

    # Blank line above; this is the first line of the code




.. _defined by Python: https://docs.python.org/3/library/exceptions.html
.. _PEP 8: https://peps.python.org/pep-0008/
.. _PEP 257: https://peps.python.org/pep-0257/
.. _PEP 484: https://peps.python.org/pep-0257/