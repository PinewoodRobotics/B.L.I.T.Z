#ifndef VECTOR3_H
#define VECTOR3_H

#include <cmath>

class Vec3 {
 public:
  Vec3(float x, float y, float z) {
    this->x = x;
    this->y = y;
    this->z = z;
  }

  Vec3() : x(0), y(0), z(0) {}

  Vec3 normalized() const {
    float length = sqrt(x * x + y * y + z * z);
    if (length > 0) {
      return Vec3(x / length, y / length, z / length);
    }
    return *this;
  }

  float dot(const Vec3& other) const {
    return x * other.x + y * other.y + z * other.z;
  }

  Vec3 cross(const Vec3& other) const {
    return Vec3(y * other.z - z * other.y, z * other.x - x * other.z,
                x * other.y - y * other.x);
  }

  Vec3 operator-(const Vec3& other) const {
    return Vec3(x - other.x, y - other.y, z - other.z);
  }

  Vec3 operator-() const { return Vec3(-x, -y, -z); }

  float x;
  float y;
  float z;
};

#endif  // VECTOR3_H
