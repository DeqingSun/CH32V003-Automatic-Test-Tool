#include "analog_capture.h"

#include "../logic_analyzer/logic_analyzer.h"

extern "C" {
#include "ch32yyxx_adc.h"
#include "ch32yyxx_dma.h"
#include "ch32yyxx_tim.h"
#include "ch32yyxx_rcc.h"
#include "ch32yyxx_misc.h"
}

bool logicAnalyzerIsBusy();

static volatile bool ac_capture_done = false;
static volatile bool ac_capture_busy = false;
static uint32_t ac_remaining = 0;
static uint32_t ac_buf_offset = 0;
static uint16_t ac_current_chunk = 0;
static uint32_t ac_actual_rate_hz = 0;
static uint32_t ac_time_samples = 0;
static uint8_t ac_channel_mask = 0;
static uint8_t ac_num_channels = 0;
static bool ac_hw_initialized = false;

static const uint32_t AC_TIMER_CLK_HZ = 144000000UL;
static const uint32_t AC_MIN_PERIOD_TICKS = 10U;
static const uint16_t AC_DMA_MAX_CHUNK = 65535U;
static const uint32_t AC_ADC_CLK_HZ = 9000000UL;
static const uint32_t AC_ADC_CYCLES_PER_CH = 20U;

static uint8_t acPopcount(uint8_t mask) {
  uint8_t count = 0;
  for (uint8_t i = 0; i < 8; i++) {
    if (mask & (1U << i)) {
      count++;
    }
  }
  return count;
}

static void acChannelsFromMask(uint8_t mask, uint8_t *channels, uint8_t *numChannels) {
  uint8_t count = 0;
  for (uint8_t i = 0; i < 8; i++) {
    if (mask & (1U << i)) {
      channels[count++] = i;
    }
  }
  *numChannels = count;
}

static bool acComputeTim3Period(uint32_t rateHz, uint16_t *psc, uint16_t *arr,
                                uint32_t *actualRateHz) {
  if (rateHz == 0) {
    return false;
  }

  uint64_t period = (uint64_t)AC_TIMER_CLK_HZ / (uint64_t)rateHz;
  if (period < AC_MIN_PERIOD_TICKS) {
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
  *actualRateHz = AC_TIMER_CLK_HZ / ticks;
  return true;
}

static bool acValidateRate(uint32_t rateHz, uint8_t numChannels, uint32_t *actualRateHz) {
  uint16_t psc = 0;
  uint16_t arr = 0;
  uint32_t actualRate = 0;
  if (!acComputeTim3Period(rateHz, &psc, &arr, &actualRate)) {
    return false;
  }

  uint64_t minPeriodNs =
      ((uint64_t)numChannels * AC_ADC_CYCLES_PER_CH * 1000000000ULL) / AC_ADC_CLK_HZ;
  uint64_t reqPeriodNs = 1000000000ULL / (uint64_t)rateHz;
  if (reqPeriodNs < minPeriodNs) {
    return false;
  }

  if (actualRateHz != nullptr) {
    *actualRateHz = actualRate;
  }
  return true;
}

static void acConfigureAnalogInputs(uint8_t channelMask) {
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
  pinMode(PA4_ALT2, INPUT);
  pinMode(PA5_ALT2, INPUT);
  for (uint8_t i = 0; i < 8; i++) {
    if (channelMask & (1U << i)) {
      pinMode(PA0 + i, INPUT);
    }
  }
}

static void acConfigureAdc(uint8_t channelMask, uint8_t numChannels) {
  uint8_t channels[8];
  uint8_t count = 0;
  acChannelsFromMask(channelMask, channels, &count);
  (void)count;

  RCC_ADCCLKConfig(RCC_PCLK2_Div8);
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1, ENABLE);

  ADC_DeInit(ADC1);

  ADC_InitTypeDef adcInit;
  ADC_StructInit(&adcInit);
  adcInit.ADC_Mode = ADC_Mode_Independent;
  adcInit.ADC_ScanConvMode = ENABLE;
  adcInit.ADC_ContinuousConvMode = DISABLE;
  adcInit.ADC_ExternalTrigConv = ADC_ExternalTrigConv_T3_TRGO;
  adcInit.ADC_DataAlign = ADC_DataAlign_Right;
  adcInit.ADC_NbrOfChannel = numChannels;
  ADC_Init(ADC1, &adcInit);

  for (uint8_t rank = 0; rank < numChannels; rank++) {
    ADC_RegularChannelConfig(ADC1, channels[rank], rank + 1,
                             ADC_SampleTime_7Cycles5);
  }

  ADC_DMACmd(ADC1, ENABLE);
  ADC_Cmd(ADC1, ENABLE);

  ADC_ResetCalibration(ADC1);
  while (ADC_GetResetCalibrationStatus(ADC1)) {
  }
  ADC_StartCalibration(ADC1);
  while (ADC_GetCalibrationStatus(ADC1)) {
  }

  ADC_ExternalTrigConvCmd(ADC1, ENABLE);
}

static void acInitDmaChannel() {
  RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);
  DMA_DeInit(DMA1_Channel1);

  DMA_InitTypeDef dmaInit;
  DMA_StructInit(&dmaInit);
  dmaInit.DMA_PeripheralBaseAddr = (uint32_t)&ADC1->RDATAR;
  dmaInit.DMA_MemoryBaseAddr = (uint32_t)logicAnalyzerBuffer();
  dmaInit.DMA_DIR = DMA_DIR_PeripheralSRC;
  dmaInit.DMA_BufferSize = 0;
  dmaInit.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
  dmaInit.DMA_MemoryInc = DMA_MemoryInc_Enable;
  dmaInit.DMA_PeripheralDataSize = DMA_PeripheralDataSize_HalfWord;
  dmaInit.DMA_MemoryDataSize = DMA_MemoryDataSize_HalfWord;
  dmaInit.DMA_Mode = DMA_Mode_Normal;
  dmaInit.DMA_Priority = DMA_Priority_High;
  dmaInit.DMA_M2M = DMA_M2M_Disable;
  DMA_Init(DMA1_Channel1, &dmaInit);

  DMA_ITConfig(DMA1_Channel1, DMA_IT_TC, ENABLE);

  NVIC_InitTypeDef nvicInit;
  nvicInit.NVIC_IRQChannel = DMA1_Channel1_IRQn;
  nvicInit.NVIC_IRQChannelPreemptionPriority = 1;
  nvicInit.NVIC_IRQChannelSubPriority = 0;
  nvicInit.NVIC_IRQChannelCmd = ENABLE;
  NVIC_Init(&nvicInit);
}

static void acInitTim3(uint32_t rateHz) {
  uint16_t psc = 0;
  uint16_t arr = 0;
  if (!acComputeTim3Period(rateHz, &psc, &arr, &ac_actual_rate_hz)) {
    ac_actual_rate_hz = 0;
    return;
  }

  RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM3, ENABLE);
  TIM_DeInit(TIM3);

  TIM_TimeBaseInitTypeDef timInit;
  TIM_TimeBaseStructInit(&timInit);
  timInit.TIM_Prescaler = psc;
  timInit.TIM_Period = arr;
  timInit.TIM_ClockDivision = TIM_CKD_DIV1;
  timInit.TIM_CounterMode = TIM_CounterMode_Up;
  TIM_TimeBaseInit(TIM3, &timInit);
  TIM_SelectOutputTrigger(TIM3, TIM_TRGOSource_Update);
}

static void acStartDmaChunk(uint16_t chunk) {
  DMA_Cmd(DMA1_Channel1, DISABLE);
  DMA1_Channel1->MADDR =
      (uint32_t)((uint16_t *)logicAnalyzerBuffer() + ac_buf_offset);
  DMA_SetCurrDataCounter(DMA1_Channel1, chunk);
  DMA_ClearITPendingBit(DMA1_IT_TC1);
  DMA_Cmd(DMA1_Channel1, ENABLE);
  ac_current_chunk = chunk;
}

static void acStopCaptureHardware() {
  TIM_Cmd(TIM3, DISABLE);
  ADC_ExternalTrigConvCmd(ADC1, DISABLE);
  ADC_DMACmd(ADC1, DISABLE);
  ADC_Cmd(ADC1, DISABLE);
  DMA_Cmd(DMA1_Channel1, DISABLE);
}

extern "C" void DMA1_Channel1_IRQHandler(void)
    __attribute__((interrupt("WCH-Interrupt-fast")));

extern "C" void DMA1_Channel1_IRQHandler(void) {
  if (DMA_GetITStatus(DMA1_IT_TC1) == RESET) {
    return;
  }

  DMA_ClearITPendingBit(DMA1_IT_TC1);
  ac_buf_offset += ac_current_chunk;
  ac_remaining -= ac_current_chunk;

  if (ac_remaining > 0) {
    uint16_t chunk = (ac_remaining > AC_DMA_MAX_CHUNK) ? AC_DMA_MAX_CHUNK
                                                       : (uint16_t)ac_remaining;
    acStartDmaChunk(chunk);
    return;
  }

  acStopCaptureHardware();
  ac_capture_done = true;
}

bool analogCaptureIsBusy() {
  return ac_capture_busy;
}

AnalogCaptureResult analogCaptureStart(uint32_t rateHz, uint32_t timeSamples,
                                       uint8_t channelMask, uint32_t *actualRateHz) {
  if (ac_capture_busy || logicAnalyzerIsBusy()) {
    return AC_ERR_BUSY;
  }
  if (channelMask == 0) {
    return AC_ERR_BAD_CHANNELS;
  }

  uint8_t numChannels = acPopcount(channelMask);
  uint32_t totalHalfwords = timeSamples * (uint32_t)numChannels;
  if (timeSamples == 0 || totalHalfwords == 0 ||
      (totalHalfwords * 2U) > LA_BUFFER_SIZE) {
    return AC_ERR_BAD_COUNT;
  }

  uint32_t actualRate = 0;
  if (!acValidateRate(rateHz, numChannels, &actualRate)) {
    return AC_ERR_BAD_RATE;
  }

  ac_capture_busy = true;
  ac_capture_done = false;
  ac_remaining = totalHalfwords;
  ac_buf_offset = 0;
  ac_time_samples = timeSamples;
  ac_channel_mask = channelMask;
  ac_num_channels = numChannels;
  ac_actual_rate_hz = actualRate;

  acConfigureAnalogInputs(channelMask);

  if (!ac_hw_initialized) {
    acInitDmaChannel();
    ac_hw_initialized = true;
  }

  acConfigureAdc(channelMask, numChannels);
  acInitTim3(rateHz);
  if (ac_actual_rate_hz == 0) {
    ac_capture_busy = false;
    return AC_ERR_BAD_RATE;
  }

  uint16_t firstChunk = (ac_remaining > AC_DMA_MAX_CHUNK) ? AC_DMA_MAX_CHUNK
                                                          : (uint16_t)ac_remaining;
  acStartDmaChunk(firstChunk);
  TIM_Cmd(TIM3, ENABLE);

  if (actualRateHz != nullptr) {
    *actualRateHz = ac_actual_rate_hz;
  }
  return AC_OK;
}

AnalogCapturePollState analogCapturePoll(Stream &out) {
  if (!ac_capture_busy) {
    out.println("M:IDLE");
    return AC_POLL_IDLE;
  }

  if (!ac_capture_done) {
    out.println("M:RUNNING");
    return AC_POLL_RUNNING;
  }

  out.print("M:OK,");
  out.print(ac_time_samples);
  out.print(",");
  out.print(ac_actual_rate_hz);
  out.print(",");
  if (ac_channel_mask < 0x10U) {
    out.print('0');
  }
  out.println(ac_channel_mask, HEX);
  analogCaptureUpload(out, ac_time_samples, ac_channel_mask, ac_num_channels);

  ac_capture_busy = false;
  ac_capture_done = false;
  return AC_POLL_DONE;
}

static void acPrintHexNibble(Stream &out, uint8_t nibble) {
  static const char hex[] = "0123456789ABCDEF";
  out.write(hex[nibble & 0x0FU]);
}

static void acPrintHexU32(Stream &out, uint32_t value) {
  for (int shift = 28; shift >= 0; shift -= 4) {
    acPrintHexNibble(out, (uint8_t)(value >> shift));
  }
}

static void acPrintHexU16(Stream &out, uint16_t value) {
  for (int shift = 12; shift >= 0; shift -= 4) {
    acPrintHexNibble(out, (uint8_t)(value >> shift));
  }
}

void analogCaptureUpload(Stream &out, uint32_t timeSamples, uint8_t channelMask,
                         uint8_t numChannels) {
  (void)channelMask;
  const uint16_t *buffer = (const uint16_t *)logicAnalyzerBuffer();

  out.println("M:DATA");
  for (uint32_t timeIndex = 0; timeIndex < timeSamples; timeIndex++) {
    if ((timeIndex % 16U) == 0U) {
      if (timeIndex > 0U) {
        out.println();
      }
      acPrintHexU32(out, timeIndex);
      out.print(':');
    }
    for (uint8_t ch = 0; ch < numChannels; ch++) {
      out.print(' ');
      acPrintHexU16(out, buffer[timeIndex * numChannels + ch] & 0x0FFFU);
    }
  }
  if (timeSamples > 0U) {
    out.println();
  }
  out.println("M:END");
  out.flush();
}
