cmake_minimum_required(VERSION 3.20)
project(application_fonts LANGUAGES CXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
   message(FATAL_ERROR "This inspection consumer requires Linux")
endif()

find_package(CopperSpice 2.1.0 EXACT CONFIG REQUIRED)
add_executable(font-inspector font-inspector.cpp)
set_target_properties(font-inspector PROPERTIES
   CXX_STANDARD 20
   CXX_STANDARD_REQUIRED YES
   CXX_EXTENSIONS NO
)
target_link_libraries(font-inspector PRIVATE CopperSpice::CsCore CopperSpice::CsGui ${CMAKE_DL_LIBS})
