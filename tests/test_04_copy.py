""" test copying PGP objects
"""
from __future__ import print_function
import pytest

import copy
import glob
import inspect
import os.path

import six

import pgpy

from pgpy import PGPSignature, PGPUID, PGPMessage, PGPKey



def sig():
    return PGPSignature.from_file('tests/testdata/blocks/rsasignature.asc')

def uid():
    return PGPUID.new('Abraham Lincoln', comment='Honest Abe', email='abraham.lincoln@whitehouse.gov')

def msg():
    return PGPMessage.from_file('tests/testdata/messages/message.signed.asc')

def key(fn):
    key, _ = PGPKey.from_file(fn)
    return key

def walk_obj(obj, prefix=""):
    from enum import Enum

    for name, val in inspect.getmembers(obj):
        if hasattr(obj.__class__, name):
            continue

        yield '{}{}'.format(prefix, name), val

        if not isinstance(val, Enum):
            for n, v in walk_obj(val, prefix="{}{}.".format(prefix, name)):
                yield n, v


_keys = glob.glob('tests/testdata/keys/*.1.pub.asc') + glob.glob('tests/testdata/keys/*.1.sec.asc')


class TestCopy(object):
    params = {
        'obj': [sig(), uid(), msg()] + [ key(fn) for fn in _keys ],
    }
    ids = {
        'test_copy_obj': ['sig' , 'uid', 'msg'] + [ '-'.join(os.path.basename(fn).split('.')[:3]) for fn in _keys ],
    }

    @staticmethod
    def check_id(obj):
        from datetime import datetime
        from enum import Enum

        # do some type checking to determine if we should check the identity of an object member
        # these types are singletons
        if isinstance(obj, (Enum, bool, type(None))):
            return False

        # these types are immutable
        if isinstance(obj, (six.string_types, datetime)):
            return False

        # integers are kind of a special case.
        #   ints that do not exceed sys.maxsize are singletons, and in either case are immutable
        #   this shouldn't apply to MPIs, though, which are subclasses of int
        if isinstance(obj, int) and not isinstance(obj, pgpy.packet.types.MPI):
            return False

        return True

    @staticmethod
    def ksort(key):
        # return a tuple of key, key.count('.') so we get a descending alphabetical, ascending depth ordering
        return key, key.count('.')


    def test_copy_obj(self, request, obj):
        obj2 = copy.copy(obj)

        objflat = {name: val for name, val in walk_obj(obj, '{}.'.format(request.node.callspec.id))}
        obj2flat = {name: val for name, val in walk_obj(obj2, '{}.'.format(request.node.callspec.id))}

        for k in sorted(objflat, key=self.ksort):
            print("checking attribute: {} ".format(k), end="")
            if isinstance(objflat[k], pgpy.types.SorteDeque):
                print("[SorteDeque] ", end="")
                assert len(objflat[k]) == len(obj2flat[k])

            if not isinstance(objflat[k], (pgpy.types.PGPObject, pgpy.types.SorteDeque)):
                print("[{} ]".format(type(objflat[k])), end="")
                assert objflat[k] == objflat[k], k

            # check identity, but only types that should definitely be copied
            if self.check_id(objflat[k]):
                print("[id]")
                assert objflat[k] is not obj2flat[k], "{}: {}".format(type(objflat[k]), k)

            else:
                print()