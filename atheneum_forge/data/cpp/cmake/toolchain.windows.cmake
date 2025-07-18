if(CMAKE_SYSTEM_NAME STREQUAL Windows)

    # Set the Windows SDK version (e.g., 10.0.22000.0)
    set(CMAKE_SYSTEM_VERSION 10.0.26100.0)

    # Set the platform toolset (e.g., v143 for Visual Studio 2022)
    set(CMAKE_GENERATOR_TOOLSET "v143")
    set(VS_PLATFORM_TOOLSET_VERSION "14.31.31103")

    # Optional: Specify the system name and processor
    set(CMAKE_SYSTEM_NAME Windows)
    set(CMAKE_SYSTEM_PROCESSOR x64)

endif()
