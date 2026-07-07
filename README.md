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

07/07/2026:  

PROTON will first be about using the geiger counters for radiation inference and visualizations, using a variety of techniques. Geiger counters are cheaper and more accessible in general, so that is my main reason for this small pivot.

I will still include early gamma spectrometer support, but specfically using it for future features are planned to be built out later on :)

I will be updating this throughout the year! Stay tuned!
