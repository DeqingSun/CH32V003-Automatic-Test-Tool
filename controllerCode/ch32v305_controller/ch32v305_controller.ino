// compile with CH32V30x , 144Mhz external clock, use board CH32V305CCT6
// new chip is not set with 128K ROM + 192K RAM setting,
// use WCH-LinkUtility on windows to set it or we get hardfault on RAM write failure

#if !defined(VARIANT_H)
  #error "VARIANT_H not defined — no board selected?"
#elif defined(__cplusplus)
  static_assert(
    __builtin_strcmp(VARIANT_H, "variant_CH32V305CCT6.h") == 0,
    "Wrong board variant. Select CH32V305CCT6."
  );
#else
  #error "Board check requires C++ (use ARDUINO_* macro in C files)"
#endif

#include <SimpleUsbSerial.h>

#include "ch446q_driver.h"

CH446Q ch446q0(PC0, PC1, PC2, PC3);

void setup() {
    SerialUSB.begin();
    ch446q0.init();
    ch446q0.reset();
    pinMode(PB15,OUTPUT);
}

// the loop function runs over and over again forever
void loop() {
    ch446q0.switchChannel(0, 0, true);
    digitalWrite(PB15,HIGH);
    delay(1000);
    ch446q0.switchChannel(0, 0, false);
    digitalWrite(PB15,LOW);
    delay(1000);
}