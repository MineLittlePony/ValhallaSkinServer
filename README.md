# Valhalla Skin Server

This is an alternative skin server for Minecraft. It has a few benefits over
 the default Yggdrasil server from Mojang.

- HD textures
- Arbitrary metadata.
- Non-skin uploads (Elytras and capes)

In order to take advantage of this server, [a client mod](https://github.com/MineLittlePony/HDSkins) is required.

See the [Scalar docs](https://skins.minelittlepony-mod.com/docs) for details on endpoints.

## Developing

### HTTP2 Support

Since Java client defaults to using http2, trying to send requests will fail. HTTP2 support is experimental in
uvicorn and requires the `zttp` library, which is part of the project dev dependencies.

To enable it, run one of the following commands.

#### Using the `litestar` command
```sh
UVICORN_HTTP=zttp UVICORN_HTTP2=1 litestar run
```

#### Using the `uvicorn` command
```sh
uvicorn app:app --http=zttp --http2
```
