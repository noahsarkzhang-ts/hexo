---
title: 搭建 FFmpeg windows 开发环境
date: 2024-10-27 10:29:08
updated: 2024-10-27 10:29:08
tags:
- FFmpeg
- cmkake
- clion
categories: 

- 音视频
---

本文讲述在 windows 环境下如何搭建 FFmpeg 开发环境，并列出常用的 cmake 常用指令。

<!-- more -->

# 环境说明

使用到的环境：

- OS: windows 10 
- IDE: CLion 2024.1.2
- FFEMPEG: 4.4
- CMAKE: 3.28

# 下载 FFMPEG 共享库
由于搭建的是 C 语言项目，需要引入 FFMPEG 共享库，可以从[官网下载](https://github.com/BtbN/FFmpeg-Builds/releases)。
![ffmpeg共享库](/images/av/ffmpeg-shared-download.png "ffmpeg共享库")

根据需要下载指定平台指定版本的共享库，如 windows 平台 4.4版本的共享库，下载完成之后解压即可。

# 新建项目

新建一个 C 语言项目，名称可以任意指定，如 HelloFfmpeg。
![新建工程](/images/av/ffempeg-new-project.png "新建工程")

在项目中使用 CMake 来构建，默认会生成 CMakeList.txt 文件。

## CMake 介绍

CMake 是个一个开源的跨平台自动化建构系统，用来管理软件建置的程序，并不依赖于某特定编译器，并可支持多层目录、多个应用程序与多个函数库。
CMake 通过使用简单的配置文件 CMakeLists.txt，自动生成不同平台的构建文件（如 Makefile、Ninja 构建文件、Visual Studio 工程文件等），简化了项目的编译和构建过程。
CMake 本身不是构建工具，而是生成构建系统的工具，它生成的构建系统可以使用不同的编译器和工具链。

### 工作流程

1. 编写 CMakeLists.txt 文件： 定义项目的构建规则和依赖关系；
2. 生成构建文件： 使用 CMake 生成适合当前平台的构建系统文件（例如 Makefile、Visual Studio 工程文件）；
3. 执行构建： 使用生成的构建系统文件（如 make、ninja、msbuild）来编译项目。

# 默认 CMakeList.txt 说明

默认生成的 CMakeList.txt 文件只包含一些最基本的指令，如下所示：
```cmake
# 指定支持的 cmake 最低版本
cmake_minimum_required(VERSION 3.28)

# 指定工程的名称及使用的语言
project(HelloFfmpeg C)

# 指定支持的 C 语言规范
set(CMAKE_C_STANDARD 11)

# 指定生成程序名称及源代码
add_executable(HelloFfmpeg main.c)
```

此时，还未引入任何第三方库，下面引入 FFmpeg 库。

# 引入 FFmpeg 库

假定 FFmpeg 共享库已经安装到指定目录下，如：D:/app/ffmpeg-shared-4.4，目录结构如下所示：
```bash
D:.
+---bin
+---doc
+---include
|   +---libavcodec
|   +---libavdevice
|   +---libavfilter
|   +---libavformat
|   +---libavutil
|   +---libpostproc
|   +---libswresample
|   \---libswscale
\---lib
    \---pkgconfig
```
说明：

- bin: FFmpeg 可执行文件；
- include: FFmpeg 头文件，程序需要引入；
- lib: FFmpeg 动态库，程序需要引入。

条件已经准备好，现在只需要向 CMakeList.txt 文件中加入如下配置，便可引入 FFmpeg 库。

```cmake
# 设置 CMake 构建目录
# 指定存放程序生成的静态库的目录
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
# 指定存放程序生成的动态库的目录
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
# 指定存放可执行软件的目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# 指定 FFmpeg 安装目录，并将目录赋值给 FFMPEG_DEV_ROOT 变量，
# 方便后续指令引用
set(FFMPEG_DEV_ROOT D:/app/ffmpeg-shared-4.4)

# 设置 FFmpeg 环境变量
# 指定 FFmpeg 头文件目录
include_directories(${FFMPEG_DEV_ROOT}/include)
# 指定 FFmpeg 动态库目录
link_directories(${FFMPEG_DEV_ROOT}/lib)
# 指定需要连接到程序中的动态库列表
link_libraries(
        avcodec
        avformat
        avfilter
        avdevice
        swresample
        swscale
        avutil
)

# 复制动态库 dll 文件
# 查询 FFmpeg 安装目录下所有的动态库列表，并赋值给 ffmpeg_shared_libries 变量
file(GLOB ffmpeg_shared_libries ${FFMPEG_DEV_ROOT}/bin/*dll)
# 将 FFmpeg 动态库复制到 CMake 构建目录，运行程序需要用到
file(COPY ${ffmpeg_shared_libries} DESTINATION ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
```

在配置 CMake 的构建目录时，使用了 `CMAKE_BINARY_DIR` 变量，该变量指定了程序最上层的构建目录，它的值一般由执行 `cmake` 命令时由 `-B` 参数指定，如下所示：
```bash
cmake.exe -DCMAKE_BUILD_TYPE=Debug -S D:\app\project\HelloFfmpeg -B D:\app\project\HelloFfmpeg\cmake-build-debug
```
在该命令中，`-S` 参数指定源码目录，它的值赋给 `CMAKE_SOURCE_DIR` 变量，`-B` 参数指定 build 目录，它的值赋给 `CMAKE_BINARY_DIR` 变量，这些变量在 CMakeList.txt 文件中可直接使用。

# 使用 FFmpeg 库

在项目中已经引入了 FFmpeg 库，在程序中便可直接使用它了。为了检验引入成果，我们可以简单输出 FFmpeg avcodec 的配置信息，若输出则表示引入成功。
```c
#include <stdio.h>

// 引入 FFmpeg 头文件
#include <libavcodec/avcodec.h>

int main(void) {
    printf("Hello, FFmpeg!\n");

    // 输出 avcodec 配置信息
    printf("%s", avcodec_configuration());

    return 0;
}
```

# CMake 常用指令说明
## cmake_minimum_required
指定 CMake 的最低版本要求
语法：
```cmake
cmake_minimum_required(VERSION <version>)
```

实例：
```cmake
cmake_minimum_required(VERSION 3.28)
```

## project
定义项目的名称和使用的编程语言
语法：
```cmake
project(<project_name> [<language>...])
```

实例：
```cmake
project(HelloFfmpeg C)
```

## add_executable
指定要生成的可执行文件和其源文件
语法：
```cmake
add_executable(<target> <source_files>...)
```

实例：
```cmake
add_executable(HelloFfmpeg main.c)
```

## add_library
用于定义和构建一个库（静态库或共享库）目标。库是一组编译后的对象文件的集合，它可以供其他目标（如可执行文件或其他库）链接使用。
语法：
```cmake
add_library(<name> [STATIC | SHARED | MODULE]
            [EXCLUDE_FROM_ALL]
            [<source>...])
```


- STATIC：指定创建静态库。静态库在链接时会被完全合并到可执行文件中。
- SHARED：指定创建共享库（也称为动态库或共享对象）。共享库在运行时加载，多个可执行文件可以共享同一个库实例。
- MODULE：用于一些平台，用于创建用于插件加载的库


实例：
```cmake
add_library(MyLibrary STATIC library.cpp)
```

## add_subdirectory
用于向当前项目添加一个子目录。它允许你在主项目中包含其他的子项目，每个子项目都可以拥有自己的 CMakeLists.txt 文件和构建配置。
语法：
```cmake
add_subdirectory(source_dir [binary_dir] [EXCLUDE_FROM_ALL] [SYSTEM])
```

- source_dir：要添加的子目录的源代码目录。
- binary_dir：可选，要求在指定的二进制目录中进行构建。如果省略，将在主项目的构建目录中进行构建。
- EXCLUDE_FROM_ALL：可选，如果指定了该选项，子目录的构建将不会作为主项目的一部分进行，默认情况下会构建。

假设项目结构如下：
```bash
HelloFfmpeg/
|-- CMakeLists.txt
|-- src/
|   |-- main.cpp
|   |-- ...
|-- subproject/
|   |-- CMakeLists.txt
|   |-- submain.cpp
|   |-- ...
```

在 HelloFfmpeg/CMakeLists.txt 中，可以使用 add_subdirectory 命令来添加 subproject 子目录：
```cmake
add_subdirectory(subproject)
```
在 subproject/CMakeLists.txt 中，你可以定义子项目的构建规则和配置。
通过使用 add_subdirectory，你可以将项目拆分为更小的模块，每个模块都有自己的构建和配置。这种方法有助于提高项目的可维护性和清晰度，同时允许在不同的子项目中定义不同的构建和设置。

## target_link_libraries
用于指定目标与其他库之间的链接关系。它告诉 CMake 在链接可执行文件或库时需要使用哪些其他库。这通常用于链接目标与依赖的库，包括系统库和自定义库。
语法：
```cmake
target_link_libraries(target_name
    PRIVATE lib1 lib2 ...
    PUBLIC lib3 lib4 ...
    INTERFACE lib5 lib6 ...
)
```


- target_name：要链接的目标的名称；
- PRIVATE：这些库将会链接到目标自身。这对于库的实现细节和内部使用的依赖非常有用；
- PUBLIC：这些库将会链接到目标自身以及使用该目标的其他目标。这对于公共接口库的依赖非常有用；
- INTERFACE：这些库将会链接到使用该目标的其他目标，但不会链接到目标自身。

实例：
```cmake
target_link_libraries(HelloAppBinary PUBLIC operations logger)
```
链接 HelloAppBinary可执行文件与 operations，logger静态库。

## link_libraries
同 target_link_libraries，该指令已经在新版本中废弃，建议使用target_link_libraries。
它们使用上的区别是：

- target_link_libraries 要在 add_executable 之后；
- link_libraries 要在 add_executable 之前。

语法：
```cmake
link_libraries(<dirs>...)
```

实例：
```cmake
link_libraries(
        avcodec
        avformat
        avfilter
        avdevice
        swresample
        swscale
        avutil
)
```

## link_directories
该指令的作用主要是指定要链接的库文件的路径。
语法：
```cmake
link_directories(<dirs>...)
```
实例：
```cmake
link_directories(${FFMPEG_DEV_ROOT}/lib)
```

## include_directories
添加头文件搜索路径。
语法：
```cmake
include_directories(<dirs>...)
```
实例：
```cmake
include_directories(${FFMPEG_DEV_ROOT}/include)
```

## aux_source_directory
添加源文件目录。
语法：
```cmake
aux_source_directory(<dir> <variable>)
```
实例：
```cmake
aux_source_directory(src SRC_DIR)
```

## target_include_directories
指定目标的头文件搜索路径，通常用于为特定的目标（比如可执行文件、静态库、共享库等）设置编译时的头文件搜索路径。
语法：
```cmake
target_include_directories(<target> [SYSTEM] [AFTER|BEFORE]
  <INTERFACE|PUBLIC|PRIVATE> [items1...]
  [<INTERFACE|PUBLIC|PRIVATE> [items2...] ...])
```
实例：
```cmake
target_include_directories(MyExecutable PRIVATE ${PROJECT_SOURCE_DIR}/include)
```

## find_package
自动检测和配置外部库和包，常用于查找系统安装的库或第三方库。可通过 PACKAGE_FOUND 变量判断是否找到，其中 PACKAGE 为包的名称，另外通过 PACKAGE_INCLUDE_DIRS、PACKAGE_LIBRARY_DIRS 及 PACKAGE_DIR 三个命令查看头文件、库文件及包目录。
语法：
```cmake
find_package(<package> [version] [EXACT] [QUIET] [MODULE]
             [REQUIRED] [[COMPONENTS] [components...]]
             [OPTIONAL_COMPONENTS components...]
             [NO_POLICY_SCOPE])

```


- package：必填参数。需要查找的包名，注意大小写；
- version 和 EXACT：可选参数，version指定的是版本，如果指定就必须检查找到的包的版本是否和version兼容。如果指定EXACT则表示必须完全匹配的版本而不是兼容版本就可以；
- QUIET：可选参数，表示如果查找失败，不会在屏幕进行输出（但是如果指定了REQUIRED字段，则QUIET无效，仍然会输出查找失败提示语）。
- MODULE：可选字段。指定查找模式；
- REQUIRED：可选字段。表示一定要找到包，找不到的话就立即停掉整个CMake。而如果不指定REQUIRED则CMake会继续执行。

实例：
```cmake
# 基本用法
find_package(Boost REQUIRED)

# 指定版本
find_package(Boost 1.70 REQUIRED)

# 查找库并指定路径
find_package(OpenCV REQUIRED PATHS /path/to/opencv)

# 使用查找到的库：
target_link_libraries(MyExecutable Boost::Boost)

# 设置包含目录和链接目录：
include_directories(${Boost_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIRS})

```

## file
执行各种文件和目录操作，如拷贝、移动、创建目录、查找文件等。

语法：
```cmake
# 拷贝文件：
file(COPY source_file DESTINATION destination_directory)

# 移动文件：
file(RENAME old_name new_name)

# 查找文件：
file(GLOB variable [LIST_DIRECTORIES true/false] [globbing expressions])
# 这个命令可以用来查找满足指定模式的文件，并将结果存储在变量中。你可以使用通配符或正则表达式来指定匹配的模式。
```

实例：
```cmake
# 拷贝文件：
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/small_bunny_1080p_60fps.mp4 DESTINATION ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})

# 查找文件：
file(GLOB ffmpeg_shared_libries ${FFMPEG_DEV_ROOT}/bin/*dll)
```

## set 变量
在CMake中，变量是用来存储信息，如路径、配置选项或是决定构建过程中行为的参数
语法：
1、设置变量: 使用set命令来定义或修改变量的值。

```cmake
set(MY_VARIABLE "SomeValue")
```

2、使用变量: 在引用变量时使用${}语法
```cmake
message(STATUS "The value of MY_VARIABLE is: ${MY_VARIABLE}")
```
3、变量作用域: 变量在其被定义的目录和子目录中可见。可以设置父目录的变量或者使用CACHE选项来跨目录访问变量。

常见变量类型：

- 内置变量: CMake预定义的变量，如CMAKE_PROJECT_NAME, CMAKE_C_COMPILER等，用于提供关于项目和构建环境的信息。
- 环境变量: 使用$ENV{VAR_NAME}语法来访问，如$ENV{PATH}。
- 缓存变量: 使用set(VAR VALUE CACHE TYPE DOCSTRING)设置，这些变量值将被存储在CMakeCache.txt中，并在项目重新配置时保持。

常用的CMake变量：

- CMAKE_PROJECT_NAME: 当前项目的名称。
- CMAKE_C_COMPILER: C编译器的完整路径。
- CMAKE_CXX_COMPILER: C++编译器的完整路径。
- CMAKE_SOURCE_DIR: 项目的顶级源目录。
- CMAKE_BINARY_DIR: 项目的顶级构建目录。
- CMAKE_CURRENT_SOURCE_DIR: 当前处理的CMakeLists.txt所在的源目录。
- CMAKE_CURRENT_BINARY_DIR: 当前处理的CMakeLists.txt所在的构建目录。

使用变量的几点注意

- 字符串和列表: 在CMake中，变量可以存储字符串或列表（字符串序列）。列表使用分号;分隔。
- 变量引用: 总是使用${}来引用变量。
- 修改和作用域: 注意变量的修改可能会影响到其他目录或父目录，尤其是在使用全局变量或缓存变量时。

## option
在CMake中，option()命令用于定义和管理用户在配置项目时可以设置的选项。这些选项通常用于控制构建过程中是否启用某些功能或代码块。

语法：
```cmake
option(<option_variable> "description of the option" [initial value])
```

实例：
```cmake
#The option command
option(OPTIMIZE "Do we want to optimize the operation?" ON)
message("Are we optimizing? ${OPTIMIZE}")

if(OPTIMIZE)
    message("We are optimizing.")
endif()
```

## message
message 命令用于在执行 CMake 配置过程中输出信息。它通常用于调试、显示变量的值、显示错误或状态消息等。
语法：
```cmake
message([<mode>] "message text" ...)
```

mode 指定消息类型。可以是以下几种：

- STATUS: 输出前缀为--的消息，通常用于显示状态信息。
- WARNING: 生成警告信息，但不会停止CMake的配置或生成过程。
- AUTHOR_WARNING: 类似于WARNING，但是可以被开发者关闭。
- SEND_ERROR: 产生一个错误，错误信息会被输出，并且会停止CMake的进程。
- FATAL_ERROR: 立即停止所有CMake的操作，并退出。错误信息会被输出。
- DEPRECATION: 如果使用的是CMake的过时特性，可以用这个模式来显示废弃警告。

实例：
```cmake
# 基本状态消息
message(STATUS "Configuring Project")

# 显示变量的值
set(VAR_NAME "Hello World")
message(STATUS "The value of VAR_NAME is: ${VAR_NAME}")

# 警告消息
message(WARNING "This is a warning message")

# 发送错误消息，将会停止CMake的配置或生成过程
message(SEND_ERROR "Error encountered!")

# 致命错误，将立即终止CMake进程
message(FATAL_ERROR "Fatal error occurred")
```

## list
list命令用于操作列表，其中列表是由分号分隔的字符串。列表在CMake中非常普遍，用于处理路径集合、源文件、定义标志等。list命令提供了一组功能来操作这些列表，包括添加元素、删除元素、查询列表信息等。
语法：
```cmake
list(LENGTH <list> <out-var>)
list(GET <list> <element index> [<index> ...] <out-var>)
list(JOIN <list> <glue> <out-var>)
list(APPEND SOURCES additional.cpp)
list(REMOVE_ITEM SOURCES del.cpp)

```
实例：
```cmake
# 定义一个列表变量
set(SOURCES main.cpp helper.cpp utils.cpp)

# 向列表中添加元素
list(APPEND SOURCES additional.cpp)

# 获取列表长度
list(LENGTH SOURCES len)

# 输出列表长度
message(STATUS "Number of source files: ${len}")

# 获取并打印列表中的所有元素
foreach(SRC IN LISTS SOURCES)
    message(STATUS "Source file: ${SRC}")
endforeach()

# 删除元素
list(REMOVE_ITEM srcs ${debug_src})
```

## if 
条件语句
语法：
```cmake
if(expression)
  # Commands
elseif(expression)
  # Commands
else()
  # Commands
endif()

```
实例：
```cmake
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
  message("Debug build")
endif()
```

## foreach
循环语句
语法：
```cmake
foreach(loop_var IN LISTS list_name)
    # 执行对每个元素的操作...
endforeach()

```
实例：
```cmake
foreach(src  ${srcs})
    get_filename_component(TARGET ${src} NAME)
    add_executable(${TARGET} ${src})
    message(STATUS "${TARGET} added")
endforeach()
```

## get_filename_component
获取完整文件名的特定部分

语法：
```cmake
get_filename_component(<var> <Filename> <mode> [CACHE])
```

mode 可取值范围:

- DICECTORY：没有文件名的目录，路径返回时带有正斜杠，并且没有尾部斜杠。
- NAME：不带名录的文件名
- EXT：文件名的最长扩展名
- NAME_WE：不带目录或最长扩展名的文件名
- LAST_EXT：文件名的最后扩展名
- NAME_WLE：文件目录或最后扩展名的文件名
- PATH：DIRECTORY的别名（cmake <= 2.8.11）

实例：
```cmake
SET(filename /tmp/cmake.dat.log.tmp)
get_filename_component(d ${filename} DIRECTORY)
get_filename_component(n ${filename} NAME ABSOLUTE)
get_filename_component(nw ${filename} NAME_WE ABSOLUTE)
get_filename_component(nwl ${filename} NAME_WLE ABSOLUTE)
get_filename_component(e ${filename} EXT ABSOLUTE)
get_filename_component(le ${filename} LAST_EXT ABSOLUTE)
 
message("${filename} DIRECTOYR:${d}")
message("${filename} NAME:${n}")
message("${filename} NAME_WE:${nw}")
message("${filename} NAME_WLE:${nwl}")
message("${filename} EXT:${e}")
message("${filename} LAST_EXT:${le}")
 
# output
/tmp/cmake.data.log.tmp DIRECTOYR:/tmp
/tmp/cmake.data.log.tmp NAME:cmake.dat.log.tmp
/tmp/cmake.data.log.tmp NAME_WE:cmake
/tmp/cmake.data.log.tmp NAME_WLE:cmake.dat.log
/tmp/cmake.data.log.tmp EXT:.dat.log.tmp
/tmp/cmake.data.log.tmp LAST_EXT:.tmp
```

</br>

**参考：**

----
[1]:https://www.runoob.com/cmake/cmake-tutorial.html


[1. CMake 教程][1]

