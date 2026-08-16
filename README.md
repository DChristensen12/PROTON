<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/PROTON_LOGO_SOLID.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/PROTON_LOGO_SOLID.png">
    <img alt="PROTON logo" src="docs/images/PROTON_LOGO_SOLID.png" width="300">
  </picture>
</div>

<p align="center">
  <b>P</b>hysics-informed <b>R</b>adiation <b>O</b>perators and <b>T</b>ime-series <b>O</b>ptimized <b>N</b>etworks
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue"></a>
  <a href="https://github.com/DChristensen12/PROTON/blob/main/LICENSE"><img src="https://img.shields.io/github/license/DChristensen12/PROTON?color=ec4899"></a>
  <a href="https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml"><img src="https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://github.com/DChristensen12/PROTON"><img src="https://img.shields.io/badge/powered%20by-radioactive%20decay-75BBE7"></a>
</p>
  
</p>

## What is PROTON?

This is a library for radiation data inference and visualization! Feed it the runs I bundle in or readings you collect yourself, pull real physical quantities out of raw counts and spectra, and turn the whole thing into organized tables and plots you can actually read. 

## Hardware Support

**PROTON has some built in hardware support, though it is important to note that getting your own detectors is not necessary to use PROTON**. 

PROTON is about using data, not acquiring it. However, using one's own detectors for research or personal projects is a natural extension of PROTON, which is why we offer a built in support for it. PROTON was built to be easily extendable to new devices. 

Direct support was built for three detectors (detailed in `hardware.md`) because they cover distinct kinds of measurements: a geiger counter for polled count rates, a geiger counter pulse device for the per-pulse inter-arrival timing, and a gamma spectrometer for energy spectra. However, general device classes and `data_handler.py` were built to be easy to modify or extend with new functionality, whether that is a different detector of the same type or a different kind of device entirely. The general classes take data from wheverever you have it, so using PROTON for new detectors is a matter of handling your readings rather than changing anything inside PROTON. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup (such as detailed examples of wiring, topology, and detector setups)!

### Collecting Data

Every detector has a `record_` script to write a run to a csv, and the pulse detector and the spectrometer each also have a `check_` script to confirm the device is connected and running before you commit to a full run. For example, for the pulse detector:

```
python -m proton.Hardware.Detectors.geiger_pulses.check_pulses --count 20
python -m proton.Hardware.Detectors.geiger_pulses.record_pulses --duration 3600 --name background_room
```

The spectrometer follows the same check_/record_ pattern; the counts package only has the record_ script. The command details, parameters, wiring, and the Linux setup notes are also in [docs/hardware.md](docs/hardware.md). 

## Current State/Updates

08/16/2026:  

I am considering implementations, improvements, and decorative aspects of PROTON. Namely, I plan to improve the visualizations, add in a diffusion model, and make use of fourier neural operators while applying these ideas to draw insights.

I will be updating this throughout the year! Stay tuned!

<br>
<div align="right">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/PROTON_LOGO_STAMP.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/PROTON_LOGO_STAMP.png">
    <img alt="PROTON" src="docs/images/PROTON_LOGO_STAMP" width="60">
  </picture>
</div>