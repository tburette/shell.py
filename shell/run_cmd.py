#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import shlex
from subprocess import Popen
from subprocess import PIPE

from .compat import basestring
from .util import str_to_pipe, check_attrs


class RunCmd():
    def __init__(self, cmd_str, input_pipe=None, through_shell = True):
        self.cmd_str = cmd_str
        self.cmd_p = None
        if input_pipe:
            self.input_pipe = input_pipe
        else:
            self.input_pipe = None
        self.std = {'out': None, 'err': None}
        self.through_shell = through_shell

    def get_cmd_lst(self):
        # handle '~'
        lst = [os.path.expanduser(c) for c in shlex.split(self.cmd_str)]
        # @TODO handle env var  03.04 2014 (houqp)
        return lst

    def init_popen(self):
        if self.cmd_p is None:
            args = self.cmd_str if self.through_shell else self.get_cmd_lst()
            shell = self.through_shell
            self.cmd_p = Popen(
                args,
                stdin=self.input_pipe, stdout=PIPE, stderr=PIPE, 
                shell=shell)
        return self

    def get_popen(self):
        return self.init_popen().cmd_p

    def p(self, cmd):
        # @TODO check cmd
        in_pipe = None
        if self.std['out']:
            # command has already been executed, get output as string
            in_pipe = str_to_pipe(self.std['out'])
        else:
            cmd_p = self.get_popen()
            in_pipe = cmd_p.stdout
        # cmd_p.stdout.close() # allow cmd_p to receive SIGPIPE?
        return RunCmd(cmd, input_pipe=in_pipe)

    def wait(self):
        cmd_p = self.get_popen()
        if cmd_p.returncode is None:
            self.std['out'], self.std['err'] = cmd_p.communicate()
        return self

    def poll(self):
        """
        return None if not terminated, otherwise return return code
        """
        cmd_p = self.get_popen()
        return cmd_p.poll()

    def stdout(self):
        if self.std['out'] is None:
            self.wait()
        return self.std['out']

    def stderr(self):
        if self.std['err'] is None:
            self.wait()
        return self.std['err']

    def re(self):
        self.wait()
        return self.cmd_p.returncode

    def __or__(self, other):
        if isinstance(other, basestring):
            return self.p(other)
        elif isinstance(other, RunCmd):
            return self.p(other.cmd_str)
        raise ValueError('argument must be a string or an instance of RunCmd')

    def wr(self, target, source='stdout'):
        if source != 'stdout' and source != 'stderr':
            raise ValueError('unsupported source: {0}'.format(source))
        if isinstance(target, basestring):
            fd = open(target, 'wb')
            fd.write(getattr(self, source)())
            fd.close()
        elif check_attrs(target, ['write', 'truncate', 'seek']):
            target.truncate(0)
            target.seek(0)  # work around bug in pypy<2.3.0-alpha0
            target.write(getattr(self, source)())
        else:
            raise ValueError('first argument must be a string'
                             'or has (write, truncate) methods')

    def __gt__(self, target):
        self.wr(target)

    def ap(self, target, source='stdout'):
        if source != 'stdout' and source != 'stderr':
            raise ValueError('unsupported source: {0}'.format(source))
        if isinstance(target, basestring):
            fd = open(target, 'ab')
            fd.write(getattr(self, source)())
            fd.close()
        elif check_attrs(target, ['write', 'seek']):
            target.seek(0, 2)
            target.write(getattr(self, source)())
        else:
            raise ValueError('first argument must be a string'
                             'or has (write, seek) methods')

    def __rshift__(self, target):
        self.ap(target)
