use futures_util::StreamExt;
use rand::Rng;
use std::fs;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::Mutex;
use tokio_tungstenite::accept_async;
use tokio_tungstenite::connect_async;
use writer::Writer;

mod writer;

#[derive(serde::Deserialize)]
struct Config {
    server: ServerConfig,
    others: std::collections::HashMap<String, OtherConfig>,
}

#[derive(serde::Deserialize)]
struct ServerConfig {
    port: u16,
}

#[derive(serde::Deserialize)]
struct OtherConfig {
    port: u16,
    url: String,
}

#[tokio::main]
async fn main() {
    let toml_content = fs::read_to_string("config.toml").expect("Failed to read config.toml");
    let config: Config = toml::from_str(&toml_content).expect("Failed to parse config.toml");
    let port = config.server.port;

    let server = TcpListener::bind(format!("127.0.0.1:{}", port))
        .await
        .expect("Failed to bind server");

    println!("Server bound to {}", server.local_addr().unwrap());

    let writers = Arc::new(Mutex::new(Vec::new()));

    for (_, other) in config.others {
        let writers = writers.clone();
        tokio::spawn(async move {
            let url = format!("ws://{}:{}", other.url, other.port);
            println!("Connecting to {}", url);
            let (ws_stream, _) = connect_async(url)
                .await
                .expect("Failed to connect to other server");

            let (writer, _) = ws_stream.split();

            let id = rand::thread_rng().gen::<u32>() % 1000000;
            writers.lock().await.push(Writer::new_with_connection(
                Arc::new(Mutex::new(writer)),
                id,
            ));
        });
    }

    while let Ok((stream, _)) = server.accept().await {
        let writers = writers.clone();
        tokio::spawn(async move {
            let ws_stream = accept_async(stream)
                .await
                .expect("Failed to accept WebSocket");

            let (write, mut read) = ws_stream.split();
            let id = rand::thread_rng().gen::<u32>() % 1000000;
            writers
                .lock()
                .await
                .push(Writer::new(Arc::new(Mutex::new(write)), id));

            while let Some(Ok(msg)) = read.next().await {
                for writer in writers.lock().await.iter_mut() {
                    if writer.id() != id {
                        continue;
                    }

                    writer.send(msg.clone()).await;
                }
            }
        });
    }
}
