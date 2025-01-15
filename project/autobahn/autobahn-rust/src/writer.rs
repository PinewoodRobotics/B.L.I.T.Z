use std::sync::Arc;

use futures_util::{stream::SplitSink, SinkExt};
use tokio::{net::TcpStream, sync::Mutex};
use tokio_tungstenite::{MaybeTlsStream, WebSocketStream};
use tungstenite::Message;

pub struct Writer {
    writer: Box<dyn FnMut(Message) -> futures_util::future::BoxFuture<'static, ()> + Send>,
    id: u32,
}

impl Writer {
    pub fn new(
        writer: Arc<Mutex<SplitSink<WebSocketStream<TcpStream>, Message>>>,
        id: u32,
    ) -> Self {
        Self {
            writer: Box::new(move |msg| {
                let writer = writer.clone();
                Box::pin(async move {
                    writer
                        .lock()
                        .await
                        .send(msg)
                        .await
                        .expect("Failed to send message");
                })
            }),
            id,
        }
    }

    pub fn new_with_connection(
        writer: Arc<Mutex<SplitSink<WebSocketStream<MaybeTlsStream<TcpStream>>, Message>>>,
        id: u32,
    ) -> Self {
        Self {
            writer: Box::new(move |msg| {
                let writer = writer.clone();
                Box::pin(async move {
                    writer
                        .lock()
                        .await
                        .send(msg)
                        .await
                        .expect("Failed to send message");
                })
            }),
            id,
        }
    }

    pub async fn send(&mut self, message: Message) {
        (self.writer)(message).await
    }

    pub fn id(&self) -> u32 {
        self.id
    }
}
