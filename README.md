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
I finished up the geiger_counts data collection feature! I collected an hour of data and will be using it as default_data (to ensure anyone can use all features of proton without having to purchase any detectors, I just think it is a cool feature to be able to use detectors). 
I'm now going to write some Pytests for it and make some more tweaks to the geiger_counts files (I need to still ensure there is a workaround for all devices if someone wants to use anything different from my setup).

I will be updating this throughout the year! Stay tuned!
