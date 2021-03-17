import sigrokdecode as srd
from enum import Enum
from common.smbus import SMBusSym, SMBusProto, SMBusAccess

class PMBusCommand(bytes, Enum):
    def __new__(cls, value, proto):
        obj = bytes.__new__(cls, [value])
        obj._value_ = value
        obj.proto = proto
        return obj

    PAGE                = (0x00, SMBusProto.BYTE)
    WRITE_PROTECT       = (0x10, SMBusProto.BYTE)
    CAPABILITY          = (0x19, SMBusProto.BYTE)
    CLEAR_FAULTS        = (0x03, SMBusProto.COMMAND)
    VOUT_MODE           = (0x20, SMBusProto.BYTE)
    FAN_CONFIG_1_2      = (0x3a, SMBusProto.BYTE)
    FAN_COMMAND_1       = (0x3b, SMBusProto.WORD)
    VOUT_OV_FAULT_LIMIT = (0x40, SMBusProto.WORD)
    VOUT_OV_WARN_LIMIT  = (0x42, SMBusProto.WORD)
    VOUT_UV_WARN_LIMIT  = (0x43, SMBusProto.WORD)
    VOUT_UV_FAULT_LIMIT = (0x44, SMBusProto.WORD)
    OT_FAULT_LIMIT      = (0x4f, SMBusProto.WORD)
    OT_WARN_LIMIT       = (0x51, SMBusProto.WORD)
    UT_WARN_LIMIT       = (0x52, SMBusProto.WORD)
    UT_FAULT_LIMIT      = (0x53, SMBusProto.WORD)
    STATUS_WORD         = (0x79, SMBusProto.WORD)
    STATUS_VOUT         = (0x7a, SMBusProto.BYTE)
    STATUS_IOUT         = (0x7b, SMBusProto.BYTE)
    STATUS_TEMPERATURE  = (0x7d, SMBusProto.BYTE)
    STATUS_CML          = (0x7e, SMBusProto.BYTE)
    STATUS_OTHER        = (0x7f, SMBusProto.BYTE)
    STATUS_MFR_SPECIFIC = (0x80, SMBusProto.BYTE)
    STATUS_FANS_1_2     = (0x81, SMBusProto.BYTE)
    READ_VOUT           = (0x8b, SMBusProto.WORD)
    READ_TEMPERATURE_1  = (0x8d, SMBusProto.WORD)
    READ_FAN_SPEED_1    = (0x90, SMBusProto.WORD)
    READ_FAN_SPEED_2    = (0x91, SMBusProto.WORD)
    MFR_REVISION        = (0x9b, SMBusProto.BLOCK)
    MFR_SPECIFIC_09     = (0xd9, SMBusProto.MFR_DEFINED)
    MFR_SPECIFIC_33     = (0xf1, SMBusProto.MFR_DEFINED)
    PMBUS_COMMAND_EXT   = (0xff, SMBusProto.MFR_DEFINED)


class Decoder(srd.Decoder):
    api_version = 3
    id = 'pmbus'
    name = 'PMBus'
    longname = 'Power Management Bus'
    desc = '''
    PMBus allows for communication between devices based on both analog and
    digital technologies, and provides true interoperability, which will reduce
    design complexity and shorten time to market for power system designers.'''
    license = 'gplv2+'
    inputs = ['smbus']
    outputs = ['pmbus']
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
            ('pec', 'PEC byte'),
            ('pec-ack', 'PEC ACK'),
            ('pec-nack', 'PEC NACK'),
    )
    options = ()

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = None
        self.address = None
        self.access = None
        self.command = None
        self.data = []
        self.response = []

    def start(self):
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def puta(self, ss, es, data=None):
        if self.state in (SMBusSym.DIRECTION, SMBusSym.DIRECTION_REPEAT):
            direction = self.access.name.capitalize()
            desc = [direction, direction[0]]
        elif self.state is SMBusSym.COMMAND:
            cmd = self.command.name
            desc = [cmd, cmd[0]]
        else:
            desc = [self.state.pretty(data), self.state.short()]
        cmd = [self.state.value, desc]
        self.put(ss, es, self.out_ann, cmd)

    def putp(self, ss, es, data):
        self.put(ss, es, self.out_python, [self.state.value, data])

    def update(self, ss, es, state, data):
        if self.state is None or self.state is SMBusSym.STOP:
            self.reset()
            if state is SMBusSym.START:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.START:
            if state is SMBusSym.ADDRESS:
                self.state = state
                self.address = data
                self.puta(ss, es, data)
                self.putp(ss, es, data)

            else:
                self.reset()

        elif self.state is SMBusSym.ADDRESS:
            if state is SMBusSym.DIRECTION:
                self.state = state
                self.access = SMBusAccess(data)
                self.puta(ss, es, data)
                self.putp(ss, es, data)

            else:
                self.reset()

        elif self.state is SMBusSym.DIRECTION:
            if state is SMBusSym.ADDRESS_ACK:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            elif state is SMBusSym.ADDRESS_NACK:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.ADDRESS_ACK:
            if state is SMBusSym.STOP:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            elif state is SMBusSym.COMMAND:
                self.state = state
                self.command = PMBusCommand(data)
                desc = [ f'{self.command.name} Command', 'C' ]
                ann = [self.state.value, desc ]
                self.put(ss, es, self.out_ann, ann)
                self.putp(ss, es, data)

            else:
                self.reset()

        elif self.state is SMBusSym.COMMAND:
            if state in (SMBusSym.COMMAND_ACK, SMBusSym.COMMAND_NACK):
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.COMMAND_ACK:
            if state is SMBusSym.STOP:
                if self.access is SMBusAccess.WRITE:
                    self.state = state
                    self.puta(ss, es)
                    self.putp(ss, es, None)
                else:
                    self.reset()

            elif state is SMBusSym.DATA:
                assert(len(self.data) == 0)
                self.data.append((ss, es, data))
                self.state = state

            elif state is SMBusSym.START_REPEAT:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.COMMAND_NACK:
            if state is SMBusSym.STOP:
                if self.access is SMBusAccess.READ:
                    self.state = state
                    self.puta(ss, es)
                    self.putp(ss, es, None)
                else:
                    self.reset()

            else:
                self.reset()

        elif self.state is SMBusSym.DATA:
            if state is SMBusSym.DATA_ACK:
                if self.access == SMBusAccess.WRITE:
                    if self.command.proto is SMBusProto.BYTE:
                        if len(self.data) == 1:
                            vss = self.data[0][0]
                            ves = self.data[0][1]
                            val = self.data[0][2]
                            desc = [ f'{self.command.name} Write: {val:02X}', 'B']
                            ann = [ SMBusSym.DATA.value, desc ]
                            self.put(vss, ves, self.out_ann, ann)
                            # FIXME: Output on python stream
                            self.state = state
                            self.puta(ss, es)
                            self.putp(ss, es, None)

                    elif self.command.proto is SMBusProto.WORD:
                        if len(self.data) == 2:
                            vss = self.data[0][0]
                            ves = self.data[1][1]
                            val = (self.data[1][2] << 8) | self.data[0][2]
                            desc = [ f'{self.command.name} Write: {val:04X}', 'W' ]
                            ann = [ SMBusSym.DATA.value, desc ]
                            self.put(vss, ves, self.out_ann, ann)
                            # FIXME: Output on python stream
                            self.state = state
                            self.puta(ss, es)
                            self.putp(ss, es, None)

                    else:
                        print(f"Unsupported proto: {self.command.proto}")
                        self.reset()

                else:
                    self.reset()

            elif state is SMBusSym.DATA_NACK:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.DATA_ACK:
            if state is SMBusSym.STOP:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            elif state is SMBusSym.DATA:
                self.data.append((ss, es, data))
                self.state = state

            elif state is SMBusSym.START_REPEAT:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.DATA_NACK:
            assert state is SMBusSym.STOP
            self.state = state
            self.puta(ss, es)
            self.putp(ss, es, None)

        elif self.state is SMBusSym.START_REPEAT:
            if state is SMBusSym.ADDRESS_REPEAT:
                if self.address == data:
                    self.state = state
                    self.puta(ss, es, data)
                    self.putp(ss, es, data)

                else:
                    self.reset()

            else:
                self.reset()

        elif self.state is SMBusSym.ADDRESS_REPEAT:
            if state is SMBusSym.DIRECTION_REPEAT:
                self.access = SMBusAccess(data)
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, data)

            else:
                self.reset()

        elif self.state is SMBusSym.DIRECTION_REPEAT:
            if state is SMBusSym.RESPONSE_ACK:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE:
            if state is SMBusSym.RESPONSE_NACK:
                if self.access == SMBusAccess.READ:
                    if self.command.proto is SMBusProto.BYTE:
                        if len(self.response) == 1:
                            vss = self.response[0][0]
                            ves = self.response[0][1]
                            val = self.response[0][2]
                            desc = [ f'{self.command.name} Read: {val:02X}', 'B']
                            ann = [ SMBusSym.RESPONSE.value, desc ]
                            self.put(vss, ves, self.out_ann, ann)
                            # FIXME: Output on python stream
                            self.state = state
                            self.puta(ss, es)
                            self.putp(ss, es, None)

                    elif self.command.proto is SMBusProto.WORD:
                        if len(self.response) == 2:
                            vss = self.response[0][0]
                            ves = self.response[1][1]
                            val = (self.response[1][2] << 8) | self.response[0][2]
                            desc = [ f'{self.command.name} Read: {val:04X}', 'W' ]
                            ann = [ SMBusSym.RESPONSE.value, desc ]
                            self.put(vss, ves, self.out_ann, ann)
                            # FIXME: Output on python stream
                            self.state = state
                            self.puta(ss, es)
                            self.putp(ss, es, None)

                    elif self.command.proto is SMBusProto.BLOCK:
                        vss = self.response[-1][0]
                        ves = self.response[-1][1]
                        val = self.response[-1][2]
                        desc = [ f'{val:02X}', 'R' ]
                        ann = [ SMBusSym.RESPONSE.value, desc ]
                        self.put(vss, ves, self.out_ann, ann)
                        self.state = state
                        self.puta(ss, es)
                        self.putp(ss, es)

                    else:
                        print(f"Unsupported proto: {self.command.proto}")
                        self.reset()

                else:
                    self.reset()

            elif state is SMBusSym.RESPONSE_ACK:
                if self.access == SMBusAccess.READ:
                    if self.command.proto is SMBusProto.BLOCK:
                        if len(self.response) == 1:
                            lss = self.response[0][0]
                            les = self.response[0][1]
                            val = self.response[0][2]
                            desc = [ f'Block Read Length: {val:02X}', 'L' ]
                            ann = [ SMBusSym.RESPONSE.value, desc ]
                            self.put(lss, les, self.out_ann, ann)
                            self.state = state

                        else:
                            vss = self.response[-1][0]
                            ves = self.response[-1][1]
                            val = self.response[-1][2]
                            desc = [ f'{val:02X}', 'R' ]
                            ann = [ SMBusSym.RESPONSE.value, desc ]
                            self.put(vss, ves, self.out_ann, ann)
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es)

            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE_ACK:
            if state is SMBusSym.STOP:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            elif state is SMBusSym.RESPONSE:
                self.response.append((ss, es, data))
                self.state = state

            else:
                self.reset()

        elif self.state is SMBusSym.RESPONSE_NACK:
            if state is SMBusSym.STOP:
                self.state = state
                self.puta(ss, es)
                self.putp(ss, es, None)

            else:
                self.reset()

        else:
            self.reset()

    def decode(self, ss, es, data):
        smbsymid, data = data
        self.update(ss, es, SMBusSym(smbsymid), data)
