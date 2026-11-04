# FROST MQTT: duplicate Observations and connection timeouts

QoS 1 can deliver the same publication more than once. In FROST's standard MQTT create path, repeated accepted publications can therefore become repeated Observation creation attempts. Connection Keep Alive controls a different concern: when the broker closes a connection that has stopped sending traffic.

This guide describes [FROST 2.8.2](https://github.com/FraunhoferIOSB/FROST-Server/releases/tag/v2.8.2) and its bundled **Fraunhofer Moquette 0.18.6**. It is based on source and specification inspection. No connector, sensor or deployed server was exercised.

## What QoS 1 guarantees

MQTT's levels are QoS 0, at most once; QoS 1, at least once; and QoS 2, exactly once for the MQTT delivery exchange. QoS does not identify a real-world measurement across separate calls to publish. Publishing an equal JSON body again is not automatically an idempotent application operation. [MQTT delivery rules, §4.3](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

In the bundled broker, successful QoS 1 routing calls `sendPubAck()` before invoking the publish interceptor. This call order does not guarantee when the client receives the acknowledgment. FROST converts the intercepted message into a request; its standard creation handler then sends a CREATE through the normal service layer. That inspected path does not compare payloads or keep a measurement-event deduplication key. A repeated accepted message can consequently create another Observation, subject to the normal validation and persistence rules. [Broker receive path](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/PostOffice.java#L669), [FROST adapter](https://github.com/FraunhoferIOSB/FROST-Server/blob/v2.8.2/FROST-Server.MQTT.Moquette/src/main/java/de/fraunhofer/iosb/ilt/frostserver/mqtt/moquette/MoquetteMqttServer.java#L392), [CREATE handler](https://github.com/FraunhoferIOSB/FROST-Server/blob/v2.8.2/FROST-Server.Core/src/main/java/de/fraunhofer/iosb/ilt/frostserver/mqtt/MqttManager.java#L315).

PUBACK acknowledges the MQTT exchange. It is not confirmation that the database transaction succeeded. Similarly, choosing QoS 2 does not establish a transaction spanning the connector, broker and Observation database. Do not infer successful insertion solely from a publish acknowledgment. [MQTT acknowledgment semantics, §4.3.2](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

The server setting `mqtt.QoS` is consumed when FROST publishes outgoing notifications. Changing that setting does not change the QoS selected by an incoming publisher. [Outgoing publication](https://github.com/FraunhoferIOSB/FROST-Server/blob/v2.8.2/FROST-Server.Core/src/main/java/de/fraunhofer/iosb/ilt/frostserver/mqtt/MqttManager.java#L229).

## Which timeout applies

| Setting or value | Meaning in this version |
| --- | --- |
| Client CONNECT Keep Alive | Used to calculate the connected client's reader-idle timeout. |
| `mqtt.server.keep.alive` | Broker-wide override of the client value; duration syntax, such as `60s`. |
| `mqtt.persistent.client.expiration` | Maximum lifetime of disconnected session state, not the TCP connection. See the [stable settings guide](https://github.com/FraunhoferIOSB/FROST-Server/blob/v2.8.2/docs/settings/settings.md#L153). |
| `mqtt.netty.channel.timeout.seconds` | Initial pre-CONNECT channel timeout; replaced by the Keep Alive handler after CONNECT. See [initial channel setup](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/NewNettyAcceptor.java#L148) and [connected-client setup](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/MQTTConnection.java#L469). |

Moquette sets the connected-client timeout to `Math.round(effectiveKeepAliveSeconds * 1.5f)`. A value of 60 gives a 90-second reader-idle threshold. Odd values round to a whole second: 5 gives 8. On reader-idle expiry, the broker closes the channel. This is an implementation threshold, not a measured promise of an exact wall-clock disconnect time. [Calculation](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/MQTTConnection.java#L469), [close handler](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/MoquetteIdleTimeoutHandler.java#L36).

An effective Keep Alive of zero disables this reader-idle timer. A configured server override replaces the client's value, including a client value of zero. Other disconnect causes still exist; disabling the timer does not keep an unusable TCP connection alive. Start with the client's Keep Alive for per-client tuning. [Netty reader-idle contract](https://netty.io/4.1/api/io/netty/handler/timeout/IdleStateHandler.html).

The broker property is named `server_keep_alive`. FROST's wrapper translates underscores to dots within the `mqtt.` namespace, giving `mqtt.server.keep.alive`; Moquette parses the value as a duration. This mapping was inspected in source, not applied to a running deployment. MQTT 5 can communicate a server Keep Alive override in CONNACK; do not assume that MQTT 3 clients learn a broker override in the same way. [FROST mapping](https://github.com/FraunhoferIOSB/FROST-Server/blob/v2.8.2/FROST-Server.MQTT.Moquette/src/main/java/de/fraunhofer/iosb/ilt/frostserver/mqtt/moquette/ConfigWrapper.java#L38), [broker parsing](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/BrokerConfiguration.java#L76), [CONNACK construction](https://github.com/FraunhoferIOSB/moquette/blob/v0.18.6/broker/src/main/java/io/moquette/broker/MQTTConnection.java#L361).

## Applying the distinction to a connector

Let the MQTT client library manage its protocol acknowledgments and retry state. Treat an application retry that calls publish again as another publication. If the application requires one stored Observation per measurement event, define that event's identity and verify the ingestion behavior explicitly; equal results or timestamps alone do not prove that two measurements are duplicates.

Before diagnosing a particular reconnect trace, record the FROST version, MQTT protocol version, client library, Keep Alive, session settings and whether the application itself calls publish again. The source analysis above does not establish which of those events occurred in an unexamined connector.

## Optional coffee

The guide is free. If it helps, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
