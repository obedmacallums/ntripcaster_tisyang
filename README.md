# ntripcaster
Ntrip broadcaster written in C and libev, supports Windows and Linux.

Currently, it can transmit data between NTRIP servers and NTRIP clients, with source table and authorization support.

## Build
You need CMake, Git, and libev.

Windows build has only been tested on MinGW/MinGW-w64 toolchains.

On Linux, you need to have CMake and Git installed, and libev (on Debian/Ubuntu you can install it with `apt-get install libev-dev`).

Windows build has only been tested on MinGW/MinGW-w64.

```shell
git clone https://github.com/tisyang/ntripcaster.git
cd ntripcaster
git submodule update --init

mkdir build
cd build
cmake ..
make
```

## Pre-built binaries

https://github.com/tisyang/ntripcaster/releases/

## Usage

The program uses a JSON configuration file. The default configuration file name is `ntripcaster.json`, but you can specify a different file name via command line: `ntripcaster.exe xxx.json`.

Configuration file options:

+ `listen_addr`: String, the caster service address to use. Default is "0.0.0.0".
+ `listen_port`: Integer, the caster service port to use. Default is 2101.
+ `max_client`: Integer, the maximum number of NTRIP client connections allowed. 0 means unlimited. Default is 0.
+ `max_source`: Integer, the maximum number of NTRIP source connections allowed. 0 means unlimited. Default is 0.
+ `max_pending`: Integer, the maximum number of unidentified clients (neither client nor source). 0 means unlimited. Default is 10.
+ `tokens_client`: Object, each entry's name is a client credential pair (username:password). The value is the mountpoint(s) the client can access. Mountpoints support `*` to allow access to any mountpoint.
+ `tokens_source`: Object, each entry's name is a source password. The value is the mountpoint(s) the source can write to. Mountpoints support `*` to allow access to any mountpoint.
+ `log_level`: String, log level, e.g. `INFO`, `DEBUG`. Default is `INFO`.
+ `log_file`: String, log output file. Default is empty, which means output to standard output.

Example configuration file:

```json
{
	"listen_addr":"0.0.0.0",
	"listen_port": 2101,
	"max_client": 0,
	"max_source": 0,
	"max_pending": 10,
	"tokens_client": {
		"test:test": "*"
	},
        "tokens_source": {
                "test": "*"
        },
        "log_level": "INFO",
        "log_file": null
}

```

## Contact

lazy.tinker#outlook.com

## test actions
