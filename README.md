# Atheneum Forge

This project is a boiler-plate generator.
Although it is intended to support multiple types of source code, it currently only supports C++.

In contrast to a static template, the main ideas of the project are to:

- not only be able to generate a "scaffolding" for a new (or existing) project
- but **ALSO** be able to keep that "scaffolding" up-to-date based on an authoratative source
- and also automate several project-level tasks such as:
    - version updating
    - checking submodules (fmt, google test, courier) to see if there are newer versions and automating their update
    - keeping copyright headers up-to-date
    - automating the addition of "include guards" (for C++)


## Current Status

This project is still young.
However, we have demonstrated the ability to generate/update the boilerplate for the ERIN project.
In so doing, no capability was lost and that project still builds and passes all tests.

The "task helper" system mentioned above only has one item implemented:

- automation of copyright header checking

The remainder of the tasks remain to be implemented.

We'll know this project is mature when it can apply the python templates (pytheneum) to itself.

As a suggestion, as we have needs to do a given task, we can add it here.
Also, we can continue to roll it out one-by-one to different company projects and fix edge cases as they arise.


## Concepts

**Template Repository**: an authoratative repository of files that serve as templates

- currently included in this repository's data directory

**Target Repository**: the actual source code repository to create / update

- this is the recipient of the template generation process

**manifest.toml**: provides parameters and indications of how files in the template repository should be used

- also includes information on dependencies

**config.toml**: the in-project configuration information for this tool

- overrides and provides key parameters from the manifest
- this is meant to be the "single-source of truth" for items specified within


## Usage

We hope to be able to get this project up on PyPI so that it will just be a pip install away!

In the mean time, it can be used with the uv dependency manager:

```
> # clone the repository
> uv sync
> uv run aforge --help
> uv run aforge init-with-config path/to/new-or-existing/repo/ cpp
> # edit the generated config.toml, fill in required data
> # now generate or update the scaffolding/boilerplate
> aforge gen path/to/new-or-existing/repo/config.toml cpp
```

## Reference

Poetry and Helix -- how to bring the Helix editor into context with a Python app being developed
https://blog.jorisl.nl/helix_python_lsp/
