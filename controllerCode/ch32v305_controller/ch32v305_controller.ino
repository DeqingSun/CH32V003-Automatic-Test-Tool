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

#include "src/ch446q/ch446q_matrix.h"

// Chip0: PC0–PC3. Chip1: set to your board wiring (PC4–PC7 placeholder).
CH446QMatrix matrix(PC0, PC1, PC2, PC6, PC0, PC1, PC2, PC3);

char rxSerialBuffer[16];
uint8_t rxSerialBufferPtr = 0;
uint8_t digitalPinSubscribed = 255;
uint8_t analogPinSubscribed = 255;
uint32_t digitalPinSubscribedLastPrintTime = 0;
uint32_t analogPinSubscribedLastPrintTime = 0;

void setup() {
    SerialUSB.begin();
    matrix.init();
    matrix.reset();
    pinMode(PB15, OUTPUT);

    pinMode(PA0, OUTPUT);
    digitalWrite(PA0, HIGH);  //set Y0 to high for test
}

void loop() {
  while (SerialUSB.available()) {
    char serialChar = SerialUSB.read();
    if ((serialChar == '\n') || (serialChar == '\r') ) {
      rxSerialBuffer[rxSerialBufferPtr] = '\0';
      if (rxSerialBufferPtr > 0) {
        SerialUSB.println(rxSerialBuffer);

        // other things to do here

        rxSerialBufferPtr = 0;
      }
    } else {
      if (rxSerialBufferPtr < (sizeof(rxSerialBuffer) - 1)) {
        rxSerialBuffer[rxSerialBufferPtr] = serialChar;
        rxSerialBufferPtr++;
      } else {
        rxSerialBuffer[rxSerialBufferPtr] = '\0';
      }
    }
  }
  SerialUSB.flush();

    // matrix.switchChannel(PIN_X6, Y_305_PA0, true);
    // digitalWrite(PB15, HIGH);
    // delay(1000);
    // matrix.switchChannel(PIN_X6, Y_305_PA0, false);
    // digitalWrite(PB15, LOW);
    // delay(1000);
}
