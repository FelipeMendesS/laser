/*
Any signal recieved on the rx pin is retransmitted on a IR LED connected to pin
5 or 6 modulating it with a carrier freq. of 38kHz
*/

#include <avr/io.h>
#include <avr/interrupt.h>


static inline void timer_setup();
static inline void led_on() __attribute__((always_inline));
static inline void led_off() __attribute__((always_inline));

volatile uint8_t rx_buffer[255];
volatile uint8_t rx_buffer_len = 0;

void timer_setup(){
    //clear timer on compare match (CTC)
    TCCR0A = _BV(WGM01);
    //start timer
    TCCR0B = _BV(CS00);
    //set to 38kHz
    OCR0A =211; // Note: (1/38e3*16e6/2) => (~211)
}
void led_on(){
    //TCNT0 = 0; //just so that the waveform looks pretty :)
    //togle OC0A/B on compare match
    TCCR0A |= _BV(COM0A0) | _BV(COM0B0);
}
void led_off(){
    //don't togle OC0A/B on compare match
    TCCR0A &= ~(_BV(COM0A0) | _BV(COM0B0));
    //output pins off
    PORTD &= ~_BV(6);
    PORTD &= ~_BV(5);
}
void led_send(uint8_t byte){
    //send via led at 600 baud
    //note: (1/600*16e6) => (~26667)
    uint8_t bitmask = 1;
    //Start bit
    led_on();
    __builtin_avr_delay_cycles(26667);
    __builtin_avr_delay_cycles(26667);
    while( bitmask ){
        if( byte & bitmask ){
            led_off();
        }
        else{
            led_on();
        }
        __builtin_avr_delay_cycles(26667);
        __builtin_avr_delay_cycles(26667);
        bitmask <<= 1;
    }
    led_on();
    __builtin_avr_delay_cycles(26667);
    __builtin_avr_delay_cycles(26667);
}

int main(){
    DDRB |= _BV(5);//Integrated LED PIN
    DDRD |= _BV(1);//TX PIN
    DDRD |= _BV(6);//OC0A (IR LED PIN)
    DDRD |= _BV(5);//OC0B (IR LED PIN)
    timer_setup();
    led_off();
    uint8_t counter = 0;
    while(1){
        //if(PIND & _BV(0)){
        //    led_off();
        //}
        //else{
            led_on();
        //}
        //led_send(10);
        //led_send(170);
        //led_off();
        //for (counter = 0; counter < 15; counter++) {
        //    __builtin_avr_delay_cycles(36500);
        //}
    }
    return 0;
}
