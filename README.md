# ntripcaster

Caster NTRIP escrito en C sobre libev, compatible con Windows y Linux. Puede retransmitir datos entre clientes y servidores NTRIP, genera din\xC3\xA1micamente la tabla de fuentes y admite autenticaci\xC3\xB3n. Incluye un caster en Python (`pycaster`) que usa Trio.

## Compilaci\xC3\xB3n
Se requieren `cmake`, `git` y la biblioteca `libev`. En Windows solo se ha probado con las toolchains MinGW/MinGW-w64.

En sistemas Linux, `libev` puede instalarse con `apt-get install libev-dev` (para Debian/Ubuntu).

Pasos para compilar:

```shell
git clone https://github.com/tisyang/ntripcaster.git
cd ntripcaster
git submodule update --init

mkdir build
cd build
cmake ..
make
```

## Binarios precompilados
https://github.com/tisyang/ntripcaster/releases/

## Uso
El programa utiliza un archivo de configuraci\xC3\xB3n JSON, por defecto `ntripcaster.json`. Puede especificarse otro archivo como argumento: `ntripcaster.exe archivo.json`.

Opciones del archivo de configuraci\xC3\xB3n:

+ `listen_addr`: cadena con la direcci\xC3\xB3n donde escuchar\xC3\xA1 el caster. Por defecto "0.0.0.0".
+ `listen_port`: entero con el puerto de escucha. Por defecto `2101`.
+ `max_client`: n\xC3\xBAmero m\xC3\xA1ximo de clientes NTRIP permitidos. `0` significa ilimitado. Por defecto `0`.
+ `max_source`: n\xC3\xBAmero m\xC3\xA1ximo de fuentes NTRIP permitidas. `0` significa ilimitado. Por defecto `0`.
+ `max_pending`: n\xC3\xBAmero m\xC3\xA1ximo de conexiones sin identificar permitidas. `0` significa ilimitado. Por defecto `10`.
+ `tokens_client`: objeto donde cada clave es `usuario:contrase\xC3\xB1a` y el valor indica los puntos de montaje accesibles. `*` permite cualquiera.
+ `tokens_source`: objeto donde cada clave es la contrase\xC3\xB1a de una fuente y el valor indica los puntos de montaje en los que puede publicar. `*` permite cualquiera.
+ `log_level`: cadena con el nivel de registro (`INFO`, `DEBUG`, etc.). Por defecto `INFO`.
+ `log_file`: cadena con la ruta del archivo de registro. Si es nulo se escribe en la salida est\xC3\xA1ndar.

Ejemplo de configuraci\xC3\xB3n:

```json
{
        "listen_addr": "0.0.0.0",
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

## Contacto
lazy.tinker#outlook.com

## Acciones de prueba
