# Big Ladder Boilerplate

This project is a boiler-plate generator.
Although it is intended to support multiple types of source code, it currently only supports C++.

In contrast to a static template, the main ideas of the project are to:

- not only be able to generate a "scaffolding" for a new (or existing) project
- but **ALSO** be able to keep that "scaffolding" up-to-date based on an authoratative source
- and also automate several project-level tasks such as:
  - version updating
  - keeping copyright headers up-to-date
  - automating the addition of "include guards" (for C++)


## Concepts

Template Repository: an authoratative repository of files that serve as templates
- currently included in this repository's data directory

Target Repository: the actual source code repository to create / update
- this is the recipient of the template generation process

manifest.toml: provides parameters and indications of how files in the template repository should be used
- also includes information on dependencies

config.toml: the in-project configuration information for this tool
- overrides and provides key parameters from the manifest
- this is meant to be the "single-source of truth" for items specified within


## Usage

We hope to be able to get this project up on PyPI so that it will just be a pip install away!

In the mean time, it can be used via poetry:

    > # clone the repository
    > poetry install
    > poetry shell
    > blbp --help
    > blbp init-with-config path/to/new-or-existing/repo/config.toml cpp
    > # edit the generated config.toml, fill in required data
    > # now generate or update the scaffolding/boilerplate
    > blbp gen path/to/new-or-existing/repo/config.toml cpp


## Reference

Poetry and Helix -- how to bring the Helix editor into context with a Python app being developed
https://blog.jorisl.nl/helix_python_lsp/
