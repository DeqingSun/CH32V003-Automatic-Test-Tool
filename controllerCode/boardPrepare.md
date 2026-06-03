# CH32V305CCT6

We want to use config "FLASH-128K + RAM-192K" to maximize RAM for data capture. And the link file is prepared for that. But a new chip does not come with this config. CH32V305CCT6 does not support USB flash so we can connect WCH-LinkE, and use WCH-LinkUtility on windows to set "FLASH-128K + RAM-192K". Otherwise we get hardfault on RAM write failure.

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


