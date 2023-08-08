# Blender Libraries for CAD Modeling

This repository contains some utilities to make CAD modeling in Blender easier.

These utilities were mainly inspired by [OpenSCAD](https://openscad.org/).
They make it possible to have a similar workflow to OpenSCAD, where you can
define CAD models in code and automatically see the render update whenever you
edit your code.  However, your CAD models can now be written purely in Python,
and using Blender's more powerful set of mesh operators and utilities.

# Auto-update on code changes

`bpycad/dev_main.py` contains a `main()` helper function that makes it easy to
run your CAD code to create objects in Blender, and automatically re-run it
whenever your code changes.

To use it, pass in the function that generates your CAD objects, as well as a
set of package or module names to monitor for changes.  Whenever any change is
detected on disk to the monitored packages, the existing Blender scene will be
deleted and your CAD function will be re-run to re-generate the objects.

# Generate STL files from the command line

The `bpycad/export_stl.py` module contains a `main()` helper function that
helps build a command line script to export STL files from your CAD models.

To use it, create your own script that wraps this function, and invokes it with
a dictionary containing all of your model functions.
`bpycad.export_stl.main()` will then parse the command line arguments to allow
exporting STL files for all of your models, or just specific ones, depending on
the command line arguments.

# Utility Libraries

This repository also contains a few other utility libraries for doing mesh
editing.

`bpycad/cad.py` contains functions for defining and manipulating 3D
points/vectors/meshes.  This code is generally independent from Blender, and is
used to create meshes that you can manipulate on your own, and later turn into
a Blender mesh object.

`bpycad/blender_util.py` contains functions for manipulating Blender mesh
objects, plus some other utility functions for interacting with Blender.

In general the lower-level code in `cad.py` gives you a lot of flexibility to
exactly define the vertices and faces you want.  This makes it easy to
programmatically place vertices, and create faces exactly connecting different
parts of your model.  The higher level `blender_util.py` module then makes it
easier to manipulate your mesh with higher-level operators, like boolean
intersection/union/difference operators, hull, bevel operators, subdivision, or
other mesh clean-up operators.

Neither of these modules currently has a stable API, and they may be refactored
in the future.
