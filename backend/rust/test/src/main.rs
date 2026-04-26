use rand::rng;

fn main() {
    let mut rng = rand::rng();
    println!("Random number: {:?}", rng.reseed().unwrap());
}
