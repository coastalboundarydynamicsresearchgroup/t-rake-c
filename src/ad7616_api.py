import pathlib
from enum import Enum
from ctypes import *

class SPIDEF(Structure):
    _fields_ = [("spi_cs_pin",   c_uint32),
                ("spi_sclk_pin", c_uint32),
                ("spi_mosi_pin", c_uint32),
                ("spi_miso_pin", c_uint32),
                ("spi_errorcode", c_int32),
                ("spi_flags", c_int32)]



class AD7616:
    bus = 1
    device = 0
    driver = None
    handle = None
    print_diagnostic = False
    sequenceLength = 0

    class Register(Enum):
        CONFIGURATION = 2
        CHANNELSEL = 3
        RANGEA_0_3 = 4
        RANGEA_4_7 = 5
        RANGEB_0_3 = 6
        RANGEB_4_7 = 7
        
    class Range(Enum):
        PLUS_MINUS_10V = 0
        PLUS_MINUS_2_5V = 1
        PLUS_MINUS_5V = 2

    def __init__(self, bus=1, device=0, print_diagnostic=False):
        self.bus = bus
        self.device = device
        self.print_diagnostic = print_diagnostic
        self.sequenceLength = 0

    def __enter__(self):
        libname = pathlib.Path().absolute() / "ad7616_driver.so"
        self.driver = CDLL(libname)

        self.driver.spi_initialize.restype = SPIDEF

        self.handle = self.driver.spi_initialize()
        if (self.print_diagnostic):
            self.handle.spi_flags |= 1
        self.driver.spi_open(self.handle, self.bus, self.device)

        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.driver.spi_terminate(self.handle)

    def WriteRegister(self, address, value):
        self.driver.spi_writeregister(self.handle, address, value)

    def ReadRegister(self, address):
        registerValue = self.driver.spi_readregister(self.handle, address)
        return registerValue

    def ReadRegisters(self, addresses):
        registerss_array = c_uint32 * len(addresses)
        sequenceaddresses = registerss_array()
        sequencevalues = registerss_array()
        for i in range(len(addresses)):
            sequenceaddresses[i] = addresses[i]
            
        self.driver.spi_readregisters(self.handle, len(addresses), sequenceaddresses, sequencevalues)

        values = []
        for value in sequencevalues:
            values.append(value)

        return values

    def ConvertPair(self, AChannel, BChannel):
        conversion = self.driver.spi_convertpair(self.handle, AChannel, BChannel)

        aconv = (conversion >> 16) & 0xff
        bconv = conversion & 0xff

        return (aconv, bconv)
    
    def DefineSequence(self, AChannels, BChannels):
        self.sequenceLength = len(AChannels)
        channels_array = c_uint32 * self.sequenceLength
        AchannelArray = channels_array()
        BchannelArray = channels_array()
        for i in range(len(AChannels)):
            AchannelArray[i] = AChannels[i]
            BchannelArray[i] = BChannels[i]

        self.driver.spi_definesequence(self.handle, self.sequenceLength, AchannelArray, BchannelArray)

    def ReadConversions(self):
        conversions_array = c_uint32 * self.sequenceLength
        conversionvalues = conversions_array()
        self.driver.spi_readconversion(self.handle, self.sequenceLength, conversionvalues)
        for conversionvalue in conversionvalues: print(f"{conversionvalue} ", end=" ")
        print()

        conversions = []
        # First, append all the A side conversions.
        for conversion in conversionvalues:
            conversions.append(((conversion >> 16) & 0xffff))
        # Second, append all the B side conversions.
        for conversion in conversionvalues:
            conversions.append(conversion & 0xffff)

        return conversions

    def Start(self, period, path, filename):
        self.driver.spi_start.argtypes = [SPIDEF, c_uint32, c_char_p, c_char_p]
        self.driver.spi_start(self.handle, period, c_char_p(bytes(path, "ASCII")), c_char_p(bytes(filename, "ASCII")))

    def Stop(self):
        self.driver.spi_stop(self.handle)
