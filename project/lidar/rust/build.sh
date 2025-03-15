g++ -shared -o libunitree_lidar_sdk_wrapper.so -fPIC src/cpp/unitree_lidar_sdk_wrapper.cpp -I./include -L./lib -lunitree_lidar_sdk -std=c++11

mv libunitree_lidar_sdk_wrapper.so lib/

cargo build --release