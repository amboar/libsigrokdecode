from enum import IntEnum

class SMBusSym(IntEnum):
    START               = 0
    ADDRESS             = 1
    DIRECTION           = 2
    ADDRESS_ACK         = 3
    ADDRESS_NACK        = 4
    COMMAND             = 5
    COMMAND_ACK         = 6
    COMMAND_NACK        = 7
    DATA                = 8
    DATA_ACK            = 9
    DATA_NACK           = 10
    START_REPEAT        = 11
    ADDRESS_REPEAT      = 12
    DIRECTION_REPEAT    = 13
    RESPONSE            = 14
    RESPONSE_ACK        = 15
    RESPONSE_NACK       = 16
    STOP                = 17
    PEC                 = 18
    PEC_ACK             = 19
    PEC_NACK            = 20

    def pretty(self, data):
        name = self.name.capitalize().replace("_", " ")
        return name if data is None else f"{name}: {data:02X}"

    def short(self):
        if self is SMBusSym.STOP: return 'P'
        elif self is SMBusSym.START: return 'S'
        elif '_ACK' in self.name: return 'A'
        elif '_NACK' in self.name: return 'N'
        elif '_REPEAT' in self.name: return self.name[0] + 'r'
        else: return self.name[0]


class SMBusProto(IntEnum):
    QUICK               = 0
    COMMAND             = 1
    BYTE                = 2
    WORD                = 3
    PROCESS_CALL        = 4
    BLOCK               = 5
    BLOCK_PROCESS_CALL  = 6
    HOST_NOTIFY         = 7
    BITS_32             = 8
    BITS_64             = 9
    MFR_DEFINED         = 10


class SMBusAccess(IntEnum):
    WRITE               = 0
    READ                = 1
