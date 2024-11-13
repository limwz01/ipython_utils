# ipython_utils

Utilities to make developing Python responsive and interactive using fully powered shells directly embedded at the target location or exception site, or dynamically reloading updated code

## Introduction

Sometimes you develop a complex Python software with multiple modules and functions. Jupyter notebooks are messy and hinder refactoring into functions, encouraging bad programming practices, so you decide against using them. But there is nothing as convenient as having a shell to directly inspect the objects and having additions to your existing code applied on live objects immediately! **Now, you can!**

## Installation

Ever since I've packaged this and published it on PyPI (https://pypi.org/project/ipython-utils/), you can just run `pip install ipython_utils`. After installation, the following should work:

```python3
from ipython_utils import embed
def outer_function():
    x = 0
    def target_function():
        print(x)
        y1 = 1
        y2 = 2
        y3 = 3
        y4 = 4
        def g():
            print(y1)
        embed() # no local variable persistence
        embed(target_function) # x can be updated, as target_function was closed over x
        print(x, y1, y2, y3, y4)
        embed([target_function, g]) # y1 can also be updated, as g was closed over y1
        print(x, y1, y2, y3, y4)
        # we can easily force a closure over y2 and y3, and pass it to embed,
        # allowing it to update y2 and y3
        embed([target_function, lambda: (y2, y3)])
    return target_function
```

## Limited functionality in default IPython embedded shell

An existing method is to call `IPython.embed()` at the end of your partially developed code. But the embedded IPython shell is quite limited, because executing dynamically compiled Python code must always have a specific `locals()` dictionary, and updates to `locals()` rarely causes an update of local variables (except perhaps in old Python versions). The default shell just has a copy of the local variables, and existing closures over them will not update the value of the copy. More importantly, all child functions and lambdas do not close over the local variables, instead leaving them as unresolved global names, which means even list comprehensions which use these [do not work](https://github.com/cknoll/ipydex/issues/3). This is shown in the small snippet below:

```python3
def test_ipython():
    x = 0
    y = 1
    def f(z, w):
        nonlocal y
        def g():
            nonlocal w
            w += 10
        y += 20
        print(x, y, z, w)
        IPython.embed()
    f(2, 3)
test_ipython()
```

```
0 21 2 3
Python 3.8.10 (default, Nov 22 2023, 10:22:35) 
Type 'copyright', 'credits' or 'license' for more information
IPython 8.10.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: x, y, z, w
Out[1]: (0, 21, 2, 3)

In [2]: g()

In [3]: x, y, z, w
Out[3]: (0, 21, 2, 3)

In [4]: (lambda: x)()
...
NameError: name 'x' is not defined

In [5]: [x for i in range(10)]
...
NameError: name 'x' is not defined

In [6]: t = 1; [t for i in range(10)]
...
NameError: name 't' is not defined
```

There are a few workarounds for this, when embedding into the scope of a function `f`:
1. Use a mocked-up `globals()` including what was in `locals()`
1. Use the real `globals()` and copy over `locals()` into the real `globals()`

Both of the above require us to patch all the `nonlocal` statements referring to locals in the scope of `f` (and parent functions) to become `global`. In the first workaround, we use IPython with a `globals()` namespace that have been updated with both the original frame's `globals()` and `locals()`, either by running `IPython.start_ipython` with `user_ns` as the mocked-up `globals()` or patching `IPython.terminal.embed.InteractiveShellEmbed` (instead of this, one could possibly keep calling `globals().update(locals())` for every statement executed but that is really inefficient and only works if the created child functions do not modify the referenced variables). In this workaround, references to real globals in created functions will no longer access/modify the real global variable, but a copy, hence diverging from functions created by other means which use the real globals. In the second workaround, the real global namespace gets polluted and globals might have their values incorrectly overwritten by the locals, causing some existing functions to behave incorrectly.

## An almost perfect embedded shell

Recognising the need for code to "just work" when pasting it unedited into the shell, we developed a novel way to wrap the code such that we are able to edit the closure of each wrapper such that they all use the same [variable cells](https://docs.python.org/3/c-api/cell.html), hence they would access and modify the same variable. We even allow embedded shells to make permanent modifications to variables under certain conditions. More details are presented in the docs for the API. The following showcases some features:

```python3
def test_embed():

    x0 = 0  # not closed over
    x1 = 1  # used only in `f`
    x2 = 2  # used in `f` and `g`

    def f(y0, y1):
        y0: int  # not closed over
        y1: int = y0 + y1  # used in `g`
        nonlocal x1
        nonlocal x2

        def g():
            nonlocal x2, y1
            x2 += 10
            y1 += 10

        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)
        # passing the enclosing function allows variables from the parent scopes
        # which were closed over to be accessed and modified (x1 and x2)
        # note that none of the shell will see `x0`
        embed(funcs=[f])
        # run: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)
        # passing a closure over local variables allow the specified variables
        # to be accessed and modified (y0 and y1)
        embed(funcs=[f, lambda: (y0, y1)])
        # run: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)

    f(3, 1)
    print(x0, x1, x2)
```

```
101 102 103 104
...
In [1]: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
...
301 312 203 214
...
In [1]: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
...
501 522 403 424
0 501 522
```

## Exception hook

In order to inspect the live objects at the point of an exception, we can add a exception handler in `sys.excepthook` using our utility `add_except_hook`, and embedding a shell using the right frame's locals and globals will allow you to quickly figure out what went wrong. However, in general uncaught exceptions are problematic because it is hard to resume the execution. It is surprising that IPython manages to handle exceptions raised in the dynamic code gracefully, and we can make use of this feature, as we remarked at the start of the next section.

## Reloading after an exception

If your program does a lot of computation, and you are only modifying/developing a small piece, you would not want to keep restarting it just because many bugs with this small piece keep causing exceptions, which are generally unrecoverable in Python. However, if you have a perfect embedded shell, there is a workflow that can save you much time when editing a function. Every time you make an edit to a line (say line `i`), it may or may not cause an exception in lines `i` and onwards. You position an `embed()` to before line `i`, run the program, and when the shell appears, paste in all of the code from line `i` onwards. If it causes an exception on line `j`, you modify the code and paste in all the code from line `j` onwards. Repeat this process until there is no exception.

As this copying and pasting process is still tedious, we made it even easier, just decorate a function with `try_all_statements`, and the function will be split into statements to be run one-by-one. If any of them raises an exception, one can either drop into a shell (e.g. by entering 0 in place of the line number; see docs) to inspect the variables, or simply edit the original source code of the function and rerun starting from a certain statement onwards.

```python3
def test_try():

    @try_all_statements
    def f(x):
        print(x)
        # editing the below statement to `x = 1 / (x + 1)` after the exception
        # is raised will allow it to continue
        x = 1 / x  # (x + 1)
        print(x)

    f(1)
    # the below raises an exception
    f(0)
    # subsequent calls use the modified function
    f(1)
    f(0)
```

```
1
1.0
0
2024-07-03 13:02:56;runner;ipython_utils;759;INFO: exception raised
Traceback (most recent call last):
  File "/working/ipython_utils/ipython_utils.py", line 757, in runner
    ret = patched(i)
  File "/working/ipython_utils/ipython_utils.py", line 1026, in f
    x = 1 / x  # (x + 1)
ZeroDivisionError: division by zero
filename [/working/ipython_utils/ipython_utils.py]: # after editing
function line num [1022]:
next statement line num [1026]:
1.0
1
0.5
0
1.0
```

We provide a magic variable `_ipy_magic_inner` to access the inner function which has the closure for all the local variables. This allows you to always be able to embed a shell within a `try_all_statements`-decorated function to modify any of the local variables as follows:

```python3
@try_all_statements
def f():
    # ...
    embed(_ipy_magic_inner)
    # changes to local variables will be persistent
```
