# PROTON

**P**hysics-informed **R**adiation **O**perators and **T**ime-series **O**ptimized **N**etworks

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)


## What is the plan for PROTON?

I plan to make PROTON an open-source Python library for quantitative inference via low-cost radiation detectors. What will happen is that it'll take the raw output of consumer instruments, the pulse trains and count rates of Geiger-Muller tubes and the energy spectra of a small scintillation spectrometer, and then turn it into physical quantities that the raw readings do not give us directly. The library will be organized as a set of independent but composable modules.


## About the Hardware Setup

**Getting your own detectors is not strictly neccesary to use PROTON**.
PROTON is about using data, not acquiring it. It comes with collected data, so you can run every part of the software without buying a single detector (I included collected data for this scenario).
My detector setup is included for how I produced my own data, in case you want to reproduce my setup. PROTON can use any data in the same format, so you can also include data from other sources or ones you collected yourself. You could also swap out any number of the detectors for your own, for example if you had a geiger counter but not a gamma spectrometer, you could just use the gamma spectrometer data I included to use all aspects of this software. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup!


# Current State/Updates

06/30/2026:  
I have been writing tests for geiger_counts, trying to be extra thorough, though I might ease off due to it taking a long time to make all these tests. Everything will still get tested, just not at this depth that I currently am doing. 

I will be updating this throughout the year! Stay tuned!
