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

06/25/2026: 
Moving around a lot, so I didn't quite have a lot of time to add new things to PROTON. Right now, I am collecting data for geiger_counts to be used as default data (for the alternative hardware/ no hardware use cases of PROTON) and to ensure everything is working as intended. The current code works how I intended for it to, but I need to test that the data handling of both the RadProDevice class and GeneralCountsDevice class work perfectly as intended. I'll then write some Pytests for it and continue onto one of the other detectors!

I will be updating this throughout the year! Stay tuned!
