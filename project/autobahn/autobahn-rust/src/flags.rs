use tungstenite::Bytes;

// TODO1: add proto-type handing where first byte is the type
pub enum MessageFlags {
    SUBSCRIBE, //= (String /*the topic*/), // TODO2: add topic
    UNSUBSCRIBE,
}

impl MessageFlags {
    pub fn get_flag(data: &Bytes) -> Option<Self> {
        if data.starts_with(b"SUBSCRIBE") {
            Some(Self::SUBSCRIBE)
        } else if data.starts_with(b"UNSUBSCRIBE") {
            Some(Self::UNSUBSCRIBE)
        } else {
            None
        }
    }

    pub fn get_topic(data: &Bytes) -> Option<String> {
        if data.starts_with(b"SUBSCRIBE") {
            String::from_utf8(data[9..].to_vec()).ok()
        } else if data.starts_with(b"UNSUBSCRIBE") {
            String::from_utf8(data[11..].to_vec()).ok()
        } else {
            None
        }
    }
}
