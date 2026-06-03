#include "ch446q_matrix.h"

CH446QMatrix::CH446QMatrix(
    uint8_t chip0Rst, uint8_t chip0Dat, uint8_t chip0Clk, uint8_t chip0Stb,
    uint8_t chip1Rst, uint8_t chip1Dat, uint8_t chip1Clk, uint8_t chip1Stb)
    : chip0_(chip0Rst, chip0Dat, chip0Clk, chip0Stb),
      chip1_(chip1Rst, chip1Dat, chip1Clk, chip1Stb) {}

void CH446QMatrix::init() {
  chip0_.init();
  chip1_.init();
}

void CH446QMatrix::reset() {
  chip0_.reset();
  chip1_.reset();
}

void CH446QMatrix::switchChannel(uint8_t x, uint8_t y, bool enabled) {
  uint8_t localX;
  chipForX(x, localX).switchChannel(localX, y, enabled);
}

void CH446QMatrix::saveMatrix() {
  chip0_.saveMatrix();
  chip1_.saveMatrix();
}

void CH446QMatrix::restoreMatrix() {
  chip0_.restoreMatrix();
  chip1_.restoreMatrix();
}

CH446Q& CH446QMatrix::chipForX(uint8_t x, uint8_t& localX) {
  if (x < kXPerChip) {
    localX = x;
    return chip0_;
  }
  localX = x - kXPerChip;
  return chip1_;
}
