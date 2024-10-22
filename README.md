# Big Ladder Boilerplate

This project is a boiler-plate generator for multiple types of source code.
Using this project, new source code repositories can be set up **and** updated from an authoratative template source.


## Concepts

Template Repository: a repository of files that serve as templates
- can be specified by git url + branch/checkout, plain url, or directory path
- if downloaded, stores in .boilerplate/ directory in HOME directory

manifest.toml: indicates the types of files in template repository
- files can be
  - static (direct copy)
  - template (a context is needed to render them)
  - built based on some source (e.g., files in a directory matching a pattern)

boilerplate.toml: the in-project config information for boilerplate
- this is meant to be the "single-source of truth" for items specified


## Usage




## Reference

Poetry and Helix
https://blog.jorisl.nl/helix_python_lsp/
