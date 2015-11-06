############### CONFIGURATION SETTINGS:

DEVICE     = atmega328p

CLOCK      = 16000000
OBJECTS    = main.o

FUSES      = -U BYTE0:w:0xff:m

INCLUDE    = ../include

PROG_BAUD  = 115200 #Arduino UNO
#PROG_BAUD = 57600 #Arduino Duemilanove

PROGRAMMER_FLAGS = -c arduino -p $(DEVICE) -b $(PROG_BAUD) -P /dev/tty.usbmodem1411 -e -v

############### END OF CONFIGURATION SETTINGS ##############

AVRDUDE = avrdude $(PROGRAMMER_FLAGS)
COMPILE = avr-gcc -Wall -Os -DF_CPU=$(CLOCK) -mmcu=$(DEVICE) -I $(INCLUDE)

# symbolic targets:
all:	main.hex

.c.o:
	$(COMPILE) -c $< -o $@

.S.o:
	$(COMPILE) -x assembler-with-cpp -c $< -o $@

.c.s:
	$(COMPILE) -S $< -o $@

flash:	all
	$(AVRDUDE) -U flash:w:main.hex

fuse:
	$(AVRDUDE) $(FUSES)

# Xcode uses the Makefile targets "", "clean" and "install"
install: flash fuse

clean:
	rm -f main.hex main.elf main.map main.lst $(OBJECTS) *.s

# file targets:
main.elf: $(OBJECTS)
	$(COMPILE) -o main.elf $(OBJECTS)

main.hex: main.elf
	rm -f main.hex
	avr-objcopy -j .text -j .data -O ihex main.elf main.hex

main.map: $(OBJECTS)
	$(COMPILE) -Wl,-Map,main.map -o main.elf $(OBJECTS)

main.lst: main.elf
	avr-objdump -h -S main.elf > main.lst

size: main.elf
	avr-size -C --mcu=$(DEVICE) main.elf
