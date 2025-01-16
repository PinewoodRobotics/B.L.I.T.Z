use flags::MessageFlags;
use futures_util::stream::{SplitSink, SplitStream};
use futures_util::StreamExt;
use log::{error, info};
use rand::Rng;
use std::sync::Arc;
use std::{collections::HashMap, fs};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Mutex;
use tokio_tungstenite::{accept_async, connect_async, tungstenite::protocol::Message};
use tokio_tungstenite::{MaybeTlsStream, WebSocketStream};
use tungstenite::Bytes;
use writer::Writer;

mod flags;
mod writer;
#[derive(serde::Deserialize)]
struct Config {
    server: ServerConfig,
    others: HashMap<String, OtherConfig>,
    debug: Option<bool>,
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

    let debug = config.debug.unwrap_or(false);
    if debug {
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("debug")).init();
        info!("Debug mode enabled");
    }

    info!("Server bound to {}", server.local_addr().unwrap());

    let writers: Arc<Mutex<HashMap<String, Vec<Writer>>>> = Arc::new(Mutex::new(HashMap::new()));
    let external_writers = Arc::new(Mutex::new(HashMap::new()));

    for (_, other) in config.others {
        let writers = writers.clone();
        let external_writers = external_writers.clone();
        tokio::spawn(async move {
            let url = format!("ws://{}:{}", other.url, other.port);
            info!("Connecting to {}", url);
            match connect_async(url).await {
                Ok((ws_stream, _)) => {
                    let (writer, mut reader) = ws_stream.split();
                    let writer = Arc::new(Mutex::new(writer));
                    let id = rand::thread_rng().gen::<u32>() % 1000000;

                    while let Some(msg) = reader.next().await {
                        match msg {
                            Ok(Message::Close(_)) => {
                                info!("Connection closed by peer");
                                break;
                            }
                            Ok(msg) => {
                                let msg = msg.into_data();
                                match MessageFlags::get_flag(&msg) {
                                    Some(MessageFlags::SUBSCRIBE) => {
                                        if let Some(topic) = MessageFlags::get_topic(&msg) {
                                            external_writers.lock().await.insert(
                                                topic,
                                                Writer::new_with_connection(writer.clone(), id),
                                            );
                                        }
                                    }
                                    Some(MessageFlags::UNSUBSCRIBE) => {
                                        if let Some(topic) = MessageFlags::get_topic(&msg) {
                                            external_writers.lock().await.remove(&topic);
                                        }
                                    }
                                    None => {
                                        for writer in writers.lock().await.iter_mut() {
                                            if is_topic_match(&writer.0, &msg) {
                                                send_to_topic(msg.clone(), writer.1).await;
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                            Err(e) => {
                                error!("Error receiving message: {:?}", e);
                                break;
                            }
                        }
                    }

                    info!("Cleaning up writer for ID: {}", id);
                    external_writers.lock().await.retain(|_, w| w.id() != id);
                }
                Err(_) => {
                    error!("Failed to connect!");
                }
            }
        });
    }

    while let Ok((stream, _)) = server.accept().await {
        let writers = writers.clone();
        let external_writers = external_writers.clone();
        info!("Accepted connection");
        tokio::spawn(async move {
            match accept_async(stream).await {
                Ok(ws_stream) => {
                    let (writer, mut reader) = ws_stream.split();
                    let id = rand::thread_rng().gen::<u32>() % 1000000;
                    let writer = Arc::new(Mutex::new(writer));

                    while let Some(msg) = reader.next().await {
                        match msg {
                            Ok(Message::Close(_)) => {
                                info!("Client closed connection");
                                break;
                            }
                            Ok(msg) => {
                                info!("Received: {:?}", msg);
                                let msg = msg.into_data();
                                match MessageFlags::get_flag(&msg) {
                                    Some(MessageFlags::SUBSCRIBE) => {
                                        if let Some(topic) = MessageFlags::get_topic(&msg) {
                                            info!("Subscribing to topic: {}", topic);
                                            writers
                                                .lock()
                                                .await
                                                .entry(topic)
                                                .or_insert_with(Vec::new)
                                                .push(Writer::new(writer.clone(), id));
                                        }
                                    }
                                    Some(MessageFlags::UNSUBSCRIBE) => {
                                        if let Some(topic) = MessageFlags::get_topic(&msg) {
                                            writers.lock().await.remove(&topic);
                                            for ext_writer in
                                                external_writers.lock().await.iter_mut()
                                            {
                                                ext_writer
                                                    .1
                                                    .send(Message::Binary(msg.clone()))
                                                    .await;
                                            }
                                        } // TODO3: fix this with retain
                                    }
                                    None => {
                                        for writer in writers.lock().await.iter_mut() {
                                            if is_topic_match(&writer.0, &msg) {
                                                send_to_topic(msg.clone(), writer.1).await;
                                                info!("Sent to topic: {}", writer.0);
                                                break;
                                            } // TODO4: have topic and payload (String, Bytes)
                                        }
                                    }
                                }
                            }
                            Err(e) => {
                                error!("Error reading message: {:?}", e);
                                break;
                            }
                        }
                    }

                    info!("Cleaning up writer for ID: {}", id);
                    let mut writers_lock = writers.lock().await;
                    for writers_vec in writers_lock.values_mut() {
                        writers_vec.retain(|w| w.id() != id);
                    }
                    writers_lock.retain(|_, writers_vec| !writers_vec.is_empty());
                }
                Err(e) => {
                    eprintln!("Failed to accept WebSocket connection: {:?}", e);
                }
            }
        });
    }
}

fn is_topic_match(topic: &str, msg: &Bytes) -> bool {
    if msg.len() < topic.len() {
        return false;
    }

    info!("Checking if topic matches: {}", topic);
    msg.starts_with(topic.as_bytes())
}

async fn send_to_topic(msg: Bytes, writers: &mut Vec<Writer>) {
    for writer in writers.iter_mut() {
        writer.send(Message::Binary(msg.clone())).await;
    }
}
