Valhalla is an alternative Minecraft skin and metadata server. It supports high
definition textures (up to 1024x1024).

## Authentication

Any operation that modifies a user's texture requires an authentication token.

There are two supported ways to authenticate. One can be done directly from the
Minecraft client. The other can be done using a browser through Xbox Live.

### Xbox Live

Logging in via Xbox Live uses OAuth2. If the server is configured with an Azure
client id and secret, and CORS is configured for your app, logging in can be as
simple as browsing to `/api/v1/auth/xbox`.

See [Microsoft Authentication](https://minecraft.wiki/w/Microsoft_authentication)

### Minecraft

In order to authenticate in the Minecraft client, we need to mimick the Multiplayer login
protocol. This allows us to verify your Minecraft account without needing to transmit your
Minecraft access token to an untrusted server.

For details, see [Mojang API on minecraft.wiki](https://minecraft.wiki/w/Mojang_API#Server)

There are three steps involved to authenticate with Mojang.

1. Server Handshake - Exchange player name for serverId and verifyToken from skin server
2. Multiplayer Login - Submit serverId, accessToken, and player id with Mojang
3. Server Callback - Exchange player name and verifyToken for an auth token

To start the authentication process via Minecraft, you will need the following information:

- The player's username
- The player's access token

#### Server Handshake

First, send the player's name to the skin server using a form POST request.

    POST /api/v1/auth/minecraft
    Content-Type: application/x-www-form-urlencoded

    name=<username>

This will return a json object with the following keys. Same these for the next step.

    HTTP/1.1 200 - OK
    Conent-Type: application/json

    {
        "serverId": "string",
        "verifyToken": 123456
    }

#### Multiplayer Login

Next, send the returned `serverId` as well as the player's UUID and access
token to Mojang. If it is successful, you will receive a
`HTTP/1.1 204 - No Content` response.

If you have access to Mojang's authlib
library, you can call `MinecraftSessionService#joinServer()`.

    POST https://sessionserver.mojang.com/session/minecraft/join
    Content-Type: application/json

    {
        "accessToken": "<accessToken>",
        "selectedProfile": "<uuid without dashes>",
        "serverId": "<serverId>",
    }

#### Server Callback

After receving a successful 204 response, you can now use the previously
received `verifyToken` to complete the authorization process.

    POST /api/v1/auth/minecraft/callback
    Content-Type: application/x-www-form-urlencoded

    name=<username>&verifyToken=<verifyToken>

If the request is successful, the following JSON object will be returned. The
accessToken field or Authorization header should be sent in future requests
using the `Authoriation` header.

    HTTP/1.1 200 - OK
    Conent-Type: application/json
    Authorization: Bearer <token>

    {
        "accessToken": "Bearer <token>",
        "userId": "<uuid>"
    }
