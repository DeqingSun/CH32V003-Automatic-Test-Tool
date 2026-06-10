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
#include "src/logic_analyzer/logic_analyzer.h"
#include "src/util/util.h"

// Chip0: PC0–PC3. Chip1: set to your board wiring (PC4–PC7 placeholder).
CH446QMatrix matrix(PC0, PC1, PC2, PC6, PC0, PC1, PC2, PC3);

char rxSerialBuffer[32];
uint8_t rxSerialBufferPtr = 0;

void setup() {
    SerialUSB.begin();
    matrix.init();
    matrix.reset();
    pinMode(PB15, OUTPUT);

    // pinMode(PA0, OUTPUT);
    // digitalWrite(PA0, HIGH);  //set Y0 to high for test
}

void loop() {
  while (SerialUSB.available()) {
    char serialChar = SerialUSB.read();
    if ((serialChar == '\n') || (serialChar == '\r') ) {
      rxSerialBuffer[rxSerialBufferPtr] = '\0';
      if (rxSerialBufferPtr > 0) {
        //SerialUSB.println(rxSerialBuffer);
        switch (rxSerialBuffer[0])
        {
          case 'I':
            if (rxSerialBufferPtr == 1) {
              matrix.reset();
              //DAC need to be disabled with ALT2
              pinMode(PA4_ALT2,INPUT);
              pinMode(PA5_ALT2,INPUT);
              //set all pins PA0-PA7 to INPUT
              for (int i = 0; i < 8; i++) {
                pinMode(PA0 + i, INPUT);
              }
              SerialUSB.println("I:Init System");
            }
            break;
          case 'C':
          case 'c':
            //connect channels on CH446Q
            if (rxSerialBufferPtr == 4) {
              uint8_t xChannel = hexToUchar2(&rxSerialBuffer[1]);
              uint8_t yChannel = hexToUchar(rxSerialBuffer[3]);
              uint8_t onOFF = (rxSerialBuffer[0] == 'C') ? 1 : 0;

              if ( (xChannel < 32) && (yChannel < 8)) {
                matrix.switchChannel(xChannel, yChannel, onOFF);
                SerialUSB.print(rxSerialBuffer[0]);
                SerialUSB.print(":Turn ");
                if (onOFF == 1) {
                  SerialUSB.print("ON");
                } else {
                  SerialUSB.print("OFF");
                }
                SerialUSB.print(" X:");
                SerialUSB.print(xChannel);
                SerialUSB.print(", Y:");
                SerialUSB.println(yChannel);
              }
            }
            break;
          // case 'B':
          //   if (rxSerialBufferPtr == 1) {
          //     CH552_enter_bootloader();
          //     SerialUSB.println("B: CH552 boot mode");
          //   }else if (rxSerialBufferPtr == 2) {
          //     if (rxSerialBuffer[1] == 'E'){
          //       rebootTargetInsteadOfSelfOn1200 = true;
          //       SerialUSB.println("BE: CH552 reboot target on 1200");
          //     }else if (rxSerialBuffer[1] == 'e'){
          //       rebootTargetInsteadOfSelfOn1200 = false;
          //       SerialUSB.println("Be: CH552 reboot self on 1200");
          //     }
          //   }
          //   break;
          // case 'b':
          //   if (rxSerialBufferPtr == 1) {
          //     CH552_reboot_usercode();
          //     SerialUSB.println("b: CH552 reboot usercode");
          //   }
          //   break;
          case 'R':
          //case 'r':
            if (rxSerialBufferPtr == 2) {
              uint8_t pin = hexToUchar(rxSerialBuffer[1]);
              SerialUSB.print(rxSerialBuffer[0]);
              SerialUSB.print(rxSerialBuffer[1]);
              SerialUSB.print((char)':');
              if (pin < 8) {
                // we only map PA0-PA7 to pins 0-7
                pin = PA0 + pin;
                uint8_t pinStatus = digitalRead(pin);
                SerialUSB.println((char)('0' + pinStatus));
                // if (rxSerialBuffer[0] == 'R') {
                //   digitalPinSubscribed = 255;
                // } else {
                //   digitalPinSubscribed = pin;
                //   digitalPinSubscribedLastPrintTime = millis();
                // }
              } else {
                SerialUSB.println("not valid");
              }
            }
            break;
          case 'A':
          //case 'a':
            if (rxSerialBufferPtr == 2) {
              uint8_t pin = hexToUchar(rxSerialBuffer[1]);
              SerialUSB.print(rxSerialBuffer[0]);
              SerialUSB.print(rxSerialBuffer[1]);
              SerialUSB.print((char)':');
              if (pin >= 8) {
                SerialUSB.println("not valid");
              } else {
                analogRead(pin);
                SerialUSB.println(analogRead(pin));
              }
            }
            break;
          case 'L':
            if (rxSerialBufferPtr == 17) {
              uint32_t rateHz = hexToUint32(&rxSerialBuffer[1]);
              uint32_t sampleCount = hexToUint32(&rxSerialBuffer[9]);
              uint32_t actualRateHz = 0;
              SerialUSB.println("L:Capture data...");
              SerialUSB.flush();
              LogicAnalyzerResult laResult =
                  logicAnalyzerCapture(rateHz, sampleCount, &actualRateHz);
              if (laResult == LA_OK) {
                SerialUSB.print("L:OK,");
                SerialUSB.print(sampleCount);
                SerialUSB.print(",");
                SerialUSB.println(actualRateHz);
                logicAnalyzerUpload(SerialUSB, sampleCount, actualRateHz);
              } else if (laResult == LA_ERR_BAD_RATE) {
                SerialUSB.println("L:ERR,bad_rate");
              } else if (laResult == LA_ERR_BAD_COUNT) {
                SerialUSB.println("L:ERR,bad_count");
              } else if (laResult == LA_ERR_BUSY) {
                SerialUSB.println("L:ERR,busy");
              }
            }
            break;
          case 'W':
            if (rxSerialBufferPtr == 3) {
              uint8_t pin = hexToUchar(rxSerialBuffer[1]);
              uint8_t value = hexToUchar(rxSerialBuffer[2]);
              SerialUSB.print(rxSerialBuffer[0]);
              SerialUSB.print(rxSerialBuffer[1]);
              SerialUSB.print((char)':');
              if (pin < 8) {
                // we only map PA0-PA7 to pins 0-7
                pin = PA0 + pin;
                pinMode(pin, OUTPUT);
                digitalWrite(pin, value);
                uint8_t pinStatus = digitalRead(pin);
                SerialUSB.println((char)('0' + pinStatus));
              } else {
                SerialUSB.println("not valid");
              }
            }
            break;
          case 'w':
            if (rxSerialBufferPtr == 6) {
              uint16_t pin = hexToUchar(rxSerialBuffer[1]);
              uint16_t value = hexToUint16(&rxSerialBuffer[2]); //12bit value for ADC, DAC and PWM
              SerialUSB.print(rxSerialBuffer[0]);
              SerialUSB.print(rxSerialBuffer[1]);
              SerialUSB.print((char)':');
              if ( pin < 8 ) {
                if (pin == 4 || pin == 5) {
                  pin = (PA0 + pin) | ALT2; //DAC uses PA4_ALT2 and PA5_ALT2
                }else{
                  pin = PA0 + pin;
                }
                analogWrite(pin, value);
                SerialUSB.println((int)value);
              } else {
                SerialUSB.println("not valid");
              }
            }
            break;
          // case 'T':
          // case 't':
          //   //set uart baudrate
          //   if (rxSerialBufferPtr == 2) {
          //     uint8_t baudrateMuliplexer = hexToUchar(rxSerialBuffer[1]);
          //     SerialUSB.print(rxSerialBuffer[0]);
          //     SerialUSB.print((char)':');
          //     if (baudrateMuliplexer == 0) {
          //       SerialUSB.println("disable UART");
          //       if (rxSerialBuffer[0] == 'T') {
          //         disableUART0();
          //       } else {
          //         disableUART1();
          //       }
          //     } else if (baudrateMuliplexer > (115200 / 9600)) {
          //       SerialUSB.println("not valid rate");
          //     } else {
          //       __xdata uint32_t baudrate = 9600L * baudrateMuliplexer;
          //       if (rxSerialBuffer[0] == 'T') {
          //         PIN_FUNC |= bUART0_PIN_X;
          //         Serial0_begin(baudrate);  //RXD0/TXD0 uses P0.2/P0.3
          //       } else {
          //         Serial1_begin(baudrate);  //RXD1/TXD1 uses P2.6/P2.7
          //       }
          //       SerialUSB.println(baudrate);
          //     }
          //   }
          //   break;
          // case 'U':
          // case 'u':
          //   {
          //     for (int i = 1; i < rxSerialBufferPtr; i++) {
          //       __data char charToSend = rxSerialBuffer[i];
          //       if (charToSend == '\\') {
          //         if (rxSerialBuffer[i + 1] == 'n') {
          //           charToSend = '\n';
          //           i++;
          //         } else if (rxSerialBuffer[i + 1] == 'r') {
          //           charToSend = '\r';
          //           i++;
          //         }
          //       }
          //       if (rxSerialBuffer[0] == 'U') {
          //         Serial0_write(charToSend);
          //       } else {
          //         Serial1_write(charToSend);
          //       }
          //     }
          //   }
          //   break;
          default:
            break;
        }

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
