#ifndef CH446Q_MATRIX_H
#define CH446Q_MATRIX_H

#include "ch446q_driver.h"

#define SSOP20_PIN1_MAP  27
#define SSOP20_PIN2_MAP  26
#define SSOP20_PIN3_MAP  25
#define SSOP20_PIN4_MAP  24
#define SSOP20_PIN5_MAP  23
#define SSOP20_PIN6_MAP  22
#define SSOP20_PIN7_MAP  31
#define SSOP20_PIN8_MAP  30
#define SSOP20_PIN9_MAP  12
#define SSOP20_PIN10_MAP 13
#define SSOP20_PIN11_MAP 15
#define SSOP20_PIN12_MAP 14
#define SSOP20_PIN13_MAP 29
#define SSOP20_PIN14_MAP 19
#define SSOP20_PIN15_MAP 28
#define SSOP20_PIN16_MAP 18
#define SSOP20_PIN17_MAP 21
#define SSOP20_PIN18_MAP 17
#define SSOP20_PIN19_MAP 20
#define SSOP20_PIN20_MAP 16

#define WCH_LINKE_SWCLK  9
#define WCH_LINKE_SWDIO  8
#define WCH_LINKE_TX    11
#define WCH_LINKE_RX    10
#define WCH_LINKE_RST    7

#define PIN_X0           0
#define PIN_X1           1
#define PIN_X2           2
#define PIN_X3           3
#define PIN_X4           4
#define PIN_X5           5
#define PIN_X6           6

#define Y_305_PA0        0
#define Y_305_PA1        1
#define Y_305_PA2        2
#define Y_305_PA3        3
#define Y_305_PA4        4
#define Y_305_PA5        5
#define Y_305_PA6        6
#define Y_305_PA7        7

class CH446QMatrix {
public:
  static constexpr uint8_t kXChannels = 32;
  static constexpr uint8_t kYChannels = 8;
  static constexpr uint8_t kXPerChip = 16;

  CH446QMatrix(
      uint8_t chip0Rst, uint8_t chip0Dat, uint8_t chip0Clk, uint8_t chip0Stb,
      uint8_t chip1Rst, uint8_t chip1Dat, uint8_t chip1Clk, uint8_t chip1Stb);

  void init();
  void reset();
  void switchChannel(uint8_t x, uint8_t y, bool enabled);
  void saveMatrix();
  void restoreMatrix();

private:
  CH446Q& chipForX(uint8_t x, uint8_t& localX);

  CH446Q chip0_;
  CH446Q chip1_;
};

#endif
