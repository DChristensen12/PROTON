# PROTON

**P**hysics-informed **R**adiation **O**perators and **T**ime-series **O**ptimized **N**etworks

[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)[![license](https://img.shields.io/github/license/DChristensen12/PROTON)](https://github.com/DChristensen12/PROTON/blob/main/LICENSE)[![tests](https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml/badge.svg)](https://github.com/DChristensen12/PROTON/actions/workflows/tests.yml)


## What is PROTON?

This is a library for radiation data inference and visualization! Feed it the runs I bundle in or readings you collect yourself, pull real physical quantities out of raw counts and spectra, and turn the whole thing into organized tables and plots you can actually read. 


## About the Hardware Setup

**Getting your own detectors is not strictly neccesary to use PROTON**.
PROTON is about using data, not acquiring it. It comes with collected data, so you can run every part of the software without buying a single detector (I included collected data for this scenario).
My detector setup is included for how I produced my own data, in case you want to reproduce my setup. PROTON can use any data in the same format, so you can also include data from other sources or ones you collected yourself. You could also swap out any number of the detectors for your own, for example if you had a geiger counter but not a gamma spectrometer, you could just use the gamma spectrometer data I included to use all aspects of this software. 

See [docs/hardware.md](docs/hardware.md) for additional information on the hardware setup!


# Current State/Updates

07/09/2026:  

While setting up my detector for geiger_pulses, I started having to add more hardware code than I initially intended. Since I want PROTON to be about using data for inference and visualization, I am going to make a branch, fix complete hardware code entirely, then edit how the classes work to ensure that PROTON can easily be used without any hardware (just a supported feature for actual research purposes). I will ensure the General Device classes work without hardware and work exactly like hardware (I'll call it parity tests for my testing of it), and that everything relating to actual hardware is optional and not directly bundled in with the main purposes of PROTON. Since this'll be a big change (likely making data.handler a huge file and changing some parts of the detector classes), I'm putting this one on a branch, separate from main. I'll merge with main when I'm confident the hardware section fits into PROTON exactly how I want it to. 

I will be updating this throughout the year! Stay tuned!
