import curses
from smbus2 import SMBus
import RPi.GPIO as GPIO
import time
import syslog

g_sol_c = 0
def sign_of_life():
    global g_sol_c
    g_sol_c = (g_sol_c + 1) % 5

    # if the LED is off, flash on, otherwise flash off
    state1 = 1
    state2 = 0
    if lstate[g_sol_c] == 1:
        state1 = 0
        state2 = 1

    GPIO.output(lpins[g_sol_c], state1)
    time.sleep(0.01)
    GPIO.output(lpins[g_sol_c], state2)

    # restore LED status
    for i in range(0,5):
        GPIO.output(lpins[i], lstate[i])

def read_voltage(ch):
    vbusreg = bus.read_i2c_block_data(0x40 + ch, 2, 2)
    vbusreg = ((vbusreg[0] << 8) + vbusreg[1])
    ovf = vbusreg & 0x0001
    voltage = (vbusreg >> 3) * 0.004
    return voltage, ovf

def read_current(ch):
    vshtreg = bus.read_i2c_block_data(0x40 + ch, 1, 2)

    vshtreg = ((vshtreg[0] << 8) + vshtreg[1])
    sign = vshtreg & 0x8000

    if sign == 0:
        current = (vshtreg / 100000) / 0.01
    else:
        current = ((65535 + 1 - vshtreg) / -100000) / 0.01

    if current < 0 and current > -0.01:  # no stinking "-0.00" please
        current = 0

    return current

stdscr = curses.initscr()
curses.noecho()
curses.curs_set(0)
curses.halfdelay(5)

GPIO.setmode(GPIO.BCM)


# Relays   K1  K2  K3  K4  K5
rpins =  [ 7, 19, 12, 16, 20 ]
rstate = [ 1, 1, 1, 1, 1]

# Input pins (opto coupler)
opins =  [ 22, 27 ]
opin_history = [[], []]


# Err LEDs E1 E2  E3  E4  E5
lpins =  [ 17, 18, 15, 4, 14 ]
lstate = [ 0, 0, 0, 0, 0]

limits = [0.1, 1, 0.2, 1, 1]

# init Relay Pins
for i in range(0,5):
    GPIO.setup(rpins[i], GPIO.OUT)
    GPIO.setup(lpins[i], GPIO.OUT)
    GPIO.output(rpins[i], rstate[i])
    GPIO.output(lpins[i], 0)

# init optocoupler pins
for i in range(0,2):
    GPIO.setup(opins[i], GPIO.IN)

stdscr.addstr(0,0,"Activate relay K1..K5 by pressing 1..5.")
syslog.syslog("Launching so5cw-kraftwerk")

try:
    while 1:
        c = stdscr.getch()
        if c >= ord('1') and c <= ord('5'):
            nr = c - ord('1')
            if rstate[nr] == 0:
                rstate[nr] = 1   # switch relay on
                lstate[nr] = 0   # reset fuse
            else:
                rstate[nr] = 0
            stdscr.addstr(1,0, "Switching relay {} (pin {}) to {}".format(nr+1, rpins[nr], rstate[nr]))
           
            GPIO.output(rpins[nr], rstate[nr])
        else:
            sign_of_life()

        with SMBus(1) as bus:
            for ch in range(0,5):
                voltage, ovf = read_voltage(ch);
                current      = read_current(ch);

                if current > limits[ch]:    # Over current limit?
                    syslog.syslog("WARN: Channel {} above current limit (limit: {}, measured: {}, voltage: {}) - re-reading current.".format(ch+1, limits[ch], current, voltage))
                    current      = read_current(ch);

                    if current < limits[ch]:    # I2C reading error - false alert
                        syslog.syslog("WARN: False alert - 2nd reading: {}".format(current))
                        continue

                    syslog.syslog("ALERT: Channel {} above current limit (limit: {}, measured: {}, voltage: {}) for two consecutive measurements. Switch OFF..".format(ch+1, limits[ch], current, voltage))

                    lstate[ch] = 1
                    rstate[ch] = 0
                    GPIO.output(rpins[ch], rstate[ch])
                    GPIO.output(lpins[ch], lstate[ch])

                stdscr.addstr(3+ch,0, "CH{0}: {1:5.2f} V\t{2:5.2f} A\tOVF = {3}  FUSE = {4}   ".format(ch+1, voltage, current, ovf, lstate[ch]))

            # show GPIO status and history (last 10 readins)
            for ch in range(0,2):
                pinstate = abs(GPIO.input(opins[ch]) - 1)
                stdscr.addstr(3+len(rpins)+ch ,0, "IN{0}: {1} {2} ".format(ch, pinstate, opin_history[ch]))
                opin_history[ch].insert(0, pinstate) 
                while len(opin_history[ch]) > 10:
                    opin_history[ch].pop()



finally:
    curses.endwin()




