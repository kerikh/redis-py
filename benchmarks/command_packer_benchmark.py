import socket
import sys
from redis.connection import (Connection, SYM_STAR, SYM_DOLLAR, SYM_EMPTY,
                              SYM_CRLF, b)
from redis._compat import imap
from base import Benchmark


class StringJoiningConnection(Connection):
    def send_packed_command(self, command):
        "Send an already packed command to the Redis server"
        if not self._sock:
            self.connect()
        try:
            self._sock.sendall(command)
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            _errno, errmsg = ('UNKNOWN', e.args[0]) if len(e.args) == 1 else e.args
            raise ConnectionError(f"Error {_errno} while writing to socket. {errmsg}.")

    def pack_command(self, *args):
        "Pack a series of arguments into a value Redis command"
        args_output = SYM_EMPTY.join([
            SYM_EMPTY.join((SYM_DOLLAR, b(str(len(k))), SYM_CRLF, k, SYM_CRLF))
            for k in imap(self.encoder.encode, args)])
        return SYM_EMPTY.join((SYM_STAR, b(str(len(args))), SYM_CRLF, args_output))


class ListJoiningConnection(Connection):
    def send_packed_command(self, command):
        if not self._sock:
            self.connect()
        try:
            if isinstance(command, str):
                command = [command]
            for item in command:
                self._sock.sendall(item)
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            _errno, errmsg = ('UNKNOWN', e.args[0]) if len(e.args) == 1 else e.args
            raise ConnectionError(f"Error {_errno} while writing to socket. {errmsg}.")

    def pack_command(self, *args):
        output = []
        buff = SYM_EMPTY.join(
            (SYM_STAR, b(str(len(args))), SYM_CRLF))

        for k in imap(self.encoder.encode, args):
            if len(buff) > 6000 or len(k) > 6000:
                buff = SYM_EMPTY.join(
                    (buff, SYM_DOLLAR, b(str(len(k))), SYM_CRLF))
                output.extend((buff, k))
                buff = SYM_CRLF
            else:
                buff = SYM_EMPTY.join((buff, SYM_DOLLAR, b(str(len(k))),
                                       SYM_CRLF, k, SYM_CRLF))
        output.append(buff)
        return output


class CommandPackerBenchmark(Benchmark):

    ARGUMENTS = (
        {
            'name': 'connection_class',
            'values': [StringJoiningConnection, ListJoiningConnection]
        },
        {
            'name': 'value_size',
            'values': [10, 100, 1000, 10000, 100000, 1000000, 10000000,
                       100000000]
        },
    )

    def setup(self, connection_class, value_size):
        self.get_client(connection_class=connection_class)

    def run(self, connection_class, value_size):
        r = self.get_client()
        x = 'a' * value_size
        r.set('benchmark', x)


if __name__ == '__main__':
    CommandPackerBenchmark().run_benchmark()
