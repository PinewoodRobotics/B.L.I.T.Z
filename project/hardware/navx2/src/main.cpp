#include "Autobahn.h"
#include <iostream>
#include <navXTimeSync/AHRS.h>
#include <proto/project/common/proto/Imu.pb.h>

[[noreturn]] int main() {
    Autobahn autobahn("localhost", "8080");
    autobahn.begin();

    auto ahrs = AHRS("/dev/tty.usbmodem00000000001A1");
    while (true) {
        auto protoImu = Imu();
        protoImu.set_acceleration_x(ahrs.GetRawAccelX());
        protoImu.set_acceleration_y(ahrs.GetRawAccelY());
        protoImu.set_acceleration_z(ahrs.GetRawAccelZ());
        protoImu.set_x(ahrs.GetDisplacementX());
        protoImu.set_y(ahrs.GetDisplacementY());
        protoImu.set_z(ahrs.GetDisplacementZ());
        protoImu.set_pitch(ahrs.GetPitch());
        protoImu.set_yaw(ahrs.GetYaw());
        protoImu.set_roll(ahrs.GetRoll());
        protoImu.set_timestamp(ahrs.GetLastSensorTimestamp());

        autobahn.publish("navx2/imu", protoImu.SerializeAsString());
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    return 0;
}