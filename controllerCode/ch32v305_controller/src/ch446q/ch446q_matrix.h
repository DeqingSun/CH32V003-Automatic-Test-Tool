#ifndef CH446Q_MATRIX_H
#define CH446Q_MATRIX_H

#include "ch446q_driver.h"

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
