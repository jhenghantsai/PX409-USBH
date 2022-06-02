# PX409-USBH script
# written by Jheng-Han Tsai, March 2019
#####################################################################
import serial
import time
import sys
import struct
import numpy as np



class PX409():
    """Driver for the PX409 pressure transducer"""
    
    def __init__(self, port):
        self.serial = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
        )
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # The exit code of the sample application.
        exitCode = 0
        #sys.exit(exitCode)
        #print ('Transducer closed.')

    def write(self, command):
        self.serial.write((command + '\r').encode('ascii'))
        time.sleep(0.5)
        waiting = self.serial.inWaiting()
        resp = self.serial.read(waiting)
        resp_unicode = resp.decode('ascii')
        #print (resp_unicode) 

        return resp_unicode

    def get_serialNumber(self):
        '''Returns the transducer’s serial number.
        '''
        return self.write('SNR')
        

    def get_firmware(self):
        '''Returns the transducer’s Unit ID, firmware version, range, and
        engineering units, all in ASCII.
        '''
        return self.write('ENQ')


    def set_iirFilter(self, num):
        '''Read/Write. Reads or sets the IIR filter period (time constant).
        where optional nnn is 0 or 1 (disabled), or between 2 to 255
        '''
        self.serial.write(('IFILTER '+str(num)+'\r').encode('ascii'))
        time.sleep(0.5)
        waiting = self.serial.inWaiting()
        resp = self.serial.read(waiting)
        resp_unicode = resp.decode('ascii')
        
        return resp_unicode

    def set_averageNumber(self, num):
        '''Reads or sets the number of data points to be averaged for the
        boxcar average filter. Valid values are 0, 2, 4, 8 and 16. Note: the output rate is
        determined by the RATE command setting divided by this value (excluding 0). AVG x
        sets the averaged number. Note: the boxcar changes the rate of the readings returned by
        the PC command. This is because the boxcar averages the specified number of readings
        given by nn, and outputs one reading for the group.

        '''
        self.serial.write(('AVG '+str(num)+'\r').encode('ascii'))
        time.sleep(0.5)
        waiting = self.serial.inWaiting()
        resp = self.serial.read(waiting)
        resp_unicode = resp.decode('ascii')
        
        return resp_unicode

    def set_rate(self, num):
        '''Reads or sets the transducer update rate. Valid Values are 0=5sps,
        1=10sps, 2=20sps, 3=40sps, 4=80sps, 5=160sps, 6=320sps, 7=640sps, 8=1000sps.
        '''
        self.serial.write(('RATE '+str(num)+'\r').encode('ascii'))
        time.sleep(0.5)
        waiting = self.serial.inWaiting()
        resp = self.serial.read(waiting)
        resp_unicode = resp.decode('ascii')
        
        return resp_unicode


    def pickAscii(self):
        '''Sends single ASCII reading (decimal point also sent as ASCII). Data is post filter, and
        scaled to the native engineering units and type of transducer.
        '''
        self.serial.write(('P' + '\r\n').encode('ascii'))
        time.sleep(0.025) #Based on reading rate, the highest transfer rate is about 50 Hz
        waiting = self.serial.inWaiting()
        resp = self.serial.read(waiting)
        resp_unicode = resp.decode('ascii')
        
        varList = resp_unicode.split()
        #print(varList)
        var = float(varList[0]) #Unit: hPa(default) 
        
        return var
        

    def pickBinary(self):
        '''Sends single Binary reading.
        '''
        self.serial.write(('B' + '\r\n').encode('ascii'))
        time.sleep(0.025) #Based on reading rate
        waiting = self.serial.inWaiting()
        packet = self.serial.read(waiting)
        print (packet)
        print ([hex(x) for x in bytes(packet)])

        bipacket = bytearray(bytes(packet)[2:]) 
        var, = struct.unpack('<f', bipacket)

        return var

    def pcClock(self, samples_per_channel):
        #Collect data using computer's clock
        #Sampling rate: 50 Hz
        data = np.zeros((samples_per_channel,2))
        print ('Transducer reading starts.\n')

        startime = time.clock()
        
        for i in range(samples_per_channel):
            dataTemp = self.pickAscii()
            data[i,0] = time.clock()-startime
            data[i,1] = float(dataTemp)

        protime = time.clock()-startime
        print ('Real time: '+str(protime)+' s.') 

        print ('Transducer reading finishes.\n')
        #print (data)
        return data

    def pickContinuous(self, samples_per_channel):
        '''Starts continuous stream of readings from the transducer, at an update rate
        specified by the RATE command. Data is in 4 byte IEEE 754 format (1 bit sign, 8 bits
        exponent, 23 bits significand (mantissa)), plus sync byte, plus packet type. Data is post
        filter, and is a scaled floating point representation of the transducer’s native engineering
        units. Data is sent Little Endian to be compatible with the PC.
        '''
        sampling_rate = 1000

        self.set_rate(8) #8 = 1000sps.
        data = np.zeros((samples_per_channel,2))
        
        self.serial.write(('PC\r').encode('ascii'))
        startime = time.clock()
        i = 0
        #databank = []
        while i < samples_per_channel:
            dataGet = self.getData()
            if dataGet  == 0:
                i = i
            else:
                data[i,1] = dataGet
                data[i,0] = time.clock()-startime
                #databank.append(dataGet)
                i = i+1
                
        print ('Real time: '+str(time.clock()-startime)+' s.')
        self.stops()
        # Output unit: hPa
        
        return data
            

    def stops(self):
        '''

        '''
        self.serial.write(('PS\r').encode('ascii'))
        print ('Stop continuous stream of readings.')
        
    def getData(self):
        data = self.serial.read(12) #Read more, in general 6 to 10 bytes

        dataLength = len(bytes(data))
        
        for i in range(dataLength):
            if hex(bytes(data)[i]) == '0xaa' and hex(bytes(data)[i+1]) != '0xaa':
                startidx = i+2
                j = 0
                bb = []
                while j<4:
                    
                    if startidx+j >= dataLength-1:
                        break

                    else:
                        bb.append(bytes(data)[startidx+j])
                        if hex(bytes(data)[startidx+j]) == '0xaa':    
                            startidx = startidx+1
                        else:
                            startidx = startidx
                        j = j+1
                    
                break
        
        if startidx+j >= dataLength-1:
            var = 0
            
        else:
            
            bipacket = bytearray(bytes(bb)[:]) 
            var, = struct.unpack('<f', bipacket)

        #print (var)
        return var
                        

'''
def main():
    with PX409(port) as omega:
        print(repr(omega.stops()))
        print(repr(omega.get_serialNumber()))
        print(repr(omega.get_firmware()))
        num = 8
        print(repr(omega.set_rate(num)))
        omega.pcClock(samples_per_channel)
        
if __name__ == "__main__" :
    main()
'''



    
