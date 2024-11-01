# Communication

---

## Function

Essentially a node communication system for inter-node talking and sending of large data quantities made easy. This can be both used for internal communication [between processes] and external communication [between nodes].

## How this works

This is an extremely simple implementation of a communication network. Essentially each node is like a retranslater where it retranslates the message to it's
subscribed nodes via another post request.

### Post chart

```mermaid
flowchart LR
    A[Post Data] --> |topic| B[Get Data]
    B --> C[Post Data in subscribed topics]
```

### Subscribe chart

```mermaid
flowchart LR
    A[Subscribe] --> |topic, on_post_url| B[Add to internal subscribers]
```

### Unsubscribe chart

```mermaid
flowchart LR
    A[Unsubscribe] --> |topic, on_post_url| B[Find topic] --> C[Find option with on_post_url] --> D[Remove from internal subscribers]
```
