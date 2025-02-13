use bytes::{Buf, BufMut, Bytes, BytesMut};

// TODO1: add proto-type handing where first byte is the type
pub enum Msg {
    SUBSCRIBE(String), //= (String /*the topic*/), // TODO2: add topic                              || flag: 0x01
    UNSUBSCRIBE(String), //= (String /*the topic*/), // TODO2: add topic                            || flag: 0x02
    PUBLISH(String, Bytes), //= (String /*the topic*/, Bytes /*the payload*/), // TODO2: add topic  || flag: 0x03
}

//  Message:
// [flag] [length] [topic] [length] [payload]

impl Msg {
    pub fn parse_message(data: Bytes) -> Option<Self> {
        if data.is_empty() {
            return None;
        }

        let mut buf = data;
        let flag = buf.get_u8();
        let topic_len = buf.get_u32();
        let topic = String::from_utf8(buf.copy_to_bytes(topic_len as usize).to_vec()).ok()?;

        match flag {
            0x01 => Some(Self::SUBSCRIBE(topic)),
            0x02 => Some(Self::UNSUBSCRIBE(topic)),
            0x03 => {
                let payload_len = buf.get_u32();
                let payload = buf.copy_to_bytes(payload_len as usize);
                Some(Self::PUBLISH(topic, payload.into()))
            }
            _ => None,
        }
    }

    pub fn build_message(flag: Msg) -> Bytes {
        let flag_bytes = Self::get_flag(&flag);
        if let Msg::PUBLISH(topic, payload) = flag {
            let mut buf = BytesMut::new();
            buf.put_u8(flag_bytes);
            buf.put_u16(topic.len() as u16);
            buf.put_slice(topic.as_bytes());
            buf.put_slice(&payload);
            buf.freeze()
        } else {
            Bytes::new()
        }
    }

    pub fn get_flag(message: &Msg) -> u8 {
        match message {
            Msg::SUBSCRIBE(_) => 0x01,
            Msg::UNSUBSCRIBE(_) => 0x02,
            Msg::PUBLISH(_, _) => 0x03,
        }
    }
}
