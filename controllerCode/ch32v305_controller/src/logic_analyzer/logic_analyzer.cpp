#include "logic_analyzer.h"

bool analogCaptureIsBusy();

extern "C" {
#include "ch32yyxx_dma.h"
#include "ch32yyxx_tim.h"
#include "ch32yyxx_rcc.h"
#include "ch32yyxx_misc.h"
}

// Requires 192K RAM linker script + chip option FLASH-128K + RAM-192K (boardPrepare.md).
static uint8_t la_buffer[LA_BUFFER_SIZE];

static volatile bool la_capture_done = false;
static volatile bool la_capture_busy = false;
static uint32_t la_remaining = 0;
static uint32_t la_buf_offset = 0;
static uint16_t la_current_chunk = 0;
static uint32_t la_actual_rate_hz = 0;
static uint32_t la_sample_count = 0;
static bool la_hw_initialized = false;

static const uint32_t LA_TIMER_CLK_HZ = 144000000UL;
static const uint32_t LA_MIN_PERIOD_TICKS = 10U;
static const uint16_t LA_DMA_MAX_CHUNK = 65535U;

static bool laComputeTim7Period(uint32_t rateHz, uint16_t *psc, uint16_t *arr,
                                uint32_t *actualRateHz) {
  if (rateHz == 0) {
    return false;
  }

  uint64_t period = (uint64_t)LA_TIMER_CLK_HZ / (uint64_t)rateHz;
  if (period < LA_MIN_PERIOD_TICKS) {
    return false;
  }
  if (period > (uint64_t)65536 * 65536ULL) {
    return false;
  }

  if (period <= 65536ULL) {
    *psc = 0;
    *arr = (uint16_t)(period - 1ULL);
  } else {
    *psc = (uint16_t)((period - 1ULL) / 65536ULL);
    uint32_t div = (uint32_t)(period / ((uint64_t)(*psc) + 1ULL));
    if (div == 0 || div > 65536U) {
      return false;
    }
    *arr = (uint16_t)(div - 1U);
  }

  uint32_t ticks = (uint32_t)(*psc + 1U) * (uint32_t)(*arr + 1U);
  *actualRateHz = LA_TIMER_CLK_HZ / ticks;
  return true;
}

/* Enable GPIOA clock only — do not change pin modes so OUTPUT drive is kept. */
static void laConfigureInputs() {
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
}

static void laInitDmaChannel() {
  RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA2, ENABLE);
  DMA_DeInit(DMA2_Channel4);

  DMA_InitTypeDef dmaInit;
  DMA_StructInit(&dmaInit);
  dmaInit.DMA_PeripheralBaseAddr = (uint32_t)&GPIOA->INDR;
  dmaInit.DMA_MemoryBaseAddr = (uint32_t)la_buffer;
  dmaInit.DMA_DIR = DMA_DIR_PeripheralSRC;
  dmaInit.DMA_BufferSize = 0;
  dmaInit.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
  dmaInit.DMA_MemoryInc = DMA_MemoryInc_Enable;
  dmaInit.DMA_PeripheralDataSize = DMA_PeripheralDataSize_Byte;
  dmaInit.DMA_MemoryDataSize = DMA_MemoryDataSize_Byte;
  dmaInit.DMA_Mode = DMA_Mode_Normal;
  dmaInit.DMA_Priority = DMA_Priority_High;
  dmaInit.DMA_M2M = DMA_M2M_Disable;
  DMA_Init(DMA2_Channel4, &dmaInit);

  DMA_ITConfig(DMA2_Channel4, DMA_IT_TC, ENABLE);

  NVIC_InitTypeDef nvicInit;
  nvicInit.NVIC_IRQChannel = DMA2_Channel4_IRQn;
  nvicInit.NVIC_IRQChannelPreemptionPriority = 1;
  nvicInit.NVIC_IRQChannelSubPriority = 0;
  nvicInit.NVIC_IRQChannelCmd = ENABLE;
  NVIC_Init(&nvicInit);
}

static void laInitTim7(uint32_t rateHz) {
  uint16_t psc = 0;
  uint16_t arr = 0;
  if (!laComputeTim7Period(rateHz, &psc, &arr, &la_actual_rate_hz)) {
    la_actual_rate_hz = 0;
    return;
  }

  RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM7, ENABLE);
  TIM_DeInit(TIM7);

  TIM_TimeBaseInitTypeDef timInit;
  TIM_TimeBaseStructInit(&timInit);
  timInit.TIM_Prescaler = psc;
  timInit.TIM_Period = arr;
  timInit.TIM_ClockDivision = TIM_CKD_DIV1;
  timInit.TIM_CounterMode = TIM_CounterMode_Up;
  TIM_TimeBaseInit(TIM7, &timInit);
  TIM_DMACmd(TIM7, TIM_DMA_Update, ENABLE);
}

static void laStartDmaChunk(uint16_t chunk) {
  DMA_Cmd(DMA2_Channel4, DISABLE);
  DMA2_Channel4->MADDR = (uint32_t)(la_buffer + la_buf_offset);
  DMA_SetCurrDataCounter(DMA2_Channel4, chunk);
  DMA_ClearITPendingBit(DMA2_IT_TC4);
  DMA_Cmd(DMA2_Channel4, ENABLE);
  la_current_chunk = chunk;
}

static void laStopCaptureHardware() {
  TIM_Cmd(TIM7, DISABLE);
  TIM_DMACmd(TIM7, TIM_DMA_Update, DISABLE);
  DMA_Cmd(DMA2_Channel4, DISABLE);
}

extern "C" void DMA2_Channel4_IRQHandler(void)
    __attribute__((interrupt("WCH-Interrupt-fast")));

extern "C" void DMA2_Channel4_IRQHandler(void) {
  if (DMA_GetITStatus(DMA2_IT_TC4) == RESET) {
    return;
  }

  DMA_ClearITPendingBit(DMA2_IT_TC4);
  la_buf_offset += la_current_chunk;
  la_remaining -= la_current_chunk;

  if (la_remaining > 0) {
    uint16_t chunk = (la_remaining > LA_DMA_MAX_CHUNK) ? LA_DMA_MAX_CHUNK
                                                       : (uint16_t)la_remaining;
    laStartDmaChunk(chunk);
    return;
  }

  laStopCaptureHardware();
  la_capture_done = true;
}

bool logicAnalyzerIsBusy() {
  return la_capture_busy;
}

LogicAnalyzerResult logicAnalyzerStart(uint32_t rateHz, uint32_t sampleCount,
                                       uint32_t *actualRateHz) {
  if (la_capture_busy || analogCaptureIsBusy()) {
    return LA_ERR_BUSY;
  }
  if (sampleCount == 0 || sampleCount > LA_BUFFER_SIZE) {
    return LA_ERR_BAD_COUNT;
  }

  uint16_t psc = 0;
  uint16_t arr = 0;
  uint32_t actualRate = 0;
  if (!laComputeTim7Period(rateHz, &psc, &arr, &actualRate)) {
    return LA_ERR_BAD_RATE;
  }

  la_capture_busy = true;
  la_capture_done = false;
  la_remaining = sampleCount;
  la_buf_offset = 0;
  la_sample_count = sampleCount;
  la_actual_rate_hz = actualRate;

  laConfigureInputs();

  if (!la_hw_initialized) {
    laInitDmaChannel();
    la_hw_initialized = true;
  }

  laInitTim7(rateHz);
  if (la_actual_rate_hz == 0) {
    la_capture_busy = false;
    return LA_ERR_BAD_RATE;
  }

  uint16_t firstChunk = (sampleCount > LA_DMA_MAX_CHUNK) ? LA_DMA_MAX_CHUNK
                                                         : (uint16_t)sampleCount;
  laStartDmaChunk(firstChunk);
  TIM_Cmd(TIM7, ENABLE);

  if (actualRateHz != nullptr) {
    *actualRateHz = la_actual_rate_hz;
  }
  return LA_OK;
}

LogicAnalyzerPollState logicAnalyzerPoll(Stream &out) {
  if (!la_capture_busy) {
    out.println("L:IDLE");
    return LA_POLL_IDLE;
  }

  if (!la_capture_done) {
    out.println("L:RUNNING");
    return LA_POLL_RUNNING;
  }

  out.print("L:OK,");
  out.print(la_sample_count);
  out.print(",");
  out.println(la_actual_rate_hz);
  logicAnalyzerUpload(out, la_sample_count, la_actual_rate_hz);

  la_capture_busy = false;
  la_capture_done = false;
  return LA_POLL_DONE;
}

const uint8_t *logicAnalyzerBuffer() {
  return la_buffer;
}

static void laPrintHexByte(Stream &out, uint8_t value) {
  static const char hex[] = "0123456789ABCDEF";
  out.write(hex[(value >> 4) & 0x0FU]);
  out.write(hex[value & 0x0FU]);
}

static void laPrintHexU32(Stream &out, uint32_t value) {
  for (int shift = 28; shift >= 0; shift -= 4) {
    static const char hex[] = "0123456789ABCDEF";
    out.write(hex[(value >> shift) & 0x0FU]);
  }
}

void logicAnalyzerUpload(Stream &out, uint32_t sampleCount, uint32_t rateHz) {
  (void)rateHz;

  out.println("L:DATA");
  for (uint32_t offset = 0; offset < sampleCount; offset++) {
    if ((offset % 16U) == 0U) {
      if (offset > 0U) {
        out.println();
      }
      laPrintHexU32(out, offset);
      out.print(':');
    }
    out.print(' ');
    laPrintHexByte(out, la_buffer[offset]);
  }
  if (sampleCount > 0U) {
    out.println();
  }
  out.println("L:END");
  out.flush();
}
