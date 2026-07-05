# twinforge Roadmap

A Python library for discovering, modelling and exporting Rockwell Automation
ControlLogix/CompactLogix systems as a vendor-neutral digital twin.

---

# Vision

Create a complete digital representation of a running Logix installation by combining

- CIP discovery
- Logix symbolic information
- network topology
- I/O relationships
- controller programs
- engineering metadata

The resulting model should be exportable to AutomationML, Asset Administration
Shell, Graph databases and other engineering tools.

---

# Current Status

## ✔ Project Structure

- [x] Modern Python package
- [x] uv project
- [x] Python 3.10 compatible
- [x] Dataclass-based domain model
- [x] Package layout established

---

## ✔ Domain Model

Implemented

- [x] Revision
- [x] Identity
- [x] Module
- [x] Chassis
- [x] Rack
- [x] Controller
- [x] Plant
- [x] Tag
- [x] Connection
- [x] Route
- [x] Network

Future

- [ ] Device
- [ ] Program
- [ ] Routine
- [ ] Task
- [ ] Port
- [ ] Assembly
- [ ] NetworkNode

---

# Phase 1
## Basic Discovery

Goal

Discover every reachable CIP device.

Tasks

- [ ] Identity Object scanner
- [ ] Chassis scanner
- [ ] Slot scanner
- [ ] Ethernet discovery
- [ ] ControlNet discovery
- [ ] Device inventory

Output

```
Plant
 └── Controller
      └── Chassis
            └── Modules
```

---
# Phase X

## Test Corpus

□ Basic controller

□ Produced Tags

□ MSG

□ Socket

□ AOI communications

□ Motion

□ Safety

□ CompactLogix

□ ControlLogix

□ Multi-controller
---
# Phase 2
## L5X Import




---
# Phase 3
## Communication Analysis

Goal

Discover every communication relationship in one or more Logix projects.

Features

□ Produced Tags

□ Consumed Tags

□ MSG Instructions

□ Socket Interface

□ CIP Generic

□ AOI communication wrappers

□ External IP addresses

□ Controller references

Outputs

Connection objects

Communication graph

Engineering report
---

# Phase 4
## Controller Discovery

Tasks

- [ ] Read controller identity
- [ ] Read controller name
- [ ] Enumerate tasks
- [ ] Enumerate programs
- [ ] Enumerate routines
- [ ] Enumerate tags

Output

Controller model

---

# Phase 5
## Module Discovery

Goal

Understand every module.

Tasks

- [ ] Read Identity Object
- [ ] Determine module family
- [ ] Determine communication protocol
- [ ] Determine backplane location
- [ ] Read module properties

Examples

1756-IB16

1756-OB16

1756-IF8

1756-OF8

1756-EN2T

1756-CN2R

1756-DHRIO

---

# Phase 6
## I/O Discovery

Goal

Build the producer/consumer graph.

Tasks

- [ ] Assembly Object discovery
- [ ] Connection Manager discovery
- [ ] Input assemblies
- [ ] Output assemblies
- [ ] Configuration assemblies
- [ ] Requested Packet Interval
- [ ] Connection size
- [ ] Ownership

Output

```
Controller

    ↓

Producer

    ↓

Assembly

    ↓

Consumer
```

---

# Phase 7
## Network Discovery

EtherNet/IP

- [ ] Topology
- [ ] Bridges
- [ ] Switches

ControlNet

- [ ] Bridges
- [ ] Remote chassis
- [ ] Node enumeration

DeviceNet

- [ ] Scanner
- [ ] Slave devices

---

# Phase 8
## Program Analysis

Tasks

- [ ] Cross references
- [ ] Alias detection
- [ ] AOI discovery
- [ ] UDT discovery
- [ ] Tag dependencies
- [ ] Program dependency graph

---

# Phase 9
## Digital Twin Construction

Construct

Plant

↓

Controllers

↓

Networks

↓

Chassis

↓

Modules

↓

Connections

↓

Assemblies

↓

Tags

↓

Programs

↓

Assets

---

# Phase 10
## Exporters

JSON

- [ ] Complete model

AutomationML

- [ ] CAEX

AAS

- [ ] Asset Administration Shell

Graphviz

- [ ] Dependency graph

Neo4j

- [ ] Knowledge graph

---

# Phase 11
## Parsers

- [ ] EDS
- [ ] ACD
- [ ] XML

---

# Phase 12
## Long-term Vision

Digital twin features

- [ ] Compare online vs offline
- [ ] Detect hardware changes
- [ ] Detect firmware drift
- [ ] Detect network changes
- [ ] Asset inventory
- [ ] Cable topology
- [ ] Signal tracing
- [ ] Automatic documentation
- [ ] Plant graph generation
- [ ] IEC 62424 integration
- [ ] IEC 81346 integration
- [ ] NAMUR MTP export
- [ ] OPC UA information model
- [ ] IEC 61850 mapping

---

# Stretch Goals

- [ ] Automatic EDS download
- [ ] FactoryTalk import
- [ ] Studio 5000 project reconstruction
- [ ] HMI tag correlation
- [ ] PlantPAx recognition
- [ ] Process object recognition
- [ ] Cable schedule generation

---

# Guiding Principles

1. Avoid heuristics where protocol data exists.
2. Prefer raw CIP over vendor-specific abstractions.
3. Keep the internal model vendor-neutral.
4. Separate discovery from modelling.
5. Make every layer independently testable.
6. Support offline reconstruction from ACD/L5X.
7. Design for future protocol support beyond Rockwell.


## Deferred Model Classes

These classes are expected to become part of the model but are not
implemented until sufficient live data has been analysed.

### Assembly

Status: Deferred

Represents a CIP Assembly Object.

Expected responsibilities:

- Input Assembly
- Output Assembly
- Configuration Assembly
- Assembly instance
- Data size
- Producer/Consumer relationship

Introduced when:

- Live IO Assembly discovery is implemented.


### Channel

Status: Deferred

Represents a physical IO point on a module.

Expected responsibilities:

- Channel number
- Signal direction
- Data type
- Engineering units
- Scaling
- Diagnostic state

Introduced when:

- Module-specific decoders are implemented.
