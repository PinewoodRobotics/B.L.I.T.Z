use config::Config;
use flags::Msg;
use futures_util::StreamExt;
use log::{debug, error, info};
use rand::Rng;
use std::collections::HashSet;
use std::env;
use std::sync::Arc;
use std::{collections::HashMap, fs};
use tokio::net::TcpListener;
use tokio::sync::Mutex;
use tokio_tungstenite::{accept_async, connect_async, tungstenite::protocol::Message};
use tungstenite::Bytes;
use writer::Writer;

mod config;
mod flags;
mod writer;

#[tokio::main]
async fn main() {
    let args: Vec<String> = env::args().collect();
    let config_path = if args.len() >= 3 && args[1] == "--config" {
        &args[2]
    } else {
        "config.toml"
    };

    let toml_content =
        fs::read_to_string(config_path).expect(&format!("Failed to read {}", config_path));
    let config: Config =
        toml::from_str(&toml_content).expect(&format!("Failed to parse {}", config_path));
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
    let external_streams: Arc<Mutex<HashMap<String, (HashSet<String>, Arc<Mutex<Writer>>)>>> =
        Arc::new(Mutex::new(HashMap::new()));
    let subscribers: Arc<Mutex<HashMap<String, Vec<Arc<Mutex<Writer>>>>>> =
        Arc::new(Mutex::new(HashMap::new()));

    for (name, other) in config.others {
        let external_streams = external_streams.clone();
        tokio::spawn(async move {
            let url = format!("ws://{}:{}", other.ip_addr_v4, other.port);
            loop {
                match connect_async(url.clone()).await {
                    Ok((ws_stream, _)) => {
                        let mut external_streams = external_streams.lock().await;
                        let (writer, mut read) = ws_stream.split();
                        external_streams.insert(
                            other.ip_addr_v4.clone(),
                            (
                                HashSet::new(),
                                Arc::new(Mutex::new(Writer::new_with_connection(
                                    Arc::new(Mutex::new(writer)),
                                    0,
                                ))),
                            ),
                        );
                        drop(external_streams);

                        while let Some(msg) = read.next().await {
                            match msg {
                                Ok(_) => {
                                    debug!("Received message from external stream");
                                } // Handle messages if needed
                                Err(e) => {
                                    error!("Connection error with {}: {}. Will retry...", url, e);
                                    break; // Break inner loop to trigger reconnection
                                }
                            }
                        }
                    }
                    Err(e) => {
                        error!(
                            "Failed to connect to {}: {}. Retrying in 5 seconds...",
                            url, e
                        );
                        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                        continue;
                    }
                }
            }
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

                    // Keep track of this client's subscriptions
                    let mut client_topics: HashSet<String> = HashSet::new();

                    while let Some(msg) = read.next().await {
                        debug!("Received message from client");
                        match msg {
                            Ok(Message::Close(_)) => {
                                info!("Client closed connection gracefully");
                                cleanup_subscriptions(&subscribers, &client_topics, id).await;
                                break;
                            }
                            Ok(Message::Ping(_)) => {}
                            Ok(msg) => {
                                let binary = msg.into_data();
                                debug!(
                                    "Received message of length: {} with data: {:?}",
                                    binary.len(),
                                    &binary
                                );
                                match Msg::parse_message(binary.clone()) {
                                    Some(msg_type) => match msg_type {
                                        Msg::SUBSCRIBE(topic) => {
                                            client_topics.insert(topic.clone()); // Track subscription
                                            debug!("SUBSCRIBE: {}", topic);
                                            let addr = peer_addr.ip().to_string();
                                            if external_streams.lock().await.contains_key(&addr) {
                                                debug!("SUBSCRIBE EXTERNAL: {} {}", topic, addr);
                                                let mut external_streams =
                                                    external_streams.lock().await;
                                                let stream =
                                                    external_streams.get_mut(&addr).unwrap();
                                                stream.0.insert(topic);
                                            } else {
                                                let mut subscribers = subscribers.lock().await;
                                                subscribers
                                                    .entry(topic.clone())
                                                    .or_insert_with(Vec::new)
                                                    .push(Arc::new(Mutex::new(Writer::new(
                                                        write.clone(),
                                                        id,
                                                    ))));

                                                // Send to all externals the subscription message
                                                let mut external_streams =
                                                    external_streams.lock().await;
                                                for (addr, (topics, writer)) in
                                                    external_streams.iter_mut()
                                                {
                                                    debug!("Sending SUBSCRIBE to {}", addr);
                                                    writer
                                                        .lock()
                                                        .await
                                                        .send(Message::Binary(Msg::build_message(
                                                            Msg::SUBSCRIBE(topic.clone()),
                                                        )))
                                                        .await;
                                                }
                                                debug!(
                                                    "Topic {} now has {} subscribers",
                                                    topic,
                                                    subscribers.get_mut(&topic).unwrap().len()
                                                );
                                            }
                                        }
                                        Msg::UNSUBSCRIBE(topic) => {
                                            client_topics.remove(&topic); // Remove from tracking
                                            debug!("UNSUBSCRIBE: {}", topic);
                                            let addr = peer_addr.ip().to_string();
                                            if external_streams.lock().await.contains_key(&addr) {
                                                debug!("UNSUBSCRIBE EXTERNAL: {}", topic);
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
                                            // Handle local subscribers
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
                                            drop(subscribers); // Release subscribers lock

                                            // Handle external streams - collect targets first
                                            let external_streams = external_streams.clone();
                                            let mut targets = Vec::new();
                                            {
                                                let external_streams =
                                                    external_streams.lock().await;
                                                for (addr, (topics, writer)) in
                                                    external_streams.iter()
                                                {
                                                    if topics.contains(&topic) {
                                                        targets.push(writer.clone());
                                                    }
                                                }
                                            } // Lock is released here

                                            // Send messages without holding the lock
                                            for writer in targets {
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
                                    },
                                    None => {
                                        error!("Failed to parse message");
                                        cleanup_subscriptions(&subscribers, &client_topics, id)
                                            .await;
                                        break;
                                    }
                                }
                            }
                            Err(e) => {
                                error!("WebSocket error: {}. Cleaning up subscriptions.", e);
                                cleanup_subscriptions(&subscribers, &client_topics, id).await;
                                break;
                            }
                        }
                    }

                    // Clean up if the loop ends (connection dropped)
                    cleanup_subscriptions(&subscribers, &client_topics, id).await;
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

async fn cleanup_subscriptions(
    subscribers: &Arc<Mutex<HashMap<String, Vec<Arc<Mutex<Writer>>>>>>,
    client_topics: &HashSet<String>,
    client_id: u32,
) {
    let mut subscribers = subscribers.lock().await;
    for topic in client_topics {
        if let Some(topic_subscribers) = subscribers.get_mut(topic) {
            let mut i = 0;
            while i < topic_subscribers.len() {
                let subscriber_id = topic_subscribers[i].lock().await.id();
                if subscriber_id == client_id {
                    topic_subscribers.swap_remove(i);
                } else {
                    i += 1;
                }
            }
        }
    }
}
