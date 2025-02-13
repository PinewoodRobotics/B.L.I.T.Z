use config::Config;
use flags::Msg;
use futures_util::StreamExt;
use log::{debug, error, info};
use rand::Rng;
use std::collections::HashSet;
use std::net::{IpAddr, TcpStream};
use std::sync::Arc;
use std::{collections::HashMap, fs};
use tokio::net::TcpListener;
use tokio::sync::Mutex;
use tokio_tungstenite::{accept_async, connect_async, tungstenite::protocol::Message};
use tokio_tungstenite::{MaybeTlsStream, WebSocketStream};
use tungstenite::Bytes;
use writer::Writer;

mod config;
mod flags;
mod writer;

#[tokio::main]
async fn main() {
    let toml_content = fs::read_to_string("config.toml").expect("Failed to read config.toml");
    let config: Config = toml::from_str(&toml_content).expect("Failed to parse config.toml");
    let debug = config.debug.unwrap_or(false);
    if debug {
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("debug")).init();
        info!("Debug mode enabled");
    }

    // -----------------------------------------------

    let server = TcpListener::bind(format!("0.0.0.0:{}", config.server.port))
        .await
        .expect("Failed to bind server");

    info!("Server bound to {}", server.local_addr().unwrap());
    let mut external_streams: Arc<Mutex<HashMap<String, (HashSet<String>, Arc<Mutex<Writer>>)>>> =
        Arc::new(Mutex::new(HashMap::new()));
    let subscribers: Arc<Mutex<HashMap<String, Vec<Arc<Mutex<Writer>>>>>> =
        Arc::new(Mutex::new(HashMap::new()));

    for (name, other) in config.others {
        let external_streams = external_streams.clone();
        tokio::spawn(async move {
            let url = format!("ws://{}:{}", other.ip_addr_v4, other.port);
            let (ws_stream, _) = connect_async(url).await.unwrap();
            let mut external_streams = external_streams.lock().await;
            let (writer, mut read) = ws_stream.split();
            external_streams.insert(
                other.ip_addr_v4,
                (
                    HashSet::new(),
                    Arc::new(Mutex::new(Writer::new_with_connection(
                        Arc::new(Mutex::new(writer)),
                        0,
                    ))),
                ),
            );
        });
    }

    while let Ok((stream, _)) = server.accept().await {
        let subscribers = subscribers.clone();
        let peer_addr = stream
            .peer_addr()
            .unwrap_or_else(|_| "unknown".parse().unwrap());
        info!("Accepted connection from {}", peer_addr);
        let external_streams = external_streams.clone();
        tokio::spawn(async move {
            match accept_async(stream).await {
                Ok(ws_stream) => {
                    let (write, mut read) = ws_stream.split();
                    let write = Arc::new(Mutex::new(write));
                    let id = rand::thread_rng().gen::<u32>() % 1000000;
                    while let Some(msg) = read.next().await {
                        match msg {
                            Ok(Message::Close(_)) => {
                                info!("Client closed connection");
                                break;
                            }
                            Ok(Message::Ping(_)) => {}
                            Ok(msg) => {
                                let msg = msg.into_data();
                                debug!("Received message of length: {}", msg.len());
                                match Msg::parse_message(msg) {
                                    Some(msg_type) => match msg_type {
                                        Msg::SUBSCRIBE(topic) => {
                                            debug!("SUBSCRIBE: {}", topic);
                                            let addr = peer_addr.ip().to_string();
                                            if external_streams.lock().await.contains_key(&addr) {
                                                let mut external_streams =
                                                    external_streams.lock().await;
                                                let stream =
                                                    external_streams.get_mut(&addr).unwrap();
                                                stream.0.insert(topic);
                                            } else {
                                                debug!("SUBSCRIBE!: {}", topic);
                                                let mut subscribers = subscribers.lock().await;
                                                subscribers
                                                    .entry(topic.clone())
                                                    .or_insert_with(Vec::new)
                                                    .push(Arc::new(Mutex::new(Writer::new(
                                                        write.clone(),
                                                        id,
                                                    ))));
                                                debug!(
                                                    "Topic {} now has {} subscribers",
                                                    topic,
                                                    subscribers.get_mut(&topic).unwrap().len()
                                                );
                                            }
                                        }
                                        Msg::UNSUBSCRIBE(topic) => {
                                            debug!("UNSUBSCRIBE: {}", topic);
                                            let addr = peer_addr.ip().to_string();
                                            if external_streams.lock().await.contains_key(&addr) {
                                                let mut external_streams =
                                                    external_streams.lock().await;
                                                let stream =
                                                    external_streams.get_mut(&addr).unwrap();
                                                stream.0.remove(&topic);
                                            } else {
                                                let mut subscribers = subscribers.lock().await;
                                                if let Some(topic_subscribers) =
                                                    subscribers.get_mut(&topic)
                                                {
                                                    topic_subscribers.retain(|subscriber| {
                                                        tokio::runtime::Handle::current().block_on(
                                                            async {
                                                                subscriber.lock().await.id() != id
                                                            },
                                                        )
                                                    });
                                                    debug!(
                                                        "Topic {} now has {} subscribers",
                                                        topic,
                                                        topic_subscribers.len()
                                                    );
                                                }
                                            }
                                        }
                                        Msg::PUBLISH(topic, payload) => {
                                            debug!("PUBLISH: {}", topic);
                                            let mut subscribers = subscribers.lock().await;
                                            if let Some(topic_subscribers) =
                                                subscribers.get_mut(&topic)
                                            {
                                                for subscriber in topic_subscribers.iter() {
                                                    debug!("PUBLISH!: {}", topic);
                                                    subscriber
                                                        .lock()
                                                        .await
                                                        .send(Message::Binary(Msg::build_message(
                                                            Msg::PUBLISH(
                                                                topic.clone(),
                                                                payload.clone(),
                                                            ),
                                                        )))
                                                        .await;
                                                }
                                            }

                                            let external_streams = external_streams.clone();
                                            let mut external_streams =
                                                external_streams.lock().await;
                                            for (addr, (topics, writer)) in
                                                external_streams.iter_mut()
                                            {
                                                if topics.contains(&topic) {
                                                    writer
                                                        .lock()
                                                        .await
                                                        .send(Message::Binary(Msg::build_message(
                                                            Msg::PUBLISH(
                                                                topic.clone(),
                                                                payload.clone(),
                                                            ),
                                                        )))
                                                        .await;
                                                }
                                            }
                                        }
                                    },
                                    None => {
                                        error!("Failed to parse message");
                                        break;
                                    }
                                }
                            }
                            Err(e) => {
                                error!("WebSocket error: {}", e);
                                break;
                            }
                        }
                    }
                }
                Err(e) => {
                    error!("Error accepting connection: {}", e);
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
