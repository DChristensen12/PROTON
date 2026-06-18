# PROTON

**P**hysics-informed **R**adiation **O**perator and **T**ime-series **O**ptimized **N**etwork

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)

## What is the plan for PROTON?

I plan to make PROTON an open-source Python library for quantitative inference via low-cost radiation detectors. What will happen is that it'll take the raw output of consumer instruments, the pulse trains and count rates of Geiger-Muller tubes and the energy spectra of a small scintillation spectrometer, and then turn it into physical quantities that the raw readings do not give us directly. The library will be organized as a set of independent but composable modules.

Getting hardware is not strictly neccesary to use PROTON. PROTON can use any data in the same format, but I will also include sample data to use the software as if you had a geiger counter but not a gamma spectrometer, you'd need gamma spectrometer data to use all aspects of this software. You could also run it with my example data too. You also don't have to use the exact same sensors as me, but I will include my hardware and sensor setup in case you'd like to copy it. 

## Hardware I am Using

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup!

### Sensors

1.) FNIRSI GC-01 with the M4011 tube type, flashed with Rad Pro firmware.
2.) GGreg20_V3 with the J305 tube
3.) Radiacode 102


# Current State/Updates

06/17/2026: 
Currently working on making a way to use PROTON without hardware or with alternative hardware! I am working on the geiger counts device classes right now and I'm working on making a specific class for my hardware, and then a general class that'll work without hardware or with one's own hardware choices.

![FNIRSI GC-01](docs/images/geiger_counts.jpeg)
![Radiacode 102](docs/images/gamma_spectrometer.jpeg)
![GGreg20 board with the J305 tube](docs/images/geiger_pulses.jpeg)


I will be updating this throughout the year! Stay tuned!
