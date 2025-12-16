# Atheneum Forge

This project is a boiler-plate generator.
In contrast to a static template, the main ideas of the project are to:

- not only be able to generate a "scaffolding" for a new (or existing) project
- but **ALSO** be able to keep that "scaffolding" up-to-date based on an authoratative source
- and also automate several project-level tasks such as:
    - version updating
    - checking submodules (fmt, google test, courier) to see if there are newer versions and automating their update
    - adding copyright headers
    - automating the addition of "include guards" (for C++)


## Usage

### From Github
Atheneum-forge can be run as an executable directly from Github, with the [uv dependency manager](https://docs.astral.sh/uv/getting-started/installation/):

```
> uvx --from git+https://github.com/bigladder/atheneum-forge.git forge-cli init . <project_name> --type <cpp | python>
```
or
```
> uvx --from git+https://github.com/bigladder/atheneum-forge.git forge
```

### From a clone
The atheneum-forge tool can be used directly from the repository directory, or built into a package.The project is managed with the uv depenency manager; to build, simply use command "uv build" from the atheneum-forge top directory.

Installing the atheneum-forge package will provide two command-line tools: a TUI (text user interface) and a command-line-app.

* _forge-cli_ allows the user to view all project-generation functionality at a glance;

* _forge_ can be called with arguments to implement one piece of functionality at a time (_forge --help_).

Project generation consists of two steps, which may be combined. First, a configuration file is generated (forge.toml), which contains default settings such as the project name and type. If more detailed defaults are desired, the _forge.toml_ file contains project-relevant settings that can be activated by removing the comment character. The project-generation step will automatically import these settings to populate project files (primarily support and build files).

>**Note**
>
>On some Windows PCs, the forge TUI may render with unexpected characters. For a cleaner experience, download and [install](https://support.microsoft.com/en-us/office/add-a-font-b7c5f17c-4426-4b53-967f-455339c564c1) a [Nerd Font](https://www.nerdfonts.com/font-downloads) (such as FiraCode).

## For developers

For each language to be supported by a project template, the _languages_ directory contains a <language_name> entry. Currently C++ and Python are supported. Each language pack consists of three conceptual pieces:

**Project directory tree**

The canonical folder structure for open-source projects, with any standard, non-customizable files that are simply copied into a new project.

**Templates**:

Files within the folder structure that must be customized (e.g. with the project name) are stored as Jinja templates with a .j2 extension. These are rendered using default parameter values before being copied into a new project.

**manifest.toml**: provides parameters and indications of how files in the template repository should be used

The manifest is a complete description of every file that comprises a project scaffold. Its sections are:
* _static_: a list of files or directories to be copied directly
* _template_: a list of files that will be modified before copying
* _template-parameters_: a list of substitution parameters for the templates
* _deps_: a set of dictionaries describing submodule dependencies


TODO: Format of manifest, to/from options, extra keywords


## Reference

Poetry and Helix -- how to bring the Helix editor into context with a Python app being developed
https://blog.jorisl.nl/helix_python_lsp/
