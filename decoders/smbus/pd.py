import sigrokdecode as srd
from enum import IntEnum
from common.smbus import SMBusSym, SMBusProto

class I2CSym(IntEnum):
    START = 0
    START_REPEAT = 1
    STOP = 2
    ACK = 3
    NACK = 4
    BITS = 5
    ADDRESS_READ = 6
    ADDRESS_WRITE = 7
    DATA_READ = 8
    DATA_WRITE = 9


class Decoder(srd.Decoder):
    api_version = 3
    id = 'smbus'
    name = 'SMBus'
    longname = 'System Management Bus'
    desc = '''
    SMBus is the System Management Bus defined by Intel® Corporation in 1995.
    It is used in personal computers and servers for low-speed system management
    communications.'''
    license = 'gplv2+'
    inputs = ['i2c']
    outputs = ['smbus']
    annotations = (
            ('start', 'Start'),
            ('address', 'Address'),
            ('direction', 'Direction'),
            ('address-ack', 'Address ACK'),
            ('address-nack', 'Address NACK'),
            ('command', 'Command'),
            ('command-ack', 'Command ACK'),
            ('command-nack', 'Command NACK'),
            ('data', 'Data'),
            ('data-ack', 'Data ACK'),
            ('data-nack', 'Data NACK'),
            ('start-repeat', 'Start Repeat'),
            ('address-repeat', 'Address Repeat'),
            ('direction-repeat', 'Direction Repeat'),
            ('response', 'Response'),
            ('response-ack', 'Response ACK'),
            ('response-nack', 'Response NACK'),
            ('stop', 'Stop'),
    )

    options = (
        {'id': 'pec', 'desc': 'Transfers contain PEC',
         'default': 'False', 'values': ('True', 'False')},
        )

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = None
        self.bits = None
        self.address = None
        self.address_mode = None

    def start(self):
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def puta(self, ss, es, data=None):
        if self.state in (SMBusSym.DIRECTION, SMBusSym.DIRECTION_REPEAT):
            direction = 'Read' if data == 1 else 'Write'
            desc = [direction, direction[0]]
        else:
            desc = [self.state.pretty(data), self.state.short()]
        cmd = [self.state.value, desc]
        self.put(ss, es, self.out_ann, cmd)

    def putp(self, ss, es, cmd):
        self.put(ss, es, self.out_python, cmd)

    def update(self, ss, es, state, data):
        if self.state is None or self.state is SMBusSym.STOP:
            if state is I2CSym.START:
                self.state = SMBusSym.START
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])
            else:
                self.reset()

        elif self.state is SMBusSym.START:
            if state in (I2CSym.ADDRESS_READ, I2CSym.ADDRESS_WRITE):
                self.address_mode = 'READ' if self.bits[0][0] else 'WRITE'
                self.address = data
                self.state = SMBusSym.ADDRESS
                self.puta(self.bits[7][1], self.bits[1][2], data)
                self.putp(self.bits[7][1], self.bits[1][2], [self.state.value, data])

                self.state = SMBusSym.DIRECTION
                self.puta(self.bits[0][1], self.bits[0][2], self.bits[0][0])
                self.putp(self.bits[0][1], self.bits[0][2],
                            [self.state.value, self.bits[0][0]])

            else:
                self.reset()

        elif self.state is SMBusSym.DIRECTION:
            if state is I2CSym.ACK:
                self.state = SMBusSym.ADDRESS_ACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            elif state is I2CSym.NACK:
                self.state = SMBusSym.ADDRESS_NACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.ADDRESS_ACK:
            # 6.5.1 Quick Command
            if state is I2CSym.STOP:
                self.state = SMBusSym.STOP
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            # Other Commands
            elif state is I2CSym.DATA_WRITE:
                self.state = SMBusSym.COMMAND
                self.puta(ss, es, data)
                self.putp(ss, es, [self.state.value, data])

            else:
                self.reset()

        elif self.state is SMBusSym.ADDRESS_NACK:
            assert state is I2CSym.STOP
            self.state = SMBusSym.STOP
            self.puta(ss, es)
            self.putp(ss, es, [self.state.value, None])
            self.reset()

        elif self.state is SMBusSym.COMMAND:
            if state is I2CSym.ACK:
                self.state = SMBusSym.COMMAND_ACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            elif state is I2CSym.NACK:
                self.state = SMBusSym.COMMAND_NACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.COMMAND_ACK:
            # 6.5.2 Send Byte
            if state is I2CSym.STOP:
                if self.address_mode == 'WRITE':
                    self.state = SMBusSym.STOP
                    self.puta(ss, es)
                    self.putp(ss, es, [self.state.value, None])
                else:
                    self.reset()

            # 6.5.2 Send Byte with PEC, or
            # 6.5.3 Receive Byte with PEC, or
            # 6.5.4 Write Byte/Word, or
            # 6.5.6 Process Call, or
            # 6.5.7 Block Write/Read
            elif state in (I2CSym.DATA_WRITE, I2CSym.DATA_READ):
                self.state = SMBusSym.DATA
                self.puta(ss, es, data)
                self.putp(ss, es, [self.state.value, data])

            # Other commands
            elif state is I2CSym.START_REPEAT:
                self.state = SMBusSym.START_REPEAT
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.COMMAND_NACK:
            # 6.5.3 Receive Byte
            if state is I2CSym.STOP:
                if self.address_mode == 'READ':
                    self.state = SMBusSym.STOP
                    self.puta(ss, es)
                    self.putp(ss, es, [self.state.value, None])
                else:
                    self.reset()
            else:
                self.reset()

        elif self.state is SMBusSym.DATA:
            if state is I2CSym.ACK:
                self.state = SMBusSym.DATA_ACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            elif state is I2CSym.NACK:
                self.state = SMBusSym.DATA_NACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.DATA_ACK:
            if state is I2CSym.STOP:
                if self.address_mode == 'WRITE':
                    self.state = SMBusSym.STOP
                    self.puta(ss, es)
                    self.putp(ss, es, [self.state.value, None])
                else:
                    self.reset()

            elif state in (I2CSym.DATA_WRITE, I2CSym.DATA_READ):
                self.state = SMBusSym.DATA
                self.puta(ss, es, data)
                self.putp(ss, es, [self.state.value, data])

            # Other commands
            elif state is I2CSym.START_REPEAT:
                self.state = SMBusSym.START_REPEAT
                self.puta(ss, es, data)
                self.putp(ss, es, [self.state.value, data])

            else:
                self.reset()

        elif self.state is SMBusSym.DATA_NACK:
            assert state is SMBusSym.STOP
            self.state = SMBusSym.STOP
            self.puta(ss, es)
            self.putp(ss, es, [self.state.value, None])
            self.reset()

        elif self.state is SMBusSym.START_REPEAT:
            if state in (I2CSym.ADDRESS_WRITE, I2CSym.ADDRESS_READ):
                if self.address == data:
                    self.state = SMBusSym.ADDRESS_REPEAT
                    self.puta(self.bits[7][1], self.bits[1][2], data)
                    self.putp(self.bits[7][1], self.bits[1][2],
                            [self.state.value, data])

                    self.state = SMBusSym.DIRECTION_REPEAT
                    self.puta(self.bits[0][1], self.bits[0][2], self.bits[0][0])
                    self.putp(self.bits[0][1], self.bits[0][2],
                                [self.state.value, self.bits[0][0]])
                else:
                    self.reset()

            else:
                self.reset()

        elif self.state is SMBusSym.DIRECTION_REPEAT:
            if state is I2CSym.ACK:
                self.state = SMBusSym.RESPONSE_ACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])
            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE:
            if state is I2CSym.ACK:
                self.state = SMBusSym.RESPONSE_ACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            elif state is I2CSym.NACK:
                self.state = SMBusSym.RESPONSE_NACK
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE_ACK:
            if state in (I2CSym.DATA_READ, I2CSym.DATA_WRITE):
                self.state = SMBusSym.RESPONSE
                self.puta(ss, es, data)
                self.putp(ss, es, [self.state.value, data])

            elif state is I2CSym.STOP:
                self.state = SMBusSym.STOP
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])

            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE_NACK:
            if state is I2CSym.STOP:
                self.state = SMBusSym.STOP
                self.puta(ss, es)
                self.putp(ss, es, [self.state.value, None])
            else:
                self.reset()

        else:
            assert False

    def record(self, bits):
        if self.state in (SMBusSym.START, SMBusSym.START_REPEAT):
            self.bits = bits
        else:
            self.bits = None

    def decode(self, ss, es, data):
        cmd, databyte = data

        state = I2CSym[cmd.replace(" ", "_")]
        if state is I2CSym.BITS:
            self.record(databyte)
        else:
            self.update(ss, es, state, databyte)
