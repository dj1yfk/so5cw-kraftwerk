import curses
from smbus2 import SMBus
import RPi.GPIO as GPIO
import time

stdscr = curses.initscr()
curses.noecho()
curses.halfdelay(10)

GPIO.setmode(GPIO.BCM)


#          K1  K2  K3  K4  K5
rpins =  [ 7, 19, 12, 16, 20 ]
rstate = [ 0, 0, 0, 0, 0]

# init
for i in range(0,5):
    GPIO.setup(rpins[i], GPIO.OUT)
    GPIO.output(rpins[i], rstate[i])

stdscr.addstr(0,0,"Activate relay K1..K5 by pressing 1..5.")

try:
    while 1:
        c = stdscr.getch()
        if c >= ord('1') and c <= ord('5'):
#            nr = chr(c)
            nr = c - ord('1')
            stdscr.addstr(2,0, "nr = {}".format(nr))
            if rstate[nr] == 0:
                rstate[nr] = 1
            else:
                rstate[nr] = 0
            stdscr.addstr(1,0, "Switching relay {} (pin {}) to {}".format(nr+1, rpins[nr], rstate[nr]))
           
            GPIO.output(rpins[nr], rstate[nr])
        else:
            stdscr.addstr(2,0, "tout")

        with SMBus(1) as bus:
            for ch in range(0,5):
                vbusreg = bus.read_i2c_block_data(0x40 + ch, 2, 2)
                vshtreg = bus.read_i2c_block_data(0x40 + ch, 1, 2)

                vbusreg = ((vbusreg[0] << 8) + vbusreg[1])
                ovf = vbusreg & 0x0001
                voltage = (vbusreg >> 3) * 0.004

                vshtreg = ((vshtreg[0] << 8) + vshtreg[1])
                sign = vshtreg & 0x8000

                if sign == 0:
                    current = (vshtreg / 100000) / 0.01
                else:
                    current = ((65535 + 1 - vshtreg) / -100000) / 0.01

                stdscr.addstr(3+ch,0, "CH{0}: {1:5.2f} V\t{2:5.2f} A\tOVF = {3}     ".format(ch, voltage, current, ovf))

finally:
    curses.endwin()



