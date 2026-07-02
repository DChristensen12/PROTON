# PROTON

**P**hysics-informed **R**adiation **O**perators and **T**ime-series **O**ptimized **N**etworks

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)


## What is PROTON?

This is a library to make sense of your radiation data! Feed it the runs I bundle in or readings you collect yourself, pull real physical quantities out of raw counts and spectra, and turn the whole thing into clean tables and plots you can actually read. 


## About the Hardware Setup

**Getting your own detectors is not strictly neccesary to use PROTON**.
PROTON is about using data, not acquiring it. It comes with collected data, so you can run every part of the software without buying a single detector (I included collected data for this scenario).
My detector setup is included for how I produced my own data, in case you want to reproduce my setup. PROTON can use any data in the same format, so you can also include data from other sources or ones you collected yourself. You could also swap out any number of the detectors for your own, for example if you had a geiger counter but not a gamma spectrometer, you could just use the gamma spectrometer data I included to use all aspects of this software. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup!


# Current State/Updates

07/01/2026:  
I have been writing tests for geiger_counts, trying to be extra thorough, though I might ease off due to it taking a long time to make all these tests. Everything will still get tested, just not at this depth that I currently am doing. 

I am also reconsidering what PROTON would be useful for, and will reorganize accordingly.= The goal is to make a library that can produce useful insights to those who are interested in nuclear science (namely researchers, hobbyists, and students).

I will be updating this throughout the year! Stay tuned!
