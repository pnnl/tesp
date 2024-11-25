# Design Notes

## Configuration file
1. We'll need a cofiguration parameter to override the residential customer parameters (primarily around DER penetration) and then specify new values (or a range of values).
   
## Software Architecture
1. TODO - TDH suspects that, to keep file lengths not crazy, we will want to split out a lot of the existing functionality into their own files and likely classes. Somebody needs to research how to do this right in Python.
2. TODO - We need to define good APIs for each class so that they can be sub-classed and re-used as much as possible. We're trying to make it as easy as possible for new users to understand what we're doing and modify it to suit their needs.
3. TDH proposes the following for our classes (but how do we not let this turn into exactly a list of GLD classes?)
- Feeder
- GLMModel
- GLMModifier
- House
- ZIPLoad
- Waterheater
- Solar
- Battery
- EV
- Inverter
- GLMBoilerplate
4. TODO - Figure out the definitions for each of the above classes. The GLD obj classes will likely have a similar structure. It could be a simple data class and if so, we could auto-generate the classes themselves from the GLD definitions in our entity stuff, right? Or maybe the entity stuff means we don't need these classes? I'm just trying to make the main files shorter by delegating the object parameter definitions out of the main file. If we pass in a Feeder object, the name of the object we need to define and its type, maybe that would work as a generic definition.