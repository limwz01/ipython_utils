import logging

from ipython_utils.core import (_ipy_magic_inner, embed, embed2,
                                try_all_statements)

L = logging.getLogger("ipython_utils." + __file__)
some_global = "global"


def main():
    logging.basicConfig(
        format=
        "%(asctime)s;%(funcName)s;%(module)s;%(lineno)s;%(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.WARNING)
    logging.getLogger("_").setLevel(logging.DEBUG)
    L.info("script %s args %s", __file__, sys.argv)
    script_dir = os.path.dirname(os.path.realpath(__file__))

    embed()
    print("embed2")
    embed2()
    test_embed()
    print("embed2")
    test_embed2()
    test_try()
    test_try_and_embed()
    test_params()


def test_embed():

    x0 = 0  # not closed over
    x1 = 1  # used only in `f`
    x2 = 2  # used in `f` and `g`

    def f(y0, y1):
        y0: int  # not closed over
        y1: int = y0 + y1  # used in `g`
        y2: int = y1 + 1  # only closed over by embed
        nonlocal x1
        nonlocal x2

        def g():
            nonlocal x2, y1
            x2 += 10
            y1 += 10

        x1, x2, y0, y1, y2 = [x + 100 for x in [x1, x2, y0, y1, y2]]
        print(x1, x2, y0, y1, y2)
        # passing the enclosing function allows variables from the parent scopes
        # which were closed over to be accessed and modified (x and y)
        # note that none of the shell will see `x0`
        embed(f)
        # run: x1, x2, y0, y1, y2 = [x + 100 for x in [x1, x2, y0, y1, y2]]; g()
        x1, x2, y0, y1, y2 = [x + 100 for x in [x1, x2, y0, y1, y2]]
        print(x1, x2, y0, y1, y2)
        # passing a closure over local variables allow the specified variables
        # to be accessed and modified (y1 and y2)
        embed([f, lambda: (y1, y2)])
        # run: x1, x2, y0, y1, y2 = [x + 100 for x in [x1, x2, y0, y1, y2]]; g()
        x1, x2, y0, y1, y2 = [x + 100 for x in [x1, x2, y0, y1, y2]]
        print(x1, x2, y0, y1, y2)

    f(3, 1)
    print(x0, x1, x2)


def test_embed2():

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
        embed2()
        # run: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)
        # passing a closure over local variables allow the specified variables
        # to be accessed and modified (y0 and w)
        embed2()
        # run: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)

    f(3, 1)
    print(x0, x1, x2)


def test_try():

    @try_all_statements
    def f(x):
        print(x)
        # editing the below statement to `x = 1 / (x + 1)` after the exception
        # is raised will allow it to continue
        x = 1 / x  # (x + 1)
        if x == 1:
            print("x is 1")
            return
        assert x != 1
        print(x)

    f(1)
    # the below raises an exception
    f(0)
    # subsequent calls use the modified function
    f(1)
    f(0)


def test_try_and_embed():

    x0 = 0  # not closed over
    x1 = 1  # used only in `f`
    x2 = 2  # used in `f` and `g`

    @try_all_statements
    def f(y0, y1):
        y0: int  # not closed over
        y1: int = y0 + y1  # used in `g`
        nonlocal x1
        nonlocal x2

        @try_all_statements
        def g():
            nonlocal x2, y1
            x2 += 10
            y1 += 10

        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)
        # passing the enclosing function allows variables from the parent scopes
        # which were closed over to be accessed and modified (x and y)
        # note that none of the shell will see `x0`
        embed(funcs=[_ipy_magic_inner])
        # run: x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]; g()
        x1, x2, y0, y1 = [x + 100 for x in [x1, x2, y0, y1]]
        print(x1, x2, y0, y1)

    f(3, 1)
    print(x0, x1, x2)


def test_params():

    @try_all_statements
    def f(x0, /, x1, x2=12, *args, x3, **kwargs):
        print(x0, x1, x2, x3, args, kwargs)

    f(0, 1, x3=3)
    f(0, 1, 2, x3=3)
    f(0, 1, 2, 5, x3=3)
    f(0, 1, 2, 5, x3=3, x4=4)

    @try_all_statements
    def f(x0=10, /, x1=11, x2=12, *args, x3, **kwargs):
        print(x0, x1, x2, x3, args, kwargs)

    f(x3=3)
    f(0, x3=3)
    f(0, 1, x3=3)
    f(0, 1, 2, x3=3)
    f(0, 1, 2, 5, x3=3)
    f(0, 1, 2, 5, x3=3, x4=4)

    @try_all_statements
    def f(x0=10, /, x1=11, x2=12, *args, x3=13, **kwargs):
        print(x0, x1, x2, x3, args, kwargs)

    f(x3=3)
    f(0, x3=3)
    f(0, 1, x3=3)
    f(0, 1, 2, x3=3)
    f(0, 1, 2, 5, x3=3)
    f(0, 1, 2, 5, x3=3, x4=4)
    f()
    f(0)
    f(0, 1)
    f(0, 1, 2)
    f(0, 1, 2, 5)
    f(0, 1, 2, 5, x4=4)


if __name__ == "__main__":
    main()
