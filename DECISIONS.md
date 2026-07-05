# Decisions

## 2026-06-29

### Domain model is the central API

All discovery modules populate the model classes.

Exporters never communicate directly with discovery code.

Reason:

Keeps online discovery, ACD parsing, and L5X parsing interchangeable.

## 2026-07-02

### Modules contain Identity objects

Identity information is not duplicated across model classes.

Reason:

Common representation for controllers, modules, drives and network devices.
