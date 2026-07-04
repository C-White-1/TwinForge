# TwinForge

TwinForge is an open-source Python toolkit for building vendor-neutral
digital twins of industrial automation systems.

## Features

- Parse Studio 5000 L5X projects
- Discover EtherNet/IP devices
- Analyse controller-to-controller communications
- Build engineering object models
- Export AutomationML
- Export Asset Administration Shell (AAS)
- Generate dependency and topology graphs

## Roadmap

- L5X parser
- CIP discovery
- Communication analysis
- AutomationML export
- Asset Administration Shell export
- IEC 81346 integration

## Example

python
from twinforge.parsers import L5XParser

plant = L5XParser().parse("controller.l5x")

for controller in plant.iter_controllers():
    print(controller)
