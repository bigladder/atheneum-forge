if(CMAKE_SYSTEM_NAME STREQUAL Windows)

    # Set the Windows SDK version (e.g., 10.0.22000.0)
    # CMAKE_SYSTEM_VERSION (defaults to CMAKE_HOST_SYSTEM_VERSION) is ignored in CMake 3.27+
    # CMAKE_GENERATOR_PLATFORM is strict

    set(CMAKE_GENERATOR_PLATFORM version=10.0.26100)

    # Set the platform toolset (e.g., v143 for Visual Studio 2022)
    set(CMAKE_GENERATOR_TOOLSET "v143")
    set(VS_PLATFORM_TOOLSET_VERSION "14.31.31103")

endif()
