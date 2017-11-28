#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper, reduce, wraps


def disable(deco):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''

    def wrapped(func):
        return func
    return wrapped


def decorator(deco):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''

    def wrapped(func):
        return update_wrapper(deco(func), func)
    update_wrapper(wrapped, deco)
    return wrapped


@decorator
def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''

    def wrapped(*args):
        wrapped.calls += 1
        return func(*args)
    wrapped.calls = 0
    return wrapped


@decorator
#@disable
def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    cache = {}

    def wrapper(*args):
        update_wrapper(wrapper, func)
        if str(args) in cache:
            return cache[str(args)]
        else:
            res = cache[str(args)] = func(*args)
            return res
    return wrapper


@decorator
def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''

    def wrapper(*args):
        if len(args) == 1:
            return args[0]
        else:
            res = func(args[0], wrapper(*args[1:]))
        return res
    return wrapper


@decorator
def trace(decor_arg):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    def trace_decorator(func):
        @wraps(func)
        def wrapper(*args):
            print("{} --> {}({})".format(decor_arg * wrapper.depth, func.__name__, ", ".join(str(arg) for arg in args)))
            wrapper.depth += 1
            res = func(*args)
            wrapper.depth -= 1
            print("{} <-- {}({}) == {}".format(decor_arg * wrapper.depth, func.__name__,
                                               ", ".join(str(arg) for arg in args), res))
            return res
        wrapper.depth = 0
        return wrapper
    return trace_decorator


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, 'calls made')

if __name__ == '__main__':
    main()
