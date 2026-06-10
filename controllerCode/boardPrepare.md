# CH32V305CCT6

We want to use config "FLASH-128K + RAM-192K" to maximize RAM for data capture. And the link file is prepared for that. But a new chip does not come with this config. CH32V305CCT6 does not support USB flash so we can connect WCH-LinkE, and use WCH-LinkUtility on windows to set "FLASH-128K + RAM-192K". Otherwise we get hardfault on RAM write failure.

When using minichlink, a new chip has "USER/RDPR  : 609f/5aa5   DATA1/DATA0: ff00/ff00   WRPR1/WRPR0: 00ff/00ff   WRPR3/WRPR2: 00ff/00ff"

Do "./minichlink -C linke -S 128 192" and we get "USER/RDPR  : 20df/5aa5  DATA1/DATA0: e339/e339   WRPR1/WRPR0: e339/e339   WRPR3/WRPR2: e339/e339"

Then the chip can run the code normally.

# CH32V305FBP6

After basic ch446q serial code runs on CH32V305CCT6. Plug off-board WCH-LinkE, SWCLK to X0, SWDIO to X1. And we send serial command to connect X0 to X9 via Y6, X1 to X8 via Y7.

```
C006
C096
C017
C087

```

And then, ```./minichlink -i``` can detect the target CH32V305.

```
./minichlink -p -a -w WCH-LinkE-APP-IAP.bin 0x08000000 -b 
```

and the new LinkE appears!

# Test Target

Use jumper to connect VCC and GND. Pin 18, X17 is SWDIO

```
C117
C087
```

And it works!

```
./minichlink -l 2C868F06B189 -i
minichlink version - 23691953bf211f3fd8a9c60103d93dd7a4ab3d5f
Found WCH Link
WCH Programmer is LinkE version 2.21
Detected CH32V003
Flash Storage: 16 kB
Part UUID: e0-f3-ab-cd-4a-ab-bd-eb
Part Type: 00-30-05-10
Read protection: disabled
Interface Setup
USER/RDPR  : e817/5aa5
DATA1/DATA0: ff00/ff00
WRPR1/WRPR0: 00ff/00ff
WRPR3/WRPR2: 00ff/00ff
R32_ESIG_UNIID1: e0f3abcd
R32_ESIG_UNIID2: 4aabbdeb
R32_ESIG_UNIID3: ffffffff
```

