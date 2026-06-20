# PROTON

**P**hysics-informed **R**adiation **O**perators and **T**ime-series **O**ptimized **N**etworks

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)


## What is the plan for PROTON?

I plan to make PROTON an open-source Python library for quantitative inference via low-cost radiation detectors. What will happen is that it'll take the raw output of consumer instruments, the pulse trains and count rates of Geiger-Muller tubes and the energy spectra of a small scintillation spectrometer, and then turn it into physical quantities that the raw readings do not give us directly. The library will be organized as a set of independent but composable modules.


## About the Hardware Setup

**Getting your own detectors is not strictly neccesary to use PROTON**.
 I included a detector setup for how I produced my own data, but you can add in data from other sources. PROTON can use any data in the same format, but I will also include sample data to use the software as if you had a geiger counter but not a gamma spectrometer, you'd need gamma spectrometer data to use all aspects of this software. You could also run it with my example data too. You also don't have to use the exact same sensors as me, but I will include my hardware and sensor setup in case you'd like to copy it. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup!


# Current State/Updates

06/17/2026: 
Currently working on making a way to use PROTON without hardware or with alternative hardware! I am working on the geiger counts device classes right now and I'm working on making a specific class for my hardware, and then a general class that'll work without hardware or with one's own hardware choices.


I will be updating this throughout the year! Stay tuned!
