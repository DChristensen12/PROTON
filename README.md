# PROTON

**P**hysics-informed **R**adiation **O**perators and **T**ime-series **O**ptimized **N**etworks

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)[![tests](https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml/badge.svg)](https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml)


## What is PROTON?

This is a library for radiation data inference and visualization! Feed it the runs I bundle in or readings you collect yourself, pull real physical quantities out of raw counts and spectra, and turn the whole thing into organized tables and plots you can actually read. 


## Hardware Support

**PROTON has some built in hardware support, though it is important to note that getting your own detectors is not necessary to use PROTON**. 

PROTON is about using data, not acquiring it. However, using one's own detectors for research or personal projects is a natural extension of PROTON, which is why we offer a built in support for it. PROTON was built to be easily extendable to new devices. 

Direct support was built for three detectors (detailed in `hardware.md`) because they cover distinct kinds of measurements: a geiger counter for polled count rates, a geiger counter pulse device for the per-pulse inter-arrival timing, and a gamma spectrometer for energy spectra. However, general device classes and `data_handler.py` were built to be easy to modify or extend with new functionality, whether that is a different detector of the same type or a different kind of device entirely. The general classes take data from wheverever you have it, so using PROTON for new detectors is a matter of handling your readings rather than changing anything inside PROTON. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup (such as detailed examples of wiring, topology, and detector setups)!

# Current State/Updates

07/13/2026:  

I am going to refactor the hardware section with my `data_handler.py`. The thing that was bothering me was that the data handling seemed very inefficient. It also made it complicated to do the no hardware option, so I'm formulating all the data handling in `data_handler.py`, then refactoring the hardware support around it. Hardware is a supported feature for research and citizen science, not the main purpose of PROTON itself, so I'll fix it up as such. I'll merge the branch after the data handling is fixed and the hardware code is refactored and validated. I'll make the first release whenever I have the hardware support, first feature (PINNs, FNOs, etc) implemented, and the first visualizations and color themes are correctly implemented. As always, the updates will be public and visible in the commits and here in the current State/Updates! 

I will be updating this throughout the year! Stay tuned!
